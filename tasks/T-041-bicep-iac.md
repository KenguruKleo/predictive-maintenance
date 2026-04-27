# T-041 · Bicep IaC Templates

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

**Priority:** 🟠 HIGH
**Status:** ✅ DONE (April 17, 2026, updated April 19, 2026)
**Gap:** Gap #1 (Track A) + Gap #6 (IaC) ✅

> **What is deployed:** 7 resources in `ODL-GHAZ-2177134` (Sweden Central): Storage, Log Analytics, App Insights, Cosmos DB (5 containers), Service Bus (`alert-queue`), App Service Plan (Y1), Azure Functions (Python 3.11).
> **What is not deployed:** AI Search, SignalR, Key Vault, Static Web App, Azure AI Foundry - see T-037, T-030, T-038, T-032, T-025.
> **Operational update (April 19, 2026):** Added `AzureWebJobsFeatureFlags=EnableWorkerIndexing` to `functions.bicep` for runtime parity between local/Core Tools and Azure host.

---

## Goal

Bicep templates for repeatable provisioning of all Azure resources. Demonstrates IaC capability for hackathon judges.

---

## Structure

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

- [x] `az bicep build --file infra/main.bicep` succeeds (no errors)
- [x] `az deployment group what-if` dry run shows all expected resources
- [x] Full deploy creates all resources in Azure (verified against resource list)
- [x] `dev.bicepparam` has all required parameters with sensible defaults
- [ ] Remaining modules: AI Search, SignalR, Key Vault, Static Web App, Azure AI Foundry (T-037, T-030, T-038, T-032, T-025)
- [ ] `prod.bicepparam` parameters file aligned
