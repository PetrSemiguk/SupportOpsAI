param prefix string = 'supportops'
param registryName string
param vaultName string
@minLength(71)
@maxLength(71)
param backendDigest string
@minLength(71)
@maxLength(71)
param frontendDigest string
param foundryEndpoint string = ''
param foundryChatDeployment string = ''
param foundryEmbeddingDeployment string = ''
param enableFoundry bool = false
param enableLangSmith bool = false
param langSmithProject string = 'supportops-ai'
param alertActionGroupId string = ''

var location = resourceGroup().location

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

var identity = {
  type: 'UserAssigned'
  userAssignedIdentities: { '${runtime.id}': {} }
}
var registryCredentials = [
  { server: registry.properties.loginServer, identity: runtime.id }
]
var secretUri = '${vault.properties.vaultUri}secrets'
var databaseSecret = { name: 'database-url', keyVaultUrl: '${secretUri}/database-url', identity: runtime.id }
var databaseEnv = { name: 'DATABASE_URL', secretRef: databaseSecret.name }
var backend = '${registry.properties.loginServer}/supportops/backend@${backendDigest}'
var frontend = '${registry.properties.loginServer}/supportops/frontend@${frontendDigest}'

var apiSecrets = [
  databaseSecret
  { name: 'demo-customer-tokens', keyVaultUrl: '${secretUri}/demo-customer-tokens', identity: runtime.id }
  { name: 'demo-operator-token', keyVaultUrl: '${secretUri}/demo-operator-token', identity: runtime.id }
  { name: 'n8n-completion-token', keyVaultUrl: '${secretUri}/n8n-completion-token', identity: runtime.id }
]

resource web 'Microsoft.App/containerApps@2025-01-01' = {
  name: '${prefix}-web'
  location: location
  identity: identity
  properties: {
    environmentId: environment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      registries: registryCredentials
      secrets: apiSecrets
      ingress: {
        external: true
        allowInsecure: false
        transport: 'http'
        targetPort: 80
      }
    }
    template: {
      scale: { minReplicas: 1, maxReplicas: 2 }
      containers: [
        {
          name: 'web'
          image: frontend
          resources: { cpu: json('0.25'), memory: '0.5Gi' }
          env: [{ name: 'API_UPSTREAM', value: '127.0.0.1:8000' }]
          probes: [
            { type: 'Startup', httpGet: { path: '/', port: 80 }, periodSeconds: 2, failureThreshold: 30 }
            { type: 'Liveness', httpGet: { path: '/', port: 80 }, periodSeconds: 15 }
            { type: 'Readiness', httpGet: { path: '/api/health/ready', port: 80 }, periodSeconds: 5 }
          ]
        }
        {
          name: 'api'
          image: backend
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [
            databaseEnv
            { name: 'DEMO_CUSTOMER_TOKENS', secretRef: 'demo-customer-tokens' }
            { name: 'DEMO_OPERATOR_TOKEN', secretRef: 'demo-operator-token' }
            { name: 'N8N_COMPLETION_TOKEN', secretRef: 'n8n-completion-token' }
          ]
          probes: [
            { type: 'Startup', httpGet: { path: '/api/health/live', port: 8000 }, periodSeconds: 2, failureThreshold: 30 }
            { type: 'Liveness', httpGet: { path: '/api/health/live', port: 8000 }, periodSeconds: 15 }
          ]
        }
      ]
    }
  }
}

var workerSecrets = concat(
  [databaseSecret],
  enableFoundry ? [{ name: 'foundry-api-key', keyVaultUrl: '${secretUri}/foundry-api-key', identity: runtime.id }] : [],
  enableLangSmith ? [{ name: 'langsmith-api-key', keyVaultUrl: '${secretUri}/langsmith-api-key', identity: runtime.id }] : []
)

resource worker 'Microsoft.App/containerApps@2025-01-01' = {
  name: '${prefix}-worker'
  location: location
  identity: identity
  properties: {
    environmentId: environment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      registries: registryCredentials
      secrets: workerSecrets
    }
    template: {
      scale: { minReplicas: 1, maxReplicas: 1 }
      containers: [
        {
          name: 'worker'
          image: backend
          command: ['.venv/bin/python']
          args: ['-m', 'supportops.worker']
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: concat(
            [databaseEnv],
            enableFoundry ? [
              { name: 'FOUNDRY_ENABLED', value: 'true' }
              { name: 'FOUNDRY_ENDPOINT', value: foundryEndpoint }
              { name: 'FOUNDRY_CHAT_DEPLOYMENT', value: foundryChatDeployment }
              { name: 'FOUNDRY_EMBEDDING_DEPLOYMENT', value: foundryEmbeddingDeployment }
              { name: 'FOUNDRY_API_KEY', secretRef: 'foundry-api-key' }
            ] : [],
            enableLangSmith ? [
              { name: 'SUPPORTOPS_LANGSMITH_ENABLED', value: 'true' }
              { name: 'SUPPORTOPS_LANGSMITH_PROJECT', value: langSmithProject }
              { name: 'SUPPORTOPS_LANGSMITH_API_KEY', secretRef: 'langsmith-api-key' }
            ] : []
          )
        }
      ]
    }
  }
}

resource restartAlerts 'Microsoft.Insights/metricAlerts@2018-03-01' = [for appName in ['web', 'worker']: {
  name: '${prefix}-${appName}-restarts'
  location: 'global'
  properties: {
    description: 'A replica of the SupportOps ${appName} app has restarted.'
    severity: 3
    enabled: true
    scopes: [resourceId('Microsoft.App/containerApps', '${prefix}-${appName}')]
    evaluationFrequency: 'PT1M'
    windowSize: 'PT5M'
    autoMitigate: true
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'ReplicaRestarted'
          metricNamespace: 'Microsoft.App/containerapps'
          metricName: 'RestartCount'
          operator: 'GreaterThan'
          threshold: 0
          timeAggregation: 'Maximum'
        }
      ]
    }
    actions: empty(alertActionGroupId) ? [] : [{ actionGroupId: alertActionGroupId }]
  }
  dependsOn: [web, worker]
}]

output webUrl string = 'https://${web.properties.configuration.ingress.fqdn}'
output webName string = web.name
output workerName string = worker.name
