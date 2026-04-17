// Azure Container Apps — 4 MCP server HTTP endpoints (streamable-http transport)
//
// Each MCP server runs as a Container App with external HTTPS ingress on port 8080.
// Agents reach them at https://<fqdn>/mcp via McpTool in create_agents.py.
//
// Images are referenced from ACR; initial deployment uses a placeholder image.
// Run backend/scripts/deploy-mcp.sh to build & push real images, then re-deploy.

param location string
param tags object

@description('Short env+suffix prefix used for resource names, e.g. "sentinel-intel-dev"')
param namePrefix string

@description('6-char unique suffix derived from RG id.')
param uniqueSuffix string

@description('Log Analytics workspace name (in the same RG) for container logs.')
param logAnalyticsWorkspaceName string

@description('ACR name (in the same RG) for pulling MCP images.')
param acrName string

@description('Cosmos DB account name (in the same RG).  Used to resolve keys.')
param cosmosAccountName string

@description('Database name inside the Cosmos DB account.')
param cosmosDatabaseName string = 'sentinel-intelligence'

@description('AI Search service name (in the same RG).  Used to resolve admin key.')
param searchServiceName string

@description('Azure AI Search endpoint URL, e.g. https://srch-xxx.search.windows.net')
param searchEndpoint string

@description('Azure OpenAI account name (in the same RG).  Used to resolve API key.')
param openaiAccountName string

@description('Azure OpenAI endpoint URL.')
param openaiEndpoint string

@description('Embedding deployment name.')
param embeddingDeployment string = 'text-embedding-3-small'

// ── Placeholder image used before real images are built and pushed ─────────
@description('Image tag for mcp-sentinel-db container.  Defaults to placeholder.')
param dbImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

@description('Image tag for mcp-sentinel-search container.  Defaults to placeholder.')
param searchImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

@description('Image tag for mcp-qms container.  Defaults to placeholder.')
param qmsImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

@description('Image tag for mcp-cmms container.  Defaults to placeholder.')
param cmmsImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

// ── Existing resource references for secret resolution ────────────────────

resource logWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: logAnalyticsWorkspaceName
}

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' existing = {
  name: cosmosAccountName
}

resource searchService 'Microsoft.Search/searchServices@2024-06-01-preview' existing = {
  name: searchServiceName
}

resource openaiAccount 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: openaiAccountName
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

// ── Resolved credentials ──────────────────────────────────────────────────

var cosmosKey = cosmosAccount.listKeys().primaryMasterKey
var searchKey = searchService.listAdminKeys().primaryKey
var openaiKey = openaiAccount.listKeys().key1
var acrLoginServer = acr.properties.loginServer
var acrUser = acr.listCredentials().username
var acrPassword = acr.listCredentials().passwords[0].value

// ── Container Apps Environment ────────────────────────────────────────────

resource containerEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: 'cae-${namePrefix}-${uniqueSuffix}'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logWorkspace.properties.customerId
        sharedKey: logWorkspace.listKeys().primarySharedKey
      }
    }
  }
}

// ── Common secrets shared across all MCP apps ─────────────────────────────

var commonSecrets = [
  { name: 'acr-password', value: acrPassword }
  { name: 'cosmos-key', value: cosmosKey }
  { name: 'search-key', value: searchKey }
  { name: 'openai-key', value: openaiKey }
]

var acrRegistryConfig = [
  {
    server: acrLoginServer
    username: acrUser
    passwordSecretRef: 'acr-password'
  }
]

// ── MCP Sentinel DB ───────────────────────────────────────────────────────

