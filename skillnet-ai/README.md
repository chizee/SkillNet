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
- **Analyze** local skills into a scenario graph with composition and similarity relationships.
- **Route** a task through a local skill Wiki and return up to k skills with source evidence.

Search and public skill download do **not** require an API key. Create, evaluate, and analyze use OpenAI-compatible endpoints. Routing uses an independently configured Claude or Codex Agent SDK and an embedding endpoint.

For the full project overview, research context, integrations, and roadmap, see the [main SkillNet repository](https://github.com/zjunlp/SkillNet).

---

## Installation

The analyze/route APIs below require the 0.2.0 source tree. Until it is published,
install this checkout with `pip install -e ".[graph,claude]"`.


```bash
pip install skillnet-ai
```

Optional extras:

```bash
pip install "skillnet-ai[graph]"        # scenario graph analysis
pip install "skillnet-ai[graph,claude]"  # local routing via Claude Agent SDK
pip install "skillnet-ai[graph,codex]"   # local routing via Codex SDK
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
| Route local skills | `client.route(...)` | `skillnet route ...` | Embedding + Agent SDK |

---

## Python SDK

### Initialize

```python
from skillnet_ai import SkillNetClient

client = SkillNetClient(
    api_key="your-api-key",       # required for create, evaluate, analyze
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

print(report["safety"]["level"], report["safety"]["reason"])
print(report["maintainability"]["level"], report["maintainability"]["reason"])
```

SkillNet evaluates five dimensions:

- Safety
- Completeness
- Executability
- Maintainability
- Cost awareness

### Analyze and route local skills

`analyze` builds a reusable scenario graph, retrieval index and Wiki from local skill
folders. `route` retrieves a task-specific subgraph and uses a configured Claude or
Codex Agent SDK to read source evidence and select up to `k` skills.

```python
analysis = client.analyze("./my_skills", output_dir="./skillnet_index")
result = client.route(
    "Compute statistics from my existing CSV tables",
    index_dir=analysis.index_dir,
    k=5,
)
for skill in result.skills:
    print(skill.name, skill.path, skill.reason)
print(result.coverage_gaps)
```

The graph has two relations: directed `compose_with` for scenario-supported
combinations, and undirected `similar_to` for comparable capabilities. Relations
suggest candidates; they do not force co-selection. Routing returns skills and
source evidence without generating an execution prompt.

Place each skill in a direct child folder containing a YAML-frontmatter `SKILL.md`.
Folder names are stable IDs; display names may repeat. Analysis reads the full
SKILL.md but does not execute or automatically inspect linked scripts/references.
The `graph` extra provides NumPy; BM25 requires SQLite FTS5. Agent SDK extras are
loaded only for routing. Install from this checkout with `pip install -e '.[graph,claude]'`
or `pip install -e '.[graph,codex]'`.

Analysis, embeddings and Explorer SDKs have separate endpoint settings. Configure
them using existing credential environment variables:

```bash
skillnet configure --base-url https://chat.example/v1 --model analysis-model \
  --api-key-env MY_CHAT_KEY
skillnet configure --embedding-base-url https://embedding.example/v1 \
  --embedding-model embedding-model --embedding-api-key-env MY_EMBEDDING_KEY
skillnet configure --explorer-backend claude --explorer-base-url https://agent.example \
  --explorer-model explorer-model --explorer-api-key-env MY_AGENT_KEY
skillnet doctor --json
```

Analysis uses Chat Completions; embeddings use the embeddings API. The Explorer
gateway must support the selected SDK's actual protocol, tools and structured
output. SkillNet does not infer one endpoint from another or load a workspace
`.env` automatically. `doctor --check-explorer --json` makes an explicitly billable
SDK tool-reading and structured-output check. Default backend: `claude`; select
Codex with `route(..., backend="codex")` or `--backend codex`.

For per-call configuration, pass `Endpoint(api_key=..., base_url=..., model=...)`
as `embedding` or `explorer`. Credentials use Pydantic `SecretStr`. The analyze
`model` keyword changes only the analysis model, retaining the client's URL/key.

Pass typed budgets through `options=AnalysisOptions(...)` or
`options=RouteOptions(...)`, imported from `skillnet_ai`:

| Analysis option | Default | Meaning |
| :-- | :-- | :-- |
| `max_workers` | `4` | Parallel profile extractions or pair judgments |
| `candidate_limit` | `8` | Fused capability candidates and aggregated handoff candidates per skill; explicit references are additional |
| `embedding_batch_size` | `8` | Texts per embedding request |
| `timeout` | `120` | Model/embedding request timeout in seconds, not a whole-build deadline |
| `request_retries` | `0` | Transport retries; no content-generation retry loop |
| `json_mode` | `"on"` | Strict JSON Schema; `"off"` requests JSON through the prompt only |
| `reasoning_effort` | `None` | Omitted unless explicitly set to a model-supported none/low/medium/high |

For reasoning models such as `gpt-5.4-mini`, set
`AnalysisOptions(reasoning_effort="medium")` or `--reasoning-effort medium` explicitly.
Invalid JSON still fails in prompt-only mode; there is no repair or automatic
protocol downgrade. The analysis option is independent of evaluation's JSON mode.

| Routing option | Default | Meaning |
| :-- | :-- | :-- |
| `seed_limit` | `24` | Seeds from BM25/vector reciprocal rank fusion |
| `candidate_limit` | `100` | Total candidates after graph expansion; must be at least seed_limit |
| `max_depth` | `2` | Graph expansion depth; zero keeps only seeds |
| `timeout` | `300` | Query embedding timeout and a separate SDK exploration timeout, in seconds |
| `max_turns` | `24` | Claude SDK turn limit; unused by Codex |
| `read_limit` | `None` | Defaults to 2 + 2*k; Claude Read-call budget; Codex command budget adds 9 |
| `reasoning_effort` | `"medium"` | Explorer reasoning: low/medium/high |

`k` is a separate route argument (default 5), an upper bound rather than a quota.
An empty selection with coverage gaps is valid. Returned order is not execution
order. Results contain `skills` (ID, name, original path, reason, source-line
evidence), `coverage_gaps`, and available SDK `usage`; embedding usage is not included.
The program validates IDs, duplicates, count, source-page reads and citation bounds;
the semantic quality of relations and selections still depends on the model.

Analysis returns `index_dir`, `skill_count`, `relation_counts` and `cache_hits`.
Output defaults to `skills/.skillnet`. A `CURRENT` pointer identifies the successful
immutable snapshot containing `graph.json`, `embeddings.npz`, `bm25.sqlite` and
template-generated `wiki/`. The graph retains full source snapshots, profiles and
relation evidence; Wiki generation makes no additional model calls.

Successful model results, including negative pair judgments, are stored in one
`cache.sqlite`. Source fingerprints and explicit model/prompt versions control reuse.
Run analyze again after editing skills; `force=True` / `--force` recomputes results.
Routing uses the published graph snapshot and regenerates a temporary task Wiki;
it does not rescan live sources or use manual edits to generated Wiki pages.
It requires the same embedding endpoint/model and compatible vector dimensions.

Publication updates `CURRENT` only after all outputs succeed. Old snapshots remain
for in-flight readers and can be removed when no readers use them. Failed model
calls, damaged indexes and SDK timeouts produce errors; there is no provider switch,
Explorer retry or retrieval-only result substituted for failed exploration.

**Migration to 0.2.0:** remove analyze's `mode` and `save_to_file`, configure embeddings
and rebuild old graphs. Replace `orchestrate(query, scene=...)` with
`route(query, index_dir=..., k=...)`. Old aliases, preset scenes and `depend_on`
relations are removed. Search, download, create and evaluate retain their APIs.
When changing extraction or relation schemas/semantics, increment the explicit
versions in `src/skillnet_ai/core/prompts.py` to invalidate obsolete cached results.

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
| `route` | Select local skills for a task | `skillnet route "analyze my CSV" --index-dir ./skillnet_index` |

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
# With GITHUB_TOKEN already configured:
skillnet download <private_url>
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

### Analyze and route

```bash
skillnet analyze ./my_skills --output-dir ./skillnet_index --json
skillnet route "Compute statistics from my CSV" --index-dir ./skillnet_index --k 5 --json
```

## Agent-facing workflow updates (0.2.0)

The [portable skill](../skills/skillnet/SKILL.md) uses this same CLI/SDK across agents.
See [Windows/macOS setup](../skills/skillnet/references/setup.md).
Before publication, install this checkout.

```text
skillnet configure --interactive
skillnet doctor --json
skillnet search "csv" --limit 5 --json
skillnet create --prompt "Check CSV required columns" --evaluate --json
skillnet validate ./generated_skills/example --json
```

`configure` prompts only with `--interactive`; headless callers can use
`--api-key-env VARIABLE_NAME` or `--api-key-stdin`. Optional user settings live in
`~/.skillnet/config.json` (override with `SKILLNET_CONFIG`). Resolution is explicit
arguments → environment → user config → defaults, at runtime. The key is stored
locally in plaintext with user-file permissions; keep this file out of repositories.
`doctor` is local by default; `--check-network` and potentially billable `--check-llm`
are opt-in. No model key is needed for search/public download.

The six workflow commands support `--json`: one `{ok, data, error}` document on stdout, with
logs on stderr. Creation remains non-evaluating by default; `--evaluate` adds
structure validation and per-skill model reports. Evaluation failures preserve
created paths and return a nonzero exit. Poor ratings are valid evaluation results.
See the [output contract and error recovery](../skills/skillnet/references/api-reference.md).

Downloads now stage complete files before installing. Existing folders require
`--overwrite` / `client.download(..., overwrite=True)`; failed replacement keeps
the previous installation. The facade/CLI checks skill structure; the lower-level
downloader can still retrieve ordinary files. GitHub authentication stays on GitHub
API requests; configured mirrors are unauthenticated public-file fallbacks only.
Encoded branch slashes (`feature%2Fcsv`) or commit SHAs disambiguate download URLs.

`SkillNetClient` also accepts keyword-only `model`, `skillnet_api_url`, and
`json_mode`. `evaluate(..., json_mode="off")` disables the optional JSON-mode API
parameter while retaining JSON parsing and five-dimension schema validation.
`auto` retries once without that parameter only when the endpoint explicitly
rejects it; an unsupported temperature can also be removed once. Provider, model
and account failures never cause an automatic provider switch.

Evaluation reads at most 5 script files, with **12,000 characters per script**
(increased from 1,200 so ordinary utility scripts can be read completely). The
script portion is bounded at 60,000 characters; SKILL.md remains capped at 12,000
and references at 10 files × 4,000 characters. These shared defaults apply to the
SDK, CLI and agent skill. Truncation or omitted files are reported in
`prompt_injection_scan.scan_issues` with `complete: false`. Larger inputs can cost
more tokens; direct `SkillLoader.load_scripts(..., max_chars=...)` callers can
retain a smaller explicit budget.

## Configuration

| Variable | Required for | Default |
| :-- | :-- | :-- |
| `API_KEY` | `create`, `evaluate`, `analyze` | unset |
| `BASE_URL` | Chat Completions endpoint for create, evaluate and analyze | `https://api.openai.com/v1` |
| `SKILLNET_MODEL` | Default LLM model | `gpt-4o` |
| `GITHUB_TOKEN` | Private repos or higher GitHub rate limits | unset |
| `GITHUB_MIRROR` | Public raw-file fallback mirror (disabled with GitHub authentication) | unset |
| `SKILLNET_API_URL` | Search service base URL | `http://api-skillnet.openkg.cn` |
| `SKILLNET_JSON_MODE` | Evaluation JSON mode: auto/on/off | `auto` |
| `SKILLNET_CONFIG` | Optional user config path | `~/.skillnet/config.json` |
| `EMBEDDING_API_KEY` | `analyze` and `route` | unset |
| `EMBEDDING_BASE_URL` | `analyze` and `route` | unset |
| `EMBEDDING_MODEL` | `analyze` and `route` | unset |
| `SKILLNET_EXPLORER_BACKEND` | `route`: claude or codex | `claude` |
| `SKILLNET_EXPLORER_API_KEY` | `route` SDK credential | unset |
| `SKILLNET_EXPLORER_BASE_URL` | `route` SDK-compatible base URL | unset |
| `SKILLNET_EXPLORER_MODEL` | `route` SDK model | unset |

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

The top level contains the main capabilities: `searcher.py`, `downloader.py`,
`creator.py`, `evaluator.py` and `analyzer.py`. Analysis owns source extraction,
relationship construction and model-result caching. `router/` contains the routing
flow (`router.py`), index construction/loading/retrieval (`index.py`), Wiki rendering
(`wiki.py`) and both Agent SDK implementations (`explorer.py`).

`core/` contains data contracts, prompts, model requests, configuration, validation
and the existing injection scanner. It does not import the business modules.
`interfaces/client.py` and `interfaces/cli.py` expose the Python and CLI entry points.
Package initializers only declare packages or export entry points. Public imports
such as `from skillnet_ai import SkillNetClient` and the `skillnet` command remain
unchanged; previous internal module paths have no forwarding aliases.

From this directory, install `pip install -e '.[graph,dev,claude,codex]'`, then run
`pytest -q`, `mypy` and `python -m build`. The analyze/route tests replace network
boundaries; ordinary tests do not require model credentials.

## License

[MIT](LICENSE)
