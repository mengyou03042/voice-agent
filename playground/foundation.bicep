targetScope = 'subscription'

param resourceGroupName string = 'voice-agent-portal-hosting-dev'
param location string = 'westus2'

resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: {
    workload: 'voice-agent-portal'
    environment: 'dev'
    OwnerAlias: 'mengyou'
  }
}

module resources 'foundation-resources.bicep' = {
  scope: resourceGroup
  name: 'voice-agent-portal-foundation'
  params: {
    location: location
  }
}

output resourceGroupName string = resourceGroup.name
output foundryAccountName string = resources.outputs.foundryAccountName
output foundryLocation string = location
output managedEnvironmentId string = resources.outputs.managedEnvironmentId
output managedEnvironmentDomain string = resources.outputs.managedEnvironmentDomain
output registryName string = resources.outputs.registryName
output registryLoginServer string = resources.outputs.registryLoginServer
