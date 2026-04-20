using '../main.bicep'

param environmentName = 'dev'
param projectName = 'sentinel-intel'
// uniqueSuffix is auto-generated from the resource group ID — no override needed
param orchestratorAgentId = 'asst_CNYK3TZIaOCH4OPKcP4N9B2r'
param researchAgentId = 'asst_NDuVHHTsxfRvY1mRSd7MtEGT'
param documentAgentId = 'asst_AXgt7fxnSnUh5WXauR27S40L'
// ODL lab environment — service principal has Contributor but not Owner/UAMI
param skipRoleAssignments = true
