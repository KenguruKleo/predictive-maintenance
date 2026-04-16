// Predictive Maintenance — GMP Deviation & CAPA Operations Assistant
// Root Bicep template

targetScope = 'resourceGroup'

// Parameters

@description('Azure region for all resources.')
param location string = resourceGroup().location

@allowed(['dev', 'staging', 'prod'])
param environmentName string = 'dev'

@description('Short project prefix used in all resource names.')
@maxLength(16)
param projectName string = 'sentinel-intel'

@description('6-char unique suffix derived from RG id — do not override unless needed.')
param uniqueSuffix string = substring(uniqueString(resourceGroup().id), 0, 6)

// Variables

var prefix = '${projectName}-${environmentName}'
var tags = {
  project: projectName
  environment: environmentName
  managedBy: 'bicep'
}

// Storage (Durable Functions state + Blob documents)
module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    location: location
    tags: tags
    storageName: 'st${replace(projectName, '-', '')}${uniqueSuffix}'
  }
}

// Monitoring (Log Analytics + App Insights)
module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    location: location
    tags: tags
    workspaceName: 'log-${prefix}-${uniqueSuffix}'
    appInsightsName: 'appi-${prefix}-${uniqueSuffix}'
  }
}

// Cosmos DB
module cosmos 'modules/cosmos.bicep' = {
  name: 'cosmos'
  params: {
    location: location
    tags: tags
    accountName: 'cosmos-${prefix}-${uniqueSuffix}'
    databaseName: 'sentinel-intelligence'
  }
}

// Service Bus
module servicebus 'modules/servicebus.bicep' = {
  name: 'servicebus'
  params: {
    location: location
    tags: tags
    namespaceName: 'sb-${prefix}-${uniqueSuffix}'
  }
}

// Azure Functions
module functions 'modules/functions.bicep' = {
  name: 'functions'
  params: {
    location: location
    tags: tags
    funcAppName: 'func-${prefix}-${uniqueSuffix}'
    storageAccountName: storage.outputs.storageName
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
  }
}

// Outputs

output functionsAppName string = functions.outputs.funcAppName
output functionsHostname string = functions.outputs.funcAppHostname
output cosmosEndpoint string = cosmos.outputs.cosmosEndpoint
output cosmosDatabaseName string = cosmos.outputs.databaseName
output serviceBusEndpoint string = servicebus.outputs.serviceBusEndpoint
output storageAccountName string = storage.outputs.storageName
output staticWebAppUrl string = 'https://${prefix}.azurestaticapps.net'
output resourcePrefix string = prefix
