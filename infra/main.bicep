targetScope = 'resourceGroup'

@description('Three to twelve lowercase letters or digits, starting with a letter.')
@minLength(3)
@maxLength(12)
param prefix string = 'supportops'
param postgresAdmin string = 'supportops_admin'
@secure()
param postgresPassword string
param provisionIntegrationServices bool = false

var location = resourceGroup().location
var suffix = uniqueString(resourceGroup().id)
var tags = { project: 'SupportOps AI', environment: 'demo' }

resource network 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: '${prefix}-network'
  location: location
  tags: tags
  properties: {
    addressSpace: { addressPrefixes: ['10.42.0.0/16'] }
    subnets: [
      {
        name: 'apps'
        properties: {
          addressPrefix: '10.42.0.0/24'
          delegations: [
            { name: 'container-apps', properties: { serviceName: 'Microsoft.App/environments' } }
          ]
        }
      }
      {
        name: 'postgres'
        properties: {
          addressPrefix: '10.42.1.0/27'
          delegations: [
            { name: 'postgres', properties: { serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers' } }
          ]
        }
      }
      {
        name: 'automation'
        properties: {
          addressPrefix: '10.42.2.0/27'
          defaultOutboundAccess: false
        }
      }
    ]
  }
}

resource postgresDns 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: '${prefix}-${suffix}.private.postgres.database.azure.com'
  location: 'global'
}

resource postgresDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: postgresDns
  name: 'supportops-network'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: { id: network.id }
  }
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2025-08-01' = {
  name: '${prefix}-${suffix}'
  location: location
  tags: tags
  sku: { name: 'Standard_B1ms', tier: 'Burstable' }
  properties: {
    administratorLogin: postgresAdmin
    administratorLoginPassword: postgresPassword
    version: '17'
    storage: { storageSizeGB: 32 }
    backup: { backupRetentionDays: 7 }
    network: {
      delegatedSubnetResourceId: resourceId('Microsoft.Network/virtualNetworks/subnets', network.name, 'postgres')
      privateDnsZoneArmResourceId: postgresDns.id
      publicNetworkAccess: 'Disabled'
    }
  }
  dependsOn: [postgresDnsLink]
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgres
  name: 'supportops'
  properties: { charset: 'UTF8', collation: 'en_US.utf8' }
}

resource vector 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2024-08-01' = {
  parent: postgres
  name: 'azure.extensions'
  properties: { value: 'vector', source: 'user-override' }
}

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${prefix}-logs'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
    workspaceCapping: { dailyQuotaGb: json('0.1') }
  }
}

resource environment 'Microsoft.App/managedEnvironments@2025-01-01' = {
  name: '${prefix}-apps'
  location: location
  tags: tags
  properties: {
    vnetConfiguration: {
      infrastructureSubnetId: resourceId('Microsoft.Network/virtualNetworks/subnets', network.name, 'apps')
      internal: false
    }
    workloadProfiles: [
      { name: 'Consumption', workloadProfileType: 'Consumption' }
    ]
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
  }
}

resource registry 'Microsoft.ContainerRegistry/registries@2025-11-01' = {
  name: '${prefix}${suffix}'
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false
    roleAssignmentMode: 'LegacyRegistryPermissions'
    policies: { azureADAuthenticationAsArmPolicy: { status: 'enabled' } }
  }
}

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${take(prefix, 10)}-${suffix}'
  location: location
  tags: tags
  properties: {
    tenantId: tenant().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    accessPolicies: []
    enablePurgeProtection: true
    softDeleteRetentionInDays: 7
  }
}

resource runtime 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-runtime'
  location: location
  tags: tags
}

var pullRole = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
resource registryPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, runtime.id, pullRole)
  scope: registry
  properties: {
    roleDefinitionId: pullRole
    principalId: runtime.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

var secretsRole = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
resource vaultRead 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(vault.id, runtime.id, secretsRole)
  scope: vault
  properties: {
    roleDefinitionId: secretsRole
    principalId: runtime.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

module integrations 'integrations.bicep' = if (provisionIntegrationServices) {
  name: '${prefix}-integrations'
  params: {
    location: location
    namespaceName: '${prefix}-${suffix}'
    storageName: '${take(prefix, 11)}${suffix}'
  }
}

output registryName string = registry.name
output vaultName string = vault.name
output databaseHost string = postgres.properties.fullyQualifiedDomainName
output databaseName string = database.name
