targetScope = 'resourceGroup'

param foundryAccountName string
param foundryLocation string
param foundryResourceGroup string
param managedEnvironmentId string
param managedEnvironmentDomain string
param location string = 'westus2'
param registryName string
param registryResourceGroup string
@description('Immutable image reference in the registry, including @sha256:digest.')
param image string
param appName string = 'voice-agent-playground'
param projectName string = 'voice-agent-playground'
@secure()
param anonymousCookieKey string
@secure()
@minLength(64)
@description('SHA-256 hash of the shared high-entropy login token.')
param invitationCodeHash string
@minValue(1)
param invitationExpiresAt int
@minValue(1)
@maxValue(400)
@description('Days that a successfully authenticated browser remains signed in.')
param accessCookieDays int = 365
@description('Public base URL owned by docs/voice_agent/12_noauth_mcp.')
param mcpBaseUrl string
@description('Expose the Portal only after hosted MCP connections are configured.')
param exposePortalIngress bool = false
@minValue(0)
@maxValue(10)
@description('Use 0 to stop hosting and at least 2 for multi-replica serving.')
param minimumReplicas int = 0
@minValue(1)
@maxValue(10)
@description('Maximum Portal replicas. Keep this greater than or equal to minimumReplicas.')
param maximumReplicas int = 5

resource runtimeIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${appName}-runtime'
  location: location
}

module foundryProject 'foundry-project.bicep' = {
  scope: resourceGroup(foundryResourceGroup)
  name: '${appName}-foundry-project'
  params: {
    accountName: foundryAccountName
    location: foundryLocation
    projectName: projectName
    runtimePrincipalId: runtimeIdentity.properties.principalId
  }
}

module registryRole 'registry-role.bicep' = {
  scope: resourceGroup(registryResourceGroup)
  name: '${appName}-registry-pull'
  params: {
    registryName: registryName
    principalId: runtimeIdentity.properties.principalId
  }
}

resource app 'Microsoft.App/containerApps@2025-01-01' = {
  name: appName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${runtimeIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: managedEnvironmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: exposePortalIngress
        targetPort: 9527
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: '${toLower(registryName)}.azurecr.io'
          identity: runtimeIdentity.id
        }
      ]
      secrets: [
        {
          name: 'anonymous-cookie-key'
          value: anonymousCookieKey
        }
        {
          name: 'invitation-code-hash'
          value: invitationCodeHash
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'portal'
          image: image
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'AZURE_CLIENT_ID'
              value: runtimeIdentity.properties.clientId
            }
            {
              name: 'AZURE_VOICE_AGENTS_ENDPOINT'
              value: 'https://${foundryAccountName}.services.ai.azure.com/api/projects/${projectName}'
            }
            {
              name: 'VOICE_PLAYGROUND_ORIGIN'
              value: 'https://${appName}.${managedEnvironmentDomain}'
            }
            {
              name: 'VOICE_PLAYGROUND_AUTH_MODE'
              value: 'invite'
            }
            {
              name: 'VOICE_PLAYGROUND_MCP_BASE_URL'
              value: mcpBaseUrl
            }
            {
              name: 'VOICE_PLAYGROUND_COOKIE_KEY'
              secretRef: 'anonymous-cookie-key'
            }
            {
              name: 'VOICE_PLAYGROUND_INVITE_HASH'
              secretRef: 'invitation-code-hash'
            }
            {
              name: 'VOICE_PLAYGROUND_INVITE_EXPIRES_AT'
              value: string(invitationExpiresAt)
            }
            {
              name: 'VOICE_PLAYGROUND_ACCESS_COOKIE_DAYS'
              value: string(accessCookieDays)
            }
            {
              name: 'VOICE_PLAYGROUND_ENABLED'
              value: exposePortalIngress ? 'true' : 'false'
            }
          ]
          probes: [
            {
              type: 'Readiness'
              httpGet: {
                path: '/healthz'
                port: 9527
              }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
            {
              type: 'Liveness'
              httpGet: {
                path: '/healthz'
                port: 9527
              }
              initialDelaySeconds: 30
              periodSeconds: 30
            }
          ]
        }
      ]
      scale: {
        minReplicas: minimumReplicas
        maxReplicas: maximumReplicas
      }
    }
  }
  dependsOn: [
    foundryProject
    registryRole
  ]
}

output appUrl string = 'https://${appName}.${managedEnvironmentDomain}'
output projectId string = foundryProject.outputs.projectId
output runtimeIdentityId string = runtimeIdentity.id
