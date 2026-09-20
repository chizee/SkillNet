# SkillNet skill 0.1.1 acceptance

This directory holds reproducible cases and explicit live checks. It is not bundled
into the runtime skill. The release target is one canonical skill usable in Codex,
Claude Code, dsh and WorkBuddy on native Windows and macOS.

## Recorded status (2026-09-20)

| Check | Status and evidence |
|---|---|
| Local baseline | 119 tests passed on Linux/Python 3.10; public commit `5c472b36d2a435001fdae3bc8439886d8050645a` plus the existing local creator-path fix/tests |
| Candidate automated suite | 199 tests passed on Linux/Python 3.10 using `python -m pytest skillnet-ai/tests -q`; covers SDK/CLI, config reuse, parameter compatibility, download recovery, wrappers and packaging |
| Skill structure | Shared SDK validator and Codex skill-creator validator passed; description fits dsh's 500-character catalog limit |
| Live public search | `csv`, limit 2: two results with complete URLs; no credentials used |
| Live public download | Downloaded all 6 files of the baseline `skills/skillnet` from the pinned GitHub commit; SKILL.md bytes match Git content |
| Windows/macOS SDK checks | CI matrix prepared for Python 3.10/3.12; remote jobs not run in this environment |
| Linux Codex CLI | 0.155.0-alpha.9.2, with a temporary minimal configuration and the project's configured `gpt-5.4-mini` compatible endpoint: explicit skill loading, search, one creation with evaluation, and both synthetic CSV execution checks passed; session exited 0 in about 111 seconds |
| Model API | The project's configured `gpt-5.4-mini` endpoint was used for real creation/evaluation and the budget reassessment below. DeepSeek API / GLM Coding Plan remain pending; those specific provider paths were not tested |
| Four Windows/macOS clients | Pending: the completed Codex run was on Linux; no native Windows/macOS, Claude Code, dsh or WorkBuddy client result is claimed |
| Search HTTPS | Prior check found a hostname certificate mismatch; HTTP default works. Infrastructure repair and TLS-valid recheck remain pending |

A release is ready only after automated checks pass and the missing client/API
rows have actual evidence. Do not turn “format supported” or a mocked HTTP test
into a claim of successful real-agent operation.

The Codex run used preconfigured model credentials and an explicit `$skillnet`
request. It does not verify first-time configuration, automatic triggering or
downloading a search candidate. The initial search timed out through the server's
local proxy; a second keyword query returned five candidates. The server's default
Codex MCP configuration and original model stream failed before the successful
run, so the test used a temporary configuration without changing global settings.

## Script-reading budget follow-up

The shared evaluator now reads 12,000 characters per script, still at most five
scripts. Regression tests cover a 2,694-character utility, the exact 12,000-character
boundary, truncation at 12,001, the five-file cap, and an explicit smaller budget.
They also verify Unicode character counting and injection screening of newly
included script content while script execution stays disabled.

A real API reassessment used the unchanged 92-line, 2,694-character
`csv-header-check` produced in a Linux Codex session, with the same configured
`gpt-5.4-mini` compatible endpoint. The previous 1,200-character budget truncated
its script and the model rated completeness/executability Average. With the new
budget, all script content was loaded, scan coverage was complete with no issues,
and this reassessment returned Good on all five dimensions (about 5.7 seconds).
This is one observed model result, not a guarantee of scores or task correctness.
The earlier two CSV execution checks passed independently; reassessment did not
regenerate the skill or execute its scripts.

## Local review before commit

The review added regression coverage for GitHub SKILL.md blob links, downloader
errors returned by remote evaluation, nested Markdown fences and malformed FILE
blocks, interrupted model completions, current-directory validation, interactive
key replacement, server error redaction, explicit repository refs and saturated
GitHub directory listings. These failures were reproduced before the fixes.
The existing creator path protections and their tests remain covered.

## Automated checks

From the public repository root, using an isolated Python environment:

