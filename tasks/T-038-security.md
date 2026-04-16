# T-038 · Security Layer (Key Vault, VNet, Managed Identities)

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🟡 MEDIUM  
**Статус:** 🔜 TODO  
**Gap:** Gap #2 Security ✅

---

## Мета

Закрити Gap #2: Azure Key Vault + Managed Identities для всіх Functions + VNet Private Endpoints для Cosmos DB та AI Search.

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

## Note for hackathon

Para demo purposes: VNet + Private Endpoints can be simplified or skipped if causing connectivity issues. Key Vault + Managed Identities are the **minimum required** for Gap #2.
