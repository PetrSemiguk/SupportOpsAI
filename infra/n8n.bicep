param prefix string = 'supportops'
param adminUsername string = 'automationadmin'
@description('Public SSH key. Supply an RSA key of at least 2048 bits.')
param sshPublicKey string
@description('Operator public IPv4 address without a CIDR suffix. Only this address can use SSH.')
@minLength(7)
@maxLength(15)
param operatorIp string
param vmSize string = 'Standard_B2s'

var location = resourceGroup().location

resource network 'Microsoft.Network/virtualNetworks@2024-05-01' existing = {
  name: '${prefix}-network'
}

resource publicIp 'Microsoft.Network/publicIPAddresses@2024-05-01' = {
  name: '${prefix}-n8n-ip'
  location: location
  sku: { name: 'Standard' }
  properties: { publicIPAllocationMethod: 'Static', publicIPAddressVersion: 'IPv4' }
}

resource firewall 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: '${prefix}-n8n-nsg'
  location: location
  properties: {
    securityRules: [
      {
        name: 'operator-ssh'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          sourceAddressPrefix: '${operatorIp}/32'
          destinationPortRange: '22'
          destinationAddressPrefix: '*'
        }
      }
      {
        name: 'deny-other-inbound'
        properties: {
          priority: 110
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourcePortRange: '*'
          sourceAddressPrefix: '*'
          destinationPortRange: '*'
          destinationAddressPrefix: '*'
        }
      }
    ]
  }
}

resource nic 'Microsoft.Network/networkInterfaces@2024-05-01' = {
  name: '${prefix}-n8n-nic'
  location: location
  properties: {
    networkSecurityGroup: { id: firewall.id }
    ipConfigurations: [
      {
        name: 'primary'
        properties: {
          privateIPAllocationMethod: 'Dynamic'
          publicIPAddress: { id: publicIp.id }
          subnet: { id: resourceId('Microsoft.Network/virtualNetworks/subnets', network.name, 'automation') }
        }
      }
    ]
  }
}

resource vm 'Microsoft.Compute/virtualMachines@2024-11-01' = {
  name: '${prefix}-n8n'
  location: location
  properties: {
    hardwareProfile: { vmSize: vmSize }
    networkProfile: { networkInterfaces: [{ id: nic.id, properties: { primary: true } }] }
    osProfile: {
      computerName: '${prefix}-n8n'
      adminUsername: adminUsername
      customData: base64(loadTextContent('n8n.cloud-init.yaml'))
      linuxConfiguration: {
        disablePasswordAuthentication: true
        ssh: {
          publicKeys: [{ path: '/home/${adminUsername}/.ssh/authorized_keys', keyData: sshPublicKey }]
        }
      }
    }
    securityProfile: {
      securityType: 'TrustedLaunch'
      uefiSettings: { secureBootEnabled: true, vTpmEnabled: true }
    }
    storageProfile: {
      osDisk: { createOption: 'FromImage', managedDisk: { storageAccountType: 'StandardSSD_LRS' } }
      imageReference: {
        publisher: 'Canonical'
        offer: 'ubuntu-24_04-lts'
        sku: 'server'
        version: 'latest'
      }
    }
  }
}

output vmName string = vm.name
output sshAddress string = publicIp.properties.ipAddress
