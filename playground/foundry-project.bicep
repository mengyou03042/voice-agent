param accountName string
param location string
param projectName string
param runtimePrincipalId string

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: accountName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: account
  name: projectName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: 'Voice Agent invitation playground'
    description: 'Isolated shared playground Project; fictional data only.'
  }
}

resource projectRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: project
  name: guid(project.id, runtimePrincipalId, 'CognitiveServicesDataContributor')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '19c28022-e58e-450d-a464-0b2a53034789')
    principalId: runtimePrincipalId
    principalType: 'ServicePrincipal'
  }
}

output projectId string = project.id
