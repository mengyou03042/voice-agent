#!/usr/bin/env bash
# Copyright (c) Microsoft. All rights reserved.
# Step 3 of 3: run the Voice Agent portal in YOUR Azure Container App, connected to YOUR Foundry project.
#
# Needs no options: it reads what prepare.sh saved in portal/.env and runs the newest image that
# build.sh put in your registry, with a user-assigned managed identity, grants that identity access to
# your project, and protects the public URL before exposing it. Re-running is safe: existing resources
# are reused. To change who may open the portal, rerun prepare.sh --reconfigure and then only this step.
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

usage() {
  cat <<'EOF'
Usage: skills/portal-remote/scripts/deploy.sh [options]
       skills/portal-remote/scripts/deploy.sh --list-projects

Every value defaults to what prepare.sh saved; options override it for this run only. All values are
checked before anything is created.
  --resource-group RG      The resource group of build.sh; the app is created there
  --project-endpoint URL   https://<account>.services.ai.azure.com/api/projects/<project>

Access protection (default: what prepare.sh saved). Switching modes applies the new protection before
the old one is removed, so there is no unprotected moment.
  --auth ip --allowed-ip CIDR[,CIDR...]   Allow only these public source ranges (repeatable; a bare
                           address means /32). Look them up in a browser on your office/VPN network;
                           an address looked up inside Azure Cloud Shell is an Azure address, not yours.
  --auth entra             Microsoft Entra sign-in for users of YOUR tenant (Container Apps built-in auth).
                           Creates a single-tenant app registration in your tenant unless you pass:
    --entra-client-id ID     Use an app registration an admin created (Web redirect URI
                             https://<app fqdn>/.auth/login/aad/callback, ID tokens enabled). Also set
                             ENTRA_CLIENT_SECRET=<its client secret> in the environment.
    --entra-renew-secret     Create a new client secret (1 year); run this before the current one expires
    --entra-assigned-only    Only users assigned to the app can sign in; an admin grants consent once
    --entra-service-management-reference REF  Set on a new app registration, if your tenant requires one
    --allowed-ip CIDR        Optional with entra: keep an IP allowlist as a second layer
  --auth none --i-understand-public   No protection: anyone with the URL acts as the app identity

Optional:
  --name NAME              Container App name (default voice-agent-portal)
  --subscription ID        Subscription for the deployment
  --image IMAGE            Run this image instead of the newest one in the registry (must be in that registry)
  --acr NAME               Registry of build.sh, if you passed --acr there
  --location REGION        Region for the app (default: the resource group's region)
  --environment NAME       Container Apps environment (default <name>-env; created if missing)
  --env KEY=VALUE          Extra portal setting, repeatable (e.g. VOICE_PORTAL_REALTIME_DEPLOYMENTS=my-rt)
  --skip-roles             Do not try to grant roles; print them for an admin instead
EOF
}

saved_ips="$(setting PORTAL_ACA_ALLOWED_IPS)"
PROJECT_ENDPOINT="$(setting endpoint)" RG="$(setting PORTAL_ACA_RESOURCE_GROUP)" LOCATION=""
NAME="$(setting PORTAL_ACA_NAME)" SUBSCRIPTION="$(setting PORTAL_ACA_SUBSCRIPTION_ID)" IMAGE=""
ACR="" ENV_NAME="" AUTH="$(setting PORTAL_ACA_AUTH)" ENTRA_CLIENT_ID="" ENTRA_ASSIGNED_ONLY=false
ENTRA_SMR="" ENTRA_RENEW_SECRET=false ALLOW_PUBLIC=false SKIP_ROLES=false
ALLOWED_IPS=() EXTRA_ENV=() LIST_PROJECTS=false IPS_GIVEN=false
NAME="${NAME:-voice-agent-portal}" AUTH="${AUTH:-ip}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --list-projects) LIST_PROJECTS=true; shift ;;
    --project-endpoint) PROJECT_ENDPOINT="${2%/}"; shift 2 ;;
    --resource-group) RG="$2"; shift 2 ;;
    --location) LOCATION="$2"; shift 2 ;;
    --name) NAME="$2"; shift 2 ;;
    --subscription) SUBSCRIPTION="$2"; shift 2 ;;
    --image) IMAGE="$2"; shift 2 ;;
    --acr) ACR="$2"; shift 2 ;;
    --environment) ENV_NAME="$2"; shift 2 ;;
    --auth) AUTH="$2"; shift 2 ;;
    --allowed-ip) $IPS_GIVEN || ALLOWED_IPS=(); IPS_GIVEN=true; ALLOWED_IPS+=("$2"); shift 2 ;;
    --entra-client-id) ENTRA_CLIENT_ID="$2"; shift 2 ;;
    --entra-assigned-only) ENTRA_ASSIGNED_ONLY=true; shift ;;
    --entra-renew-secret) ENTRA_RENEW_SECRET=true; shift ;;
    --entra-service-management-reference) ENTRA_SMR="$2"; shift 2 ;;
    --i-understand-public) ALLOW_PUBLIC=true; shift ;;
    --env) EXTRA_ENV+=("$2"); shift 2 ;;
    --skip-roles) SKIP_ROLES=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage; die "Unknown option: $1" ;;
  esac
