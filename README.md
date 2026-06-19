<div align="center">
<a href="http://skillnet.openkg.cn/">
    <img src="images/skillnet.png" width="200" alt="SkillNet Logo">
</a>

# SkillNet: The Operating System for AI Skills

<p><strong>Search, install, evaluate, and connect reusable AI skills.</strong></p>

<p>
SkillNet treats AI agent skills as first-class software assets.<br/>
It provides a public skill library, Python SDK, CLI, quality evaluation, and a skill graph.
</p>

[![PyPI version](https://badge.fury.io/py/skillnet-ai.svg)](https://pypi.org/project/skillnet-ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![arXiv](https://img.shields.io/badge/arXiv-b5212f.svg?logo=arxiv)](https://arxiv.org/abs/2603.04448)
[![Hugging Face](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-FFD21E)](https://huggingface.co/blog/xzwnlp/skillnet)
[![Website](https://img.shields.io/badge/%F0%9F%8C%90_Website-skillnet.openkg.cn-0078D4.svg)](http://skillnet.openkg.cn/)

<p>
  <a href="#get-started">Get started</a> ·
  <a href="#skillnet-explorer">Explorer</a> ·
  <a href="#python-sdk">Python SDK</a> ·
  <a href="#cli-reference">CLI</a> ·
  <a href="#rest-api">REST API</a> ·
  <a href="#citation">Citation</a>
</p>

</div>

---

## What is SkillNet?

SkillNet is open infrastructure for building and reusing AI agent skills. A skill can package instructions, metadata, references, scripts, and evaluation results so that an agent can install it, inspect it, and use it again later.

Use SkillNet when you want to:

- Find existing skills before an agent rebuilds the same capability.
- Install skills from public GitHub repositories into a local agent workspace.
- Create new skills from repositories, office documents, prompts, or execution traces.
- Evaluate skills across five quality dimensions.
- Build a local graph that shows how skills relate to each other.

## Get started

Install the Python package:

```bash
pip install skillnet-ai
```

Search and download a skill:

```python
from skillnet_ai import SkillNetClient

client = SkillNetClient()

results = client.search("pdf understanding", limit=5)
print(results[0].skill_name)
print(results[0].skill_url)

client.download(url=results[0].skill_url, target_dir="./my_skills")
```

Or use the CLI:

```bash
skillnet search "pdf understanding" --limit 5
skillnet download <skill_url> -d ./my_skills
```

`search` and public GitHub downloads do not require credentials. Set `API_KEY` when you use `create`, `evaluate`, or `analyze` with an LLM.

## News

- **[2026-03-26] JiuwenClaw integration released.** JiuwenClaw now includes SkillNet as a built-in skill marketplace. [View guide](./examples/JiuwenClaw/README.md)
- **[2026-03-12] SkillNet MCP server released.** MCP support is maintained by [CycleChain](https://github.com/CycleChain).
- **[2026-03-04] Technical report released.** Read the SkillNet report on [arXiv](https://arxiv.org/abs/2603.04448).
- **[2026-02-23] OpenClaw integration released.** SkillNet is available as a built-in skill for [OpenClaw](https://github.com/openclaw/openclaw).

## Table of contents

- [SkillNet Explorer](#skillnet-explorer)
- [Core capabilities](#core-capabilities)
- [Use SkillNet in Code Agents](#use-skillnet-in-code-agents)
- [Python SDK](#python-sdk)
- [CLI Reference](#cli-reference)
- [Configuration](#configuration)
- [REST API](#rest-api)
- [Examples and experiments](#examples-and-experiments)
- [More integrations](#more-integrations)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Citation](#citation)

---

## SkillNet Explorer

[SkillNet Explorer](http://skillnet.openkg.cn/) is the visual entry point for the public skill library. It is designed for browsing skills the way developers browse packages or model hubs.

Use the Explorer to:

- Search skills by keyword or semantic meaning.
- Browse quality-ranked skills and curated collections.
- Inspect skill graph visualizations.
- Find the install path for a skill.

<div align="center">

![Skill graph demo](https://github.com/user-attachments/assets/1d27d046-48a1-4ab2-a6f5-58c8fa07a134)

</div>

The website also includes interactive scenarios for web scraping, paper summarization, and experiment planning.

<div align="center">

https://github.com/user-attachments/assets/9f9d35b0-36fd-4d7d-a072-39afa380b241

</div>

---

## Core capabilities

| Capability | What it does |
| :--- | :--- |
| Search | Find skills through keyword search or semantic vector search. |
| Install | Download a skill folder from GitHub into a local workspace. |
| Create | Convert repositories, documents, prompts, or trajectories into structured skill packages. |
| Evaluate | Score skills for Safety, Completeness, Executability, Maintainability, and Cost-Awareness. |
| Connect | Infer `similar_to`, `belong_to`, `compose_with`, and `depend_on` relationships between skills. |

SkillNet treats a skill as a software primitive, not just a prompt. The package format keeps the skill portable; the evaluation layer makes quality visible; the graph layer makes skills easier to compose.

---

## Use SkillNet in Code Agents

SkillNet is also packaged as a portable agent skill at [`skills/skillnet/`](https://github.com/zjunlp/SkillNet/tree/main/skills/skillnet). Install this folder into your code agent's local skills directory, then the agent can search, download, create, evaluate, and organize skills during coding tasks.

<div align="center">

https://github.com/user-attachments/assets/ae6020d9-6846-4672-84ce-fa9c8057e92b

</div>

### Claude Code

Claude Code discovers user skills from `~/.claude/skills/` and project skills from `.claude/skills/`.

Install as a user skill:

```bash
git clone https://github.com/zjunlp/SkillNet.git
cd SkillNet

mkdir -p ~/.claude/skills
cp -R skills/skillnet ~/.claude/skills/skillnet
```

Or install as a project-local skill:

```bash
mkdir -p .claude/skills
cp -R /path/to/SkillNet/skills/skillnet .claude/skills/skillnet
```

Restart Claude Code or start a new session, then try:

```text
Use SkillNet to search for a docker skill and summarize the top result.
```

### Codex

Codex discovers user skills from `$CODEX_HOME/skills`. If `CODEX_HOME` is not set, use `~/.codex/skills`.

```bash
git clone https://github.com/zjunlp/SkillNet.git
cd SkillNet

CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
mkdir -p "$CODEX_HOME/skills"
cp -R skills/skillnet "$CODEX_HOME/skills/skillnet"
```

Restart Codex or start a new session, then try:

```text
Use $skillnet to search for a LangGraph skill before planning this task.
```

---

## Python SDK

### Initialize

```python
from skillnet_ai import SkillNetClient

client = SkillNetClient(
    api_key="YOUR_API_KEY",          # Required for create, evaluate, and analyze
    # base_url="https://api.openai.com/v1",
    # github_token="YOUR_GITHUB_TOKEN"
)
```

Credentials can also be set through environment variables: `API_KEY`, `BASE_URL`, and `GITHUB_TOKEN`.

### Search

```python
# Keyword search
results = client.search(q="pdf", limit=10, min_stars=5, sort_by="stars")

# Semantic search
results = client.search(
    q="analyze financial PDF reports",
    mode="vector",
    threshold=0.85,
)

if results:
    print(results[0].skill_name)
    print(results[0].skill_url)
```

### Install

```python
local_path = client.download(
    url="https://github.com/anthropics/skills/tree/main/skills/skill-creator",
    target_dir="./my_skills",
)
print(local_path)
```

### Create

`create` requires `API_KEY`.

```python
# From a conversation log or execution trace
client.create(
    trajectory_content="User: rename .jpg to .png\nAgent: Done.",
    output_dir="./skills",
)

# From a GitHub repository
client.create(github_url="https://github.com/zjunlp/DeepKE", output_dir="./skills")

# From an office document: PDF, PPT, or Word
client.create(office_file="./guide.pdf", output_dir="./skills")

# From a natural language prompt
client.create(prompt="A skill for web scraping article titles", output_dir="./skills")
```

### Evaluate

`evaluate` requires `API_KEY`. It accepts local paths and GitHub URLs.

```python
result = client.evaluate(
    target="https://github.com/anthropics/skills/tree/main/skills/algorithmic-art"
)

print(result["safety"]["level"])
print(result["executability"]["reason"])
```

### Analyze

`analyze` requires `API_KEY`. It maps relationships between skills in a local directory.

```python
relationships = client.analyze(skills_dir="./my_skills")

for rel in relationships:
    print(f"{rel['source']} --[{rel['type']}]--> {rel['target']}")
```

Relationship types: `similar_to`, `belong_to`, `compose_with`, and `depend_on`.

---

## CLI Reference

The CLI ships with `pip install skillnet-ai`.

| Command | Description | Example |
| :--- | :--- | :--- |
| `search` | Find skills | `skillnet search "pdf" --mode vector` |
| `download` | Install a skill | `skillnet download <url> -d ./skills` |
| `create` | Create from repos, docs, logs, or prompts | `skillnet create log.txt --model gpt-4o` |
| `evaluate` | Quality report | `skillnet evaluate ./my_skill` |
| `analyze` | Relationship graph | `skillnet analyze ./my_skills` |

Use `skillnet <command> --help` for full options.

### Search

```bash
skillnet search "pdf"
skillnet search "analyze financial reports" --mode vector --threshold 0.85
skillnet search "visualization" --category "Development" --sort-by stars --limit 10
```

### Install

```bash
skillnet download https://github.com/anthropics/skills/tree/main/skills/algorithmic-art
skillnet download <url> -d ./my_agent/skills
skillnet download <private_url> --token <your_github_token>
skillnet download <url> --mirror https://ghfast.top/
```

### Create

```bash
skillnet create ./logs/trajectory.txt -d ./generated_skills
skillnet create --github https://github.com/owner/repo
skillnet create --office ./docs/guide.pdf
skillnet create --prompt "A skill for extracting tables from images"
```

### Evaluate

```bash
skillnet evaluate https://github.com/anthropics/skills/tree/main/skills/algorithmic-art
skillnet evaluate ./my_skills/web_search
skillnet evaluate ./my_skills/tool --category "Development" --model gpt-4o
```

### Analyze

```bash
skillnet analyze ./my_agent_skills
skillnet analyze ./my_agent_skills --no-save
skillnet analyze ./my_agent_skills --model gpt-4o
```

---

## Configuration

| Variable | Required for | Default |
| :--- | :--- | :--- |
| `API_KEY` | `create`, `evaluate`, `analyze` | - |
| `BASE_URL` | Custom OpenAI-compatible endpoint | `https://api.openai.com/v1` |
| `GITHUB_TOKEN` | Private repositories or higher rate limits | - |
| `SKILLNET_MODEL` | Default LLM model for all commands | `gpt-4o` |
| `GITHUB_MIRROR` | Faster GitHub downloads in restricted networks | - |

`search` and public GitHub downloads work without credentials.

Linux and macOS:

```bash
export API_KEY="YOUR_API_KEY"
export BASE_URL="https://..."
```

Windows PowerShell:

```powershell
$env:API_KEY = "YOUR_API_KEY"
$env:BASE_URL = "https://..."
```

---

## REST API

The SkillNet search API is public and requires no authentication.

```bash
# Keyword search
curl "http://api-skillnet.openkg.cn/v1/search?q=pdf&sort_by=stars&limit=5"

# Semantic search
curl "http://api-skillnet.openkg.cn/v1/search?q=reading%20charts&mode=vector&threshold=0.8"
```

<details>
<summary><b>Full parameter reference</b></summary>

**Endpoint:** `GET http://api-skillnet.openkg.cn/v1/search`

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `q` | string | required | Search query, keywords or natural language |
| `mode` | string | `keyword` | `keyword` or `vector` |
| `category` | string | - | Filter: Development, AIGC, Research, Science, etc. |
| `limit` | int | `10` | Results per page, max 50 |
| `page` | int | `1` | Page number, keyword mode only |
| `min_stars` | int | `0` | Minimum star count, keyword mode only |
| `sort_by` | string | `stars` | `stars` or `recent`, keyword mode only |
| `threshold` | float | `0.8` | Similarity threshold from 0.0 to 1.0, vector mode only |

**Response:**

```json
{
  "data": [
    {
      "skill_name": "pdf-extractor-v1",
      "skill_description": "Extracts text and tables from PDF documents.",
      "author": "openkg-team",
      "stars": 128,
      "skill_url": "https://...",
      "category": "Productivity",
      "evaluation": {
        "safety": { "level": "Good", "reason": "..." }
      }
    }
  ],
  "meta": {
    "query": "pdf",
    "mode": "keyword",
    "total": 1,
    "limit": 10
  },
  "success": true
}
```

</details>

---

## Examples and experiments

### Scientific discovery

SkillNet can help an agent plan and execute a scientific workflow, from raw scRNA-seq data to a cancer target validation report.

![Scientific discovery demo](https://github.com/user-attachments/assets/5b65865a-312a-4dd7-ae80-ee1f968e2702)

| Step | What happens |
| :--- | :--- |
| Task | User asks: "Analyze scRNA-seq data to find cancer targets" |
| Plan | Agent decomposes the job into data, mechanism, validation, and report steps |
| Discover | `client.search()` finds useful skills such as `cellxgene-census` and `kegg-database` |
| Evaluate | Skills are quality-gated before use |
| Execute | Skills run in sequence and produce the final report |

[Try the interactive demo](http://skillnet.openkg.cn/) or open the [scientific workflow notebook](https://github.com/zjunlp/SkillNet/blob/main/examples/scientific_workflow_demo.ipynb).

### Benchmark scripts

Reproduction scripts for ALFWorld, WebShop, and ScienceWorld are available under [`experiments/`](https://github.com/zjunlp/SkillNet/tree/main/experiments).

```bash
cd experiments

python alfworld_run.py --model o4-mini --split dev --max_workers 10 --exp_name alf_test --use_skill
python scienceworld_run.py --model o4-mini --split test --max_workers 5 --exp_name sci_test --use_skill
python webshop_run.py --model o4-mini --max_workers 3 --exp_name web_test --use_skill
```

---

## More integrations

### OpenClaw

SkillNet integrates with [OpenClaw](https://github.com/openclaw/openclaw) as a built-in, lazy-loaded skill. The agent can search, download, create, evaluate, and analyze skills from inside OpenClaw.

<div align="center">

https://github.com/user-attachments/assets/9d49a00c-827d-47a4-8954-0e6b977ca547

</div>

Install with the CLI:

```bash
npm i -g clawhub
clawhub install skillnet --workdir ~/.openclaw/workspace
openclaw gateway restart
```

Or ask OpenClaw:

```text
Install the skillnet skill from ClawHub.
```

Optional OpenClaw configuration:

```json
{
  "skills": {
    "entries": {
      "skillnet": {
        "enabled": true,
        "apiKey": "YOUR_API_KEY",
        "env": {
          "BASE_URL": "https://api.openai.com/v1",
          "GITHUB_TOKEN": "YOUR_GITHUB_TOKEN"
        }
      }
    }
  }
}
```

### Model Context Protocol (MCP)

The SkillNet MCP server is maintained by [CycleChain](https://github.com/CycleChain). It lets MCP-compatible clients such as Claude Desktop, Cursor, Antigravity, and Windsurf call SkillNet tools directly.

Source build:

```bash
git clone https://github.com/CycleChain/skillnet-mcp
cd skillnet-mcp
npm install && npm run build
```

Docker:

```bash
docker pull fmdogancan/skillnet-mcp:latest
```

Claude Desktop configuration with Docker:

```json
{
  "mcpServers": {
    "skillnet": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "fmdogancan/skillnet-mcp:latest"],
      "env": {
        "API_KEY": "YOUR_API_KEY"
      }
    }
  }
}
```

`search_skills` and `download_skill` do not require an API key. `create`, `evaluate`, and `analyze` do.

### JiuwenClaw

[JiuwenClaw](https://github.com/openJiuwen-ai/jiuwenclaw) integrates SkillNet as a built-in skill marketplace. See the [JiuwenClaw guide](./examples/JiuwenClaw/README.md).

---

## Roadmap

SkillNet is growing beyond search and installation.

- **SkillFabric:** workflow-level skill substrates and routing across skill collections.
- **SkillGym:** lifecycle evaluation and training environments for skills.

Start from [skillnet.openkg.cn](http://skillnet.openkg.cn/) and open SkillFabric or SkillGym from the website navigation.

---

## Contributing

Contributions are welcome: bug fixes, docs, examples, and new skills all help.

1. Fork the repository.
2. Create a feature branch: `git checkout -b feat/amazing-feature`.
3. Commit your changes: `git commit -m 'feat: add amazing feature'`.
4. Push to the branch: `git push origin feat/amazing-feature`.
5. Open a pull request.

You can also [open an issue](https://github.com/zjunlp/SkillNet/issues) or contribute skills through the [SkillNet website](http://skillnet.openkg.cn/).

---

## Citation

If SkillNet helps your work, please cite the paper:

```bibtex
@misc{liang2026skillnetcreateevaluateconnect,
      title={SkillNet: Create, Evaluate, and Connect AI Skills},
      author={Yuan Liang and Ruobin Zhong and Haoming Xu and Chen Jiang and Yi Zhong and Runnan Fang and Jia-Chen Gu and Shumin Deng and Yunzhi Yao and Mengru Wang and Shuofei Qiao and Xin Xu and Tongtong Wu and Kun Wang and Yang Liu and Zhen Bi and Jungang Lou and Yuchen Eleanor Jiang and Hangcheng Zhu and Gang Yu and Haiwen Hong and Longtao Huang and Hui Xue and Chenxi Wang and Yijun Wang and Zifei Shan and Xi Chen and Zhaopeng Tu and Feiyu Xiong and Xin Xie and Peng Zhang and Zhengke Gui and Lei Liang and Jun Zhou and Chiyu Wu and Jin Shang and Yu Gong and Junyu Lin and Changliang Xu and Hongjie Deng and Wen Zhang and Keyan Ding and Qiang Zhang and Fei Huang and Ningyu Zhang and Jeff Z. Pan and Guilin Qi and Haofen Wang and Huajun Chen},
      year={2026},
      eprint={2603.04448},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2603.04448}
}
```
