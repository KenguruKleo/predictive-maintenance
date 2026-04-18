// Azure SignalR Service — real-time push notifications (T-030)
// Serverless mode: Function App sends messages; React SPA connects via negotiate endpoint.

param location string
param tags object
param signalrName string

@allowed(['Free_F1', 'Standard_S1'])
@description('Free_F1 for dev/demo; Standard_S1 for production.')
param skuName string = 'Free_F1'

resource signalr 'Microsoft.SignalRService/signalR@2023-02-01' = {
  name: signalrName
  location: location
  tags: tags
  sku: {
    name: skuName
    capacity: 1
  }
  properties: {
    features: [
      {
        flag: 'ServiceMode'
        value: 'Serverless'
      }
      {
        flag: 'EnableConnectivityLogs'
        value: 'true'
      }
      {
        flag: 'EnableMessagingLogs'
        value: 'true'
      }
    ]
    cors: {
      allowedOrigins: ['*']
    }
    upstream: {}
  }
}

output signalrName string = signalr.name
output signalrHostname string = signalr.properties.hostName

@secure()
output signalrConnectionString string = signalr.listKeys().primaryConnectionString
