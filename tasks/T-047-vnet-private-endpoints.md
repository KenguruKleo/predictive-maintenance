# T-047 · Network Isolation: VNet / NSGs / Private Endpoints (SE:06)

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

**Priority:** 🟡 MEDIUM (post-hackathon)
**Status:** 🔜 TODO
**WAR Gap:** SE:06 P:90 / P:80 / P:70  
**Depends on:** T-038 (Key Vault), Function App plan → Flex Consumption

---

## Goal

Close SE:06 — complete network isolation of PaaS services. Disable public access to Cosmos DB, AI Search, Service Bus, Storage, Key Vault, Azure OpenAI. All Function App traffic → via VNet.

**Hackathon Compromise:** Consumption plan does not support VNet Integration. In production, we switch to Flex Consumption + PE. The design is documented in §8.15 02-architecture.md.

---

## Definition of Done

- [ ] VNet `vnet-sentinel-intel-dev-{suffix}` is deployed
- [ ] Two subnets: `snet-functions` and `snet-private-endpoints`
- [ ] NSGs on both subnets with a minimum allow-list
- [ ] Function App transferred to **Flex Consumption** plan (supports VNet Integration)
- [ ] VNet Integration on Function App (`vnetRouteAllEnabled = true`)
- [ ] Private Endpoint for each PaaS service in `snet-private-endpoints`
- [ ] Private DNS Zone for each service, bound to VNet
- [ ] `publicNetworkAccess = Disabled` on Cosmos DB, AI Search, Service Bus, Key Vault
- [ ] Function App HTTP trigger remains public (frontend → API)
- [ ] All tests (smoke + E2E) pass after the change

---

## Architecture

```
VNet: vnet-sentinel-intel-dev (10.0.0.0/16)
│
├── snet-functions (10.0.1.0/24)
│   NSG rules:
│     inbound:  allow 443 from Azure (Functions platform)
│     outbound: allow to snet-private-endpoints; allow to AzureCloud:443 (Foundry)
│               deny internet
│   Delegation: Microsoft.App/environments (Flex Consumption)
│   [Function App] — VNet Integration
│
└── snet-private-endpoints (10.0.2.0/24)
    NSG rules:
      inbound:  allow from snet-functions; deny all else
      outbound: allow to internet (updates)
    privateEndpointNetworkPolicies: Disabled
    │
    ├── PE: Cosmos DB       → privatelink.documents.azure.com
    ├── PE: AI Search       → privatelink.search.windows.net
    ├── PE: Service Bus     → privatelink.servicebus.windows.net
    ├── PE: Storage Blob    → privatelink.blob.core.windows.net
    ├── PE: Key Vault       → privatelink.vaultcore.azure.net
    └── PE: Azure OpenAI    → privatelink.openai.azure.com
```

**What remains public (and rightly so):**
- Static Web App — public (browser → SPA)
- Function App HTTP trigger — public (only for SWA + RBAC-protected)
- SignalR negotiate endpoint — public (via Function trigger)

---

## Checklist details

### 1. Bicep — new module `infra/modules/network.bicep`

```bicep
// VNet + 2 subnets + NSGs
resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: 'vnet-${projectName}-${env}-${suffix}'
  location: location
  properties: {
    addressSpace: { addressPrefixes: ['10.0.0.0/16'] }
    subnets: [
      {
        name: 'snet-functions'
        properties: {
          addressPrefix: '10.0.1.0/24'
          delegations: [{ name: 'funcDelegation'
            properties: { serviceName: 'Microsoft.App/environments' } }]
          networkSecurityGroup: { id: nsgFunctions.id }
        }
      }
      {
        name: 'snet-private-endpoints'
        properties: {
          addressPrefix: '10.0.2.0/24'
          privateEndpointNetworkPolicies: 'Disabled'
          networkSecurityGroup: { id: nsgPe.id }
        }
      }
    ]
  }
}
```

