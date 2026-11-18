# portal.env settings for va-portal-v2 on Windows

Open `C:\va-portal-v2\portal.env` in Notepad. Write one `KEY=value` per line, with no spaces around `=` and no quotes. Lines that start with `#` are ignored.

| Variable | When to set it | Value |
|---|---|---|
| `AZURE_VOICE_AGENTS_ENDPOINT` | Always | Your project endpoint, from Foundry portal > your project > **Overview**. It looks like `https://<account>.services.ai.azure.com/api/projects/<project>`. |
| `AZURE_CLIENT_ID` | For a service principal or a user-assigned managed identity | For a service principal, the app's **Application (client) ID**. For a user-assigned managed identity, the identity's client ID. Leave it empty for a system-assigned managed identity. |
| `AZURE_TENANT_ID` | Service principal only | The **Directory (tenant) ID**. |
| `AZURE_CLIENT_SECRET` | Service principal only | The secret's **Value**, not its Secret ID. |
| `AZURE_CREDENTIAL_MODE` | Only to sign in with your own `az login` | `cli` |
| `REQUESTS_CA_BUNDLE` and `SSL_CERT_FILE` | Usually not. Set them only if `check.cmd` says a certificate "is not trusted" and you can't install your root CA in Windows. | Set both to the full path of the same root CA file in PEM format, for example `C:\va-portal-v2\corp-root-ca.pem`. Set both or neither: the first covers HTTPS calls and the second covers the voice WebSocket. |
| `DEMO_PORT` | Optional | The portal port. The default is `9527`. |

There is no `CA_CERT_FILE` setting. The package ignores it.

Whichever identity you use, it needs the **Foundry User** role on the project.

## Example for a service principal

```text
AZURE_VOICE_AGENTS_ENDPOINT=https://<account>.services.ai.azure.com/api/projects/<project>
AZURE_CLIENT_ID=<application client id>
AZURE_TENANT_ID=<tenant id>
AZURE_CLIENT_SECRET=<secret value>
```

## Then

1. Run `check.cmd`. Every line should say `PASS`. A `WARN` on `Foundry address` is fine if this machine can reach that address.
2. Run `start.cmd` and keep its window open.
3. Open `http://127.0.0.1:9527/editor/` in a browser on the same machine.

For download, upgrade and troubleshooting, see the [guide](README.md).
