// Azure AI Services account — provides OpenAI API + Agent Service endpoint
// kind=AIServices replaces kind=OpenAI to enable Foundry Agent Service

param location string
param tags object
param openaiAccountName string

@description('TPM capacity for text-embedding-3-small (in thousands). Default 50K.')
param embeddingCapacity int = 50

@description('TPM capacity for gpt-4o (in thousands). Default 150K.')
param gpt4oCapacity int = 150

resource openaiAccount 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: openaiAccountName
  location: location
  tags: tags
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: openaiAccountName
    publicNetworkAccess: 'Enabled'
  }
}

// Embedding model — used by ingestion pipeline and Research Agent RAG tools
resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openaiAccount
  name: 'text-embedding-3-small'
  sku: {
    name: 'GlobalStandard'
    capacity: embeddingCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-small'
      version: '1'
    }
  }
}

// GPT-4o — used by Research Agent, Document Agent, Execution Agent
resource gpt4oDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openaiAccount
  name: 'gpt-4o'
  dependsOn: [embeddingDeployment]
  sku: {
    name: 'GlobalStandard'
    capacity: gpt4oCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-11-20'
    }
  }
}

output openaiEndpoint string = openaiAccount.properties.endpoint
output openaiAccountName string = openaiAccount.name
output openaiAccountId string = openaiAccount.id
output embeddingDeploymentName string = embeddingDeployment.name
output gpt4oDeploymentName string = gpt4oDeployment.name
// Agents endpoint: https://<name>.services.ai.azure.com/api/projects/<project>
output aiServicesEndpoint string = 'https://${openaiAccountName}.services.ai.azure.com'