done

# ---------- validate input (nothing is created before all of it passes) ----------
re='^https://([a-z0-9][a-z0-9-]*)\.services\.ai\.azure\.com/api/projects/([A-Za-z0-9][A-Za-z0-9._-]*)$'
$IPS_GIVEN || [[ -z "$saved_ips" ]] || ALLOWED_IPS=("$saved_ips")
if ! $LIST_PROJECTS; then
  [[ -n "$RG" && -n "$PROJECT_ENDPOINT" ]] || die "Nothing prepared yet: run skills/portal-remote/scripts/prepare.sh first."
  [[ "$PROJECT_ENDPOINT" =~ $re ]] \
    || die "'$PROJECT_ENDPOINT' is not a project endpoint (https://<account>.services.ai.azure.com/api/projects/<project>). Rerun prepare.sh --reconfigure."
fi
[[ "$NAME" =~ ^[a-z][a-z0-9-]{0,30}[a-z0-9]$ ]] || die "--name must be 2-32 lowercase letters, digits or hyphens."
# --allowed-ip values may be comma- or space-separated lists; a bare address means /32.
IPS=()
for value in ${ALLOWED_IPS[@]+"${ALLOWED_IPS[@]}"}; do
  if [[ "$value" == *"<"* || "$value" == *">"* ]]; then
    die "Replace the placeholder in --allowed-ip '$value' with your office/VPN egress ranges, e.g. 203.0.113.0/24,198.51.100.7."
  fi
  for ip in ${value//,/ }; do
    [[ "$ip" == */* ]] || ip="$ip/32"
    if ! [[ "$ip" =~ ^([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})/([0-9]{1,2})$ ]] \
        || (( 10#${BASH_REMATCH[1]} > 255 || 10#${BASH_REMATCH[2]} > 255 || 10#${BASH_REMATCH[3]} > 255 \
              || 10#${BASH_REMATCH[4]} > 255 || 10#${BASH_REMATCH[5]} > 32 )); then
      die "'$ip' is not an IPv4 address or range. Use your office/VPN egress range, e.g. 203.0.113.0/24 or 198.51.100.7."
    fi
    [[ "$ip" != */0 ]] || die "$ip allows every address. List your office/VPN ranges instead."
    IPS+=("$ip")
  done
done
ALLOWED_IPS=(${IPS[@]+"${IPS[@]}"})
case "$AUTH" in
  entra) ;;
  ip) $LIST_PROJECTS || [[ ${#ALLOWED_IPS[@]} -gt 0 ]] || die "No allowed addresses are saved: rerun prepare.sh --reconfigure (or pass --allowed-ip)." ;;
  none) $ALLOW_PUBLIC || die "--auth none exposes your project to anyone with the URL; add --i-understand-public to confirm."
        [[ ${#ALLOWED_IPS[@]} -eq 0 ]] || die "--allowed-ip with --auth none: use --auth ip instead." ;;
  *) die "--auth must be ip, entra or none." ;;
esac
# ${arr[@]+"${arr[@]}"} keeps empty arrays safe under set -u on macOS bash 3.2.
for kv in ${EXTRA_ENV[@]+"${EXTRA_ENV[@]}"}; do [[ "$kv" == *=* ]] || die "--env expects KEY=VALUE, got: $kv"; done
for tool in az curl; do command -v "$tool" >/dev/null || die "$tool is required (Azure Cloud Shell has all of them)."; done

# ---------- subscription & tooling ----------
log "Checking Azure sign-in"
[[ -n "$SUBSCRIPTION" ]] && az account set --subscription "$SUBSCRIPTION"
SUB_ID="$(az account show --query id -o tsv)" || die "Run az login first."
TENANT_ID="$(az account show --query tenantId -o tsv)"

# ---------- find the Foundry project (portal/setup_azure.py: one implementation for all scripts) ----------
if $LIST_PROJECTS; then python3 "$SETUP" projects; exit 0; fi
PROJECT_ID="" FOUNDRY_ACCOUNT_ID=""
log "Foundry project $PROJECT_ENDPOINT"
IFS=$'\t' read -r _ PROJECT_ID FOUNDRY_ACCOUNT_ID < <(python3 "$SETUP" projects --endpoint "$PROJECT_ENDPOINT" || true)
[[ -n "$PROJECT_ID" ]] || die "Rerun prepare.sh --reconfigure to choose a project you can see."
az resource show --ids "$PROJECT_ID" --query id -o tsv >/dev/null || die "Project not found or not readable: $PROJECT_ID"
FOUNDRY_SUB="$(cut -d/ -f3 <<<"$FOUNDRY_ACCOUNT_ID")" FOUNDRY_RG="$(cut -d/ -f5 <<<"$FOUNDRY_ACCOUNT_ID")"

# ---------- tooling (only after every value checked out) ----------
az extension add --name containerapp --upgrade --only-show-errors -y >/dev/null
for ns in Microsoft.App Microsoft.OperationalInsights Microsoft.ContainerRegistry Microsoft.ManagedIdentity; do
  az provider register --namespace "$ns" --only-show-errors >/dev/null
done

# ---------- names (the registry name is derived exactly as in build.sh) ----------
SUFFIX="$(printf '%s' "$SUB_ID/$RG/$NAME" | { sha256sum 2>/dev/null || shasum -a 256; } | cut -c1-8)"
ACR="${ACR:-vaportal$SUFFIX}" ENV_NAME="${ENV_NAME:-$NAME-env}" ID_NAME="$NAME-id"

# ---------- image from build.sh ----------
STEP1="skills/portal-remote/scripts/build.sh"
[[ "$(az group exists -n "$RG" -o tsv)" == "true" ]] || die "Resource group $RG not found. Run $STEP1 first."
LOCATION="${LOCATION:-$(az group show -n "$RG" --query location -o tsv)}"
ACR_ID="$(az acr show -n "$ACR" --query id -o tsv 2>/dev/null || true)"
[[ -n "$ACR_ID" ]] || die "Registry $ACR not found. Run $STEP1 first."
ACR_LOGIN="$(az acr show -n "$ACR" --query loginServer -o tsv)"
if [[ -z "$IMAGE" ]]; then
  TAG="$(az acr repository show-tags -n "$ACR" --repository voice-agent-portal --orderby time_desc --top 1 -o tsv 2>/dev/null || true)"
  [[ -n "$TAG" ]] || die "No portal image in $ACR yet. Run $STEP1 first."
  IMAGE="$ACR_LOGIN/voice-agent-portal:$TAG"
fi
log "Image $IMAGE"

# ---------- environment & identity ----------
log "Container Apps environment $ENV_NAME"
if ! az containerapp env show -n "$ENV_NAME" -g "$RG" -o none 2>/dev/null; then
  ENV_ERR="$(mktemp)"
  if ! az containerapp env create -n "$ENV_NAME" -g "$RG" -l "$LOCATION" --enable-workload-profiles true \
      --only-show-errors -o none 2>"$ENV_ERR"; then
    grep -q 'RequestDisallowedByPolicy' "$ENV_ERR" && grep -qiE 'vnet|virtual network' "$ENV_ERR" \
      || { cat "$ENV_ERR" >&2; die "Cannot create the Container Apps environment (see above)."; }
    # Many organizations require Container Apps environments inside a virtual network (Azure Policy).
    # The portal still gets its public HTTPS address, protected as configured below.
    VNET="$NAME-vnet" SUBNET="container-apps"
    log "Your organization requires a virtual network for Container Apps: creating $VNET"
    az network vnet show -g "$RG" -n "$VNET" -o none 2>/dev/null \
      || az network vnet create -g "$RG" -n "$VNET" -l "$LOCATION" --address-prefixes 10.240.0.0/16 --only-show-errors -o none \
      || die "Cannot create the virtual network (see above)."
    az network vnet subnet show -g "$RG" --vnet-name "$VNET" -n "$SUBNET" -o none 2>/dev/null \
      || az network vnet subnet create -g "$RG" --vnet-name "$VNET" -n "$SUBNET" --address-prefixes 10.240.0.0/23 \
           --delegations Microsoft.App/environments --only-show-errors -o none \
      || die "Cannot create the subnet (see above)."
    SUBNET_ID="$(az network vnet subnet show -g "$RG" --vnet-name "$VNET" -n "$SUBNET" --query id -o tsv)"
    az containerapp env create -n "$ENV_NAME" -g "$RG" -l "$LOCATION" --enable-workload-profiles true \
      --infrastructure-subnet-resource-id "$SUBNET_ID" --only-show-errors -o none \
      || die "Cannot create the Container Apps environment in the virtual network (see above)."
  fi
  rm -f "$ENV_ERR"
fi
ENV_DOMAIN="$(az containerapp env show -n "$ENV_NAME" -g "$RG" --query properties.defaultDomain -o tsv --only-show-errors)"
FQDN="$NAME.$ENV_DOMAIN"

log "Managed identity $ID_NAME"
az identity show -n "$ID_NAME" -g "$RG" -o none 2>/dev/null || az identity create -n "$ID_NAME" -g "$RG" -l "$LOCATION" -o none
ID_RES="$(az identity show -n "$ID_NAME" -g "$RG" --query id -o tsv)"
ID_PRINCIPAL="$(az identity show -n "$ID_NAME" -g "$RG" --query principalId -o tsv)"
ID_CLIENT="$(az identity show -n "$ID_NAME" -g "$RG" --query clientId -o tsv)"

# Roles of the portal identity (one list for all scripts: portal/setup_azure.py roles). Granting needs
# Owner, User Access Administrator or Role Based Access Control Administrator. Without it, the exact steps
# for an admin are printed and saved, and the run stops here if a required role is missing.
NEW_GRANTS=0 MISSING_REQUIRED=false ADMIN_STEPS=()
GRANT_ERR="$(mktemp)"
while IFS='|' read -r role_id role scope why need <&4; do
  # No Graph lookups here: some tenants block Graph from developer machines (AADSTS530084).
  if [[ -n "$(az role assignment list --scope "$scope" --fill-principal-name false --fill-role-definition-name false \
      --query "[?principalId=='$ID_PRINCIPAL' && ends_with(roleDefinitionId, '$role_id')].id | [0]" -o tsv 2>/dev/null)" ]]; then
    continue
  fi
  if ! $SKIP_ROLES; then
    log "Granting '$role' ($why)"
    if az role assignment create --assignee-object-id "$ID_PRINCIPAL" --assignee-principal-type ServicePrincipal \
        --role "$role_id" --scope "$scope" --only-show-errors -o none 2>"$GRANT_ERR"; then
      NEW_GRANTS=1
      continue
    fi
    grep -q 'AuthorizationFailed' "$GRANT_ERR" || cat "$GRANT_ERR" >&2
  fi
  ADMIN_STEPS+=("$role|$role_id|$scope|$why|$need")
  [[ "$need" != required ]] || MISSING_REQUIRED=true
done 4< <(python3 "$SETUP" roles --registry-id "$ACR_ID" --project-id "$PROJECT_ID" --account-id "$FOUNDRY_ACCOUNT_ID")
rm -f "$GRANT_ERR"
if [[ ${#ADMIN_STEPS[@]} -gt 0 ]]; then
  STEPS_FILE="$HOME/voice-agent-portal-admin-steps.txt"
  {
    echo "The Voice Agent portal needs these roles for its managed identity '$ID_NAME' (object id $ID_PRINCIPAL)."
    echo "Only an Owner, User Access Administrator or Role Based Access Control Administrator of each resource can grant them."
    echo
    echo "In the Azure portal, for each line: open the resource > Access control (IAM) > Add > Add role assignment >"
    echo "the role > Next > Assign access to: Managed identity > Select members > '$ID_NAME' > Review + assign."
    for step in "${ADMIN_STEPS[@]}"; do
      IFS='|' read -r role role_id scope why need <<<"$step"
      echo "  - '$role' on resource '${scope##*/}' ($need: $why)"
    done
    echo
    echo "Or with the Azure CLI (for example in Azure Cloud Shell):"
    for step in "${ADMIN_STEPS[@]}"; do
      IFS='|' read -r role role_id scope why need <<<"$step"
      echo "  az role assignment create --assignee-object-id $ID_PRINCIPAL --assignee-principal-type ServicePrincipal --role $role_id --scope $scope"
    done
  } > "$STEPS_FILE"
  printf '\n------------------------------------------------------------------------\n' >&2
  printf 'Your account cannot grant the portal its roles (Contributor is not enough).\nSend these steps to an admin:\n\n' >&2
  cat "$STEPS_FILE" >&2
  printf '\nSaved to %s (Cloud Shell: Manage files > Download, to send it).\n' "$STEPS_FILE" >&2
  printf -- '------------------------------------------------------------------------\n' >&2
  $MISSING_REQUIRED && die "Stopped before creating the app. After the admin granted the roles, run deploy.sh again (nothing is rebuilt)."
  warn "Only optional roles are missing; the portal works without them."
fi
[[ $NEW_GRANTS -eq 1 ]] && { log "Waiting 60 s for role assignments to propagate"; sleep 60; }

# ---------- container app (internal until protected) ----------
ENV_VARS=(
  "AZURE_CLIENT_ID=$ID_CLIENT"
  "AZURE_VOICE_AGENTS_ENDPOINT=$PROJECT_ENDPOINT"
  "AZURE_SUBSCRIPTION_ID=$FOUNDRY_SUB"
  "AZURE_RESOURCE_GROUP=$FOUNDRY_RG"
  ${EXTRA_ENV[@]+"${EXTRA_ENV[@]}"}
)
if az containerapp show -n "$NAME" -g "$RG" -o none 2>/dev/null; then
  log "Updating container app $NAME to $IMAGE"
  az containerapp update -n "$NAME" -g "$RG" --image "$IMAGE" --set-env-vars "${ENV_VARS[@]}" --only-show-errors -o none
else
  log "Creating container app $NAME (internal ingress until access protection is in place)"
  # --registry-identity makes the CLI try to grant AcrPull itself. AcrPull is already handled
  # above (or by the admin with --skip-roles), and that redundant attempt logs a misleading
  # "Role assignment failed" where Graph is blocked, so drop only that message on success.
  CREATE_ERR="$(mktemp)"
  for attempt in 1 2 3 4 5; do
    if az containerapp create -n "$NAME" -g "$RG" --environment "$ENV_NAME" --image "$IMAGE" \
        --user-assigned "$ID_RES" --registry-server "$ACR_LOGIN" --registry-identity "$ID_RES" \
        --ingress internal --target-port 8080 --transport auto \
        --min-replicas 1 --max-replicas 1 --cpu 0.5 --memory 1Gi \
        --env-vars "${ENV_VARS[@]}" --only-show-errors -o none 2>"$CREATE_ERR"; then
      grep -vE '^(ERROR: Role assignment failed|To add the role assignment manually|You may have to restart the containerapp)' "$CREATE_ERR" >&2 || true
      rm -f "$CREATE_ERR"
      break
    fi
    cat "$CREATE_ERR" >&2
    [[ $attempt -eq 5 ]] && { rm -f "$CREATE_ERR"; die "Container app creation failed."; }
    warn "Create failed (often AcrPull still propagating); retrying in 30 s"; sleep 30
  done
fi

# ---------- access protection ----------
# Switching modes applies the new protection first and removes the old one afterwards.
auth_enabled() {
  [[ "$(az containerapp auth show -n "$NAME" -g "$RG" --query platform.enabled -o tsv 2>/dev/null || true)" == "true" ]]
}

disable_entra() {
  if auth_enabled; then
    log "Turning off Entra sign-in"
    az containerapp auth update -n "$NAME" -g "$RG" --enabled false --only-show-errors -o none
  fi
}

# Writes allow-1..N for --allowed-ip and deletes allow-N rules from earlier runs that are no longer listed.
apply_ip_rules() {
  local i=0 cidr rule n
  if [[ ${#ALLOWED_IPS[@]} -gt 0 ]]; then
    log "Restricting ingress to: ${ALLOWED_IPS[*]}"
    for cidr in "${ALLOWED_IPS[@]}"; do
      i=$((i + 1))
      az containerapp ingress access-restriction set -n "$NAME" -g "$RG" --rule-name "allow-$i" \
        --ip-address "$cidr" --action Allow --only-show-errors -o none
    done
  fi
  for rule in $(az containerapp ingress access-restriction list -n "$NAME" -g "$RG" --query "[].name" -o tsv 2>/dev/null || true); do
    n="${rule#allow-}"
    if [[ "$rule" == allow-* && "$n" =~ ^[0-9]+$ ]] && (( n > i )); then
      log "Removing IP rule $rule (no longer listed)"
      az containerapp ingress access-restriction remove -n "$NAME" -g "$RG" --rule-name "$rule" --only-show-errors -o none
    fi
  done
}

configure_entra() {
  local callback="https://$FQDN/.auth/login/aad/callback" given="$ENTRA_CLIENT_ID" current secret=""
  if [[ -z "$ENTRA_CLIENT_ID" ]]; then
    local app_name="$NAME-portal-signin-$SUFFIX"
    ENTRA_CLIENT_ID="$(az ad app list --display-name "$app_name" --query '[0].appId' -o tsv)" \
      || die "Cannot read app registrations (Microsoft Graph). Ask an admin for one and rerun with --entra-client-id and ENTRA_CLIENT_SECRET, or use --auth ip."
    if [[ -z "$ENTRA_CLIENT_ID" ]]; then
      log "Creating Entra app registration $app_name"
      ENTRA_CLIENT_ID="$(az ad app create --display-name "$app_name" --sign-in-audience AzureADMyOrg \
        --web-redirect-uris "$callback" --enable-id-token-issuance true \
        ${ENTRA_SMR:+--service-management-reference "$ENTRA_SMR"} \
        --query appId -o tsv)" \
        || die "Cannot create an app registration. Ask an admin for one (single tenant, Web redirect URI $callback, ID tokens enabled, plus a client secret) and rerun with --entra-client-id and ENTRA_CLIENT_SECRET, or use --auth ip."
    fi
  fi
  current="$(az containerapp auth show -n "$NAME" -g "$RG" \
    --query "join('|', [to_string(platform.enabled), identityProviders.azureActiveDirectory.registration.clientId || ''])" -o tsv 2>/dev/null || true)"
  if [[ -n "${ENTRA_CLIENT_SECRET:-}" ]]; then
    secret="$ENTRA_CLIENT_SECRET"
  elif $ENTRA_RENEW_SECRET || [[ "$current" != "true|$ENTRA_CLIENT_ID" ]]; then
    secret="$(az ad app credential reset --id "$ENTRA_CLIENT_ID" --display-name "containerapp-$NAME" --years 1 --append --query password -o tsv)" \
      || die "Cannot create a client secret for $ENTRA_CLIENT_ID (you must own the app registration). Or set ENTRA_CLIENT_SECRET to an existing secret of it."
  fi
  if [[ -z "$secret" ]]; then
    log "Entra sign-in already configured (app $ENTRA_CLIENT_ID). Its client secret lasts 1 year: rerun with --entra-renew-secret before it expires."
  else
    log "Configuring Entra sign-in (app $ENTRA_CLIENT_ID)"
    az containerapp secret set -n "$NAME" -g "$RG" --secrets "microsoft-provider-authentication-secret=$secret" --only-show-errors -o none
    az containerapp auth microsoft update -n "$NAME" -g "$RG" --client-id "$ENTRA_CLIENT_ID" \
      --client-secret-name microsoft-provider-authentication-secret \
      --issuer "https://login.microsoftonline.com/$TENANT_ID/v2.0" --yes --only-show-errors -o none
    az containerapp auth update -n "$NAME" -g "$RG" --enabled true --require-https true \
      --unauthenticated-client-action RedirectToLoginPage --redirect-provider azureactivedirectory --only-show-errors -o none
    [[ -z "$given" ]] || warn "Make sure app $ENTRA_CLIENT_ID has the Web redirect URI $callback and ID tokens enabled."
  fi
  if $ENTRA_ASSIGNED_ONLY; then
    local sp_id me
    sp_id="$(az ad sp show --id "$ENTRA_CLIENT_ID" --query id -o tsv 2>/dev/null || az ad sp create --id "$ENTRA_CLIENT_ID" --query id -o tsv)"
    az ad sp update --id "$sp_id" --set appRoleAssignmentRequired=true
    me="$(az ad signed-in-user show --query id -o tsv)"
    az rest --method post --url "https://graph.microsoft.com/v1.0/servicePrincipals/$sp_id/appRoleAssignedTo" \
      --body "{\"principalId\":\"$me\",\"resourceId\":\"$sp_id\",\"appRoleId\":\"00000000-0000-0000-0000-000000000000\"}" \
      -o none 2>/dev/null || true
    log "Only assigned users can sign in. Assign more under Enterprise apps > $ENTRA_CLIENT_ID > Users and groups."
    warn "Assignment required turns off user consent for this app. An admin (Cloud Application Administrator or above) must grant tenant-wide admin consent once: Entra admin center > Enterprise apps > $ENTRA_CLIENT_ID > Permissions > Grant admin consent."
  fi
}

case "$AUTH" in
  ip) apply_ip_rules; disable_entra ;;
  entra) configure_entra; apply_ip_rules ;;
  none) apply_ip_rules; disable_entra; warn "No access protection: anyone with the URL can use your project through this portal." ;;
esac

log "Exposing https://$FQDN"
az containerapp ingress update -n "$NAME" -g "$RG" --type external --only-show-errors -o none

# ---------- smoke check ----------
log "Waiting for the portal to answer"
code=000
for _ in $(seq 1 40); do
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "https://$FQDN/healthz" || true)"
  [[ "$code" =~ ^(200|302|401|403)$ ]] && break
  sleep 6
done
case "$AUTH:$code" in
  entra:302|entra:401) msg="protected by Entra sign-in (unauthenticated request got $code)" ;;
  ip:200|none:200) msg="healthy (HTTP 200 from this machine)" ;;
  ip:403) msg="running; this machine's IP is not in the allowlist (HTTP 403)" ;;
  *) msg="unexpected HTTP $code; check: az containerapp logs show -n $NAME -g $RG --follow" ;;
esac

cat <<EOF

Portal URL      : https://$FQDN/editor/
Status          : $msg
Foundry project : $PROJECT_ENDPOINT
Image           : $IMAGE
Identity        : $ID_NAME (client id $ID_CLIENT, principal $ID_PRINCIPAL)
Access          : $AUTH${ENTRA_CLIENT_ID:+ (app $ENTRA_CLIENT_ID)}
Logs            : az containerapp logs show -n $NAME -g $RG --follow
Remove          : az group delete -n $RG   (Agents in the Foundry project are not deleted)
EOF
if [[ "$AUTH" == entra ]]; then
  echo "                  The app registration $ENTRA_CLIENT_ID is not in the resource group; when no longer needed: az ad app delete --id $ENTRA_CLIENT_ID"
fi
# In Cloud Shell a correct office/VPN allowlist answers 403 above. A 200 means the list includes this
# Cloud Shell's outbound address, an Azure address that other Azure tenants can use too.
if [[ "$AUTH:$code" == ip:200 && ( "${AZUREPS_HOST_ENVIRONMENT:-}" == cloud-shell* || -n "${ACC_CLOUD:-}" ) ]]; then
  warn "Cloud Shell can open the portal, so your --allowed-ip list includes an Azure address (probably looked up in Cloud Shell). Rerun with the egress ranges of your office/VPN, looked up from a browser there."
fi