### 2. Bicep - update `infra/modules/functions.bicep`

```bicep
// Replace ASP plan from Y1 (Consumption) to FC1 (Flex Consumption)
resource funcPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  sku: { name: 'FC1', tier: 'FlexConsumption' }
  properties: { reserved: true }
}

// Add VNet Integration to Function App
resource funcApp 'Microsoft.Web/sites@2023-12-01' = {
  properties: {
virtualNetworkSubnetId: vnetSubnetFunctionsId // from network module output
    vnetRouteAllEnabled: true
  }
}
```

### 3. Private Endpoints (template, repeat for each service)

```bicep
// Example for Cosmos DB — similarly for AI Search, Service Bus, etc.
resource peCosmos 'Microsoft.Network/privateEndpoints@2023-11-01' = {
  name: 'pe-cosmos-${suffix}'
  location: location
  properties: {
    subnet: { id: peSubnetId }
    privateLinkServiceConnections: [{
      name: 'cosmos-connection'
      properties: {
        privateLinkServiceId: cosmosAccountId
        groupIds: ['Sql']
      }
    }]
  }
}

resource dnsZoneCosmos 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.documents.azure.com'
  location: 'global'
}

resource dnsLinkCosmos 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: dnsZoneCosmos
  name: 'cosmos-dns-link'
  location: 'global'
  properties: {
    virtualNetwork: { id: vnetId }
    registrationEnabled: false
  }
}
```

### 4. Disable public access to PaaS

```bicep
// Cosmos DB — modules/cosmos.bicep
properties: {
  publicNetworkAccess: 'Disabled'
  networkAclBypass: 'None'
}

// AI Search — modules/search.bicep
properties: {
  publicNetworkAccess: 'disabled'
}

// Service Bus — modules/servicebus.bicep
properties: {
  publicNetworkAccess: 'Disabled'
}
```

### 5. DNS Zones (full list)

| Service | Private DNS Zone |
|---|---|
| Cosmos DB | `privatelink.documents.azure.com` |
| AI Search | `privatelink.search.windows.net` |
| Service Bus | `privatelink.servicebus.windows.net` |
| Storage (Blob) | `privatelink.blob.core.windows.net` |
| Key Vault | `privatelink.vaultcore.azure.net` |
| Azure OpenAI | `privatelink.openai.azure.com` |

### 6. Update `infra/main.bicep`

- Add `module network 'modules/network.bicep'` as the first module
- Transfer `subnetFunctionsId` and `subnetPeId` to `functions.bicep`, `cosmos.bicep`, etc.
- Add a separate `module privateEndpoints` or embed it in each module

---

## Testing after implementation

1. `func azure functionapp publish` → check that the functions are available
2. `GET /api/incidents` → 200 (Cosmos via PE)
3. `POST /api/alerts` → 200 → Service Bus receives (Service Bus via PE)
4. Check in Portal: Cosmos `Firewall` → `Public access: Disabled`
5. E2E Playwright tests - all green

---

## Files to change

| File | Change |
|---|---|
| `infra/modules/network.bicep` | **New File** |
| `infra/modules/functions.bicep` | FC1 plan + VNet Integration |
| `infra/modules/cosmos.bicep` | `publicNetworkAccess: Disabled` |
| `infra/modules/servicebus.bicep` | `publicNetworkAccess: Disabled` |
| `infra/main.bicep` | Add network module, wire subnet IDs |

---

## Risks and dependencies

- **Breaking change:** switching to Flex Consumption can break deployment — test in staging
- **Price:** Flex Consumption is another price model; evaluate before deployment
- **Foundry SDK:** calls to Azure AI Foundry (`api.cognitive.microsoft.com`) - check that `vnetRouteAllEnabled` + Azure OpenAI PE covers this traffic
- **Local dev:** after `publicNetworkAccess: Disabled` - local.settings.json no longer works for Cosmos/Search; need a VPN or open your machine's IP (temporarily)
