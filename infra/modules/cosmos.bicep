// Cosmos DB — main operational database for incidents, batches, equipment, CAPA

param location string
param tags object
param accountName string
param databaseName string = 'sentinel-intelligence'

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: accountName
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    enableFreeTier: false
    capabilities: [
      { name: 'EnableServerless' }
    ]
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: cosmosAccount
  name: databaseName
  properties: {
    resource: { id: databaseName }
  }
}

var containers = [
  { id: 'incidents', partitionKey: '/equipmentId' }
  { id: 'equipment', partitionKey: '/id' }
  { id: 'batches', partitionKey: '/equipmentId' }
  { id: 'capa-plans', partitionKey: '/incidentId' }
  { id: 'approval-tasks', partitionKey: '/incidentId' }
  { id: 'templates', partitionKey: '/id' }
]

resource sqlContainers 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = [for c in containers: {
  parent: database
  name: c.id
  properties: {
    resource: {
      id: c.id
      partitionKey: {
        paths: [c.partitionKey]
        kind: 'Hash'
      }
    }
  }
}]

output cosmosAccountId string = cosmosAccount.id
output cosmosAccountName string = cosmosAccount.name
output cosmosEndpoint string = cosmosAccount.properties.documentEndpoint
output databaseName string = database.name
