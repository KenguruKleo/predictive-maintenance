// Azure Static Web App — hosts React SPA frontend
targetScope = 'resourceGroup'

@description('Azure region for the Static Web App.')
param location string

@description('Resource tags.')
param tags object

@description('Name for the Static Web App resource.')
param swaName string

@description('SKU tier: Free or Standard.')
@allowed(['Free', 'Standard'])
param skuName string = 'Free'

// Static Web Apps resource
resource swa 'Microsoft.Web/staticSites@2023-01-01' = {
  name: swaName
  location: location
  tags: tags
  sku: {
    name: skuName
    tier: skuName
  }
  properties: {
    // buildProperties omitted — deployment handled by GitHub Actions / swa-cli
    stagingEnvironmentPolicy: 'Enabled'
    allowConfigFileUpdates: true
  }
}

// Outputs

@description('Deployment token for GitHub Actions / swa-cli.')
output deploymentToken string = swa.listSecrets().properties.apiKey

@description('Default hostname of the Static Web App.')
output swaHostname string = swa.properties.defaultHostname

@description('Resource name.')
output swaName string = swa.name
