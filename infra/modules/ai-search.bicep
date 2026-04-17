// Azure AI Search Service
// NOTE: basic SKU not available in swedencentral — deployed in westeurope via az cli
// This module provisions/updates the service when region allows.

param location string
param tags object
param searchServiceName string

@allowed(['free', 'basic', 'standard', 'standard2', 'standard3'])
param sku string = 'basic'

resource searchService 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: searchServiceName
  location: location
  tags: tags
  sku: {
    name: sku
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
    semanticSearch: 'free'
  }
}

output searchServiceName string = searchService.name
output searchServiceEndpoint string = 'https://${searchService.name}.search.windows.net'
output searchServiceId string = searchService.id
