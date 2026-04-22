# T-049 · WAR Easy Wins — Security & Cost

**Статус:** 🔜 TODO  
**Пріоритет:** 🟡 MEDIUM (post-hackathon, ~4h total)  
**WAR gaps:** SE:10 P:90, SE:03, SE:08, SE:09, CO:04  
**Архітектура:** [02-architecture.md §8.16](../02-architecture.md)

---

## Мета

Закрити 5 lightweight WAR gaps через зміни в Bicep та Entra ID — без зміни application logic. Кожен item ~30–60 хвилин.

---

## Subtasks

### 1. SE:10 — Microsoft Defender for Cloud (~1h)

**Що:** Увімкнути Defender plans для App Service + Key Vault у Bicep.

```bicep
// infra/modules/security.bicep (новий модуль або в main.bicep)
resource defenderAppService 'Microsoft.Security/pricings@2023-01-01' = {
  name: 'AppServices'
  properties: {
    pricingTier: 'Standard'
  }
}

resource defenderKeyVault 'Microsoft.Security/pricings@2023-01-01' = {
  name: 'KeyVaults'
  properties: {
    pricingTier: 'Standard'
  }
}
```

**DoD:** `az security pricing list` показує `Standard` для AppServices та KeyVaults.

---

### 2. SE:03 — Resource tags (~30min)

**Що:** Додати уніфіковані теги на всі Bicep modules.

```bicep
// infra/main.bicep — додати параметр
param tags object = {
  environment: 'dev'
  project: 'sentinel-intelligence'
  team: 'hackathon-2026'
  costCenter: 'engineering'
  dataClassification: 'confidential'
}
```

Передати `tags: tags` у всі module виклики: `functionApp`, `cosmosDb`, `serviceBus`, `aiSearch`, `storage`, `keyVault`, `signalR`.

**DoD:** `az resource list --tag project=sentinel-intelligence` повертає всі 7+ ресурсів.

---

### 3. SE:08 — Block legacy auth (~30min)

**Що:** CA policy в Entra ID — block legacy authentication protocols.

```
Entra ID → Security → Conditional Access → New policy
  Name: "Block Legacy Auth — Sentinel Intelligence"
  Users: sg-sentinel-operators, sg-sentinel-qa-managers, sg-sentinel-auditors, sg-sentinel-it-admin
  Conditions: Client apps → Legacy authentication clients
  Grant: Block access
  State: On
```

Або через Bicep (якщо є Entra ID P1+):
```bicep
// Потребує Microsoft Graph API / bicep-extensions — або ручна конфігурація
```

**DoD:** Спроба auth з Basic credentials → 400 Block.

---

### 4. SE:09 — Secret rotation (~1h)

**Що:** Увімкнути Key Vault rotation policy для всіх secrets.

```bicep
// infra/modules/keyvault.bicep — для кожного secret
resource secretRotation 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  // ...
  properties: {
    // ...
    attributes: {
      enabled: true
      exp: dateTimeToEpoch(dateTimeAdd(utcNow(), 'P90D')) // 90 днів
    }
  }
}
```

Додатково: Event Grid subscription `Microsoft.KeyVault.SecretNearExpiry` → Function App alert або Logic App notification.

**DoD:** KV secrets мають `expiresOn` = now + 90 days; Event Grid alert спрацьовує за 30 днів до expiry.

---

### 5. CO:04 — Cost budget alerts (~30min)

**Що:** Azure Budget $100/місяць з alert при 80% та 100%.

```bicep
// infra/modules/budget.bicep
resource budget 'Microsoft.Consumption/budgets@2023-05-01' = {
  name: 'sentinel-monthly-budget'
  properties: {
    category: 'Cost'
    amount: 100
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: '2026-05-01'
      endDate: '2027-05-01'
    }
    notifications: {
      actual_80: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 80
        contactEmails: ['team@example.com']
      }
      actual_100: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 100
        contactEmails: ['team@example.com']
      }
    }
  }
}
```

**DoD:** `az consumption budget list` показує бюджет; тестовий alert отриманий на email.

---

## Definition of Done

- [ ] Defender for Cloud увімкнено (AppService + KeyVault plans = Standard)
- [ ] Теги на всіх ресурсах (≥5 tags per resource)
- [ ] CA policy blocking legacy auth — On
- [ ] KV secrets мають expiry + Event Grid near-expiry alert
- [ ] Azure Budget $100/місяць з 80%+100% alerts

## Estimated effort

~4 години (1 dev session)

## Dependencies

- Доступ до Azure subscription з Owner/Contributor правами
- Entra ID з правами Global Admin / Security Admin (для CA policies)
- Bicep redeploy після змін infra
