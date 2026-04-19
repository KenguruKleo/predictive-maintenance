// Azure Functions — Python 3.11, Consumption plan, Durable Functions enabled

param location string
param tags object
param funcAppName string
param storageAccountName string
param appInsightsConnectionString string
param appInsightsResourceId string
param appInsightsWorkspaceId string

// Runtime wiring — endpoints + keys from other modules
param cosmosEndpoint string
param cosmosAccountName string
param serviceBusNamespaceName string
param openaiEndpoint string
param openaiAccountName string
param searchEndpoint string
param searchServiceName string
param foundryProjectConnectionString string
param foundrySearchConnectionId string
param signalrConnectionString string
param orchestratorAgentId string = ''
param researchAgentId string = ''
param documentAgentId string = ''

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

// Existing resources for listKeys() calls
resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' existing = {
  name: cosmosAccountName
}

resource serviceBusNamespace 'Microsoft.ServiceBus/namespaces@2022-10-01-preview' existing = {
  name: serviceBusNamespaceName
}

resource serviceBusAuthRule 'Microsoft.ServiceBus/namespaces/authorizationRules@2021-11-01' existing = {
  parent: serviceBusNamespace
  name: 'RootManageSharedAccessKey'
}

resource openaiAccount 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: openaiAccountName
}

resource searchService 'Microsoft.Search/searchServices@2024-06-01-preview' existing = {
  name: searchServiceName
}

var monitoringReaderRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '43d0d8ad-25c7-4714-9337-8ba259a9fe05'
)

var readerRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  'acdd72a7-3385-48ef-bd42-f606fba81ae7'
)

var logAnalyticsReaderRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '73c42c96-874c-492b-b04d-ab87d138a893'
)

resource appInsights 'Microsoft.Insights/components@2020-02-02' existing = {
  name: last(split(appInsightsResourceId, '/'))
}

resource appInsightsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: last(split(appInsightsWorkspaceId, '/'))
}

resource appServicePlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: 'asp-${funcAppName}'
  location: location
  tags: tags
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  kind: 'functionapp'
  properties: {
    reserved: true // required for Linux
  }
}

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: funcAppName
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'python|3.11'
      appSettings: [
        { name: 'AzureWebJobsStorage', value: 'DefaultEndpointsProtocol=https;AccountName=${storage.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storage.listKeys().keys[0].value}' }
        { name: 'FUNCTIONS_EXTENSION_VERSION', value: '~4' }
        { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }
        { name: 'AzureWebJobsFeatureFlags', value: 'EnableWorkerIndexing' }
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
        { name: 'APPLICATIONINSIGHTS_RESOURCE_ID', value: appInsightsResourceId }
        { name: 'SCM_DO_BUILD_DURING_DEPLOYMENT', value: 'true' }
        // Cosmos DB
        { name: 'COSMOS_ENDPOINT', value: cosmosEndpoint }
        { name: 'COSMOS_KEY', value: cosmosAccount.listKeys().primaryMasterKey }
        // Service Bus
        { name: 'SERVICEBUS_CONNECTION_STRING', value: serviceBusAuthRule.listKeys().primaryConnectionString }
        { name: 'SERVICEBUS_NAMESPACE', value: '${serviceBusNamespaceName}.servicebus.windows.net' }
        // Azure OpenAI
        { name: 'AZURE_OPENAI_ENDPOINT', value: openaiEndpoint }
        { name: 'AZURE_OPENAI_API_KEY', value: openaiAccount.listKeys().key1 }
        { name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT', value: 'text-embedding-3-small' }
        { name: 'AZURE_OPENAI_GPT4O_DEPLOYMENT', value: 'gpt-4o' }
        // Azure AI Search
        { name: 'AZURE_SEARCH_ENDPOINT', value: searchEndpoint }
        { name: 'AZURE_SEARCH_ADMIN_KEY', value: searchService.listAdminKeys().primaryKey }
        // Azure AI Foundry (agents)
        // AZURE_AI_FOUNDRY_AGENTS_ENDPOINT uses the connection string format for Hub-based projects
        { name: 'AZURE_AI_FOUNDRY_PROJECT_CONNECTION_STRING', value: foundryProjectConnectionString }
        { name: 'AZURE_AI_FOUNDRY_AGENTS_ENDPOINT', value: foundryProjectConnectionString }
        { name: 'AZURE_AI_AGENTS_TESTS_IS_TEST_RUN', value: 'True' }
        { name: 'FOUNDRY_PROMPT_TRACE_ENABLED', value: '1' }
        // Foundry Hub connection ID for AzureAISearchTool in Research Agent
        { name: 'AZURE_AI_SEARCH_CONNECTION_ID', value: foundrySearchConnectionId }
        // Azure SignalR (T-030)
        { name: 'AzureSignalRConnectionString', value: signalrConnectionString }
        { name: 'MAX_MORE_INFO_ROUNDS', value: '3' }
        { name: 'CONFIDENCE_THRESHOLD', value: '0.75' }
        // Agent IDs — populated after agents/create_agents.py runs
        { name: 'ORCHESTRATOR_AGENT_ID', value: orchestratorAgentId }
        { name: 'RESEARCH_AGENT_ID', value: researchAgentId }
        { name: 'DOCUMENT_AGENT_ID', value: documentAgentId }
        { name: 'EXECUTION_AGENT_ID', value: '' }
      ]
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
    }
    httpsOnly: true
  }
}

resource functionAppMonitoringReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, functionApp.id, 'monitoring-reader')
  scope: resourceGroup()
  properties: {
    roleDefinitionId: monitoringReaderRoleDefinitionId
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource functionAppAppInsightsReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(appInsights.id, functionApp.id, 'reader')
  scope: appInsights
  properties: {
    roleDefinitionId: readerRoleDefinitionId
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource functionAppWorkspaceLogAnalyticsReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(appInsightsWorkspace.id, functionApp.id, 'log-analytics-reader')
  scope: appInsightsWorkspace
  properties: {
    roleDefinitionId: logAnalyticsReaderRoleDefinitionId
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

output funcAppId string = functionApp.id
output funcAppName string = functionApp.name
output funcAppHostname string = functionApp.properties.defaultHostName
