<div align="center">

# skillnet-ai

**The official Python SDK & CLI for [SkillNet](http://skillnet.openkg.cn/) — search, install, create, evaluate, and connect AI agent skills.**

[![PyPI version](https://badge.fury.io/py/skillnet-ai.svg)](https://pypi.org/project/skillnet-ai/)
[![Downloads](https://img.shields.io/pypi/dm/skillnet-ai.svg)](https://pypi.org/project/skillnet-ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

[Website](http://skillnet.openkg.cn/) · [GitHub](https://github.com/zjunlp/SkillNet) · [PyPI](https://pypi.org/project/skillnet-ai/)

</div>

---

## Quick Start

```bash
pip install skillnet-ai
```

```python
from skillnet_ai import SkillNetClient

client = SkillNetClient()  # No API key needed for search & download

# Find a skill
results = client.search(q="pdf", limit=5)
print(results[0].skill_name, results[0].stars)

# Install it
client.download(url=results[0].skill_url, target_dir="./my_skills")
```

That's it. Search and download are free — no API key, no rate limit.

> For **create**, **evaluate**, and **analyze**, set `API_KEY` (any OpenAI-compatible key) or `MINIMAX_API_KEY` (for MiniMax). See [Configuration](#%EF%B8%8F-configuration).

---

## Features

|     | Feature      | What it does                                                                                           |
| :-- | :----------- | :----------------------------------------------------------------------------------------------------- |
| 🔍  | **Search**   | Keyword match or AI semantic search across 500+ community skills                                       |
| 📦  | **Install**  | One-line download from any GitHub skill directory                                                      |
| ✨  | **Create**   | Auto-convert repos, PDFs, conversation logs, or text prompts → structured skill packages               |
| 📊  | **Evaluate** | Score skills on 5 dimensions: Safety · Completeness · Executability · Maintainability · Cost-Awareness |
| 🕸️  | **Analyze**  | Map `similar_to` · `belong_to` · `compose_with` · `depend_on` relationships between skills             |

---

## Python SDK

### Initialize

```python
from skillnet_ai import SkillNetClient

client = SkillNetClient(
    api_key="sk-...",         # Required for create / evaluate / analyze
    # provider="minimax",     # Optional: "openai" (default) or "minimax"
    # base_url="...",         # Optional: custom LLM endpoint (default: OpenAI)
    # github_token="ghp-..." # Optional: for private repos or higher rate limits
)
```

Credentials can also be set via environment variables: `API_KEY`, `BASE_URL`, `GITHUB_TOKEN`.

Provider is auto-detected when `MINIMAX_API_KEY` is set. See [Using MiniMax](#using-minimax-as-llm-provider) for details.

### Search

```python
# Keyword search
results = client.search(q="pdf", limit=10, min_stars=5, sort_by="stars")

# Semantic search — find skills by meaning, not just keywords
results = client.search(q="analyze financial PDF reports", mode="vector", threshold=0.85)

if results:
    print(f"{results[0].skill_name} ⭐{results[0].stars}")
    print(results[0].skill_url)
```

<details>
<summary><b>Search Parameters</b></summary>

| Parameter   | Type  | Default     | Description                                  |
| :---------- | :---- | :---------- | :------------------------------------------- |
| `q`         | str   | _required_  | Search query (keywords or natural language)  |
| `mode`      | str   | `"keyword"` | `"keyword"` or `"vector"`                    |
| `category`  | str   | `None`      | Filter by category                           |
| `limit`     | int   | `20`        | Max results per request                      |
| `page`      | int   | `1`         | Page number _(keyword only)_                 |
| `min_stars` | int   | `0`         | Minimum star count _(keyword only)_          |
| `sort_by`   | str   | `"stars"`   | `"stars"` or `"recent"` _(keyword only)_     |
| `threshold` | float | `0.8`       | Similarity threshold 0.0–1.0 _(vector only)_ |

</details>

### Install

```python
local_path = client.download(
    url="https://github.com/anthropics/skills/tree/main/skills/skill-creator",
    target_dir="./my_skills"
)
print(f"Installed at: {local_path}")
```

### Create

Convert diverse sources into structured skill packages:

```python
# From conversation logs / execution traces
client.create(trajectory_content="User: rename .jpg→.png\nAgent: Done.", output_dir="./skills")

# From a GitHub repository
client.create(github_url="https://github.com/zjunlp/DeepKE", output_dir="./skills")

# From office documents (PDF / PPT / Word)
client.create(office_file="./guide.pdf", output_dir="./skills")

# From a natural language description
client.create(prompt="A skill for web scraping article titles", output_dir="./skills")

# Use a specific model
client.create(prompt="A skill for PDF parsing", output_dir="./skills", model="gpt-4o")
```

All modes auto-generate a complete skill package: `SKILL.md` + optional `scripts/`, `references/`, `assets/`.

### Evaluate

Score any skill on 5 quality dimensions. Accepts local paths or GitHub URLs:

```python
result = client.evaluate(
    target="https://github.com/anthropics/skills/tree/main/skills/algorithmic-art"
)
# {
#   "safety":          {"level": "Good", "reason": "..."},
#   "completeness":    {"level": "Good", "reason": "..."},
#   "executability":   {"level": "Average", "reason": "..."},
#   "maintainability": {"level": "Good", "reason": "..."},
#   "cost_awareness":  {"level": "Good", "reason": "..."}
# }
```

### Analyze Relationships

Discover connections between skills in a local directory:

```python
relationships = client.analyze(skills_dir="./my_skills")

for rel in relationships:
    print(f"{rel['source']} --[{rel['type']}]--> {rel['target']}")
# PDF_Parser --[compose_with]--> Text_Summarizer
# Web_Scraper --[similar_to]--> Data_Extractor
```

Detects four relationship types: `similar_to` · `belong_to` · `compose_with` · `depend_on`. Results are saved to `relationships.json` by default.

---

## CLI

The CLI ships automatically with `pip install skillnet-ai` — powered by [Typer](https://typer.tiangolo.com/) + [Rich](https://rich.readthedocs.io/) for beautiful terminal output.

```
skillnet <command> --help    # Full options for any command
```

### Commands at a Glance

| Command    | What it does           | Example                               |
| :--------- | :--------------------- | :------------------------------------ |
| `search`   | Find skills            | `skillnet search "pdf" --mode vector` |
| `download` | Install a skill        | `skillnet download <url> -d ./skills` |
| `create`   | Create from any source | `skillnet create log.txt -d ./skills` |
| `evaluate` | Quality report         | `skillnet evaluate ./my_skill`        |
| `analyze`  | Relationship graph     | `skillnet analyze ./my_skills`        |

> All LLM-powered commands (`create`, `evaluate`, `analyze`) support `--provider` (e.g. `--provider minimax`) and `--model` flags.

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

# Use a mirror for faster downloads in restricted networks
skillnet download <url> --mirror https://ghfast.top/
```

### Create

```bash
skillnet create ./logs/trajectory.txt -d ./skills          # from trajectory
skillnet create --github https://github.com/owner/repo      # from GitHub repo
skillnet create --office ./docs/guide.pdf                    # from PDF/PPT/Word
skillnet create --prompt "A skill for table extraction"      # from prompt
skillnet create --office report.pdf --model gpt-4o           # custom model
skillnet create --provider minimax --prompt "web scraping"   # use MiniMax
```

### Evaluate

```bash
skillnet evaluate ./my_skills/web_search
skillnet evaluate https://github.com/anthropics/skills/tree/main/skills/algorithmic-art
skillnet evaluate ./my_skill --category "Development" --model gpt-4o
skillnet evaluate --provider minimax ./my_skill
```

### Analyze

```bash
skillnet analyze ./my_skills
skillnet analyze ./my_skills --no-save     # print only, don't write file
skillnet analyze ./my_skills --model gpt-4o
skillnet analyze --provider minimax ./my_skills
```

---

## ⚙️ Configuration

### Environment Variables

| Variable          | Required For                            | Default                     |
| :---------------- | :-------------------------------------- | :-------------------------- |
| `API_KEY`         | `create` · `evaluate` · `analyze`       | —                           |
| `MINIMAX_API_KEY` | MiniMax provider (auto-detected)        | —                           |
| `BASE_URL`        | Custom LLM endpoint                     | `https://api.openai.com/v1` |
| `GITHUB_TOKEN`    | Private repos / higher rate limits      | —                           |
| `SKILLNET_MODEL`  | Default LLM model for all commands      | `gpt-4o`                    |
| `GITHUB_MIRROR`   | Faster downloads in restricted networks | —                           |

> `search` and `download` (public repos) require **no credentials at all**.
>
> **Recommended mirror:** [`https://ghfast.top/`](https://ghfast.top/) — set `GITHUB_MIRROR` or pass `--mirror` to speed up downloads in restricted networks.

**Linux / macOS:**

```bash
export API_KEY="sk-..."
export BASE_URL="https://..."   # optional
```

**Windows PowerShell:**

```powershell
$env:API_KEY = "sk-..."
$env:BASE_URL = "https://..."   # optional
```

Or pass credentials directly in code:

```python
client = SkillNetClient(api_key="sk-...", base_url="https://...")
```

### Using MiniMax as LLM Provider

SkillNet supports [MiniMax](https://www.minimax.io/) as a first-class LLM provider. MiniMax offers the M2.7 model with a 1M-token context window and OpenAI-compatible API.

**Quick start — environment variable (auto-detected):**

```bash
export MINIMAX_API_KEY="your-minimax-api-key"
skillnet create --prompt "A skill for web scraping"
# Provider, base URL, and model are auto-configured
```

**Explicit provider flag:**

```bash
skillnet create --provider minimax --prompt "A skill for web scraping"
skillnet evaluate --provider minimax ./my_skill
skillnet analyze --provider minimax ./my_skills
```

**Python SDK:**

```python
from skillnet_ai import SkillNetClient

# Auto-detected when MINIMAX_API_KEY is set
client = SkillNetClient()

# Or explicit provider
client = SkillNetClient(provider="minimax", api_key="your-minimax-api-key")
```

**Provider comparison:**

| Provider  | Default Model  | Base URL                    | API Key Env       |
| :-------- | :------------- | :-------------------------- | :---------------- |
| `openai`  | `gpt-4o`       | `https://api.openai.com/v1` | `API_KEY`         |
| `minimax` | `MiniMax-M2.7` | `https://api.minimax.io/v1` | `MINIMAX_API_KEY` |

**Model priority:** `--model` flag > `SKILLNET_MODEL` env var > provider's default model.

---

## 📂 Skill Structure

Every created or downloaded skill follows a standardized layout:

```text
skill-name/
├── SKILL.md          # [Required] YAML metadata + markdown instructions
├── scripts/          # [Optional] Executable Python / Bash scripts
├── references/       # [Optional] Static docs, API specs, schemas
└── assets/           # [Optional] Templates, icons, examples
```

---

## 🤝 Contributing

Contributions are welcome! Feel free to [open an Issue](https://github.com/zjunlp/SkillNet/issues) or submit a Pull Request.

## 📄 License

[MIT](LICENSE)
