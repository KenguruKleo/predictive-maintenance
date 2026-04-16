# T-041 · Bicep IaC Templates

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🟠 HIGH  
**Статус:** 🔜 TODO  
**Gap:** Gap #1 (Track A) + Gap #6 (IaC) ✅

---

## Мета

Bicep templates для repeatable provisioning всіх Azure ресурсів. Demonstrates IaC capability для hackathon judges.

---

## Структура

```
infra/
  main.bicep                    # Top-level: calls all modules, sets params
  parameters/
    dev.bicepparam               # Dev environment parameters
    prod.bicepparam              # Production parameters
  modules/
    cosmos-db.bicep              # Cosmos DB account + database + 5 containers
    ai-search.bicep              # AI Search service + 4 indexes
    service-bus.bicep            # Service Bus namespace + alert-queue
    functions.bicep              # Azure Functions app + App Service Plan
    storage.bicep                # Storage account (Durable + Blob)
    signalr.bicep                # SignalR service
    key-vault.bicep              # Key Vault + secrets references
    static-web-app.bicep         # Static Web App for React frontend
    app-insights.bicep           # App Insights + Log Analytics workspace
    vnet.bicep                   # VNet + subnets (optional for hackathon)
```

---

## main.bicep outline

```bicep
targetScope = 'resourceGroup'

param location string = resourceGroup().location
param environmentName string
param projectName string = 'sentinel-intelligence'

var prefix = '${projectName}-${environmentName}'

module cosmos 'modules/cosmos-db.bicep' = {
  name: 'cosmos'
  params: { prefix: prefix, location: location }
}

module aiSearch 'modules/ai-search.bicep' = {
  name: 'ai-search'
  params: { prefix: prefix, location: location }
}

module serviceBus 'modules/service-bus.bicep' = {
  name: 'service-bus'
  params: { prefix: prefix, location: location }
}

module functions 'modules/functions.bicep' = {
  name: 'functions'
  params: {
    prefix: prefix
    location: location
    cosmosConnectionString: cosmos.outputs.connectionString
    serviceBusNamespace: serviceBus.outputs.namespace
    aiSearchEndpoint: aiSearch.outputs.endpoint
    signalRConnectionString: signalr.outputs.connectionString
  }
}

// ... etc
```

---

## Deploy commands

```bash
# Provision all resources
az deployment group create \
  --resource-group rg-sentinel-intelligence-dev \
  --template-file infra/main.bicep \
  --parameters infra/parameters/dev.bicepparam

# Validate (no deploy)
az bicep build --file infra/main.bicep
az deployment group what-if \
  --resource-group rg-sentinel-intelligence-dev \
  --template-file infra/main.bicep \
  --parameters infra/parameters/dev.bicepparam
```

---

## Definition of Done

- [ ] `az bicep build --file infra/main.bicep` succeeds (no errors)
- [ ] `az deployment group what-if` dry run shows all expected resources
- [ ] Full deploy creates all resources in Azure (verified against resource list)
- [ ] `dev.bicepparam` + `prod.bicepparam` have all required parameters with sensible defaults
- [ ] README documents how to run deploy commands
