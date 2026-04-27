# T-038 · Security Layer (Key Vault, VNet, Managed Identities)

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

**Priority:** 🟡 MEDIUM
**Status:** 🔜 TODO
**Gap:** Gap #2 Security ✅

---

## Goal

Close Gap #2: Azure Key Vault + Managed Identities for all Functions + VNet Private Endpoints for Cosmos DB and AI Search.

---

## Checklist

### Key Vault
- [ ] Azure Key Vault provisioned (`infra/modules/key-vault.bicep`)
- [ ] All secrets migrated from `.env` / local.settings.json to Key Vault
- [ ] Key Vault references in `local.settings.json`: `@Microsoft.KeyVault(SecretUri=...)`
- [ ] Azure Functions use `DefaultAzureCredential` to read Key Vault (no plain secrets in env)

### Managed Identities
- [ ] System-assigned Managed Identity enabled on Azure Functions app
- [ ] MI granted: `Key Vault Secrets User` on Key Vault
- [ ] MI granted: `Cosmos DB Built-in Data Contributor` on Cosmos DB
- [ ] MI granted: `Search Index Data Contributor` on AI Search
- [ ] MI granted: `Azure Service Bus Data Receiver` + `Data Sender` on Service Bus namespace

### Network (VNet)
- [ ] VNet created with 2 subnets: `functions-subnet`, `private-endpoints-subnet`
- [ ] Functions App VNet integrated into `functions-subnet`
- [ ] Private Endpoint for Cosmos DB in `private-endpoints-subnet`
- [ ] Private Endpoint for AI Search in `private-endpoints-subnet`
- [ ] Private Endpoint for Service Bus in `private-endpoints-subnet`
- [ ] Private DNS Zones configured for auto-resolution

### Data
- [ ] Cosmos DB: encryption at rest (default Azure-managed)
- [ ] Blob Storage: private endpoint, no public access
- [ ] HTTPS-only enforced on Static Web App + Functions
- [ ] TLS-only enforced: Cosmos DB (`minimalTlsVersion: 'Tls12'`), Service Bus (transport security), AI Search (HTTPS only)

### Audit Log Retention (21 CFR Part 11)
- [ ] Cosmos DB `audit-log` container: `defaultTtl = -1` (no expiry = immutable retention)
- [ ] Cosmos DB `audit-log` container: analytical store enabled (read-only historical queries)
- [ ] Log Analytics workspace: retention policy ≥ 90 days (regulatory minimum)
- [ ] App Insights: data retention set to 90 days

### Data Classification
- [ ] SOP/BPR documents in Blob Storage: access restricted to `SentinelResearcher` Managed Identity only (no public access, no SAS tokens)
- [ ] Cosmos DB `incidents` container: RBAC — operators see own incidents only (server-side filter on `assigned_to`); already implemented in T-035 but document here
- [ ] Cosmos DB `audit-log` container: read-only for `Auditor` role; no write/delete via API

---

## Files

```
infra/
  modules/
    key-vault.bicep
    vnet.bicep
    private-endpoints.bicep
    managed-identity.bicep   # role assignments
```

---

## Definition of Done

- [ ] Key Vault provisioned; Functions read secrets via Key Vault references (not env vars)
- [ ] Managed Identity has minimum required roles on all services
- [ ] `az network private-endpoint list` shows 3 endpoints (Cosmos, Service Bus, AI Search)
- [ ] `curl http://cosmos-...documents.azure.com` from public IP → connection refused
- [ ] Cosmos `audit-log` container has `defaultTtl = -1` (check in the portal)
- [ ] Log Analytics retention = 90 days

## Note for hackathon

For demo purposes: VNet + Private Endpoints can be simplified or skipped if causing connectivity issues. Key Vault + Managed Identities + Retention Policy are the **minimum required** for Gap #2 and 21 CFR Part 11 compliance story.
