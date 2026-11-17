# Offline Voice Agent portal installation bundle

Use this folder when the VM, jumpbox, or virtual network where you want to run the **Voice Agent portal** has **no internet access** (cannot reach PyPI, Docker Hub, or GitHub directly), and you are retrieving the installer from a workstation or jumpbox that can reach GitHub.

If your environment can use Azure Cloud Shell normally, you do **not** need this bundle: run the portal locally with [`portal/README.md`](../../portal/README.md) or deploy it to Azure Container Apps with [`skills/portal-remote/README.md`](../../skills/portal-remote/README.md).

## Why the archive is split

`voice-agent-portal-delivery-d112175c0dcb.zip` (`245,224,424` bytes / `233.9 MiB`) is stored in [`parts/`](./parts/) as ten raw byte slices (`part-01` through `part-10`, each `< 25 MB`) so every file stays directly inside Git without Git LFS or external download hosts:

- **`git clone` only contacts `github.com`**, so it works even behind strict corporate firewalls that allow `github.com` while blocking `*.githubusercontent.com` redirects.
- **No third-party archiver (such as `7-Zip`) is needed on the offline target machine.** The parts are raw byte slices of a standard `.zip` archive and can be joined with the included scripts or built-in OS commands (`cat` on Linux/macOS, `copy /b` on Windows).

---

## Step 1: download this folder on a machine that can reach GitHub

### Option A: `git` sparse checkout (recommended; contacts only `github.com`)

Downloads only `dist/portal-offline` instead of the whole repository:

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/microsoft/voice-agent.git
cd voice-agent
git sparse-checkout set dist/portal-offline
cd dist/portal-offline
```

A regular shallow clone works the same way if your `git` client is older:

```bash
git clone --depth 1 https://github.com/microsoft/voice-agent.git
cd voice-agent/dist/portal-offline
```

### Option B: browser download without `git`

If `git` is not installed on the machine that reaches GitHub (requires firewall access to `codeload.github.com` or `raw.githubusercontent.com`):

1. Download the repository ZIP from GitHub (**Code** -> **Download ZIP**), extract it, and open `dist/portal-offline/`, **or**
2. Download all files in `dist/portal-offline/` (`SHA256SUMS`, `voice-agent-portal-delivery-d112175c0dcb.zip.sha256`, `assemble.sh`, `assemble.ps1`, `assemble.cmd`) and all ten files in [`parts/`](./parts/) into a `parts/` subfolder.

---

## Step 2: reassemble and verify the `.zip` archive

You can reassemble the `.zip` either **before** copying it to your offline VM/jumpbox (so you only transfer one verified `.zip` file over Azure Bastion or a private Storage account) or **after** copying `dist/portal-offline/` to the target machine.

### Automated verify + join + extract

**Linux or macOS:**

```bash
chmod +x assemble.sh
./assemble.sh --extract
```

**Windows (Command Prompt):**

```cmd
assemble.cmd -Extract
```

**Windows (PowerShell):**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\assemble.ps1 -Extract
```

`assemble.sh` and `assemble.ps1` check the SHA-256 hash of every part in [`SHA256SUMS`](./SHA256SUMS) (telling you immediately which part to re-download if one was truncated), join the ten parts into `voice-agent-portal-delivery-d112175c0dcb.zip`, verify the archive hash against [`voice-agent-portal-delivery-d112175c0dcb.zip.sha256`](./voice-agent-portal-delivery-d112175c0dcb.zip.sha256), and unpack `voice-agent-portal-delivery-d112175c0dcb/`.

### Manual join without helper scripts (built-in OS commands only)

**Linux:**

```bash
sha256sum -c SHA256SUMS
cat parts/voice-agent-portal-delivery-d112175c0dcb.zip.part-* > voice-agent-portal-delivery-d112175c0dcb.zip
sha256sum -c voice-agent-portal-delivery-d112175c0dcb.zip.sha256
unzip voice-agent-portal-delivery-d112175c0dcb.zip
```

**macOS:**

```bash
shasum -a 256 -c SHA256SUMS
cat parts/voice-agent-portal-delivery-d112175c0dcb.zip.part-* > voice-agent-portal-delivery-d112175c0dcb.zip
shasum -a 256 -c voice-agent-portal-delivery-d112175c0dcb.zip.sha256
unzip voice-agent-portal-delivery-d112175c0dcb.zip
```

**Windows (PowerShell):**

```powershell
cmd /c copy /b "parts\voice-agent-portal-delivery-d112175c0dcb.zip.part-*" "voice-agent-portal-delivery-d112175c0dcb.zip"
(Get-FileHash .\voice-agent-portal-delivery-d112175c0dcb.zip -Algorithm SHA256).Hash.ToLower()
Get-Content .\voice-agent-portal-delivery-d112175c0dcb.zip.sha256
Expand-Archive -LiteralPath .\voice-agent-portal-delivery-d112175c0dcb.zip -DestinationPath . -Force
```

