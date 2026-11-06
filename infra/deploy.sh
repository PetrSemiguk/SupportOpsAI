#!/usr/bin/env bash
set -euo pipefail

: "${RESOURCE_GROUP:?Set AZURE_RESOURCE_GROUP}"
: "${NAME_PREFIX:?Set AZURE_NAME_PREFIX}"
: "${REGISTRY:?Set AZURE_REGISTRY_NAME}"
: "${VAULT:?Set AZURE_VAULT_NAME}"
: "${IMAGE_TAG:?Supply the published image tag}"
if [[ ! "$IMAGE_TAG" =~ ^[0-9a-f]{40}-[0-9]+-[0-9]+$ ]]; then
    echo "Expected a commit SHA, run ID and attempt from the publishing workflow." >&2
    exit 1
fi

registry_digest() {
    local image="$1"
    local digest
    digest=$(az acr repository show --name "$REGISTRY" --image "$image:$IMAGE_TAG" --query digest --output tsv)
    if [[ ! "$digest" =~ ^sha256:[0-9a-f]{64}$ ]]; then
        echo "No valid digest found for $image:$IMAGE_TAG." >&2
        return 1
    fi
    printf '%s\n' "$digest"
}

wait_for_migration() {
    local execution="$1"
    local status
    for (( attempt = 0; attempt < 72; attempt++ )); do
        if status=$(az containerapp job execution show --resource-group "$RESOURCE_GROUP" --name "$migration_job" --job-execution-name "$execution" --query properties.status --output tsv); then
            case "$status" in
                Succeeded) return 0 ;;
                Failed|Stopped|Degraded)
                    echo "Migration $execution finished with $status." >&2
                    return 1
                    ;;
            esac
        fi
        sleep 10
    done
    echo "Migration $execution did not succeed before the deadline." >&2
    return 1
}

wait_for_revision() {
    local name="$1"
    local ready
    local query='properties.latestRevisionName != null && properties.latestRevisionName == properties.latestReadyRevisionName'
    for (( attempt = 0; attempt < 36; attempt++ )); do
        if ready=$(az containerapp show --resource-group "$RESOURCE_GROUP" --name "$name" --query "$query" --output tsv) && [[ "${ready,,}" == true ]]; then
            return 0
        fi
        sleep 5
    done
    echo "The latest revision of $name did not become ready." >&2
    return 1
}

backend_digest=$(registry_digest supportops/backend)
frontend_digest=$(registry_digest supportops/frontend)
base_parameters=("prefix=$NAME_PREFIX" "registryName=$REGISTRY" "vaultName=$VAULT" "backendDigest=$backend_digest")
deployment=(deployment group create --resource-group "$RESOURCE_GROUP")
migration_parameters=("${base_parameters[@]}" "seedDemoData=${SEED_DEMO_DATA:-false}")
migration_job=$(az "${deployment[@]}" --template-file infra/migration.bicep --parameters "${migration_parameters[@]}" --query properties.outputs.jobName.value --output tsv)
execution=$(az containerapp job start --name "$migration_job" --resource-group "$RESOURCE_GROUP" --query name --output tsv)
if [[ -z "$execution" || "$execution" == null ]]; then
    echo "Azure did not return a migration execution name." >&2
    exit 1
fi
wait_for_migration "$execution"

app_parameters=("${base_parameters[@]}" "frontendDigest=$frontend_digest" "alertActionGroupId=${ALERT_ACTION_GROUP_ID:-}")
web_url=$(az "${deployment[@]}" --template-file infra/apps.bicep --parameters "${app_parameters[@]}" --query properties.outputs.webUrl.value --output tsv)
[[ "$web_url" == https://* ]]
wait_for_revision "$NAME_PREFIX-web"
wait_for_revision "$NAME_PREFIX-worker"
curl --fail --silent --show-error --max-time 15 --retry 5 "$web_url/" > /dev/null
curl --fail --silent --show-error --max-time 15 --retry 5 "$web_url/api/health/ready"
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    printf 'Deployed %s\n\n- Backend: `%s`\n- Frontend: `%s`\n' "$web_url" "$backend_digest" "$frontend_digest" >> "$GITHUB_STEP_SUMMARY"
fi