```text
python -m pip install -e ./skillnet-ai pytest build
python -m pytest skillnet-ai/tests -q
python -m skillnet_ai validate skills/skillnet --strict --json
python -m build ./skillnet-ai --outdir dist
python skillnet-ai/tools/package_skill.py --output dist/skillnet-0.1.1.zip
```

The default suite isolates user configuration and blocks external network traffic.
Compatibility tests use the real OpenAI SDK with an in-memory HTTP transport.
Existing creator path and evaluator injection-boundary tests remain included.
CI adds native Windows/macOS runners; WSL is not a substitute for the Windows run.
The known Pydantic class-config deprecation comes from the pre-existing model code.

The ZIP contains `skillnet/SKILL.md`, references and scripts; it excludes caches and
local configuration. SDK wheel/sdist and the skill ZIP are separate artifacts.
WorkBuddy's accepted archive layout must still be checked on the actual client.

## Real model API check (explicitly billable)

Configure the endpoint/model from the provider's current documentation. Supply the
key through a named environment variable; never record its value in artifacts.
The same small task is used for each service:

```text
python skillnet-ai/acceptance/run_live.py --provider-label deepseek --base-url "<DeepSeek-compatible-base>" --model "<model-id>" --api-key-env DEEPSEEK_API_KEY --output-dir ./live-results/deepseek-run-1
python skillnet-ai/acceptance/run_live.py --provider-label glm-coding-plan --base-url "<Coding-Plan-compatible-base>" --model "<model-id>" --api-key-env ZHIPU_API_KEY --output-dir ./live-results/glm-run-1
```

Use a new output directory each time. The runner creates one CSV-header skill,
checks its structure and evaluates it through the selected model. It saves paths,
reports, elapsed time, endpoint/model and SDK/OS versions. Missing credentials exit
2 as pending, not passed. Failure exits 1. A passed result still records actual
execution of the generated skill as pending: review and exercise it separately.

## Four-client acceptance

Run each workflow in `cases.json` in native Windows and macOS, where that client
version is available. Record a separate result for each agent/OS combination:

1. Install/import the whole package. Verify discovery, a linked reference and
   `skillnet doctor --json` from a different working directory.
2. Configure API once; open a new conversation and verify reuse without requesting
   the key again. Check a desktop app whose PATH differs from the terminal's.
3. Search, select, download and use a relevant skill on a real small input. Verify
   complete resources and the intended installed location.
4. Create and evaluate the CSV-header checker. Inspect its script before running;
   use one CSV with all required headers and one missing a header. Check output,
   exit behavior and that input files were not modified.
5. Cover prompt/repository/document/trace input routing. Use a small repository,
   a text-bearing DOCX/PDF and a short sanitized trace to keep cost bounded.
6. Exercise missing configuration, an existing destination and evaluation failure.
   Verify preserved files, nonzero failure status and evaluation-only recovery.

WorkBuddy additionally needs evidence of the imported archive layout, resources
remaining accessible, Python/CLI execution and the config path visible to its
runtime. Do not use CodeBuddy CLI's directory as evidence of WorkBuddy support.

## Old/new behavior comparison

`cases.json` pins the old public skill revision and includes English/Chinese trigger
positives and hard negatives. Use fresh conversations, the same host/model settings,
and the same task inputs. Do not load both skill versions in one conversation.
Do not run both credentialed variants if a smaller targeted comparison suffices.

Record: case ID, agent/version, OS/version, skill revision, endpoint/model,
trigger/no-trigger, task completion, actual artifact checks, manual interventions,
time and token/API usage when the runtime exposes it. Unknown usage is `not available`,
not zero. Keep credentials and private inputs out of traces.

Prioritize correct completion and accurate failure reporting. Publish per-case
outcomes and explain regressions; do not claim a percentage improvement from
static inspection or fabricate client runs. Keep course assignments outside this
release; these cases can later become small exercises.

## Release ordering

The source declares **0.1.1**, which is not published by these commands. First run
the remaining checks, then release the SDK through the maintainer's normal process,
and only then switch the skill's installation instructions from source checkout
to the published version. No publication, deployment or agent installation is
performed by the packaging/check scripts.
