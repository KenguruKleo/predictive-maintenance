# T-048 · Privileged Access Control: JIT / Conditional Access (SE:05)

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🟡 MEDIUM (post-hackathon)  
**Статус:** 🔜 TODO  
**WAR Gap:** SE:05 P:100 / P:95  
**Потребує:** Entra ID P2 ліцензії (недоступні в sandbox)

---

## Мета

Закрити SE:05 — JIT (Just-In-Time) для привілейованих ролей через Azure PIM + Conditional Access Policies для MFA enforcement. Дизайн задокументований у §8.15 02-architecture.md.

**Хакатонний компроміс:** Entra ID P2 (CA + PIM) — недоступна в sandbox. Реалізовано: RBAC 5 ролей + `assignment_required = true` на App Registration (P1 достатньо). Решта — post-hackathon.

---

## Definition of Done

- [ ] Entra ID Security Groups створені (4 групи)
- [ ] App Registration: `assignment_required = true`, всі 4 групи assigned
- [ ] Conditional Access Policy 1: MFA для всіх Sentinel Intelligence users
- [ ] Conditional Access Policy 2: Block non-EU countries
- [ ] Conditional Access Policy 3: MFA + compliant device для IT Admin
- [ ] Azure PIM: IT Admin → eligible Contributor (не постійна роль)
- [ ] Azure PIM: QA Manager → eligible для PIM approvals (optional)
- [ ] Lifecycle Workflows: onboarding (auto MFA) + offboarding (auto group removal)
- [ ] Тест: IT Admin намагається активувати привілей без PIM → заблоковано

---

## Архітектура

### Entra ID Security Groups

```
sg-sentinel-operators     → App Assignment + operator role claim
sg-sentinel-qa-managers   → App Assignment + qa-manager role claim
sg-sentinel-auditors      → App Assignment + auditor + maint-tech role claims
sg-sentinel-it-admin      → App Assignment + it-admin role claim (PIM eligible)
```

Переваги груп над прямими user assignments:
- Onboarding = додати в групу (один крок)
- Offboarding = видалити з груп (Lifecycle Workflow)
- Audit = "хто в якій групі" — єдиний source of truth

### Conditional Access Policies

```
Policy 1: "Sentinel — Require MFA — All Users"
  Users:     All assigned to SPA App Registration (1bdb80fb-...)
  Apps:      Sentinel Intelligence SPA
  Condition: —
  Grant:     Require multi-factor authentication
  Session:   Sign-in frequency 8h; Persistent browser: No

Policy 2: "Sentinel — Block Non-EU Countries"
  Users:     All
  Apps:      Sentinel Intelligence SPA + any backend API
  Condition: Named locations NOT IN [EU + UA]
  Grant:     Block
  Note:      GMP pharma — GxP data не повинні покидати регіон

Policy 3: "Sentinel — IT Admin — Compliant Device"
  Users:     sg-sentinel-it-admin
  Apps:      All
  Grant:     Require MFA + Require compliant/Hybrid Azure AD joined device
```

### Azure PIM — JIT для IT Admin

```
Поточна (хакатон): IT Admin → постійна роль → завжди активна

Після PIM:
  IT Admin → eligible Contributor → щоб отримати доступ:
    1. Відкрити PIM Portal → "Activate role"
    2. Вибрати тривалість (max 4h)
    3. Написати justification ("Deploy hotfix для QMS connector")
    4. Отримати схвалення QA Manager (якщо approver налаштований)
    5. Роль активна на вказаний час
    6. Після закінчення → автоматично деактивується

  Оперативні ролі (operator, maint-tech, auditor) → залишаються постійними
  (ці ролі не дають доступу до інфраструктури, тільки до даних через API)
```

### Lifecycle Workflows (Entra ID → Identity Governance)

```
Onboarding workflow:
  Trigger: user added to sg-sentinel-* group
  Actions:
    1. Send welcome email з MFA setup link
    2. Auto-assign TAP (Temporary Access Pass) на 24h
    3. Notify IT Admin

Offboarding workflow:
  Trigger: user's department/manager removed (HR system integration)
  Actions:
    1. Remove from all sg-sentinel-* groups
    2. Revoke all active sessions (Revoke-AzureADUserAllRefreshToken)
    3. Disable account після 30 днів
    4. Notify QA Manager + IT Admin
```

