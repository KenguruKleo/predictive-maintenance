# T-048 · Privileged Access Control: JIT / Conditional Access (SE:05)

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

**Priority:** 🟡 MEDIUM (post-hackathon)
**Status:** 🔜 TODO
**WAR Gap:** SE:05 P:100 / P:95  
**Requires:** Entra ID P2 licenses (not available in sandbox)

---

## Goal

Close SE:05 - JIT (Just-In-Time) for privileged roles via Azure PIM + Conditional Access Policies for MFA enforcement. The design is documented in §8.15 02-architecture.md.

**Hackathon Compromise:** Entra ID P2 (CA + PIM) - not available in sandbox. Implemented: RBAC 5 roles + `assignment_required = true` on App Registration (P1 is enough). The rest is post-hackathon.

---

## Definition of Done

- [ ] Entra ID Security Groups created (4 groups)
- [ ] App Registration: `assignment_required = true`, all 4 groups assigned
- [ ] Conditional Access Policy 1: MFA for all Sentinel Intelligence users
- [ ] Conditional Access Policy 2: Block non-EU countries
- [ ] Conditional Access Policy 3: MFA + compliant device for IT Admin
- [ ] Azure PIM: IT Admin → eligible Contributor (not permanent role)
- [ ] Azure PIM: QA Manager → eligible for PIM approvals (optional)
- [ ] Lifecycle Workflows: onboarding (auto MFA) + offboarding (auto group removal)
- [ ] Test: IT Admin tries to activate privilege without PIM → blocked

---

## Architecture

### Entra ID Security Groups

```
sg-sentinel-operators     → App Assignment + operator role claim
sg-sentinel-qa-managers   → App Assignment + qa-manager role claim
sg-sentinel-auditors      → App Assignment + auditor + maint-tech role claims
sg-sentinel-it-admin      → App Assignment + it-admin role claim (PIM eligible)
```

Advantages of groups over direct user assignments:
- Onboarding = add to the group (one step)
- Offboarding = remove from groups (Lifecycle Workflow)
- Audit = "who is in which group" — the only source of truth

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
Note: GMP pharma — GxP data should not leave the region

Policy 3: "Sentinel — IT Admin — Compliant Device"
  Users:     sg-sentinel-it-admin
  Apps:      All
  Grant:     Require MFA + Require compliant/Hybrid Azure AD joined device
```

### Azure PIM - JIT for IT Admin

```
Current (hackathon): IT Admin → permanent role → always active

After PIM:
IT Admin → eligible Contributor → to gain access:
1. Open PIM Portal → "Activate role"
2. Choose the duration (max 4h)
3. Write justification ("Deploy hotfix for QMS connector")
4. Get QA Manager approval (if approver is configured)
5. The role is active for the specified time
6. After completion → is automatically deactivated

Operational roles (operator, maint-tech, auditor) → remain permanent
(these roles do not give access to infrastructure, only to data via API)
```

### Lifecycle Workflows (Entra ID → Identity Governance)

```
Onboarding workflow:
  Trigger: user added to sg-sentinel-* group
  Actions:
1. Send welcome email with MFA setup link
2. Auto-assign TAP (Temporary Access Pass) for 24 hours
    3. Notify IT Admin

Offboarding workflow:
  Trigger: user's department/manager removed (HR system integration)
  Actions:
    1. Remove from all sg-sentinel-* groups
    2. Revoke all active sessions (Revoke-AzureADUserAllRefreshToken)
3. Disable account after 30 days
    4. Notify QA Manager + IT Admin
```

---

## Implementation steps

### 1. Create Security Groups (Azure CLI)

```bash
# Operators
az ad group create \
  --display-name "sg-sentinel-operators" \
  --mail-nickname "sg-sentinel-operators"

# QA Managers
az ad group create \
  --display-name "sg-sentinel-qa-managers" \
  --mail-nickname "sg-sentinel-qa-managers"

# Auditors (both auditor and maint-tech get access)
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
# Set assignment_required = true (only assigned users can log in)
az ad app update \
  --id 1bdb80fb-950c-45b8-be9c-8f8a7fa26ca9 \
--set "requiredResourceAccess=[]" # if not set

# Via Portal: Enterprise Application → Properties → Assignment required: YES
# Or via Microsoft Graph:
# PATCH /servicePrincipals/{id}
# { "appRoleAssignmentRequired": true }

# Assign groups to App Registration:
az ad group show --group "sg-sentinel-operators" --query id -o tsv
# → {group-id}
# PATCH /servicePrincipals/{sp-id}/appRoleAssignedTo
# (via Graph API or Portal: Enterprise Apps → Users and Groups → Add)
```

### 3. Conditional Access — Microsoft Graph (Bicep does not support)

CA policies cannot be deployed via Bicep - Microsoft Graph API or Portal is required.

```bash
# Example via Graph API (requires Global Admin or CA Administrator)
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

Alternative: Terraform `azuread_conditional_access_policy` (AzureAD provider).

### 4. Azure PIM — eligible assignment

```bash
# Via Portal: Entra ID → Identity Governance → Privileged Identity Management
# → Azure Resources → Select subscription → Role assignments
# → Add assignments → Role: Contributor → Principal: sg-sentinel-it-admin
# → Assignment type: Eligible (not Active)
# → Duration: Permanent eligible (activating JIT; max active: 4h)

# Or Bicep (preview API):
# Microsoft.Authorization/roleEligibilityScheduleRequests@2022-04-01-preview
```

---

## Testing

| Test | Expected result |
|---|---|
| Login as an operator (without MFA setup) | Blocked CA Policy 1 → redirect to MFA setup |
| Login with IP non-EU | Blocked by CA Policy 2 |
| IT Admin without PIM activation → attempt to delete resource | 403 Forbidden (no active role) |
| IT Admin → PIM activate → Contributor active 4h → action | Successfully; after 4h → again 403 |
| User removed from group | Immediately loses access (Revoke sessions) |

---

## Files to change

| File | Change |
|---|---|
| `scripts/setup_entra.sh` | Add commands for creating Security Groups + App Registration assignment |
| `infra/main.bicep` | Comment: CA + PIM is not through Bicep - link to this task |
| `docs/entra-role-assignment.md` | Update with new group model + PIM instruction |

---

## Risks and dependencies

- **Entra ID P2 license** — required for CA + PIM. `ODL-GHAZ-2177134` is not available in the sandbox. Entra ID production required.
- **Global Admin or CA Administrator** — required to create CA policies. A regular Contributor cannot.
- **MFA rollout** - All current test accounts must be enrolled for MFA before enabling Policy 1.
- **Terraform alternative** — if you need IaC for CA policies, `azuread_conditional_access_policy` resource in Terraform; Bicep is not yet supported.
