# Setup / 安装与 API 配置

## Reuse an existing installation

Run `skillnet --version`. This skill requires **skillnet-ai 0.2.0+**. If it works,
keep using that command: a pipx installation does not imply that another `python`
interpreter can import the package. Legacy scripts in this skill resolve the CLI
first and use their own Python only when it contains the SDK.

Version 0.2.0 is the release candidate accompanying this source tree. Before its
PyPI publication, install from the reviewed SkillNet checkout. Do not repeatedly
try to install an unavailable release.

## Isolated installation / 隔离安装

Python 3.10+ is required. If Python is absent, install it from python.org (Windows:
include the Python launcher). No Node, GPU, graph extras or agent SDK is required.

macOS, from a SkillNet checkout:

```sh
python3 -m venv "$HOME/.skillnet/venv"
"$HOME/.skillnet/venv/bin/python" -m pip install ./skillnet-ai
"$HOME/.skillnet/venv/bin/python" -m skillnet_ai --version
```

Windows PowerShell, from a SkillNet checkout:

```powershell
py -3 -m venv "$env:USERPROFILE\.skillnet\venv"
& "$env:USERPROFILE\.skillnet\venv\Scripts\python.exe" -m pip install .\skillnet-ai
& "$env:USERPROFILE\.skillnet\venv\Scripts\python.exe" -m skillnet_ai --version
```

After 0.2.0 is published, the install source can be replaced by
`"skillnet-ai>=0.2.0"`. Existing pipx/uv users can upgrade with their existing tool.
When the CLI is not on the agent's PATH, use the full virtualenv Python path plus
`-m skillnet_ai` in place of `skillnet` in subsequent examples. Activation is not
required. For Linux, use the macOS Python commands.

## Configure once / 配置一次，多端复用

搜索与公开下载不需要模型 Key。创建和评估需要同一组配置：

| Setting | Environment | Meaning |
|---|---|---|
| `api_key` | `API_KEY` | Key for the selected model endpoint |
| `base_url` | `BASE_URL` | OpenAI-compatible Chat Completions API base URL |
| `model` | `SKILLNET_MODEL` | Exact model name accepted by that endpoint |
| `github_token` | `GITHUB_TOKEN` | Optional GitHub authentication |
| `github_mirror` | `GITHUB_MIRROR` | Optional public raw-file fallback mirror |
| `skillnet_api_url` | `SKILLNET_API_URL` | SkillNet search base URL, separate from the model API |
| `json_mode` | `SKILLNET_JSON_MODE` | Evaluation mode: `auto` (default), `on`, `off` |

Precedence is explicit SDK/CLI arguments → nonempty environment variables → user
config → defaults. Defaults remain `gpt-4o`, `https://api.openai.com/v1`, and
`http://api-skillnet.openkg.cn` for search. Choose the correct model when using a
custom provider. The HTTP search default is retained while its HTTPS certificate
issue is tracked; never bypass TLS validation to make an HTTPS URL work.

用户在自己的终端中运行（使用刚才验证过的执行入口）：

```text
skillnet configure --interactive
```

This explicitly interactive command asks for the endpoint, model and a hidden key.
Press Enter at the key prompt to keep an existing credential, or enter a replacement.
Agent subprocesses should use noninteractive flags instead:

```text
skillnet configure --api-key-env MY_MODEL_KEY --base-url "https://your-provider.example/v1" --model "your-model" --json
```

`MY_MODEL_KEY` is the **name** of an environment variable already populated by the
user, not a credential to paste into chat. `--api-key-stdin` accepts a key supplied
through stdin. `--github-token-env` works similarly for an existing GitHub variable.
Never put a real key in a command argument or include it in a transcript.

配置默认保存在 `~/.skillnet/config.json`；可用 `SKILLNET_CONFIG` 指定另一个文件。
它是用户目录中的明文配置，macOS/Linux 文件权限为 0600，Windows 使用用户目录
访问权限；需要避免将其提交、分享或放入技能包。只想使用环境变量的用户无需保存。
同一用户、可访问同一配置文件的 agent 可以复用配置；沙箱内路径不同需显式指定。

Changing the model or endpoint later does not require re-entering the saved key:

```text
skillnet configure --base-url "https://your-provider.example/v1" --model "your-model"
```

## Verify / 验证

```text
skillnet doctor --json
skillnet doctor --check-network --json
skillnet doctor --check-llm --json
```

The first command is local only. The second checks search and GitHub access.
The third sends one short model request and may be billed; use it when testing
model configuration. A successful probe proves connectivity, not evaluation schema
support or generated-skill quality. A missing model key does not block search.

DeepSeek、智谱 Coding Plan 和其他兼容服务使用相同三项配置。套餐端点可能不同于
普通 API 端点，以服务商文档和账户权限为准。配置能力不代表该渠道已经通过实测。
宿主 agent 的登录状态不是模型 API Key。