---

## Кроки реалізації

### 1. Створити Security Groups (Azure CLI)

```bash
# Оператори
az ad group create \
  --display-name "sg-sentinel-operators" \
  --mail-nickname "sg-sentinel-operators"

# QA Managers
az ad group create \
  --display-name "sg-sentinel-qa-managers" \
  --mail-nickname "sg-sentinel-qa-managers"

# Auditors (отримують і auditor, і maint-tech доступ)
az ad group create \
  --display-name "sg-sentinel-auditors" \
  --mail-nickname "sg-sentinel-auditors"

# IT Admin (PIM eligible)
az ad group create \
  --display-name "sg-sentinel-it-admin" \
  --mail-nickname "sg-sentinel-it-admin"
```

### 2. App Registration — assignment required

```bash
# Встановити assignment_required = true (тільки assigned users можуть логінитись)
az ad app update \
  --id 1bdb80fb-950c-45b8-be9c-8f8a7fa26ca9 \
  --set "requiredResourceAccess=[]"  # якщо не встановлено

# Через Portal: Enterprise Application → Properties → Assignment required: YES
# Або через Microsoft Graph:
# PATCH /servicePrincipals/{id}
# { "appRoleAssignmentRequired": true }

# Assign groups до App Registration:
az ad group show --group "sg-sentinel-operators" --query id -o tsv
# → {group-id}
# PATCH /servicePrincipals/{sp-id}/appRoleAssignedTo
# (через Graph API або Portal: Enterprise Apps → Users and Groups → Add)
```

### 3. Conditional Access — Microsoft Graph (Bicep не підтримує)

CA policies не можна задеплоїти через Bicep — потрібен Microsoft Graph API або Portal.

```bash
# Приклад через Graph API (потрібен Global Admin або CA Administrator)
# POST https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies
# {
#   "displayName": "Sentinel — Require MFA — All Users",
#   "state": "enabled",
#   "conditions": {
#     "applications": { "includeApplications": ["1bdb80fb-..."] },
#     "users": { "includeGroups": ["{sg-sentinel-operators-id}", ...] }
#   },
#   "grantControls": {
#     "operator": "OR",
#     "builtInControls": ["mfa"]
#   }
# }
```

Альтернатива: Terraform `azuread_conditional_access_policy` (AzureAD provider).

### 4. Azure PIM — eligible assignment

```bash
# Через Portal: Entra ID → Identity Governance → Privileged Identity Management
# → Azure Resources → Select subscription → Role assignments
# → Add assignments → Role: Contributor → Principal: sg-sentinel-it-admin
# → Assignment type: Eligible (не Active)
# → Duration: Permanent eligible (activating JIT; max active: 4h)

# Або Bicep (preview API):
# Microsoft.Authorization/roleEligibilityScheduleRequests@2022-04-01-preview
```

---

## Тестування

| Тест | Очікуваний результат |
|---|---|
| Login як operator (без MFA setup) | Заблоковано CA Policy 1 → redirect to MFA setup |
| Login з IP non-EU | Заблоковано CA Policy 2 |
| IT Admin без PIM activation → спроба видалити ресурс | 403 Forbidden (no active role) |
| IT Admin → PIM activate → Contributor active 4h → дія | Успішно; після 4h → знову 403 |
| User видалений з групи | Негайно втрачає доступ (Revoke sessions) |

---

## Файли для зміни

| Файл | Зміна |
|---|---|
| `scripts/setup_entra.sh` | Додати команди створення Security Groups + App Registration assignment |
| `infra/main.bicep` | Коментар: CA + PIM не через Bicep — посилання на цю task |
| `docs/entra-role-assignment.md` | Оновити з новою груповою моделлю + PIM інструкцією |

---

## Ризики та залежності

- **Entra ID P2 ліцензія** — потрібна для CA + PIM. У sandbox `ODL-GHAZ-2177134` — недоступна. Потрібна продакшн Entra ID.
- **Global Admin або CA Administrator** — потрібні для створення CA policies. Звичайний Contributor не може.
- **MFA rollout** — всі поточні тестові облікові записи треба зареєструвати для MFA перед увімкненням Policy 1.
- **Terraform альтернатива** — якщо треба IaC для CA policies, `azuread_conditional_access_policy` resource у Terraform; Bicep поки не підтримує.
