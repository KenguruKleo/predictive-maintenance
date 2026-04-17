// Predictive Maintenance — GMP Deviation & CAPA Operations Assistant
// Azure AI Foundry — Hub + Project (T-025, T-026, T-024)
//
// Provisions:
//   - AI Foundry Hub  (Microsoft.MachineLearningServices/workspaces kind=Hub)
//   - AI Foundry Project (kind=Project, references Hub)
//   - Connection: Hub → Azure AIServices account (OpenAI + Agent Service)
//   - Connection: Hub → Azure AI Search (for Research Agent search tools)
//
// Outputs include searchConnectionId so create_agents.py can attach AzureAISearchTool
// to the Research Agent without manual steps.

param location string
param tags object
param hubName string
param projectName string

// Dependencies wired in from main.bicep
param storageAccountName string
param appInsightsId string
param keyVaultName string
param openaiAccountName string
param openaiEndpoint string
param searchServiceName string
param searchServiceEndpoint string

// ── Key Vault (required by Hub) ─────────────────────────────────────────
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    enableRbacAuthorization: true
    publicNetworkAccess: 'Enabled'
  }
}

// ── AI Foundry Hub ───────────────────────────────────────────────────────
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource hub 'Microsoft.MachineLearningServices/workspaces@2024-10-01' = {
  name: hubName
  location: location
  tags: tags
  kind: 'Hub'
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
  properties: {
    friendlyName: hubName
    storageAccount: storageAccount.id
    applicationInsights: appInsightsId
    keyVault: keyVault.id
    publicNetworkAccess: 'Enabled'
  }
}

// ── OpenAI / AIServices connection on the Hub ────────────────────────────
resource openaiAccount 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: openaiAccountName
}

resource openaiConnection 'Microsoft.MachineLearningServices/workspaces/connections@2024-10-01' = {
  parent: hub
  name: 'aiservices-connection'
  properties: {
    category: 'AIServices'
    target: openaiEndpoint
    authType: 'ApiKey'
    isSharedToAll: true
    credentials: {
      key: openaiAccount.listKeys().key1
    }
    metadata: {
      ApiVersion: '2024-05-01-preview'
      ApiType: 'azure'
      ResourceId: openaiAccount.id
    }
  }
}

// ── AI Search connection on the Hub ──────────────────────────────────────
// Enables AzureAISearchTool in the Research Agent (T-025, T-037).
// searchConnectionId output is consumed by create_agents.py via
// AZURE_AI_SEARCH_CONNECTION_ID env var to avoid manual lookups.
resource searchService 'Microsoft.Search/searchServices@2024-06-01-preview' existing = {
  name: searchServiceName
}

resource searchConnection 'Microsoft.MachineLearningServices/workspaces/connections@2024-10-01' = {
  parent: hub
  name: 'search-connection'
  properties: {
    category: 'CognitiveSearch'
    target: searchServiceEndpoint
    authType: 'ApiKey'
    isSharedToAll: true
    credentials: {
      key: searchService.listAdminKeys().primaryKey
    }
    metadata: {
      ApiVersion: '2024-05-01-preview'
      ApiType: 'azure'
      ResourceId: searchService.id
    }
  }
}

// ── AI Foundry Project ───────────────────────────────────────────────────
resource project 'Microsoft.MachineLearningServices/workspaces@2024-10-01' = {
  name: projectName
  location: location
  tags: tags
  kind: 'Project'
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
  properties: {
    friendlyName: projectName
    hubResourceId: hub.id
    publicNetworkAccess: 'Enabled'
  }
}

// ── Outputs ──────────────────────────────────────────────────────────────

// Connection string used by azure-ai-projects SDK and create_agents.py
output projectConnectionString string = '${location}.api.azureml.ms;${subscription().subscriptionId};${resourceGroup().name};${project.name}'
output hubName string = hub.name
output projectName string = project.name
output projectId string = project.id
// Endpoint for AgentsClient: https://<aiservices>.services.ai.azure.com/api/projects/<project>
output agentsEndpoint string = '${openaiEndpoint}/api/projects/${project.name}'
// Foundry connection ID for AzureAISearchTool — used in create_agents.py as AZURE_AI_SEARCH_CONNECTION_ID
output searchConnectionId string = searchConnection.id
