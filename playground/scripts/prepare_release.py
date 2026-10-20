"""Prepare ignored deployment parameters from existing approved Azure resources."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import time

from azure.identity import AzureCliCredential
import requests


ROOT = Path(__file__).resolve().parents[1]
SUBSCRIPTION = "f6e76fc8-e9fc-435f-982a-9007a547ea2d"
GROUP = "voice-agent-portal-hosting-dev"
PREFIX = f"/subscriptions/{SUBSCRIPTION}/resourceGroups/{GROUP}"
PORTAL_ID = PREFIX + "/providers/Microsoft.App/containerApps/voice-agent-playground"
MCP_ID = PREFIX + "/providers/Microsoft.App/containerApps/voice-agent-noauth-mcp"
ACR_ID = PREFIX + "/providers/Microsoft.ContainerRegistry/registries/vaportall3hddama"
ACCOUNT_ID = PREFIX + "/providers/Microsoft.CognitiveServices/accounts/voice-agent-portal-l3hddama"
PROJECT_ID = ACCOUNT_ID + "/projects/voice-agent-playground"


def private_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    os.chmod(path, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image")
    args = parser.parse_args()
    invitation = json.loads((ROOT / ".run/access/invitation.local.json").read_text())
    assert invitation["invitationHash"] == hashlib.sha256(invitation["invitationCode"].encode()).hexdigest()
    assert int(invitation["expiresAt"]) > int(time.time())

    with AzureCliCredential(process_timeout=30) as credential, requests.Session() as session:
        token = credential.get_token("https://management.azure.com/.default").token
        session.headers["Authorization"] = f"Bearer {token}"

        def arm(method, resource, api="2025-01-01", **kwargs):
            response = session.request(
                method, "https://management.azure.com" + resource,
                params={"api-version": api}, timeout=90, allow_redirects=False, **kwargs,
            )
            if not 200 <= response.status_code < 300:
                raise RuntimeError(f"{method} {resource} failed: HTTP {response.status_code}")
            return response.json()

        portal = arm("GET", PORTAL_ID)
        mcp = arm("GET", MCP_ID)
        environment = arm("GET", portal["properties"]["managedEnvironmentId"])
        registry = arm("GET", ACR_ID, api="2023-07-01")
        account = arm("GET", ACCOUNT_ID, api="2025-06-01")
        project = arm("GET", PROJECT_ID, api="2025-06-01")
        assert portal["location"].lower().replace(" ", "") == "westus2"
        assert account["location"].lower().replace(" ", "") == "westus2"
        assert environment["properties"]["provisioningState"] == "Succeeded"
        identities = portal["identity"]["userAssignedIdentities"]
        assert len(identities) == 1
        runtime = next(iter(identities.values()))
        principal = runtime["principalId"].lower()

        roles = {}
        for scope, role_id, label in (
            (PROJECT_ID, "19c28022-e58e-450d-a464-0b2a53034789", "Project data"),
            (ACR_ID, "7f951dda-4ed3-4680-a7ca-43fe172d538d", "ACR pull"),
        ):
            result = arm(
                "GET", scope + "/providers/Microsoft.Authorization/roleAssignments",
                api="2022-04-01",
            )
            matching = [
                item for item in result["value"]
                if item["properties"]["principalId"].lower() == principal
                and item["properties"]["roleDefinitionId"].lower().endswith("/" + role_id)
                and item["properties"]["scope"].lower() == scope.lower()
            ]
            assert matching, f"Missing expected scoped role: {label}"
            roles[label] = {"scope": scope, "assignments": len(matching)}

        def secret(resource, name):
            values = arm("POST", resource + "/listSecrets", json={})["value"]
            selected = [item["value"] for item in values if item["name"] == name]
            assert len(selected) == 1, f"Missing existing secret: {name}"
            return selected[0]

        image = args.image or portal["properties"]["template"]["containers"][0]["image"]
        assert re.fullmatch(
            r"vaportall3hddama\.azurecr\.io/voice-agent-playground@sha256:[0-9a-f]{64}",
            image,
        ), "Portal image must be an immutable approved-registry digest."
        mcp_image = mcp["properties"]["template"]["containers"][0]["image"]
        assert "@sha256:" in mcp_image
        mcp_ingress = mcp["properties"]["configuration"]["ingress"]
        assert mcp_ingress and mcp_ingress["external"], "Canonical noauth MCP ingress is not ready."
        mcp_url = "https://" + mcp_ingress["fqdn"]
        domain = environment["properties"]["defaultDomain"]
        parameters = {
            "foundryAccountName": account["name"],
            "foundryLocation": account["location"].lower().replace(" ", ""),
            "foundryResourceGroup": GROUP,
            "managedEnvironmentId": environment["id"],
            "managedEnvironmentDomain": domain,
            "location": portal["location"].lower().replace(" ", ""),
            "registryName": registry["name"],
            "registryResourceGroup": GROUP,
            "image": image,
            "mcpBaseUrl": mcp_url,
            "anonymousCookieKey": secret(PORTAL_ID, "anonymous-cookie-key"),
            "invitationCodeHash": invitation["invitationHash"],
            "invitationExpiresAt": invitation["expiresAt"],
            "accessCookieDays": 365,
            "exposePortalIngress": True,
            "minimumReplicas": 2,
            "maximumReplicas": 5,
        }
        private_json(ROOT / ".azure/parameters.local.json", {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
            "contentVersion": "1.0.0.0",
            "parameters": {key: {"value": value} for key, value in parameters.items()},
        })
        context = {
            "subscription": SUBSCRIPTION, "resourceGroup": GROUP, "location": portal["location"],
            "portalUrl": f"https://voice-agent-playground.{domain}",
            "mcpUrl": mcp_url,
            "projectEndpoint": f"https://{account['name']}.services.ai.azure.com/api/projects/{project['name'].split('/')[-1]}",
            "registry": registry["name"], "image": image, "mcpImage": mcp_image,
            "roles": roles, "invitationExpiresUtc": invitation["expiresUtc"],
            "runtimePrincipalId": principal,
        }
        private_json(ROOT / ".run/cloud-context.json", context)
        print(json.dumps({
            "subscription": SUBSCRIPTION, "resourceGroup": GROUP,
            "location": portal["location"], "scopedRolesVerified": list(roles),
            "portalUrl": context["portalUrl"], "mcpUrl": context["mcpUrl"],
            "invitationExpiresUtc": invitation["expiresUtc"],
            "existingSecretsPreserved": True, "secretValuesPrinted": False,
        }, indent=2))


if __name__ == "__main__":
    main()
