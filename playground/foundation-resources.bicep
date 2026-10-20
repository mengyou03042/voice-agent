param location string

var suffix = take(uniqueString(subscription().id, resourceGroup().id), 8)
var registryName = 'vaportal${suffix}'
var foundryAccountName = 'voice-agent-portal-${suffix}'

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'voice-agent-portal-logs'
  location: location
  properties: {
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: registryName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

resource environment 'Microsoft.App/managedEnvironments@2025-01-01' = {
  name: 'voice-agent-portal-dev-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
    zoneRedundant: false
  }
}

resource foundry 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: foundryAccountName
  location: location
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    allowProjectManagement: true
    customSubDomainName: foundryAccountName
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
}

output foundryAccountName string = foundry.name
output managedEnvironmentId string = environment.id
output managedEnvironmentDomain string = environment.properties.defaultDomain
output registryName string = registry.name
output registryLoginServer string = registry.properties.loginServer
