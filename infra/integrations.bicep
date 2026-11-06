param location string
param namespaceName string
param storageName string

resource bus 'Microsoft.ServiceBus/namespaces@2024-01-01' = {
  name: namespaceName
  location: location
  sku: { name: 'Basic', tier: 'Basic' }
  properties: { disableLocalAuth: true, minimumTlsVersion: '1.2' }
}

resource queue 'Microsoft.ServiceBus/namespaces/queues@2024-01-01' = {
  parent: bus
  name: 'ticket-events'
  properties: {
    defaultMessageTimeToLive: 'P7D'
    deadLetteringOnMessageExpiration: true
    maxDeliveryCount: 5
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowSharedKeyAccess: false
    allowBlobPublicAccess: false
    publicNetworkAccess: 'Disabled'
  }
}

resource blobs 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
}

resource artifacts 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobs
  name: 'supportops-artifacts'
  properties: { publicAccess: 'None' }
}
