# Azure demo runbook

The templates target a dedicated Azure resource group. The default footprint is
an Azure Container Apps Consumption environment, two apps, a manual migration
job, PostgreSQL Flexible Server 17 with pgvector, ACR Basic, Key Vault and a Log
Analytics workspace. Deploying this footprint incurs Azure charges. Confirm the
budget, regional SKU availability, quotas and Azure Policy before provisioning.
For Singapore, create the resource group in `southeastasia`.

The public app runs Nginx and FastAPI in the same replica. Nginx serves React and
proxies `/api/` to FastAPI over loopback. The worker has no ingress and polls the
PostgreSQL queue. The database has private networking and a linked DNS zone.
Azure Container Apps pulls the images and reads Key Vault references using a
managed identity. Use synthetic data and dedicated demo credentials.

`provisionIntegrationServices=true` adds a Service Bus namespace and a Blob
account. They are reserved for later integrations. The app currently uses
PostgreSQL for its queue and completion events and reads its policy source from
the image. Blob access would need private connectivity and a data-plane role.
The n8n VM is provisioned separately.

## Local validation

From the repository root, with Bicep CLI 0.48.1, Bash and actionlint installed:

```bash
for template in infra/*.bicep; do
  bicep build "$template" --stdout > /dev/null || exit 1
done
bash -n infra/deploy.sh
actionlint
```

Bicep compilation checks the templates locally. Azure deployment validation,
regional capacity, DNS, identity propagation and runtime smoke tests require the
target subscription.

## 1. Provision the foundation

After budget approval, sign in to the intended Azure subscription with Azure CLI
and install Bicep with `az bicep install --version v0.48.1`. The provisioning
identity needs resource creation and role assignment rights in the dedicated
group. Register the resource providers used by the templates if the subscription
requires it. Use a prefix with 3–12 lowercase letters or digits, starting with a
letter.

```powershell
$rg = 'supportops-demo'
$prefix = 'supportops'
az group create --name $rg --location southeastasia --output none
az deployment group create --resource-group $rg --name foundation --template-file infra/main.bicep --parameters "prefix=$prefix" --query properties.outputs
```

Enter the PostgreSQL password at Azure CLI's secure parameter prompt. The
deployment outputs include the registry name, vault name, database host and
database name. Give the owner `Key Vault Secrets Officer` at vault scope for
initial setup, then use the vault's Secrets page to set these values.

| Secret name | Value |
| --- | --- |
| `database-url` | SQLAlchemy URL for the dedicated demo database, as shown below |
| `demo-customer-tokens` | JSON object mapping demo customer aliases to distinct random tokens |
| `demo-operator-token` | Separate random token for operator access |
| `n8n-completion-token` | Separate random token for completion polling and acknowledgement |

```text
postgresql+psycopg://supportops_admin:<url-encoded-password>@<database-host>:5432/supportops?sslmode=verify-full&sslrootcert=/etc/ssl/certs/ca-certificates.crt
```

Use the server hostname from the deployment output so the client can verify
its TLS certificate. This demo uses the database owner for migrations and
runtime. Keep the vault and identity dedicated to this demo. The user-assigned
identity receives `AcrPull` and `Key Vault Secrets User` from Bicep. Allow time
for role propagation before the first release.

## 2. Configure manual workflows

Create GitHub environments `azure-publish` and `azure-deploy`, restrict them to
`main`, and set reviewers where available. Use separate Microsoft Entra
application identities. For each, configure a federated credential with issuer
`https://token.actions.githubusercontent.com`, audience
`api://AzureADTokenExchange` and the matching subject.

| Environment | Federated subject | Azure roles |
| --- | --- | --- |
| `azure-publish` | `repo:PetrSemiguk/SupportOpsAI:environment:azure-publish` | `Reader` and `AcrPush` on the registry |
| `azure-deploy` | `repo:PetrSemiguk/SupportOpsAI:environment:azure-deploy` | `Contributor` on the dedicated group and `AcrPull` on the registry |

Add environment secrets `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` and
`AZURE_SUBSCRIPTION_ID` for the corresponding identity. These identify the
federation and require no client password.

