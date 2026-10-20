---
title: User Playground 部署与本地调试 Guide
status: active
verified: 2026-10-20
keywords: [playground, deployment, local, debug, port-forwarding, guide]
---

# User Playground 部署与本地调试 Guide

这份指南说明怎样更新线上服务，以及怎样从同一份 UI 源码启动本地版本。日常看界面和调试先走[本地启动](#2-启动本地版本)，不要为看一个 UI 改动直接部署 Azure。

## 1. 先分清源码和运行位置

| 位置 | 负责什么 |
| --- | --- |
| [本目录](./) | Playground 部署、托管策略、邀请码登录、镜像装配与运维 |
| [voice-agent/portal](../../../voice-agent/portal/) | Editor、AgentRuntime、WebRTC 的前端源码和通用本地服务 |
| [build_context.py](build_context.py) | 把 Portal、示例和本目录的托管适配装配到新的构建目录 |
| [12_noauth_mcp](../12_noauth_mcp/) | 独立的共享 MCP 服务；更新 UI 不等于更新 MCP |

所以，改前端时通常改 Portal 源码；从本目录装配、启动或部署时会把这些改动带进去。不要在构建目录里直接修源码：重新装配后，这些临时修改会丢失。

固定的线上目标：

| 项目 | 值 |
| --- | --- |
| Subscription | `f6e76fc8-e9fc-435f-982a-9007a547ea2d` |
| Resource group | `voice-agent-portal-hosting-dev` |
| Container App | `voice-agent-playground` |
| ACR | `vaportall3hddama` |
| Foundry Project | `voice-agent-playground` |
| Portal | <https://voice-agent-playground.blackground-c889ecc7.westus2.azurecontainerapps.io> |
| MCP | <https://voice-agent-noauth-mcp.lemonsky-36682081.westus2.azurecontainerapps.io> |

下文的终端命令默认使用 Bash。不要把这个 Playground 部署到 `PrincetonOnlineMeetingsDev`。

## 2. 启动本地版本

### 2.1 准备依赖和身份

在 Linux 开发机的 canonical checkout 中执行：

```bash
cd /home/jimxie/repo/one-speech-service/docs/voice_agent/03_user_playground
```

首次使用、尚未创建 Python 环境时：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r ../../../voice-agent/portal/requirements.txt
```

本地后端使用你当前的 Azure CLI 身份。先确认已登录；没有登录时再运行 `az login`：

```bash
az account show --query '{name:name,id:id}' --output json
```

登录成功不代表已有 Foundry 数据权限。打开 Agent 列表或连接语音遇到 401/403 时，应检查所选 Project 的权限，而不是关闭认证或切换成假数据。

如果改过 React、CSS 或共享前端模块，需要先重新构建。要求 Node.js **22 或更新版本**；系统自带的 Node.js 18 不能运行当前 Playwright：

```bash
node --version
cd ../../../voice-agent/portal/web
# 仅首次使用或依赖变更后需要：npm ci
npm run build:all
cd /home/jimxie/repo/one-speech-service/docs/voice_agent/03_user_playground
```

没有改前端源码、只想使用已经构建的 UI 时，可以跳过前端构建。

### 2.2 装配并启动

在**同一个终端**执行整段命令；`CONTEXT` 指向本次独立的源码快照：

```bash
cd /home/jimxie/repo/one-speech-service/docs/voice_agent/03_user_playground

CONTEXT="$(pwd)/.run/local-ui-$(date -u +%Y%m%dT%H%M%SZ)"
.venv/bin/python build_context.py "$CONTEXT" --portal-source ../../../voice-agent

export VOICE_PLAYGROUND_MCP_BASE_URL=https://voice-agent-noauth-mcp.lemonsky-36682081.westus2.azurecontainerapps.io

.venv/bin/python -u "$CONTEXT/portal/demo_server.py" \
  --bind 127.0.0.1 \
  --port 9527 \
  --project-endpoint https://voice-agent-portal-l3hddama.services.ai.azure.com/api/projects/voice-agent-playground \
  --credential-mode cli \
  --no-record-sessions \
  --template-profile "$CONTEXT/portal/hosting/profile.json" \
  --data-dir "$CONTEXT/data"
```

保留这个终端，按 **Ctrl+C** 停止。另开终端验证：

```bash
curl --fail http://127.0.0.1:9527/healthz
curl --fail --silent --output /dev/null \
  --write-out 'Editor HTTP %{http_code}\n' \
  http://127.0.0.1:9527/editor/
```

预期健康检查包含 `"status": "ok"`、`"project": "voice-agent-playground"`，Editor 返回 `200`。

如果 `9527` 已被占用，先用 `ss -ltnp '( sport = :9527 )'` 确认是谁的服务。不要结束其他人的进程；可以把启动和验证命令里的端口一起改为 `9528`。

### 2.3 从 Windows / Mac 浏览器打开

如果服务和浏览器在同一台机器，打开 <http://127.0.0.1:9527/editor/>。

如果 VS Code 是 **Remote-SSH**，Linux 的 `127.0.0.1` 和你电脑的 `127.0.0.1` 不是同一个位置，需要在当前 VS Code 窗口转发端口：

1. 打开底部 **PORTS** 面板，选择 **Forward a Port**。
2. 输入远端端口 `9527`，保持 **Private**。
3. 使用这一行显示的 **Forwarded Address**，或选择 **Open in Browser**。
4. 在实际转发地址后打开 `/editor/`；AgentRuntime 是 `/demo/`，独立 WebRTC 是 `/webrtc`。

本机端口冲突时，Forwarded Address 可能不是 `9527`。Linux 中 `curl` 返回 200 只能证明服务已启动，不能证明 Windows / Mac 的端口转发已建立。

如果仍然 `ERR_CONNECTION_REFUSED`，先检查当前窗口的 PORTS，不要反复重启健康的后端。完整排查见[Remote-SSH 端口转发 runbook](../../utils/01_vscode_remote_ssh_port_forwarding.md)。

### 2.4 打开 Debug mode

- **Editor / AgentRuntime**：在页面顶部导航旁勾选 **Debug mode**。
- **WebRTC**：在页面顶部右侧勾选 **Debug mode**。
- 默认关闭；刷新页面或跨页面导航后重新默认关闭。
- 关闭时不展示 model、STT、TTS 的 cost/latency 预估，以及逐轮 STT、User→Agent 延时。
- 开启后可查看这些指标；AgentRuntime 同时显示协议事件，WebRTC 回看也可查看延时轨迹和原始 metadata。
- 左侧的 **Agent Debug** 只是流程图面板，展开它不会自动开启 Debug mode。

改完前端后，在原始源码目录重新构建，再从本目录生成一个**新**的 `CONTEXT`，停止旧进程并启动新快照。运行中的构建目录不会自动跟随源码更新；只刷新浏览器不能更新旧快照。

### 2.5 本地版本和线上不完全一样

这里启动的是经过 Playground 构建适配的**通用本地入口** `demo_server.py`，不是容器入口 `playground_server.py`。

| 行为 | 本地调试入口 | 线上容器入口 |
| --- | --- | --- |
| 后端位置 | 本机 / Remote Linux 的 loopback | Azure Container App |
| Azure 身份 | 当前 Azure CLI 用户 | 托管身份 |
| 邀请码、email namespace、Secure cookie | 不启用托管准入策略 | 启用 |
| UI 源码 | 同一份 Portal 构建产物 | 同一份 Portal 构建产物 |
| 会话持久化默认值 | 从托管 profile 读取，`store=false` | `store=false` |
| 本地语音事件文件记录 | 本命令显式关闭 | 关闭 |
| STT / LLM / TTS / Foundry / MCP | 仍然调用 Azure / 共享 MCP | 调用 Azure / 共享 MCP |

这不是离线模拟。**Try it now** 会发布真实 Agent，**Connect & start session** 会使用真实语音服务，可能产生费用。上面的默认命令连接团队的共享 Project；本地通用入口没有 email namespace 过滤，调试时优先使用你自己的测试 Agent 或单独的测试 Project，不要修改其他用户的 Agent。

本地 UI 不能证明线上登录、email 隔离、托管身份权限、HTTPS cookie 或多副本行为正确。这些需要托管策略测试和部署后的验收。不要为了在 HTTP localhost 上运行而放宽线上 HTTPS / cookie / Origin 限制，也不要把使用个人 Azure 身份的本地服务暴露到公网。

## 3. 更新已有线上服务：优先只换镜像

以下命令会构建云端镜像、更新现有 Container App。**写文档、启动本地版本或验证 UI 都不要求执行这一节。** 只有决定发布时才执行；普通 UI 更新不要顺便重建资源、改 RBAC、轮换邀请码或修改副本设置。

构建读取当前磁盘内容，**未提交的改动也会被打包**。发布前确认 Portal 仓库和本目录中被装配的改动都允许上线。下面的命令必须按顺序执行；任意一步失败就停止，不要继续更新线上服务。

### 3.1 构建新镜像并保留回滚地址

如果前端有改动，先完成上一节的 `npm run build:all`。然后在同一个 Bash 终端执行：

```bash
cd /home/jimxie/repo/one-speech-service/docs/voice_agent/03_user_playground

SUBSCRIPTION=f6e76fc8-e9fc-435f-982a-9007a547ea2d
RESOURCE_GROUP=voice-agent-portal-hosting-dev
APP=voice-agent-playground
REGISTRY=vaportall3hddama

PREVIOUS_IMAGE="$(az containerapp show \
  --subscription "$SUBSCRIPTION" --resource-group "$RESOURCE_GROUP" \
  --name "$APP" --query 'properties.template.containers[0].image' --output tsv)"

TAG="ui-$(date -u +%Y%m%dT%H%M%SZ)"
CONTEXT="$(pwd)/.run/image-context-$TAG"
.venv/bin/python build_context.py "$CONTEXT" --portal-source ../../../voice-agent

az acr build \
  --subscription "$SUBSCRIPTION" --registry "$REGISTRY" \
  --file "$CONTEXT/portal/hosting/Dockerfile" \
  --image "voice-agent-playground:$TAG" "$CONTEXT"

DIGEST="$(az acr repository show \
  --subscription "$SUBSCRIPTION" --name "$REGISTRY" \
  --image "voice-agent-playground:$TAG" --query digest --output tsv)"
printf '%s\n' "$DIGEST" | grep -Eq '^sha256:[0-9a-f]{64}$' || exit 1
NEW_IMAGE="$REGISTRY.azurecr.io/voice-agent-playground@$DIGEST"
```

保留 `PREVIOUS_IMAGE` 和 `NEW_IMAGE` 两个完整地址，不要只记录可变 tag。装配时若报告 hosting patch 不匹配，应修复源代码与适配的兼容性，不能跳过 patch。构建目录已经存在时换一个新目录，不要删除不确定用途的目录。

装配器读取 Portal 的模板清单，复制每个启用模板的默认 Agent 文件，以及同一 sample 目录下所有同名的备份文件，不复制备份旁边的其他文件。当前 8 张模板卡片共包含 17 个版本。Editor 的 **Load from templates** 和独立 Templates 页都可以按相对文件夹路径选择版本。托管策略对每个版本保留 `store=false`，并按实际模型和 MCP 工具进行校验。

即使终端使用 `umask 077`，装配器在应用补丁后也会把这些已核准源码文件设为 `0644`，供容器内非 root 用户读取；外层构建目录仍保持私有。镜像中的非 root 启动检查若失败，应修复装配器后生成新快照，不能在构建目录中临时修补或跳过检查。

### 3.2 更新、检查、验收

```bash
az containerapp update \
  --subscription "$SUBSCRIPTION" --resource-group "$RESOURCE_GROUP" \
  --name "$APP" --image "$NEW_IMAGE" \
  --query '{latest:properties.latestRevisionName,ready:properties.latestReadyRevisionName}'

az containerapp revision list \
  --subscription "$SUBSCRIPTION" --resource-group "$RESOURCE_GROUP" \
  --name "$APP" \
  --query '[].{name:name,active:properties.active,health:properties.healthState,traffic:properties.trafficWeight,image:properties.template.containers[0].image}'

az containerapp show \
  --subscription "$SUBSCRIPTION" --resource-group "$RESOURCE_GROUP" \
  --name "$APP" \
  --query '{ingress:properties.configuration.ingress,min:properties.template.scale.minReplicas,max:properties.template.scale.maxReplicas}'
```

确认新 revision ready、实际流量使用新镜像、当前副本配置没有被顺便更改。不要只看到 update 命令返回就认定发布成功。

然后检查未登录的健康状态和 API 准入：

```bash
PORTAL=https://voice-agent-playground.blackground-c889ecc7.westus2.azurecontainerapps.io
curl --fail "$PORTAL/healthz"
test "$(curl --silent --output /dev/null --write-out '%{http_code}' "$PORTAL/config")" = 401
```

需要做完整验收时使用现有脚本，token 只从权限为 `0600` 的本地文件读取：

```bash
.venv/bin/python scripts/accept_live.py \
  --base-url "$PORTAL" \
  --invitation-file .run/access/invitation.local.json \
  --email acceptance@example.com \
  --output .run/live-acceptance.json

VOICE_PLAYGROUND_BASE_URL="$PORTAL" \
VOICE_PLAYGROUND_EMAIL=acceptance@example.com \
  node scripts/accept_browser.mjs

.venv/bin/python scripts/usage_stats.py --hours 1
```

`accept_live.py` 会发布并读回每个模板版本，检查所选版本的实际指令，并为每个模板的默认版本连接真实 Voice 会话；它不是只读检查。使用专门的验收 email namespace，按[详细启动 runbook](STARTUP.md)核对结果。浏览器验收核对实际部署的静态资源与本地源码 hash，并在桌面和手机宽度下加载备份版本；源码又改过但还没部署时，hash 不一致是正确的失败结果，不能跳过。

上线后检查 Debug mode 默认关闭，主动开启才出现指标；再核对 telemetry heartbeat、登录和错误。健康检查 200 不能替代这些检查。发布成功后，把完整新镜像摘要同步到私有部署参数文件的 `parameters.image.value`，不要提交或输出含密钥的整个参数文件。

### 3.3 回滚

新版本验证失败时，在仍然保留上述变量的终端中使用发布前记录的完整镜像地址：

```bash
az containerapp update \
  --subscription "$SUBSCRIPTION" --resource-group "$RESOURCE_GROUP" \
  --name "$APP" --image "$PREVIOUS_IMAGE" \
  --query '{latest:properties.latestRevisionName,ready:properties.latestReadyRevisionName}'
```

回滚后重新检查 revision、流量、健康和登录；同步私有参数文件中的镜像地址。回滚 UI 不需要轮换签名密钥或邀请码。

## 4. 首次部署或确实要改基础设施

首次建资源、修改身份 / RBAC / ingress / 副本配置，不走上面的“只换镜像”快捷路径。按 [STARTUP.md](STARTUP.md) 的 Foundation、Parameters、Validate Portal IaC 和 Start order 执行，先 validate / what-if，再检查变更范围：

- MCP 先就绪；它由 [12_noauth_mcp](../12_noauth_mcp/README.md) 独立部署。
- 参数示例是 [parameters.example.json](parameters.example.json)，不要把真实密钥写入示例。
- 当前 [prepare_release.py](scripts/prepare_release.py) 为**已有环境**读取资源并生成 `.azure/parameters.local.json`；部分旧命令写的是根目录 `parameters.local.json`，实际执行时必须用你已核对的私有参数路径。
- `prepare_release.py` 会生成 IaC 参数，不是单纯给 UI 换镜像的必需步骤。其输出仍需 review；尤其检查副本数、身份和角色，不能假设它等于线上当前设置。
- [issue_invitation.py](issue_invitation.py) 用于显式创建 / 轮换邀请码，正常 UI 发布不要运行。
- token、签名密钥、Azure 凭据不得出现在 Git、URL、命令行、日志、截图或聊天中。

排查见 [DEBUGGING.md](DEBUGGING.md)，副本与可用性边界见 [SCALING.md](SCALING.md)。

## 5. 常见现象

| 现象 | 先检查什么 |
| --- | --- |
| Linux `curl` 是 200，电脑浏览器拒绝连接 | 当前 Remote-SSH 窗口的 PORTS 和实际 Forwarded Address |
| 本地看不到新加的 Debug mode | 是否重建前端、重新装配并启动了新快照，而不是只刷新旧页面 |
| 展开 Agent Debug 还是没有延时 | 页头的 Debug mode 是独立开关，默认关闭 |
| Agent 列表或语音返回 401/403 | 本地 Azure CLI 身份及目标 Project 数据权限；不要关认证 |
| `build_context.py` 报目录已存在 | 使用新的时间戳构建目录，不覆盖正在运行的快照 |
| hosting patch 应用失败 | public Portal 与托管适配不兼容，不能继续上传这个构建 |
| 本地没有邀请码登录页 | 这是通用本地入口的预期行为，不等于线上登录策略被移除 |
| 线上已更新但验收 hash 不一致 | 部署 digest、流量 revision 与本地构建输入是否确实相同 |

## 结论

本目录是部署和本地装配的入口，前端源码来自 Portal。看界面先构建并启动 loopback 本地版本，Remote-SSH 通过 Private 端口转发访问；需要指标时打开页头的 Debug mode。决定上线后再构建新镜像、只更新现有服务，并完成登录、资源 hash 和功能验收；本地成功不能替代线上托管策略验证。
