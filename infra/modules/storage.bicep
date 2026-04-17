// Storage Account — used by Azure Functions (Durable state) and Blob (documents)

param location string
param tags object
param storageName string

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
}

resource documentsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'documents'
  properties: {
    publicAccess: 'None'
  }
}

// Document ingestion containers — one per source type (separate ingestors, separate AI Search indexes)
var docContainers = ['blob-sop', 'blob-manuals', 'blob-gmp', 'blob-bpr', 'blob-history']

resource ingestionContainers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = [for name in docContainers: {
  parent: blobService
  name: name
  properties: {
    publicAccess: 'None'
  }
}]

output storageId string = storage.id
output storageName string = storage.name
