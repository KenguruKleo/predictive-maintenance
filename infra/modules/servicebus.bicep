// Service Bus — alert-queue for SCADA anomaly signals

param location string
param tags object
param namespaceName string

resource serviceBusNamespace 'Microsoft.ServiceBus/namespaces@2022-10-01-preview' = {
  name: namespaceName
  location: location
  tags: tags
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
}

resource alertQueue 'Microsoft.ServiceBus/namespaces/queues@2022-10-01-preview' = {
  parent: serviceBusNamespace
  name: 'alert-queue'
  properties: {
    maxDeliveryCount: 5
    lockDuration: 'PT1M'
    defaultMessageTimeToLive: 'P1D'
  }
}

output serviceBusId string = serviceBusNamespace.id
output serviceBusName string = serviceBusNamespace.name
output serviceBusEndpoint string = serviceBusNamespace.properties.serviceBusEndpoint
output alertQueueName string = alertQueue.name
