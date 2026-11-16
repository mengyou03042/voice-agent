#!/usr/bin/env bash
# Copyright (c) Microsoft. All rights reserved.
# Step 1 of 2: build the Voice Agent Portal image in YOUR Azure Container Registry.
#
# Run it in Azure Cloud Shell (bash) from a voice-agent checkout. The build runs in Azure (az acr build):
# your network never needs Docker, PyPI or Docker Hub. It builds the commit checked out here:
# git pull (or git checkout <tag>) first to choose the version.
# Step 2, deploy_app.sh, runs the newest image of this registry in a Container App.
set -euo pipefail
usage() {
  cat <<'EOF'
Usage: portal/deploy/aca/build_image.sh --resource-group RG [--location REGION] [options]
  --resource-group RG   Resource group for the registry and the portal (created if missing)
  --location REGION     Azure region, e.g. westus2. Needed only when the resource group does not exist yet
  --name NAME           Portal name (default voice-agent-portal). Use the same name in deploy_app.sh
  --subscription ID     Subscription (default: current az account)
  --acr NAME            Registry name (default derived from subscription, resource group and name; created if missing)
  --tag KEY=VALUE       Resource-group tag, repeatable (pass any tags your policy requires). Merged into an
                        existing group; the group's other tags are never removed
EOF
}
log() { printf '\n==> %s\n' "$*" >&2; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
# The portal runs in the resource group's region (step 2 default), so it must offer Container Apps.
check_region() {
  local display
  display="$(az account list-locations --query "[?name=='$1'].displayName | [0]" -o tsv)"
  [[ -n "$display" ]] || die "Unknown region '$1'. Use a short name such as westus2, eastus2 or swedencentral (list: az account list-locations -o table)."
  az provider show -n Microsoft.App --query "resourceTypes[?resourceType=='managedEnvironments'].locations[]" -o tsv \
    | grep -qixF "$display" || die "Azure Container Apps is not available in $1 ($display). Choose another region."
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$(cd "$SCRIPT_DIR/../../.." && pwd)"
RG="" LOCATION="" NAME="voice-agent-portal" SUBSCRIPTION="" ACR="" TAGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --resource-group) RG="$2"; shift 2 ;;
    --location) LOCATION="$2"; shift 2 ;;
    --name) NAME="$2"; shift 2 ;;
    --subscription) SUBSCRIPTION="$2"; shift 2 ;;
    --acr) ACR="$2"; shift 2 ;;
    --tag) TAGS+=("$2"); shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) usage; die "Unknown option: $1" ;;
  esac
done
[[ -n "$RG" ]] || { usage; die "--resource-group is required."; }
LOCATION="$(printf '%s' "$LOCATION" | tr -d ' ' | tr '[:upper:]' '[:lower:]')"   # "West US 2" -> westus2
[[ "$NAME" =~ ^[a-z][a-z0-9-]{0,30}[a-z0-9]$ ]] || die "--name must be 2-32 lowercase letters, digits or hyphens."
for tool in az git tar; do command -v "$tool" >/dev/null || die "$tool is required (Azure Cloud Shell has all of them)."; done
[[ -f "$SOURCE/portal/demo_server.py" ]] || die "$SOURCE is not a voice-agent checkout (portal/demo_server.py missing)."
git -C "$SOURCE" rev-parse --git-dir >/dev/null 2>&1 || die "$SOURCE is not a git checkout: get the code with git clone."

log "Checking Azure sign-in"
[[ -n "$SUBSCRIPTION" ]] && az account set --subscription "$SUBSCRIPTION"
SUB_ID="$(az account show --query id -o tsv)" || die "Run az login first."
az provider register --namespace Microsoft.ContainerRegistry --only-show-errors >/dev/null

# deploy_app.sh derives the same registry name from the same inputs.
SUFFIX="$(printf '%s' "$SUB_ID/$RG/$NAME" | { sha256sum 2>/dev/null || shasum -a 256; } | cut -c1-8)"
ACR="${ACR:-vaportal$SUFFIX}"

# Never re-PUT an existing group: "az group create" replaces its tags (and policy may deny that).
if [[ "$(az group exists -n "$RG" -o tsv)" == "true" ]]; then
  log "Resource group $RG (existing; its tags are kept)"
  if [[ ${#TAGS[@]} -gt 0 ]]; then
    az tag update --resource-id "$(az group show -n "$RG" --query id -o tsv)" --operation Merge \
      --tags "${TAGS[@]}" --only-show-errors -o none
  fi
  LOCATION="$(az group show -n "$RG" --query location -o tsv)"
  check_region "$LOCATION"
else
  [[ -n "$LOCATION" ]] || die "Resource group $RG does not exist: pass --location to create it."
  check_region "$LOCATION"
  log "Creating resource group $RG ($LOCATION)"
  TAG_ARGS=()
  if [[ ${#TAGS[@]} -gt 0 ]]; then TAG_ARGS=(--tags "${TAGS[@]}"); fi
  az group create -n "$RG" -l "$LOCATION" ${TAG_ARGS[@]+"${TAG_ARGS[@]}"} --only-show-errors -o none \
    || die "Cannot create resource group $RG. If a policy requires tags, pass them with --tag KEY=VALUE (e.g. --tag OwnerAlias=<you>)."
fi

log "Container registry $ACR"
if ! az acr show -n "$ACR" -o none 2>/dev/null; then
  az acr create -n "$ACR" -g "$RG" -l "$LOCATION" --sku Basic --admin-enabled false --only-show-errors -o none
fi
ACR_LOGIN="$(az acr show -n "$ACR" --query loginServer -o tsv)"

# Tracked files only (including uncommitted edits to them): never ships .env, virtual environments,
# node_modules or local logs. `git stash create` snapshots the working tree without touching it.
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
REV="$(git -C "$SOURCE" rev-parse --short HEAD)"
DIRTY="$(git -C "$SOURCE" status --porcelain -- portal samples docs | head -1)"
SNAPSHOT="$(git -C "$SOURCE" stash create 2>/dev/null || true)"
mkdir -p "$WORK/context"
git -C "$SOURCE" archive --format=tar "${SNAPSHOT:-HEAD}" -- portal samples docs \
  ':(exclude)portal/web' ':(exclude)portal/tests' ':(exclude)portal/tools' | tar -xf - -C "$WORK/context"
TAG="$REV${DIRTY:+-dirty}-$(date -u +%Y%m%d%H%M%S)"
IMAGE="$ACR_LOGIN/voice-agent-portal:$TAG"
log "Building $IMAGE in Azure (voice-agent $REV${DIRTY:+, with local changes})"
az acr build --registry "$ACR" --image "voice-agent-portal:$TAG" --platform linux/amd64 \
  --file portal/deploy/aca/Dockerfile "$WORK/context" --only-show-errors -o none

NEXT="portal/deploy/aca/deploy_app.sh --resource-group $RG"
[[ "$NAME" == voice-agent-portal ]] || NEXT+=" --name $NAME"
[[ "$ACR" == "vaportal$SUFFIX" ]] || NEXT+=" --acr $ACR"
cat <<EOF

Image : $IMAGE
Next  : $NEXT \\
          --project-endpoint "\$PROJECT_ENDPOINT" --allowed-ip "\$ALLOWED_IPS"
        (PROJECT_ENDPOINT and ALLOWED_IPS as set in step 0 of portal/deploy/aca/README.md)
EOF