Both hashes must match `0744e4a0b0f6c7dc33fb536543df2969fc95753977124864b81be465a839ddaa`.

---

## Step 3: pick a deployment option inside the unpacked folder

Open `voice-agent-portal-delivery-d112175c0dcb/README.md` after unpacking:

| | Solution 1: package on a VM | Solution 2: Azure Container App |
|---|---|---|
| **Where the portal runs** | One Linux x64 or Windows x64 VM inside your virtual network (zero internet egress required; talks only to your Foundry private endpoint and VM IMDS) | An Azure Container App in your subscription, using the prebuilt container image pushed into your Azure Container Registry |
| **Who uses it** | One person at a time on the VM browser (for example via Azure Bastion) or over an SSH local port forward (`127.0.0.1:9527`) | Your team at one shared HTTPS address behind an IP allowlist or Microsoft Entra sign-in |
| **What is bundled** | Portable CPython `3.12.16` with all 39 locked Python dependencies pre-installed, the compiled portal UI, 38 starter templates, `check.sh` / `start.sh` / `install-service.sh` (or `.cmd`), and the terminal `agent` command | Prebuilt `linux/amd64` container image `.tar`, standalone `crane` binaries (Linux, Windows, macOS x64/arm64) + `push_from_file.sh` to push without Docker, Container Apps deployment scripts, and standalone `agent-cli` packages |
| **Step-by-step guide inside the unpacked folder** | `solution-1-vm-package/GUIDE.md` | `solution-2-container-app/GUIDE.md` |

Start with **Solution 1** when the target VNet has zero outbound internet access or only one operator needs the portal on a VM. Choose **Solution 2** when a team needs one shared URL in Azure Container Apps without building the image from PyPI or Docker Hub.

### Unpacked directory layout

```text
voice-agent-portal-delivery-d112175c0dcb/
  README.md                                              overview and checksum instructions
  VERSION                                                source commit, Python runtime, image digest
  SHA256SUMS                                             checksum of every file in the bundle
  LICENSE.md, LICENSE-IMAGE.md                           license terms
  solution-1-vm-package/
    GUIDE.md                                             step-by-step VM offline installation guide
    voice-agent-portal-d112175c0dcb-linux-x64.tar.gz     self-contained portal + agent CLI for Linux x64 (44.6 MiB)
    voice-agent-portal-d112175c0dcb-win-x64.zip          self-contained portal + agent CLI for Windows x64 (29.1 MiB)
  solution-2-container-app/
    GUIDE.md                                             step-by-step prebuilt Container Apps deployment guide
    voice-agent-portal-image-d112175c0dcb/               OCI image .tar (43.0 MiB), crane binaries, push & deploy scripts
    agent-cli/
      voice-agent-cli-d112175c0dcb-linux-x64.tar.gz      standalone agent CLI for Linux x64 (43.7 MiB)
      voice-agent-cli-d112175c0dcb-win-x64.zip           standalone agent CLI for Windows x64 (28.1 MiB)
```

You do not have to copy the entire `234 MiB` unpacked folder onto the target machine: for example, a Linux VM using Solution 1 only needs `solution-1-vm-package/GUIDE.md` and `voice-agent-portal-d112175c0dcb-linux-x64.tar.gz` (`44.6 MiB` + its `.sha256`).

---

## Build provenance

- **Portal source**: [`microsoft/voice-agent`](https://github.com/microsoft/voice-agent) commit `d112175c0dcb355902d6129d5a09dbf279cd39ee` (tree identical to merged PR [#138](https://github.com/microsoft/voice-agent/pull/138), `dad3d8f4c7f619825b56fef05cb651b084ac53e7`)
- **Built (UTC)**: `2026-11-17T09:03:33Z`
- **Bundled Python runtime**: CPython `3.12.16` (`python-build-standalone` `20261110`, `pip` removed; 39 locked runtime packages pre-installed with hashes recorded in `requirements.lock` inside each package)
- **Bundled container image**: `voice-agent-portal:d112175c0dcb` (`linux/amd64`), digest `sha256:954490bef731e0174faf371ea5e03eea398fc480882909f8644009467d05ce3c`
- **Reassembled archive SHA-256**: `0744e4a0b0f6c7dc33fb536543df2969fc95753977124864b81be465a839ddaa` (`245,224,424` bytes across 10 parts; individual part hashes in [`SHA256SUMS`](./SHA256SUMS))
- **Licenses**: [`LICENSE.md`](../../LICENSE.md), [`LICENSE-IMAGE.md`](../../LICENSE-IMAGE.md), plus `THIRD_PARTY_LICENSES` / `crane` Apache-2.0 `LICENSE` inside the archive