resource mcpSentinelDb 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'mcp-db-${uniqueSuffix}'
  location: location
  tags: union(tags, { mcpServer: 'sentinel-db' })
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      secrets: commonSecrets
      registries: acrRegistryConfig
      ingress: {
        external: true
        targetPort: 8080
        transport: 'http'
        allowInsecure: false
      }
    }
    template: {
      containers: [
        {
          name: 'mcp-sentinel-db'
          image: dbImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'MCP_TRANSPORT', value: 'streamable-http' }
            { name: 'FASTMCP_HOST', value: '0.0.0.0' }
            { name: 'FASTMCP_PORT', value: '8080' }
            { name: 'FASTMCP_STATELESS_HTTP', value: 'true' }
            { name: 'FASTMCP_TRANSPORT_SECURITY__ENABLE_DNS_REBINDING_PROTECTION', value: 'false' }
            { name: 'COSMOS_ENDPOINT', value: cosmosAccount.properties.documentEndpoint }
            { name: 'COSMOS_KEY', secretRef: 'cosmos-key' }
            { name: 'COSMOS_DATABASE', value: cosmosDatabaseName }
            { name: 'PYTHONUNBUFFERED', value: '1' }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

// ── MCP Sentinel Search ───────────────────────────────────────────────────

resource mcpSentinelSearch 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'mcp-search-${uniqueSuffix}'
  location: location
  tags: union(tags, { mcpServer: 'sentinel-search' })
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      secrets: commonSecrets
      registries: acrRegistryConfig
      ingress: {
        external: true
        targetPort: 8080
        transport: 'http'
        allowInsecure: false
      }
    }
    template: {
      containers: [
        {
          name: 'mcp-sentinel-search'
          image: searchImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'MCP_TRANSPORT', value: 'streamable-http' }
            { name: 'FASTMCP_HOST', value: '0.0.0.0' }
            { name: 'FASTMCP_PORT', value: '8080' }
            { name: 'FASTMCP_STATELESS_HTTP', value: 'true' }
            { name: 'FASTMCP_TRANSPORT_SECURITY__ENABLE_DNS_REBINDING_PROTECTION', value: 'false' }
            { name: 'AZURE_SEARCH_ENDPOINT', value: searchEndpoint }
            { name: 'AZURE_SEARCH_KEY', secretRef: 'search-key' }
            { name: 'AZURE_OPENAI_ENDPOINT', value: openaiEndpoint }
            { name: 'AZURE_OPENAI_API_KEY', secretRef: 'openai-key' }
            { name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT', value: embeddingDeployment }
            { name: 'PYTHONUNBUFFERED', value: '1' }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

// ── MCP QMS ───────────────────────────────────────────────────────────────

resource mcpQms 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'mcp-qms-${uniqueSuffix}'
  location: location
  tags: union(tags, { mcpServer: 'qms' })
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      secrets: commonSecrets
      registries: acrRegistryConfig
      ingress: {
        external: true
        targetPort: 8080
        transport: 'http'
        allowInsecure: false
      }
    }
    template: {
      containers: [
        {
          name: 'mcp-qms'
          image: qmsImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'MCP_TRANSPORT', value: 'streamable-http' }
            { name: 'FASTMCP_HOST', value: '0.0.0.0' }
            { name: 'FASTMCP_PORT', value: '8080' }
            { name: 'FASTMCP_STATELESS_HTTP', value: 'true' }
            { name: 'FASTMCP_TRANSPORT_SECURITY__ENABLE_DNS_REBINDING_PROTECTION', value: 'false' }
            { name: 'COSMOS_ENDPOINT', value: cosmosAccount.properties.documentEndpoint }
            { name: 'COSMOS_KEY', secretRef: 'cosmos-key' }
            { name: 'COSMOS_DATABASE', value: cosmosDatabaseName }
            { name: 'PYTHONUNBUFFERED', value: '1' }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 2
      }
    }
  }
}

// ── MCP CMMS ──────────────────────────────────────────────────────────────

resource mcpCmms 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'mcp-cmms-${uniqueSuffix}'
  location: location
  tags: union(tags, { mcpServer: 'cmms' })
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      secrets: commonSecrets
      registries: acrRegistryConfig
      ingress: {
        external: true
        targetPort: 8080
        transport: 'http'
        allowInsecure: false
      }
    }
    template: {
      containers: [
        {
          name: 'mcp-cmms'
          image: cmmsImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'MCP_TRANSPORT', value: 'streamable-http' }
            { name: 'FASTMCP_HOST', value: '0.0.0.0' }
            { name: 'FASTMCP_PORT', value: '8080' }
            { name: 'FASTMCP_STATELESS_HTTP', value: 'true' }
            { name: 'FASTMCP_TRANSPORT_SECURITY__ENABLE_DNS_REBINDING_PROTECTION', value: 'false' }
            { name: 'COSMOS_ENDPOINT', value: cosmosAccount.properties.documentEndpoint }
            { name: 'COSMOS_KEY', secretRef: 'cosmos-key' }
            { name: 'COSMOS_DATABASE', value: cosmosDatabaseName }
            { name: 'PYTHONUNBUFFERED', value: '1' }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 2
      }
    }
  }
}

// ── Outputs ───────────────────────────────────────────────────────────────

output containerEnvId string = containerEnv.id
output mcpDbFqdn string = mcpSentinelDb.properties.configuration.ingress.fqdn
output mcpSearchFqdn string = mcpSentinelSearch.properties.configuration.ingress.fqdn
output mcpQmsFqdn string = mcpQms.properties.configuration.ingress.fqdn
output mcpCmmsFqdn string = mcpCmms.properties.configuration.ingress.fqdn

// Full MCP endpoint URLs (used by McpTool in create_agents.py)
output mcpDbUrl string = 'https://${mcpSentinelDb.properties.configuration.ingress.fqdn}/mcp'
output mcpSearchUrl string = 'https://${mcpSentinelSearch.properties.configuration.ingress.fqdn}/mcp'
output mcpQmsUrl string = 'https://${mcpQms.properties.configuration.ingress.fqdn}/mcp'
output mcpCmmsUrl string = 'https://${mcpCmms.properties.configuration.ingress.fqdn}/mcp'
