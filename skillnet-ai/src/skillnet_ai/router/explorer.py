"""SDK-managed Wiki exploration using Claude or Codex.

SDK setup adapted from SkillFabric; Copyright (c) 2026 SkillFabric Contributors, MIT.
"""

import asyncio
import logging
import threading
from collections import Counter
from collections.abc import AsyncGenerator, AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import aclosing
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel

from skillnet_ai.core.models import Endpoint, Exploration, RouteOptions, SkillSelection
from skillnet_ai.core.prompts import CODEX_EXPLORER_TOOLS, explorer_prompt, task_prompt

if TYPE_CHECKING:
    from claude_agent_sdk import Message
    from claude_agent_sdk.types import HookContext, HookInput, HookJSONOutput

logger = logging.getLogger(__name__)
PATH_KEYS = {"Read": "file_path", "Glob": "path", "Grep": "path", "LS": "path"}


class ClaudeExplorer:
    """Run exactly one SDK-managed conversation, including in notebook callers."""

    def explore(
        self, root: Path, query: str, k: int, endpoint: Endpoint, options: RouteOptions
    ) -> Exploration:
        try:
            import claude_agent_sdk  # noqa: F401
        except ImportError as exc:
            raise ImportError("Install skillnet-ai[graph,claude] to use this backend.") from exc
        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(
                lambda: asyncio.run(self._run(root, query, k, endpoint, options))
            ).result()

    async def _run(
        self, root: Path, query: str, k: int, endpoint: Endpoint, options: RouteOptions
    ) -> Exploration:
        from claude_agent_sdk import ClaudeAgentOptions, HookMatcher, ResultMessage
        from claude_agent_sdk import query as sdk_query

        root = root.resolve()
        counts: Counter[str] = Counter()
        read_limit = options.read_limit or 2 + 2 * k

        async def pre_tool(
            data: "HookInput", _tool_id: str | None, _context: "HookContext"
        ) -> "HookJSONOutput":
            name = str(data.get("tool_name", ""))
            arguments = data.get("tool_input", {})
            key = PATH_KEYS.get(name)
            allowed = key is not None and isinstance(arguments, dict)
            if key is not None and isinstance(arguments, dict):
                path = (root / str(arguments.get(key, "."))).resolve()
                allowed = path.is_relative_to(root) and counts[name] < (
                    read_limit if name == "Read" else 3
                )
            if allowed:
                counts[name] += 1
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow" if allowed else "deny",
                    "permissionDecisionReason": "Read-only task Wiki and tool budget.",
                }
            }

        sdk_options = ClaudeAgentOptions(
            model=endpoint.model,
            cwd=root,
            system_prompt=explorer_prompt(k, read_limit),
            tools=list(PATH_KEYS),
            allowed_tools=list(PATH_KEYS),
            permission_mode="default",
            setting_sources=[],
            max_turns=options.max_turns,
            env={
                "ANTHROPIC_API_KEY": endpoint.api_key.get_secret_value(),
                "ANTHROPIC_AUTH_TOKEN": "",
                "CLAUDE_CODE_OAUTH_TOKEN": "",
                "ANTHROPIC_BASE_URL": endpoint.base_url,
                "ANTHROPIC_MODEL": endpoint.model,
                "ANTHROPIC_SMALL_FAST_MODEL": endpoint.model,
                "ANTHROPIC_DEFAULT_HAIKU_MODEL": endpoint.model,
                "ANTHROPIC_DEFAULT_SONNET_MODEL": endpoint.model,
                "ANTHROPIC_DEFAULT_OPUS_MODEL": endpoint.model,
                "CLAUDE_CODE_MAX_RETRIES": "0",
                "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            },
            effort=options.reasoning_effort,
            extra_args={"disable-slash-commands": None},
            hooks={
                "PreToolUse": [HookMatcher(matcher="Read|LS|Glob|Grep", hooks=[pre_tool])],
            },
            output_format={"type": "json_schema", "schema": SkillSelection.model_json_schema()},
        )

        async def prompt_stream() -> AsyncIterator[dict[str, object]]:
            yield {"type": "user", "message": {"role": "user", "content": task_prompt(query)}}

        async def collect() -> Exploration:
            result: Exploration | None = None
            stream = cast(
                "AsyncGenerator[Message, None]",
                sdk_query(prompt=prompt_stream(), options=sdk_options),
            )
            async with aclosing(stream):
                async for message in stream:
                    if isinstance(message, ResultMessage):
                        if message.is_error:
                            raise RuntimeError(f"Claude Explorer failed: {message.subtype}")
                        if message.structured_output is None:
                            raise RuntimeError(
                                "Claude Explorer completed without structured output."
                            )
                        selection = SkillSelection.model_validate(message.structured_output)
                        usage = {
                            key: value
                            for key, value in (message.usage or {}).items()
                            if isinstance(value, (int, float)) and not isinstance(value, bool)
                        }
                        result = Exploration(selection, usage=usage or None)
            if result is None:
                raise RuntimeError("Claude Explorer did not return a structured result.")
            return result

        try:
            return await asyncio.wait_for(collect(), timeout=options.timeout)
        except asyncio.TimeoutError as exc:
            raise TimeoutError(f"Claude Explorer exceeded {options.timeout:g} seconds.") from exc


def validate_wiki_command(item: dict[str, Any], root: Path) -> None:
    """Check SDK-parsed command types and paths against the task Wiki."""

    cwd = (root / item["cwd"]).resolve()
    if not cwd.is_relative_to(root):
        raise ValueError("Codex command left the task Wiki.")
    actions = item["commandActions"]
    if not actions:
        raise ValueError("Codex command has no recognized read/search action.")
    for action in actions:
        if action["type"] not in {"read", "listFiles", "search"}:
            raise ValueError("Codex Explorer supports only file reads and searches.")
        value = action.get("path")
        if value is None:
            continue
        path = (cwd / value).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Codex command accessed a path outside the task Wiki.")


class CodexExplorer:
    """Own one isolated SDK session; no alternate transport or result recovery."""

    def explore(
        self, root: Path, query: str, k: int, endpoint: Endpoint, options: RouteOptions
    ) -> Exploration:
        try:
            import openai_codex as sdk
            from openai_codex.types import ReasoningEffort
        except ImportError as exc:
            raise ImportError("Install skillnet-ai[graph,codex] to use this backend.") from exc

        root = root.resolve()
        read_limit = options.read_limit or 2 + 2 * k
        with TemporaryDirectory(prefix="skillnet-codex-") as state_dir:
            config = sdk.CodexConfig(
                cwd=state_dir,
                env={
                    "CODEX_HOME": state_dir,
                    "CODEX_SQLITE_HOME": state_dir,
                    "OPENAI_API_KEY": endpoint.api_key.get_secret_value(),
                    "CODEX_API_KEY": "",
                    "CODEX_ACCESS_TOKEN": "",
                },
                config_overrides=("check_for_update_on_startup=false",),
            )
            client = sdk.Codex(config=config)
            expired = threading.Event()

            def expire() -> None:
                expired.set()
                try:
                    client.close()
                except Exception:
                    logger.warning("Codex timeout cleanup failed", exc_info=False)

            watchdog = threading.Timer(options.timeout, expire)
            watchdog.daemon = True
            watchdog.start()
            failed = False
            try:
                client.__enter__()
                client.login_api_key(endpoint.api_key.get_secret_value())
                thread = client.thread_start(
                    cwd=str(root),
                    model=endpoint.model,
                    model_provider="skillnet",
                    ephemeral=True,
                    approval_mode=sdk.ApprovalMode.deny_all,
                    sandbox=sdk.Sandbox.read_only,
                    developer_instructions=explorer_prompt(k, read_limit) + CODEX_EXPLORER_TOOLS,
                    config={
                        "openai_base_url": endpoint.base_url,
                        "web_search": "disabled",
                        "project_root_markers": [],
                        "project_doc_max_bytes": 0,
                        "project_doc_fallback_filenames": [],
                        "allow_login_shell": False,
                        "model_providers": {
                            "skillnet": {
                                "name": "SkillNet configured gateway",
                                "base_url": endpoint.base_url,
                                "env_key": "OPENAI_API_KEY",
                                "wire_api": "responses",
                                "request_max_retries": 0,
                                "stream_max_retries": 0,
                            }
                        },
                        "features": {
                            "apps": False,
                            "multi_agent": False,
                            "plugins": False,
                            "remote_plugin": False,
                            "skill_mcp_dependency_install": False,
                        },
                        "mcp_servers": {},
                    },
                )
                turn = thread.turn(
                    task_prompt(query),
                    cwd=str(root),
                    model=endpoint.model,
                    effort=ReasoningEffort(options.reasoning_effort),
                    sandbox=sdk.Sandbox.read_only,
                    output_schema=SkillSelection.model_json_schema(),
                )
                command_count = 0
                response: str | None = None
                completed = False
                usage: dict[str, int | float] | None = None
                for event in turn.stream():
                    if event.method not in {
                        "item/started",
                        "item/completed",
                        "turn/completed",
                        "thread/tokenUsage/updated",
                        "item/commandExecution/terminalInteraction",
                    }:
                        continue
                    if not isinstance(event.payload, BaseModel):
                        raise RuntimeError("Codex returned an unsupported SDK event payload.")
                    payload = event.payload.model_dump(mode="json", by_alias=True)
                    if event.method == "item/commandExecution/terminalInteraction":
                        turn.interrupt()
                        raise ValueError("Interactive Codex commands are not allowed.")
                    if event.method in {"item/started", "item/completed"}:
                        item = payload["item"]
                        if item["type"] not in {
                            "commandExecution",
                            "agentMessage",
                            "reasoning",
                            "userMessage",
                            "contextCompaction",
                        }:
                            turn.interrupt()
                            raise ValueError(
                                f"Codex Explorer used an unsupported item: {item['type']}"
                            )
                        if item["type"] == "commandExecution":
                            validate_wiki_command(item, root)
                            if event.method == "item/started":
                                command_count += 1
                                if command_count > read_limit + 9:
                                    turn.interrupt()
                                    raise ValueError("Codex Explorer exceeded its command budget.")
                        elif item["type"] == "agentMessage" and event.method == "item/completed":
                            if item.get("phase") == "final_answer":
                                response = item["text"]
                    elif event.method == "turn/completed":
                        if payload["turn"]["status"] != "completed":
                            raise RuntimeError("Codex Explorer turn did not complete successfully.")
                        completed = True
                    elif event.method == "thread/tokenUsage/updated":
                        totals = payload["tokenUsage"]["total"]
                        usage = {
                            key: value
                            for key, value in totals.items()
                            if isinstance(value, (int, float)) and not isinstance(value, bool)
                        }
                if expired.is_set():
                    raise TimeoutError("Codex Explorer timed out.")
                if not completed or response is None:
                    raise RuntimeError(
                        "Codex Explorer did not return a completed structured result."
                    )
                return Exploration(SkillSelection.model_validate_json(response), usage=usage)
            except BaseException as exc:
                failed = True
                if expired.is_set():
                    raise TimeoutError(
                        f"Codex Explorer exceeded {options.timeout:g} seconds."
                    ) from exc
                raise
            finally:
                watchdog.cancel()
                try:
                    client.close()
                except Exception:
                    if not failed:
                        raise
                    logger.warning("Codex cleanup failed after a session error", exc_info=False)
