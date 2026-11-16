# Share the portal with your team on Azure Container Apps

The [Voice Agent portal](../../README.md) runs on your own computer by default, and that stays the recommended way to use it: [run it locally](../../README.md#run-locally). It has no sign-in of its own; it only accepts requests from the same computer and calls Foundry with your own Azure identity.

This folder is an **optional** alternative for teams that want one shared URL. Two scripts, run in [Azure Cloud Shell](https://shell.azure.com), build the unchanged portal into a container image in **your own** Azure Container Registry and run it in an Azure Container App in **your own** subscription, connected to **your own** Foundry project. Because a public URL removes the "same computer only" protection, the app is protected by an IP allowlist before it gets a public address, and you can add Microsoft Entra sign-in.

## Choose how to run the portal

| | Local (default) | Container App + IP allowlist | Container App + Entra sign-in |
|---|---|---|---|
| Where it runs | Each person's own computer | One container in your subscription | Same |
| Who can open it | Only that computer | Anyone whose traffic comes from the IP ranges you list | Users of your Microsoft Entra tenant who sign in |
| Identity used to call Foundry | Your own account | The container's managed identity, shared by everyone | Same |
| How | [Run locally](../../README.md#run-locally) | [Steps 1 and 2](#deploy-from-azure-cloud-shell) below | Steps 1 and 2, then [add Entra sign-in](#add-microsoft-entra-sign-in) |
| Good for | One or two people | A team on the office network or VPN | A team that also works off-network |

In both Container App options, everyone who gets in acts as the same managed identity: they can publish and delete Agents in your project and start sessions that incur cost, and the portal does not record who did what. Only let in people you would give that access to.

## Deploy from Azure Cloud Shell

You need **Contributor** on the subscription or resource group you deploy to. Step 2 also grants the portal's identity roles on your Foundry project and resource, which needs Owner, User Access Administrator or Role Based Access Control Administrator there; without that, add `--skip-roles` to step 2 and it prints the roles an admin must grant.

Open [Azure Cloud Shell](https://shell.azure.com) (Bash), signed in to the tenant and subscription you deploy to (`az account show`; switch with `az account set --subscription <name or id>`). It already has Azure CLI, git and curl. Get the scripts:

```bash
git clone https://github.com/microsoft/voice-agent.git
cd voice-agent
```

### Step 0: set your values

Edit the right-hand sides, then paste the block into Cloud Shell. Every later command uses these variables, so you can paste those unchanged.

```bash
RG=voice-agent-portal          # resource group for the portal; step 1 creates it if it does not exist
LOCATION=westus2               # region for the portal, e.g. the region of your Foundry resource
ALLOWED_IPS=203.0.113.0/24     # your office/VPN egress ranges, comma-separated (see below)
PROJECT_ENDPOINT=              # your Foundry project endpoint; leave empty if you can see only one project
```

| Variable | Where to get it |
|---|---|
| `RG` | Any name; an existing resource group also works (its tags are kept). |
| `LOCATION` | Any region with Azure Container Apps, as a short name (`westus2`, `eastus2`, `swedencentral`; full list: `az account list-locations -o table`). It does not have to match your Foundry resource. |
| `ALLOWED_IPS` | Open any "what is my IP" page in a browser **on a computer on your office network or VPN**, or ask your network team for the full ranges. A single address means just that address. **Do not look it up in Cloud Shell**: that is an Azure address, not yours. |
| `PROJECT_ENDPOINT` | The project's overview page in the Foundry portal, `https://<account>.services.ai.azure.com/api/projects/<project>`. To list the projects your sign-in can see, run `portal/deploy/aca/deploy_app.sh --list-projects`. |

The scripts check these values before they create anything and stop with a message that says what to fix: step 1 checks that the region exists and offers Container Apps; step 2 checks the endpoint and that you can see that project, that every IP is a valid address or range (and not `0.0.0.0/0`), and that step 1 ran for this resource group. Cloud Shell forgets the variables when its session ends: if you come back later, paste the block again.

### Step 1: build the image

```bash
portal/deploy/aca/build_image.sh --resource-group "$RG" --location "$LOCATION"
```

It creates the resource group if it does not exist yet, creates an Azure Container Registry (Basic) in it, and builds the image **inside that registry** from your checkout with `az acr build`. Nothing is built or pulled in Cloud Shell. It takes about two minutes and ends with the image name and the step 2 command.

If a policy requires tags on resource groups, add them with `--tag KEY=VALUE` (repeatable), e.g. `--tag CostCenter=1234`; they are merged into an existing group and its other tags are kept.

### Step 2: run the portal

```bash
portal/deploy/aca/deploy_app.sh --resource-group "$RG" --project-endpoint "$PROJECT_ENDPOINT" --allowed-ip "$ALLOWED_IPS"
```

It finds the registry of step 1 in the same resource group and runs the newest image there. It takes about five minutes the first time and ends with the portal URL and a reachability check from where it runs:

```text
Portal URL      : https://voice-agent-portal.<environment>.<region>.azurecontainerapps.io/editor/
Status          : running; this machine's IP is not in the allowlist (HTTP 403)
```

In Cloud Shell that 403 is the expected result: Cloud Shell is not on your office network. Open the URL from a computer on your office network or VPN. If the status instead says `healthy` in Cloud Shell, your list includes an Azure address and the script warns you; rerun step 2 with the right ranges.

Run step 2 on its own whenever only access changes: it does not rebuild. Change `ALLOWED_IPS` to the **complete** new list and rerun it; rules that are no longer listed are removed. `--help` lists all options, including `--env KEY=VALUE`, `--image` and `--skip-roles`.

The two steps can be run by different people, for example a platform team builds and the project owner deploys, as long as both use the same `RG`.

### What it creates

Everything is in the resource group you chose:

| Resource | Created by | Purpose |
|---|---|---|
| Azure Container Registry (Basic) `vaportal<8 characters>` | Step 1 | Holds the portal image, tagged `<commit>-<UTC time>` |
| Container Apps environment `<name>-env` and its Log Analytics workspace | Step 2 | Hosts the app; keeps logs |
| User-assigned managed identity `<name>-id` | Step 2 | The identity the portal calls Foundry with |
| Container App `<name>` (default `voice-agent-portal`; one replica, 0.5 vCPU, 1 GiB) | Step 2 | Runs the portal |

Roles granted to the identity:

| Role | Scope | Why |
|---|---|---|
| AcrPull | The registry | Pull the portal image |
| Foundry User | Your Foundry project | Publish, read and run Voice Agents (required) |
| Cognitive Services Speech User | Your Foundry resource | Realtime voice list (optional) |
| Reader | Your Foundry resource | Project picker and region lookup (optional) |

The app is created with internal-only ingress, gets its access protection, and only then a public address, so it is never reachable unprotected. Inside the container the portal runs unchanged on `127.0.0.1:9527`; [`nginx.conf`](./nginx.conf) on port 8080 forwards same-origin requests as same-computer requests and rejects cross-site ones; [`supervise.py`](./supervise.py) runs both. The image recipe is [`Dockerfile`](./Dockerfile). The image only works behind the Container Apps HTTPS ingress; to run the portal on a computer, [run it locally](../../README.md#run-locally) instead.

## Add Microsoft Entra sign-in

Use this when people need the portal off your network, or only named people should get in. Either way the app registration lives in your tenant.

**With the script**: rerun step 2 with `--auth entra`. It creates a single-tenant app registration with a one-year client secret, turns on sign-in, and then removes the IP rules (add `--allowed-ip` to keep both). If you cannot register applications, an admin creates one (platform **Web**, redirect URI `https://<app host>/.auth/login/aad/callback`, **ID tokens** enabled, a client secret); then run `read -rs ENTRA_CLIENT_SECRET && export ENTRA_CLIENT_SECRET` and add `--auth entra --entra-client-id <client-id>`. Before the secret expires, rerun with `--entra-renew-secret`. `--entra-assigned-only` limits sign-in to assigned users; an admin then grants admin consent once.

**In the Azure portal**:

1. Open the Container App > **Security > Authentication** > **Add identity provider** > **Microsoft**.
2. Keep **Create new app registration**, supported account types **Current tenant - Single tenant**, and pick a client secret expiration. Keep **Require authentication** and **HTTP 302 Found redirect**. Select **Add**.
3. Open the portal URL and sign in. The first user consents to the app reading their basic profile; if your tenant blocks user consent, an admin grants it under **Enterprise applications > your app > Permissions > Grant admin consent**.
4. Only after sign-in works, remove the IP rules in the app's **Ingress** settings if you want off-network access. Keeping them requires both.

Sign-in only decides who gets in; the portal still calls Foundry as the managed identity. Rerunning step 2 with `--auth ip --allowed-ip <CIDR>` writes the IP rules first and then turns sign-in off.

## Upgrade and remove

- **Upgrade**: `git pull` (or `git checkout <tag>`), paste the step 0 block, then run step 1 and step 2 again. Step 2 moves the app to the newest image and keeps your access settings and roles. Restarts end sessions in progress. To roll back, rerun step 2 with `--image` set to an older image; the image names are printed by step 1 and listed by `az acr repository show-tags -n <registry> --repository voice-agent-portal -o table`.
- **Remove**: `az group delete -n "$RG"`. Agents in your Foundry project are not deleted. The identity's role assignments on the Foundry project and resource stay behind as "Identity not found" entries; remove them under **Access control (IAM)** on the project and the resource. An Entra app registration, if you added one, is deleted separately under **App registrations**.

## Restricted subscriptions and network requirements

The image is built by Azure Container Registry on Microsoft-managed build machines, and the Container Apps environment uses Microsoft-managed outbound networking, not your virtual network. Your own network and Cloud Shell never download the base image or Python packages.

| Who connects | To | Why |
|---|---|---|
| Cloud Shell | `github.com` | Clone this repository |
| The registry's build (step 1) | Docker Hub (`python:3.12-alpine`), Alpine package mirrors, PyPI | Build the image |
| Container Apps, when a revision starts | `<registry>.azurecr.io` | Pull the portal image |
| Users, in a browser | `<name>.<environment>.<region>.azurecontainerapps.io` (HTTPS and WebSocket) | Use the portal and its voice sessions |
| Users, in a browser (Entra sign-in only) | `login.microsoftonline.com` | Sign in |
| The portal container | `<account>.services.ai.azure.com` (HTTPS and WebSocket) | Publish, read and run Voice Agents; voice sessions (required) |
| The portal container | `<account>.cognitiveservices.azure.com` | Realtime voice list (optional) |
| The portal container | `management.azure.com`, `login.microsoftonline.com` | Project picker and region lookup; tokens for the managed identity |
| The portal container | `<region>.tts.speech.microsoft.com` | Only the **Automatic voice language** button |
| The portal container | The MCP server a template uses (by default the public sample MCP in `portal/templates.config.json`) | Connection check before publishing a template. During a session, Foundry, not the portal, calls the MCP server |

What a policy or network setting can block, and what to do:

| Situation | What to do |
|---|---|
| A policy requires tags on resource groups | Pass them to step 1 with `--tag KEY=VALUE`, or create the resource group with its tags first. |
| A policy allows only approved container registries | The image is in your own registry. If registries must be created centrally, have the platform team create one and pass `--acr <name>` to both steps. |
| A policy requires Container Apps environments in a virtual network, or denies public ingress | Not supported by these scripts. Run the portal locally on a computer inside your network. |
| Your Foundry resource has public network access disabled (private endpoint only) | The container cannot reach it. Run the portal locally on a computer that can reach the private endpoint. |
| Users' browsers go through a proxy that blocks unknown domains | Allow `*.azurecontainerapps.io` (or the exact portal host) for HTTPS and WebSocket. |

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Step 2 stops with "Run step 1 first" | The resource group or its registry does not exist, or step 1 used a different `RG` (or `--name` / `--acr`). Cloud Shell may have lost the variables: paste the step 0 block again. |
| HTTP 403 when opening the URL from the office | Your egress IP is not in the allowlist, often because it was looked up in Cloud Shell. Fix `ALLOWED_IPS` and rerun step 2. |
| Step 2 fails on a role assignment | You cannot assign roles on the Foundry project. Rerun with `--skip-roles` and have an admin grant the roles it prints. |
| Publishing an Agent fails with 403 | The identity lacks **Foundry User** on the project, for example while an admin has not granted it yet. |
| The realtime voice list or project picker is short | The optional **Cognitive Services Speech User** or **Reader** roles are missing on the Foundry resource. |
| A session that sends no audio is closed after about four minutes | The Container Apps ingress closes idle connections. Keep the microphone stream running. |
| Sign-in fails after it used to work | The Entra client secret expired. Rerun step 2 with `--auth entra --entra-renew-secret`, or add a new secret in the app's **Authentication** settings. |
| Logs | `az containerapp logs show -n voice-agent-portal -g "$RG" --follow` |
