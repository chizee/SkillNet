<div align="center">

# skillnet-ai

**The Python SDK and CLI package for SkillNet.**

[![PyPI version](https://badge.fury.io/py/skillnet-ai.svg)](https://pypi.org/project/skillnet-ai/)
[![Downloads](https://img.shields.io/pypi/dm/skillnet-ai.svg)](https://pypi.org/project/skillnet-ai/)
[![GitHub stars](https://img.shields.io/github/stars/zjunlp/SkillNet?style=social)](https://github.com/zjunlp/SkillNet)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

[Website](http://skillnet.openkg.cn/) · [GitHub](https://github.com/zjunlp/SkillNet) · [PyPI](https://pypi.org/project/skillnet-ai/)

</div>

---

## What Is SkillNet?

`skillnet-ai` is the installable Python package for SkillNet. It gives applications, scripts, and agent runtimes one interface for the skill lifecycle:

- **Find** skills with keyword or semantic search.
- **Install** skills from GitHub skill directories.
- **Create** structured skill packages from prompts, execution traces, repositories, or documents.
- **Evaluate** skill quality across safety, completeness, executability, maintainability, and cost awareness.
- **Analyze** how local skills compose into relationship graphs or scenario-level workflows.
- **Orchestrate** a preset scene by selecting the right skills and generating a downstream agent prompt.

Search and public skill download do **not** require an API key. Create, evaluate, and analyze use OpenAI-compatible endpoints. Orchestration runs through Claude Agent SDK and requires a compatible gateway configured through `API_KEY`, `BASE_URL`, and `SKILLNET_MODEL`.

For the full project overview, research context, integrations, and roadmap, see the [main SkillNet repository](https://github.com/zjunlp/SkillNet).

---

## Installation

```bash
pip install skillnet-ai
```

Optional extras:

```bash
pip install "skillnet-ai[graph]"        # scenario graph analysis
pip install "skillnet-ai[orchestrate]"  # scene orchestration via Claude Agent SDK
```

---

## Quick Start

```python
from skillnet_ai import SkillNetClient

client = SkillNetClient()

results = client.search(q="pdf", limit=5)
print(results[0].skill_name)
print(results[0].skill_url)

local_path = client.download(results[0].skill_url, target_dir="./my_skills")
print(local_path)
```

Equivalent CLI:

```bash
skillnet search "pdf" --limit 5
skillnet download <skill_url> -d ./my_skills
```

---

## Feature Overview

| Feature | SDK | CLI | Requires API key |
| :-- | :-- | :-- | :-- |
| Search skills | `client.search(...)` | `skillnet search ...` | No |
| Download skills | `client.download(...)` | `skillnet download ...` | No for public repos |
| Create skills | `client.create(...)` | `skillnet create ...` | Yes |
| Evaluate skills | `client.evaluate(...)` | `skillnet evaluate ...` | Yes |
| Analyze relationships | `client.analyze(...)` | `skillnet analyze ...` | Yes |
| Orchestrate scene skills | `client.orchestrate(...)` | `skillnet orchestrate ...` | Yes |

---

## Python SDK

### Initialize

```python
from skillnet_ai import SkillNetClient

client = SkillNetClient(
    api_key="your-api-key",       # required for create, evaluate, analyze, orchestrate
    base_url="https://api.openai.com/v1",
    github_token=None,            # optional, for private repos or higher GitHub rate limits
)
```

Credentials can also be set through environment variables:

```bash
export API_KEY="your-api-key"
export BASE_URL="https://api.openai.com/v1"
export SKILLNET_MODEL="gpt-4o"
export GITHUB_TOKEN="your-github-token"
```

### Search

```python
results = client.search(
    q="analyze financial PDF reports",
    mode="vector",
    threshold=0.85,
    limit=10,
)

for skill in results:
    print(skill.skill_name, skill.stars, skill.skill_url)
```

<details>
<summary><b>Search parameters</b></summary>

| Parameter | Type | Default | Description |
| :-- | :-- | :-- | :-- |
| `q` | `str` | required | Keyword query or natural language description |
| `mode` | `str` | `"keyword"` | `"keyword"` or `"vector"` |
| `category` | `str` | `None` | Category filter |
| `limit` | `int` | `20` | Maximum returned results |
| `page` | `int` | `1` | Page number for keyword search |
| `min_stars` | `int` | `0` | Minimum star count for keyword search |
| `sort_by` | `str` | `"stars"` | `"stars"` or `"recent"` for keyword search |
| `threshold` | `float` | `0.8` | Similarity threshold for vector search |

</details>

### Download

```python
local_path = client.download(
    url="https://github.com/anthropics/skills/tree/main/skills/skill-creator",
    target_dir="./my_skills",
)
print(f"Installed at: {local_path}")
```

### Create

```python
# From a conversation or execution trace
client.create(
    trajectory_content="User: rename .jpg files to .png\nAgent: Done.",
    output_dir="./skills",
)

# From a GitHub repository
client.create(
    github_url="https://github.com/zjunlp/DeepKE",
    output_dir="./skills",
)

# From an office document
client.create(
    office_file="./guide.pdf",
    output_dir="./skills",
)

# From a direct prompt
client.create(
    prompt="A skill for extracting tables from academic PDFs",
    output_dir="./skills",
)
```

Created skills follow the standard layout:

```text
skill-name/
├── SKILL.md
├── scripts/
├── references/
└── assets/
```

### Evaluate

```python
report = client.evaluate("./my_skills/table-extractor")

print(report["overall_score"])
print(report["summary"])
```

SkillNet evaluates five dimensions:

- Safety
- Completeness
- Executability
- Maintainability
- Cost awareness

### Analyze

`analyze` reads a local directory of skill folders. The default `basic` mode infers lightweight relationships from skill names, descriptions, and metadata:

```python
relationships = client.analyze("./my_skills")

for rel in relationships:
    print(f"{rel['source']} --[{rel['type']}]--> {rel['target']}")
```

Relationship types are `similar_to`, `belong_to`, `compose_with`, and `depend_on`.

For workflow composition, `scenario` mode extracts each skill's required and produced scenarios, retrieves candidate handoffs with embeddings, verifies them with the configured LLM, and builds a directed skill graph. It analyzes local skill folders only.

Install the graph extra before using scenario mode:

```bash
pip install "skillnet-ai[graph]"
```

```python
graph = client.analyze(
    "./my_skills",
    mode="scenario",
    embedding_api_key="your-embedding-api-key",
    embedding_base_url="https://embedding.example/v1",
    embedding_model="your-embedding-model",
    output_dir="./my_skills/skillnet_graph",
    max_workers=4,
    top_k=30,
    timeout=120,
)

print(graph["scenario_skill_graph"]["edges"])
print(graph["relationships"])  # compatibility view
```

`basic` mode returns `list[dict]`. `scenario` mode returns a graph result dictionary with a `relationships` compatibility view.

Scenario mode writes graph artifacts under `SKILLS_DIR/skillnet_graph` by default:

```text
skillnet_graph/
├── skill_scenarios.json
├── scenario_dedup.json
├── scenario_alignment.json
├── scenario_alignment_keep.json
├── skill_edge_redundancy_reviews.json
├── scenario_alignment_nonredundant_keep.json
├── scenario_skill_graph.json
└── relationships.json
```

Scenario embedding configuration is intentionally separate from chat LLM configuration. `API_KEY`, `BASE_URL`, and `SKILLNET_MODEL` configure extraction and verification; `EMBEDDING_API_KEY`, `EMBEDDING_BASE_URL`, and `EMBEDDING_MODEL` configure the embedding API.

### Orchestrate

`orchestrate` requires `API_KEY`. It selects skills for a preset scene and returns a skill collection URL, selected skill names, and a downstream agent prompt. The first release supports `scene="sciatlas"`.
Its `BASE_URL` must support Claude Agent SDK requests; an OpenAI-only endpoint is not sufficient.

```bash
pip install "skillnet-ai[orchestrate]"
```

```python
result = client.orchestrate(
    "Find recent papers on retrieval-augmented generation and propose three follow-up ideas.",
    scene="sciatlas",
    timeout=240,
)

print(result.package_url)
print([skill.name for skill in result.skills])
print(result.prompt)
```

Returned object:

```python
result.package_url  # GitHub URL for the full skill collection
result.skills       # selected skills with skill_id and name
result.prompt       # downstream execution-agent prompt
```

---

## CLI

The CLI is installed with the package:

```bash
skillnet --help
skillnet <command> --help
```

### Commands

| Command | What it does | Example |
| :-- | :-- | :-- |
| `search` | Search SkillNet | `skillnet search "pdf" --mode vector` |
| `download` | Install a skill | `skillnet download <url> -d ./skills` |
| `create` | Create a skill package | `skillnet create --prompt "A skill for table extraction"` |
| `evaluate` | Evaluate a local or remote skill | `skillnet evaluate ./my_skill` |
| `analyze` | Analyze local skill relationships or scenario graphs | `skillnet analyze ./my_skills` |
| `orchestrate` | Build a scene skill handoff | `skillnet orchestrate "search papers about RAG"` |

### Search

```bash
skillnet search "pdf"
skillnet search "analyze financial reports" --mode vector --threshold 0.85
skillnet search "visualization" --category "Development" --sort-by stars --limit 10
```

### Download

```bash
skillnet download https://github.com/anthropics/skills/tree/main/skills/algorithmic-art
skillnet download <url> -d ./my_agent/skills
skillnet download <private_url> --token <your_github_token>
skillnet download <url> --mirror https://ghfast.top/
```

### Create

```bash
skillnet create ./logs/trajectory.txt -d ./skills
skillnet create --github https://github.com/owner/repo
skillnet create --office ./docs/guide.pdf
skillnet create --prompt "A skill for table extraction"
skillnet create --office report.pdf --model gpt-4o
```

### Evaluate

```bash
skillnet evaluate ./my_skills/web_search
skillnet evaluate https://github.com/anthropics/skills/tree/main/skills/algorithmic-art
skillnet evaluate ./my_skill --category "Development" --model gpt-4o
```

### Analyze

Basic relationship analysis:

```bash
skillnet analyze ./my_skills
skillnet analyze ./my_skills --no-save
skillnet analyze ./my_skills --model gpt-4o
```

Scenario graph analysis requires `skillnet-ai[graph]` and an OpenAI-compatible embedding endpoint:

```bash
pip install "skillnet-ai[graph]"

export EMBEDDING_API_KEY="your-embedding-api-key"
export EMBEDDING_BASE_URL="https://embedding.example/v1"
export EMBEDDING_MODEL="your-embedding-model"

skillnet analyze ./my_skills --mode scenario \
  --output-dir ./my_skills/skillnet_graph \
  --max-workers 4 \
  --top-k 30 \
  --timeout 120
```

You can also pass `--embedding-api-key`, `--embedding-base-url`, and `--embedding-model` directly. `--max-workers` controls scenario extraction, candidate verification, and redundancy review concurrency. `--top-k` controls how many candidate scenario handoffs are retrieved for each produced scenario before LLM verification. Use `--force` to recompute existing artifacts.

### Orchestrate

```bash
pip install "skillnet-ai[orchestrate]"

skillnet orchestrate "Find recent RAG papers and propose three follow-up ideas" \
  --scene sciatlas \
  --timeout 240
```

The terminal output includes the collection URL, selected skills, and the downstream agent prompt. Use `--json` when calling from scripts.

---

## Configuration

| Variable | Required for | Default |
| :-- | :-- | :-- |
| `API_KEY` | `create`, `evaluate`, `analyze`, `orchestrate` | unset |
| `BASE_URL` | Custom LLM endpoint; orchestration requires a Claude Agent SDK-compatible gateway | `https://api.openai.com/v1` |
| `SKILLNET_MODEL` | Default LLM model | `gpt-4o` |
| `GITHUB_TOKEN` | Private repos or higher GitHub rate limits | unset |
| `GITHUB_MIRROR` | GitHub download mirror | unset |
| `EMBEDDING_API_KEY` | `analyze --mode scenario` | unset |
| `EMBEDDING_BASE_URL` | `analyze --mode scenario` | unset |
| `EMBEDDING_MODEL` | `analyze --mode scenario` | unset |

`search` and public `download` require no credentials.

Linux / macOS:

```bash
export API_KEY="your-api-key"
export BASE_URL="https://api.openai.com/v1"
export SKILLNET_MODEL="gpt-4o"
```

Windows PowerShell:

```powershell
$env:API_KEY = "your-api-key"
$env:BASE_URL = "https://api.openai.com/v1"
$env:SKILLNET_MODEL = "gpt-4o"
```

---

## Skill Package Layout

Every created or downloaded skill uses the same basic structure:

```text
skill-name/
├── SKILL.md          # required metadata and instructions
├── scripts/          # optional executable helpers
├── references/       # optional reference material
└── assets/           # optional templates, examples, or media
```

This layout keeps routing instructions, deterministic helper code, and heavier reference material separate so agents can load only what they need.

---

## Contributing

Contributions are welcome. Open an issue for bugs, feature requests, or documentation improvements, and submit pull requests for focused changes.

## License

[MIT](LICENSE)