Set `AZURE_REGISTRY_NAME` and `AZURE_RESOURCE_GROUP` in both environments.
In `azure-deploy`, also set `AZURE_NAME_PREFIX` and `AZURE_VAULT_NAME`.
`AZURE_ALERT_ACTION_GROUP_ID` is optional. Use an action group in the same
resource group, or give the deploy identity access to the selected group.

1. Dispatch **Publish Azure images** from `main`. Copy the image tag from its
   summary after both pushes succeed.
2. Dispatch **Deploy Azure demo** with that tag. Select `seed_demo_data` on the
   first run to download and checksum the pinned research fixture, then import
   the demo customers and orders. Re-running the seed preserves existing orders.
3. The deployment resolves both image digests before changing anything. It
   waits for the exact migration execution to succeed, deploys both apps and
   checks the latest revisions, web root and API readiness. Save the digests
   from the summary for rollback.
4. At the HTTPS address, sign in with demo tokens and submit an order status
   request. Verify the worker completes it and the operator sees a policy citation.
   Confirm cancellation and return through the normal operator approval path.

The manual workflow deploys with Foundry and LangSmith disabled. Following
separate authorization, an owner can apply `apps.bicep` with the same image
digests and set `enableFoundry`, `foundryEndpoint` and `foundryChatDeployment`.
Put `foundry-api-key` in the vault. Set `foundryEmbeddingDeployment` only after
planning the separate hosted policy index build from inside the virtual network.
To enable LangSmith, set `enableLangSmith` and store `langsmith-api-key`.
A later manual workflow deployment restores the offline defaults.

## 3. Optional n8n VM

Deploy `infra/n8n.bicep` into the same group after approval for the VM, disk and
public IP. Pass the prefix, your RSA SSH public key in `sshPublicKey` and your
public IPv4 address in `operatorIp`. The network rule admits SSH only from that
address. Cloud-init installs Docker and the Compose plugin.

1. Copy `infra/n8n.compose.yaml` to the VM as `compose.yaml`. After
   `sudo cloud-init status --wait`, create a private `.env` on the VM with a
   persistent random `N8N_ENCRYPTION_KEY`. Back up the key and n8n volume
   together. Run `sudo docker compose up -d`.
2. Forward the editor and webhook over SSH using
   `ssh -N -L 5678:127.0.0.1:5678 automationadmin@<sshAddress>`.
   Open `http://localhost:5678` from your machine. Stop any local instance using
   port 5678 before opening the tunnel.
3. Import both workflows using the [n8n setup guide](../n8n/README.md). Set up
   fresh credentials and use the same completion token as in Key Vault. In
   **Create or replay ticket**, **Read pending completions** and **Record demo
   notification**, replace `http://api:8000` with the Azure HTTPS base URL. Publish
   the workflows and use the local forwarded URL for demo webhook requests.

The VM exposes n8n through the SSH tunnel for a private operator demo. Public
webhook access would require separate HTTPS ingress configuration.

## 4. Monitor and recover

Azure Monitor provides `RestartCount` alerts for the web/API app and worker.
An action group can send alerts to the owner. The workspace stores app console
and system logs with 30-day retention and a daily ingestion cap. Start with
**Container Apps → Revisions**, then check the migration execution status and
`ContainerAppSystemLogs_CL` or `ContainerAppConsoleLogs_CL` in Log Analytics.
Inspect startup/registry/Key Vault errors before retrying.

If a migration fails, inspect its logs and fix the cause before redeploying.
The workflow leaves the existing app revisions in place at that stage.
Use schema changes compatible with the currently running app. For an app-only
rollback, apply `apps.bicep` with the prior working backend/frontend digests
and the same foundation parameters, after checking schema compatibility.
Recover database changes through the configured backup and restore process.

When ending the demo, back up data you need and remove the dedicated resource
group through Azure. Stopping the optional VM leaves its disk and public IP.
Review residual charges, vault retention and the federated credentials after
teardown.

References

- [Container Apps networking](https://learn.microsoft.com/en-us/azure/container-apps/networking)
- [PostgreSQL TLS verification](https://learn.microsoft.com/en-us/azure/postgresql/security/security-tls-how-to-connect)
- [Container Apps Key Vault references](https://learn.microsoft.com/en-us/azure/container-apps/manage-secrets)
- [GitHub Actions OIDC reference](https://docs.github.com/en/actions/reference/security/oidc)
