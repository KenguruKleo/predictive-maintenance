# T-049 · WAR Easy Wins — Security & Cost

**Status:** 🔜 TODO
**Priority:** 🟡 MEDIUM (post-hackathon, ~4h total)
**WAR gaps:** SE:10 P:90, SE:03, SE:08, SE:09, CO:04  
**Architecture:** [02-architecture.md §8.16](../02-architecture.md)

---

## Goal

Close 5 lightweight WAR gaps due to changes in Bicep and Entra ID — without changing application logic. Each item ~30–60 minutes.

---

## Subtasks

### 1. SE:10 — Microsoft Defender for Cloud (~1h)

**What:** Enable Defender plans for App Service + Key Vault in Bicep.

```bicep
// infra/modules/security.bicep (new module or in main.bicep)
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

**DoD:** `az security pricing list` shows `Standard` for AppServices and KeyVaults.

---

### 2. SE:03 — Resource tags (~30min)

**What:** Add unified tags to all Bicep modules.

```bicep
// infra/main.bicep — add parameter
param tags object = {
  environment: 'dev'
  project: 'sentinel-intelligence'
  team: 'hackathon-2026'
  costCenter: 'engineering'
  dataClassification: 'confidential'
}
```

Pass `tags: tags` to all module calls: `functionApp`, `cosmosDb`, `serviceBus`, `aiSearch`, `storage`, `keyVault`, `signalR`.

**DoD:** `az resource list --tag project=sentinel-intelligence` returns all 7+ resources.

---

### 3. SE:08 — Block legacy auth (~30min)

**What:** CA policy in Entra ID — block legacy authentication protocols.

```
Entra ID → Security → Conditional Access → New policy
  Name: "Block Legacy Auth — Sentinel Intelligence"
  Users: sg-sentinel-operators, sg-sentinel-qa-managers, sg-sentinel-auditors, sg-sentinel-it-admin
  Conditions: Client apps → Legacy authentication clients
  Grant: Block access
  State: On
```

Or via Bicep (if there is an Entra ID P1+):
```bicep
// Requires Microsoft Graph API / bicep-extensions — or manual configuration
```

**DoD:** Attempting auth with Basic credentials → 400 Block.

---

### 4. SE:09 — Secret rotation (~1h)

**What:** Enable Key Vault rotation policy for all secrets.

```bicep
// infra/modules/keyvault.bicep — for each secret
resource secretRotation 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  // ...
  properties: {
    // ...
    attributes: {
      enabled: true
exp: dateTimeToEpoch(dateTimeAdd(utcNow(), 'P90D')) // 90 days
    }
  }
}
```

Additionally: Event Grid subscription `Microsoft.KeyVault.SecretNearExpiry` → Function App alert or Logic App notification.

**DoD:** KV secrets have `expiresOn` = now + 90 days; Event Grid alert is triggered 30 days before expiry.

---

### 5. CO:04 — Cost budget alerts (~30min)

**What:** Azure Budget $100/month with alert at 80% and 100%.

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

**DoD:** `az consumption budget list` shows the budget; test alert received by email.

---

## Definition of Done

- [ ] Defender for Cloud enabled (AppService + KeyVault plans = Standard)
- [ ] Tags on all resources (≥5 tags per resource)
- [ ] CA policy blocking legacy auth — On
- [ ] KV secrets have expiry + Event Grid near-expiry alert
- [ ] Azure Budget $100/month with 80%+100% alerts

## Estimated effort

~4 hours (1 dev session)

## Dependencies

- Access to Azure subscription with Owner/Contributor rights
- Entra ID with Global Admin / Security Admin rights (for CA policies)
- Bicep redeploy after infra changes
