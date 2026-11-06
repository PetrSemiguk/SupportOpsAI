param prefix string = 'supportops'
param registryName string
param vaultName string
@minLength(71)
@maxLength(71)
param backendDigest string
param seedDemoData bool = false

var prepareDatabase = '''
  .venv/bin/alembic upgrade head
  .venv/bin/python -m supportops.index_policies
  .venv/bin/python -m supportops.worker --setup
  '''
var seed = seedDemoData ? '\n.venv/bin/python -m supportops.seed_retail --download --directory /tmp/supportops-retail' : ''

resource environment 'Microsoft.App/managedEnvironments@2025-01-01' existing = {
  name: '${prefix}-apps'
}
resource registry 'Microsoft.ContainerRegistry/registries@2025-11-01' existing = {
  name: registryName
}
resource vault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: vaultName
}
resource runtime 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: '${prefix}-runtime'
}

resource migration 'Microsoft.App/jobs@2025-01-01' = {
  name: '${prefix}-migration'
  location: resourceGroup().location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${runtime.id}': {} }
  }
  properties: {
    environmentId: environment.id
    workloadProfileName: 'Consumption'
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 600
      replicaRetryLimit: 0
      manualTriggerConfig: { parallelism: 1, replicaCompletionCount: 1 }
      registries: [{ server: registry.properties.loginServer, identity: runtime.id }]
      secrets: [
        { name: 'database-url', keyVaultUrl: '${vault.properties.vaultUri}secrets/database-url', identity: runtime.id }
      ]
    }
    template: {
      containers: [
        {
          name: 'migrate'
          image: '${registry.properties.loginServer}/supportops/backend@${backendDigest}'
          command: ['/bin/sh']
          args: ['-ec', '${prepareDatabase}${seed}']
          env: [{ name: 'DATABASE_URL', secretRef: 'database-url' }]
          resources: { cpu: json('0.5'), memory: '1Gi' }
        }
      ]
    }
  }
}

output jobName string = migration.name
