// ─────────────────────────────────────────────────────────────────────────────
// Predictive Maintenance — GMP Deviation & CAPA Operations Assistant
// Root Bicep template  (stub — resources added in T-041)
// ─────────────────────────────────────────────────────────────────────────────

targetScope = 'resourceGroup'

// ── Parameters ───────────────────────────────────────────────────────────────

@description('Azure region for all resources.')
param location string = resourceGroup().location  // swedencentral (ODL-GHAZ-2177134)

@allowed(['dev', 'staging', 'prod'])
param environmentName string = 'dev'

@description('Short project prefix used in all resource names.')
@maxLength(16)
param projectName string = 'sentinel-intel'

@description('Unique suffix appended to globally-scoped names (storage, KV, CosmosDB). Auto-derived from RG id.')
param uniqueSuffix string = substring(uniqueString(resourceGroup().id), 0, 6)

// ── Variables ─────────────────────────────────────────────────────────────────

var prefix = '${projectName}-${environmentName}'
var tags = {
  project: projectName
  environment: environmentName
  managedBy: 'bicep'
}

// ── Outputs ───────────────────────────────────────────────────────────────────
// Outputs are declared now so deploy.yml can parse them from day 1.
// Values default to empty strings until the real resources are deployed.

@description('Azure Functions app hostname')
output functionsAppName string = 'func-${prefix}-${uniqueSuffix}'

@description('Static Web App default URL')
output staticWebAppUrl string = 'https://${prefix}.azurestaticapps.net'

@description('Resource prefix used by all child modules')
output resourcePrefix string = prefix

output location string = location
output tags object = tags
