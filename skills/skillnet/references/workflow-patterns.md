# Creation sources and representative tasks

All creation workflows call the real SkillNet SDK and use the configured model
API. Explain what input will be sent when that matters for the user's data.
Outputs default to the workspace's `generated_skills/` directory.

## Description / 从需求创建

User: “把检查 CSV 必需列的流程做成一个 skill，并评估一下。”

```text
skillnet create --prompt "Check CSV required columns supplied by the user; report missing columns without modifying the input file." --output-dir "./generated_skills" --evaluate --json
```

Inspect the returned structure and ratings. Exercise the generated skill on one
CSV with a missing column and one valid CSV; compare the actual reports with the
known headers. A Good rating alone does not satisfy that test.

## GitHub repository / 从仓库创建

User: “Turn this repository into a reusable skill for its normal users.”

```text
skillnet create --github "https://github.com/owner/repository" --max-files 20 --output-dir "./generated_skills" --evaluate --json
```

SkillNet fetches repository metadata, README, file tree and selected code signatures
for the configured model. It does not exhaustively understand a repository.
Choose a relevant, reasonably sized repository. A repository URL supplied merely
for code review is not by itself a request to create a skill.

## Document / 从文档创建

User: “把这份操作手册整理成可复用 skill。”

```text
skillnet create --office "./inputs/操作手册.docx" --output-dir "./generated_skills" --evaluate --json
```

Supported readers cover PDF, DOCX and PPTX text. Scanned pages, layout-dependent
instructions and images may not produce adequate text; empty extraction must be
reported rather than treated as a completed skill. No OCR or GPU stack is installed
by this skill. The existing Office readers are included in the base SDK.

## Execution trace / 从执行经验创建

User: “Package the reusable workflow in this execution trace.”

```text
skillnet create "./inputs/trace.txt" --output-dir "./generated_skills" --evaluate --json
```

Use a task-relevant trace with secrets and unrelated private information removed.
Trajectory creation can produce multiple skills and uses metadata extraction
followed by generation. The evaluation request covers each generated skill, so
cost grows with output count. Inspect per-path results.

## Existing skill / 评估已有技能

User: “这个 skill 能直接使用吗？有哪些需要改进的地方？”

```text
skillnet validate "./my-skill" --json
skillnet evaluate "./my-skill" --json
```

Explain structural issues separately from the five model-rated dimensions. If
execution was not tested, say so. A focused follow-up should address the reported
issue rather than regenerate everything.

## Compatibility scripts

The retained `scripts/skillnet_create.py` accepts `--prompt`, `--github`, `--office`
and `--trajectory`; evaluation defaults on and `--no-evaluate` skips it. It delegates
to the CLI. `scripts/skillnet_validate.py` delegates to the same SDK validator.
Use their `--help` for arguments; direct CLI commands are preferred for new usage.
