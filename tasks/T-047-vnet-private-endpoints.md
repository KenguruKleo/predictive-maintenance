# T-047 · Network Isolation: VNet / NSGs / Private Endpoints (SE:06)

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🟡 MEDIUM (post-hackathon)  
**Статус:** 🔜 TODO  
**WAR Gap:** SE:06 P:90 / P:80 / P:70  
**Залежить від:** T-038 (Key Vault), Function App план → Flex Consumption

---

## Мета

Закрити SE:06 — повна мережева ізоляція PaaS-сервісів. Вимкнути публічний доступ до Cosmos DB, AI Search, Service Bus, Storage, Key Vault, Azure OpenAI. Весь трафік Function App → через VNet.

**Хакатонний компроміс:** Consumption plan не підтримує VNet Integration. У production переходимо на Flex Consumption + PE. Дизайн задокументований у §8.15 02-architecture.md.

---

## Definition of Done

- [ ] VNet `vnet-sentinel-intel-dev-{suffix}` задеплоєний
- [ ] Два subnet-и: `snet-functions` і `snet-private-endpoints`
- [ ] NSGs на обох subnet-ах з мінімальним allow-списком
- [ ] Function App переведений на **Flex Consumption** plan (підтримує VNet Integration)
- [ ] VNet Integration на Function App (`vnetRouteAllEnabled = true`)
- [ ] Private Endpoint для кожного PaaS сервісу в `snet-private-endpoints`
- [ ] Private DNS Zone для кожного сервісу, прив'язана до VNet
- [ ] `publicNetworkAccess = Disabled` на Cosmos DB, AI Search, Service Bus, Key Vault
- [ ] Function App HTTP trigger залишається публічним (frontend → API)
- [ ] Усі тести (smoke + E2E) проходять після зміни

---

## Архітектура

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

**Що залишається публічним (і це правильно):**
- Static Web App — публічний (браузер → SPA)
- Function App HTTP trigger — публічний (тільки для SWA + RBAC-захищений)
- SignalR negotiate endpoint — публічний (через Function trigger)

---

## Checklist деталі

### 1. Bicep — новий модуль `infra/modules/network.bicep`

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

### 2. Bicep — оновити `infra/modules/functions.bicep`

```bicep
// Замінити ASP план з Y1 (Consumption) на FC1 (Flex Consumption)
resource funcPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  sku: { name: 'FC1', tier: 'FlexConsumption' }
  properties: { reserved: true }
}

// Додати VNet Integration на Function App
resource funcApp 'Microsoft.Web/sites@2023-12-01' = {
  properties: {
    virtualNetworkSubnetId: vnetSubnetFunctionsId  // з network module output
    vnetRouteAllEnabled: true
  }
}
```

### 3. Private Endpoints (шаблон, повторити для кожного сервісу)

```bicep
// Приклад для Cosmos DB — аналогічно для AI Search, Service Bus, etc.
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

### 4. Вимкнути публічний доступ до PaaS

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

### 5. DNS Zones (повний список)

| Сервіс | Private DNS Zone |
|---|---|
| Cosmos DB | `privatelink.documents.azure.com` |
| AI Search | `privatelink.search.windows.net` |
| Service Bus | `privatelink.servicebus.windows.net` |
| Storage (Blob) | `privatelink.blob.core.windows.net` |
| Key Vault | `privatelink.vaultcore.azure.net` |
| Azure OpenAI | `privatelink.openai.azure.com` |

### 6. Оновити `infra/main.bicep`

- Додати `module network 'modules/network.bicep'` як перший модуль
- Передати `subnetFunctionsId` і `subnetPeId` в `functions.bicep`, `cosmos.bicep`, etc.
- Додати окремий `module privateEndpoints` або вбудувати в кожен модуль

---

## Тестування після впровадження

1. `func azure functionapp publish` → перевірити, що функції доступні
2. `GET /api/incidents` → 200 (Cosmos через PE)
3. `POST /api/alerts` → 200 → Service Bus отримує (Service Bus через PE)
4. Перевірити у Portal: Cosmos `Firewall` → `Public access: Disabled`
5. E2E Playwright тести — усі зелені

---

## Файли для зміни

| Файл | Зміна |
|---|---|
| `infra/modules/network.bicep` | **Новий файл** |
| `infra/modules/functions.bicep` | FC1 plan + VNet Integration |
| `infra/modules/cosmos.bicep` | `publicNetworkAccess: Disabled` |
| `infra/modules/servicebus.bicep` | `publicNetworkAccess: Disabled` |
| `infra/main.bicep` | Додати network module, wire subnet IDs |

---

## Ризики та залежності

- **Breaking change:** перехід на Flex Consumption може зламати deployment — тестувати у staging
- **Ціна:** Flex Consumption — інша цінова модель; оцінити перед деплоєм
- **Foundry SDK:** виклики до Azure AI Foundry (`api.cognitive.microsoft.com`) — перевірити, що `vnetRouteAllEnabled` + Azure OpenAI PE охоплює цей трафік
- **Local dev:** після `publicNetworkAccess: Disabled` — local.settings.json більше не працює для Cosmos/Search; потрібен VPN або відкрити IP вашої машини (тимчасово)
