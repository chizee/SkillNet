# Agent installation and resource paths

Distribute the same complete `skillnet/` directory to every host. Do not maintain
four different prompts. Copy all references and scripts along with SKILL.md.
Host discovery, CLI execution and successful task completion are separate checks.

| Agent | Installation |
|---|---|
| Codex | New project installation: `.agents/skills/skillnet/`. Preserve an existing `$CODEX_HOME/skills/skillnet/` or `~/.codex/skills/skillnet/`; newer versions also document `~/.agents/skills`. Use one active copy. |
| Claude Code | Project `.claude/skills/skillnet/` or user `~/.claude/skills/skillnet/`; invoke through the host's skill UI or `/skillnet`. |
| dsh | Project `.dsh/skills/skillnet/` or `.agents/skills/skillnet/`; user `$DSH_HOME/skills/skillnet/` (normally `~/.dsh/skills/skillnet/`). The supplied snapshot's catalog truncates descriptions at 500 characters. |
| WorkBuddy | Add Skill → upload/import the local skill package, then enable it. Follow the actual client's supported import format. Do not infer its storage path from CodeBuddy CLI documentation. |

Where the host already provides the loaded skill path, use it as the resource
base. Otherwise locate the installed SKILL.md through the host's file tools.
Relative references resolve against that file's directory. No Claude-specific
shell interpolation, special question tool, plugin hooks or symlinks are required.

## Windows and macOS

Use native file tools or PowerShell on Windows and native file tools or the user's
shell on macOS. The core `skillnet` command flags are the same. Quote paths with
spaces. Python helpers use pathlib/subprocess argument lists rather than shell
commands. See [setup.md](setup.md) if the desktop app does not inherit the terminal's
PATH; use the installed virtualenv's full interpreter path.

For downloads, prefer the user's explicit target, then `SKILLNET_SKILLS_DIR`, then
the active host's known skill directory when permanent installation is requested.
For task-local use, `./downloaded_skills` is sufficient. Creation defaults to
`./generated_skills`; inspect and test output before moving it into an active skill
library. Do not guess a WorkBuddy directory or overwrite an imported copy.

After installation, refresh the host's skill list or start a fresh conversation
as required by that client. Verify that it can read a linked reference and run
`skillnet doctor --json` from a workspace other than the skill directory.

## WorkBuddy release check

Official documentation confirms local package import and enable/disable support.
The archive layout, full resource import and Python/config access still require
Windows/macOS client testing. Record the supported client version and archive
layout after testing before marking compatibility verified.

Sources:
- Codex: https://learn.chatgpt.com/docs/build-skills
- Claude Code: https://code.claude.com/docs/en/skills
- dsh: https://github.com/deepseek-ai/deepseek-harness/blob/ddefc45fbc7f8e46dd73185e68295696d1297887/docs/subsystems/skills.zh.md
- WorkBuddy: https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market
