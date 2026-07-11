from __future__ import annotations

import asyncio
import json
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from skillnet_ai.models import (
    OrchestratedSkill,
    OrchestrateResult,
)
from skillnet_ai.prompts import (
    ORCHESTRATOR_ALLOWED_TOOLS,
    ORCHESTRATOR_DEFAULT_TOOL_BUDGET,
    render_orchestrator_explorer_system_prompt,
    render_orchestrator_explorer_user_prompt,
    render_orchestrator_execution_prompt_planner_prompt,
)

_PATH_KEYS = {"Glob": "path", "Grep": "path", "LS": "path", "Read": "file_path"}
_WRITE_TOOLS = {"Edit", "NotebookEdit", "Write"}
_DISALLOWED_TOOLS = sorted(
    _WRITE_TOOLS
    | {
        "Agent",
        "AskUserQuestion",
        "Bash",
        "EnterPlanMode",
        "ExitPlanMode",
        "Task",
        "TodoWrite",
        "WebFetch",
        "WebSearch",
    }
)

_FORBIDDEN_EXECUTION_PROMPT_FRAGMENTS = (
    "SkillNet implementation",
    "planner artifacts",
    "claude-agent-sdk",
)

_SCENE_PACKAGE_URLS = {
    "sciatlas": "https://github.com/zjunlp/Skills/tree/main/skills/skill-collections/sciatlas",
}

DEFAULT_ORCHESTRATION_TIMEOUT = 240.0


@dataclass
class SkillOrchestrator:
    api_key: str
    base_url: Optional[str] = None
    model: Optional[str] = None
    env_file: Optional[Union[str, Path]] = None
    max_selected_skills: int = 5
    max_turns: int = 12
    load_timeout_ms: int = 30_000
    execution_timeout_seconds: float = DEFAULT_ORCHESTRATION_TIMEOUT

    def orchestrate(
        self,
        query: str,
        *,
        scene: str = "sciatlas",
    ) -> OrchestrateResult:
        if not query or not query.strip():
            raise ValueError("query must be a non-empty string")

        scene_wiki = _load_scene_wiki(scene=scene)
        raw_package = _explore_scene_wiki(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            env_file=self.env_file,
            query=query,
            scene_wiki=scene_wiki,
            max_selected_skills=self.max_selected_skills,
            max_turns=self.max_turns,
            load_timeout_ms=self.load_timeout_ms,
            execution_timeout_seconds=self.execution_timeout_seconds,
        )
        validation = _validate_skill_package(raw_package, scene_wiki)
        if not validation.valid:
            raise ValueError(f"invalid SkillPackage: {'; '.join(validation.errors)}")
        warnings = [
            *validation.warnings,
            *(f"skill package validation error: {error}" for error in validation.errors),
        ]

        prompt = _plan_execution_prompt(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            env_file=self.env_file,
            query=query,
            scene_wiki=scene_wiki,
            package=validation.valid_package,
            warnings=warnings,
            load_timeout_ms=self.load_timeout_ms,
            execution_timeout_seconds=self.execution_timeout_seconds,
        )
        return _to_orchestrate_result(
            scene_skills=scene_wiki.skills,
            package=validation.valid_package,
            prompt=prompt,
            package_url=scene_wiki.package_url,
        )


@dataclass
class _SceneSkill:
    skill_id: str
    name: str
    description: str
    card_path: str
    source_path: str
    selectable: bool = True


@dataclass
class _SceneWiki:
    scene: str
    root: Path
    skills: Dict[str, _SceneSkill]
    package_url: Optional[str] = None


@dataclass
class _SkillPackageEvidence:
    path: str
    reason: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {"path": self.path, "reason": self.reason}


@dataclass
class _SkillPackageSelectedSkill:
    skill_id: str
    role: str
    evidence: List[_SkillPackageEvidence] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "role": self.role,
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass
class _SkillPackageRequiredEdge:
    before: str
    after: str
    relation_type: str = "depend_on"
    evidence_path: str = ""
    reason: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {
            "before": self.before,
            "after": self.after,
            "relation_type": self.relation_type,
            "evidence_path": self.evidence_path,
            "reason": self.reason,
        }


@dataclass
class _SkillPackageOrderedHint:
    skill_id: str
    hint: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {"skill_id": self.skill_id, "hint": self.hint}


@dataclass
class _SkillPackageNearMiss:
    skill_id: str
    reason: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {"skill_id": self.skill_id, "reason": self.reason}


@dataclass
class _SkillPackageCoverageNote:
    requirement_id: str
    status: str
    skill_ids: List[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "status": self.status,
            "skill_ids": list(self.skill_ids),
            "reason": self.reason,
        }


@dataclass
class _SkillPackage:
    selected_skills: List[_SkillPackageSelectedSkill] = field(default_factory=list)
    required_edges: List[_SkillPackageRequiredEdge] = field(default_factory=list)
    ordered_hints: List[_SkillPackageOrderedHint] = field(default_factory=list)
    near_misses: List[_SkillPackageNearMiss] = field(default_factory=list)
    coverage_notes: List[_SkillPackageCoverageNote] = field(default_factory=list)
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_skills": [item.to_dict() for item in self.selected_skills],
            "required_edges": [item.to_dict() for item in self.required_edges],
            "ordered_hints": [item.to_dict() for item in self.ordered_hints],
            "near_misses": [item.to_dict() for item in self.near_misses],
            "coverage_notes": [item.to_dict() for item in self.coverage_notes],
            "rationale": self.rationale,
        }


@dataclass
class _SkillPackageValidationResult:
    valid: bool
    valid_package: _SkillPackage
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "valid_package": self.valid_package.to_dict(),
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


def _load_scene_wiki(scene: str = "sciatlas") -> _SceneWiki:
    if scene != "sciatlas":
        raise ValueError(f"unsupported scene: {scene}")
    root = Path(__file__).parent / "resources" / "scenes" / scene
    root = root.resolve()
    if not (root / "index.md").exists():
        raise FileNotFoundError(f"missing scene wiki index: {root / 'index.md'}")
    skills = _load_scene_skills(root)
    if not skills:
        raise ValueError(f"scene wiki has no skill cards: {root / 'skills' / 'cards'}")
    return _SceneWiki(scene=scene, root=root, skills=skills, package_url=_SCENE_PACKAGE_URLS[scene])


def _load_scene_skills(wiki_root: Path) -> Dict[str, _SceneSkill]:
    cards_dir = wiki_root / "skills" / "cards"
    if not cards_dir.exists():
        return {}
    skills: Dict[str, _SceneSkill] = {}
    for card_path in sorted(cards_dir.glob("*.md")):
        metadata = _frontmatter(card_path.read_text(encoding="utf-8"))
        skill_id = metadata.get("skill_id") or f"skill:{card_path.stem}"
        source_path = _source_path(wiki_root, card_path, metadata.get("source", ""))
        skills[skill_id] = _SceneSkill(
            skill_id=skill_id,
            name=metadata.get("title") or card_path.stem,
            description=metadata.get("description", ""),
            card_path=card_path.relative_to(wiki_root).as_posix(),
            source_path=source_path,
            selectable=_bool_value(metadata.get("selectable", "true")),
        )
    return skills


def _explore_scene_wiki(
    *,
    api_key: str,
    base_url: Optional[str],
    model: Optional[str],
    env_file: Optional[Union[str, Path]],
    query: str,
    scene_wiki: _SceneWiki,
    max_selected_skills: int,
    max_turns: int,
    load_timeout_ms: int,
    execution_timeout_seconds: float,
) -> _SkillPackage:
    tool_budget = _normalize_tool_budget(None)
    system_prompt = render_orchestrator_explorer_system_prompt(
        query=query,
        wiki_root=str(scene_wiki.root),
        max_selected_skills=max_selected_skills,
        allowed_tools=ORCHESTRATOR_ALLOWED_TOOLS,
        tool_budget=tool_budget,
    )
    user_prompt = render_orchestrator_explorer_user_prompt(
        query=query,
        wiki_root=str(scene_wiki.root),
        max_selected_skills=max_selected_skills,
    )
    runtime = _load_sdk_runtime()
    options = _build_claude_agent_options(
        runtime,
        system_prompt=system_prompt,
        cwd=scene_wiki.root,
        model=model,
        read_roots=[scene_wiki.root],
        env=_build_claude_code_sdk_env(
            api_key=api_key,
            base_url=base_url,
            model=model,
            env_file=env_file,
        ),
        max_turns=max_turns,
        load_timeout_ms=load_timeout_ms,
        tool_budget=tool_budget,
        output_schema=_skill_package_json_schema(),
    )
    payload = _run_sdk_json_query(
        runtime,
        prompt=user_prompt,
        options=options,
        timeout_seconds=execution_timeout_seconds,
        label="Claude Code scene explorer",
    )
    return _package_from_payload(payload, scene_wiki.root)


def _plan_execution_prompt(
    *,
    api_key: str,
    base_url: Optional[str],
    model: Optional[str],
    env_file: Optional[Union[str, Path]],
    query: str,
    scene_wiki: _SceneWiki,
    package: _SkillPackage,
    warnings: List[str],
    load_timeout_ms: int,
    execution_timeout_seconds: float,
) -> str:
    planner_context = _planner_context(
        query=query,
        scene=scene_wiki.scene,
        package=package,
        scene_skills=scene_wiki.skills,
        wiki_root=scene_wiki.root,
        warnings=warnings,
    )
    prompt = render_orchestrator_execution_prompt_planner_prompt(context=planner_context)
    runtime = _load_sdk_runtime()
    options = _build_claude_agent_options(
        runtime,
        system_prompt="Return strict JSON only.",
        cwd=scene_wiki.root,
        model=model,
        read_roots=[scene_wiki.root],
        env=_build_claude_code_sdk_env(
            api_key=api_key,
            base_url=base_url,
            model=model,
            env_file=env_file,
        ),
        max_turns=8,
        load_timeout_ms=load_timeout_ms,
        tool_budget={"Read": 2, "LS": 0, "Glob": 0, "Grep": 0, "total": 2},
        output_schema=_planner_output_json_schema(),
    )
    payload = _run_sdk_json_query(
        runtime,
        prompt=prompt,
        options=options,
        timeout_seconds=execution_timeout_seconds,
        label="Claude Code execution-prompt planner",
    )
    planner_output = _normalize_planner_output(payload)
    validation_errors = _validate_planner_output(planner_output)
    if validation_errors:
        raise ValueError(f"invalid planner output: {'; '.join(validation_errors)}")
    return str(planner_output["execution_prompt"]).rstrip()


def _build_claude_agent_options(
    runtime: Any,
    *,
    system_prompt: str,
    cwd: Path,
    model: Optional[str],
    read_roots: List[Path],
    env: Dict[str, str],
    max_turns: int,
    load_timeout_ms: int,
    tool_budget: Dict[str, int],
    output_schema: Dict[str, Any],
) -> Any:
    cwd_path = cwd.resolve()
    resolved_read_roots = tuple(root.resolve() for root in read_roots)
    all_roots = tuple(dict.fromkeys([cwd_path, *resolved_read_roots]))
    permission_updates = _directory_permission_updates(runtime, all_roots)
    permission_updates_sent = False
    tool_counts: Dict[str, int] = {tool: 0 for tool in ORCHESTRATOR_ALLOWED_TOOLS}
    tool_counts["total"] = 0

    def allow_tool() -> Any:
        nonlocal permission_updates_sent
        if permission_updates and not permission_updates_sent:
            permission_updates_sent = True
            return runtime.PermissionResultAllow(updated_permissions=permission_updates)
        return runtime.PermissionResultAllow()

    async def can_use_tool(tool_name: str, tool_input: Dict[str, Any], _context: Any) -> Any:
        if tool_name in _WRITE_TOOLS:
            return runtime.PermissionResultDeny(message=f"{tool_name} is not allowed for SkillNet orchestration.")
        path_key = _PATH_KEYS.get(tool_name)
        if path_key is None:
            return runtime.PermissionResultDeny(message=f"{tool_name} is not allowed for SkillNet orchestration.")
        raw_path = tool_input.get(path_key)
        if raw_path is None:
            candidate_path = cwd_path
        else:
            path = Path(str(raw_path))
            candidate_path = (cwd_path / path if not path.is_absolute() else path).resolve()
        if not any(_is_relative_to(candidate_path, root) for root in resolved_read_roots):
            return runtime.PermissionResultDeny(message=f"{tool_name} path outside allowed read roots: {candidate_path}")
        budget_error = _consume_tool_budget(tool_name, tool_counts, tool_budget)
        if budget_error:
            return runtime.PermissionResultDeny(message=budget_error)
        return allow_tool()

    def stderr(line: str) -> None:
        return None

    kwargs: Dict[str, Any] = {
        "tools": list(ORCHESTRATOR_ALLOWED_TOOLS),
        "allowed_tools": list(ORCHESTRATOR_ALLOWED_TOOLS),
        "disallowed_tools": list(_DISALLOWED_TOOLS),
        "permission_mode": "default",
        "system_prompt": system_prompt,
        "cwd": cwd_path,
        "add_dirs": [str(root) for root in all_roots if root != cwd_path],
        "env": env,
        "setting_sources": [],
        "extra_args": {"disable-slash-commands": None},
        "max_turns": max(1, int(max_turns)),
        "load_timeout_ms": max(1000, int(load_timeout_ms)),
        "can_use_tool": can_use_tool,
        "stderr": stderr,
        "output_format": {"type": "json_schema", "schema": output_schema},
    }
    if model:
        kwargs["model"] = model
    return runtime.ClaudeAgentOptions(**kwargs)


def _run_sdk_json_query(
    runtime: Any,
    *,
    prompt: str,
    options: Any,
    timeout_seconds: float,
    label: str,
) -> Dict[str, Any]:
    result_message = _run_sdk_query_sync(
        runtime,
        prompt=prompt,
        options=options,
        timeout_seconds=timeout_seconds,
        label=label,
    )
    return _unwrap_finish_payload(_payload_from_result_message(result_message))


def _run_sdk_query_sync(
    runtime: Any,
    *,
    prompt: str,
    options: Any,
    timeout_seconds: float,
    label: str,
) -> Any:
    timeout = max(1.0, float(timeout_seconds))
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            _run_sdk_query_with_timeout(
                runtime,
                prompt=prompt,
                options=options,
                timeout_seconds=timeout,
                label=label,
            )
        )

    result: Dict[str, Any] = {}
    errors: List[BaseException] = []

    def worker() -> None:
        try:
            result["message"] = asyncio.run(
                _run_sdk_query_with_timeout(
                    runtime,
                    prompt=prompt,
                    options=options,
                    timeout_seconds=timeout,
                    label=label,
                )
            )
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=worker, name="skillnet-claude-agent-sdk", daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        raise TimeoutError(f"{label} exceeded {timeout:g} seconds")
    if errors:
        raise errors[0]
    return result["message"]


async def _run_sdk_query_with_timeout(
    runtime: Any,
    *,
    prompt: str,
    options: Any,
    timeout_seconds: float,
    label: str,
) -> Any:
    try:
        return await asyncio.wait_for(
            _run_sdk_query(runtime, prompt=prompt, options=options),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        raise TimeoutError(f"{label} exceeded {timeout_seconds:g} seconds") from exc


async def _run_sdk_query(runtime: Any, *, prompt: str, options: Any) -> Any:
    result_message = None
    assistant_text_parts: List[str] = []
    query_exception: Optional[BaseException] = None
    try:
        async for message in runtime.query(prompt=_streaming_prompt(prompt), options=options):
            assistant_text_parts.extend(_assistant_text_parts(message))
            if _is_result_message(runtime, message):
                result_message = message
    except Exception as exc:
        if result_message is None:
            raise
        query_exception = exc
    if result_message is None:
        raise RuntimeError("Claude agent finished without result message.")
    if assistant_text_parts and not getattr(result_message, "structured_output", None):
        result_message._skillnet_assistant_text = "\n".join(assistant_text_parts)
    if query_exception is not None:
        result_message._skillnet_query_exception = f"{type(query_exception).__name__}: {query_exception}"
    return result_message


async def _streaming_prompt(prompt: str) -> Any:
    yield {
        "type": "user",
        "session_id": "",
        "message": {"role": "user", "content": prompt},
        "parent_tool_use_id": None,
    }


def _package_from_payload(payload: Dict[str, Any], wiki_root: Path) -> _SkillPackage:
    normalized = dict(payload)
    selected = []
    for raw in normalized.get("selected_skills", []):
        if not isinstance(raw, dict):
            continue
        row = dict(raw)
        if not row.get("role"):
            row["role"] = _first_text(row, "selection_reason", "why_selected", "why", "reason")
        evidence = row.get("evidence", row.get("evidence_paths", []))
        if isinstance(evidence, str):
            evidence = [evidence]
        if isinstance(evidence, list):
            row["evidence"] = [
                _normalize_evidence_item(item, wiki_root)
                for item in evidence
                if str(item)
            ]
        selected.append(_selected_skill_from_dict(row))

    required_edges = [
        _required_edge_from_dict(edge)
        for edge in (
            _normalize_edge(item, wiki_root)
            for item in normalized.get("required_edges", [])
            if isinstance(item, dict)
        )
        if edge["before"] and edge["after"]
    ]
    return _SkillPackage(
        selected_skills=selected,
        required_edges=required_edges,
        ordered_hints=_normalize_ordered_hints(normalized.get("ordered_hints", [])),
        near_misses=_normalize_near_misses(normalized.get("near_misses", [])),
        coverage_notes=_normalize_coverage_notes(normalized.get("coverage_notes", [])),
        rationale=str(normalized.get("rationale", "")),
    )


def _validate_skill_package(package: _SkillPackage, scene_wiki: _SceneWiki) -> _SkillPackageValidationResult:
    selected: List[_SkillPackageSelectedSkill] = []
    selected_ids = set()
    errors: List[str] = []
    warnings: List[str] = []

    for skill in package.selected_skills:
        row = scene_wiki.skills.get(skill.skill_id)
        if row is None:
            errors.append(f"selected skill not in scene wiki: {skill.skill_id}")
            continue
        if not row.selectable:
            errors.append(f"selected skill is not selectable: {skill.skill_id}")
            continue

        valid_evidence = []
        for evidence in skill.evidence:
            if not _path_is_inside(scene_wiki.root, evidence.path):
                errors.append(f"evidence path escapes scene wiki: {evidence.path}")
                continue
            if not (scene_wiki.root / evidence.path).exists():
                errors.append(f"evidence path missing: {evidence.path}")
                continue
            valid_evidence.append(evidence)
        if not valid_evidence:
            errors.append(f"selected skill has no valid evidence: {skill.skill_id}")
            continue
        selected.append(_SkillPackageSelectedSkill(skill_id=skill.skill_id, role=skill.role, evidence=valid_evidence))
        selected_ids.add(skill.skill_id)

    required_edges: List[_SkillPackageRequiredEdge] = []
    for edge in package.required_edges:
        if edge.evidence_path:
            if not _path_is_inside(scene_wiki.root, edge.evidence_path):
                errors.append(f"edge evidence path escapes scene wiki: {edge.evidence_path}")
                continue
            if not _valid_edge_evidence_path(edge.evidence_path):
                errors.append(
                    "edge evidence path must be workflows/*.md, skills/cards/*.md, "
                    f"skills/sources/*.md, or edges/*.jsonl: {edge.evidence_path}"
                )
                continue
            if not (scene_wiki.root / edge.evidence_path).exists():
                errors.append(f"edge evidence path missing: {edge.evidence_path}")
                continue
        if edge.before not in selected_ids or edge.after not in selected_ids:
            warnings.append(f"dropped required edge whose endpoints are not selected: {edge.before} -> {edge.after}")
            continue
        required_edges.append(edge)

    near_misses: List[_SkillPackageNearMiss] = []
    for near_miss in package.near_misses:
        if near_miss.skill_id not in scene_wiki.skills:
            warnings.append(f"dropped near miss outside scene wiki: {near_miss.skill_id}")
            continue
        if near_miss.skill_id in selected_ids:
            warnings.append(f"dropped near miss already selected: {near_miss.skill_id}")
            continue
        near_misses.append(near_miss)

    valid_package = _SkillPackage(
        selected_skills=selected,
        required_edges=required_edges,
        ordered_hints=[hint for hint in package.ordered_hints if hint.skill_id in selected_ids],
        near_misses=near_misses,
        coverage_notes=list(package.coverage_notes),
        rationale=package.rationale,
    )
    return _SkillPackageValidationResult(
        valid=bool(selected),
        valid_package=valid_package,
        errors=errors,
        warnings=warnings,
    )


def _planner_context(
    *,
    query: str,
    scene: str,
    package: _SkillPackage,
    scene_skills: Dict[str, _SceneSkill],
    wiki_root: Path,
    warnings: List[str],
) -> Dict[str, Any]:
    return {
        "query": query,
        "scene": scene,
        "selected_skills": [
            {
                "skill_id": skill.skill_id,
                "name": scene_skills.get(skill.skill_id, _SceneSkill(skill.skill_id, _skill_name(skill.skill_id), "", "", "")).name,
                "role": skill.role,
                "evidence": [item.to_dict() for item in skill.evidence],
                "card_excerpt": _read_scene_excerpt(wiki_root, scene_skills.get(skill.skill_id).card_path if skill.skill_id in scene_skills else ""),
            }
            for skill in package.selected_skills
        ],
        "required_edges": [edge.to_dict() for edge in package.required_edges],
        "ordered_hints": [hint.to_dict() for hint in package.ordered_hints],
        "near_misses": [item.to_dict() for item in package.near_misses],
        "coverage_notes": [item.to_dict() for item in package.coverage_notes],
        "rationale": package.rationale,
        "warnings": list(warnings),
    }


def _to_orchestrate_result(
    *,
    scene_skills: Dict[str, _SceneSkill],
    package: _SkillPackage,
    prompt: str,
    package_url: Optional[str],
) -> OrchestrateResult:
    return OrchestrateResult(
        prompt=prompt,
        skills=[
            OrchestratedSkill(
                skill_id=skill.skill_id,
                name=str(getattr(scene_skills.get(skill.skill_id), "name", "") or skill.skill_id.removeprefix("skill:")),
            )
            for skill in package.selected_skills
        ],
        package_url=package_url,
    )


def _selected_skill_from_dict(payload: Dict[str, Any]) -> _SkillPackageSelectedSkill:
    return _SkillPackageSelectedSkill(
        skill_id=str(payload.get("skill_id", "")),
        role=str(payload.get("role", payload.get("reason", ""))),
        evidence=[
            _SkillPackageEvidence(path=str(item.get("path", "")), reason=str(item.get("reason", "")))
            for item in payload.get("evidence", [])
            if isinstance(item, dict)
        ],
    )


def _required_edge_from_dict(payload: Dict[str, Any]) -> _SkillPackageRequiredEdge:
    return _SkillPackageRequiredEdge(
        before=str(payload.get("before", payload.get("before_skill", ""))),
        after=str(payload.get("after", payload.get("after_skill", ""))),
        relation_type=str(payload.get("relation_type", payload.get("edge_type", "depend_on"))),
        evidence_path=str(payload.get("evidence_path", "")),
        reason=str(payload.get("reason", "")),
    )


def _normalize_edge(raw: Dict[str, Any], wiki_root: Path) -> Dict[str, Any]:
    evidence_paths = raw.get("evidence_path", raw.get("evidence_paths", ""))
    if isinstance(evidence_paths, list):
        evidence_path = next((str(item) for item in evidence_paths if str(item).startswith(("edges/", "workflows/"))), "")
        if not evidence_path and evidence_paths:
            evidence_path = str(evidence_paths[0])
    else:
        evidence_path = str(evidence_paths)
    return {
        "before": str(raw.get("before", raw.get("before_skill", raw.get("from", "")))),
        "after": str(raw.get("after", raw.get("after_skill", raw.get("to", "")))),
        "relation_type": str(raw.get("relation_type", raw.get("edge_type", raw.get("type", raw.get("relation", "depend_on"))))),
        "evidence_path": _normalize_wiki_path(evidence_path, wiki_root),
        "reason": _first_text(raw, "reason", "selection_reason", "why"),
    }


def _normalize_evidence_item(raw: Any, wiki_root: Path) -> Dict[str, str]:
    if isinstance(raw, dict):
        path = str(raw.get("path", ""))
        reason = _first_text(raw, "reason", "selection_reason", "why")
    else:
        path = str(raw)
        reason = ""
    return {"path": _normalize_wiki_path(path, wiki_root), "reason": reason}


def _normalize_wiki_path(path: str, wiki_root: Path) -> str:
    if not path:
        return ""
    candidate = Path(path)
    if not candidate.is_absolute():
        return path
    try:
        return candidate.resolve().relative_to(wiki_root.resolve()).as_posix()
    except (OSError, ValueError):
        return path


def _normalize_ordered_hints(raw_hints: Any) -> List[_SkillPackageOrderedHint]:
    if not isinstance(raw_hints, list):
        return []
    hints = []
    for item in raw_hints:
        if isinstance(item, dict):
            hints.append(_SkillPackageOrderedHint(skill_id=str(item.get("skill_id", "")), hint=str(item.get("hint", ""))))
        elif isinstance(item, str) and item.startswith("skill:"):
            hints.append(_SkillPackageOrderedHint(skill_id=item, hint="ordered sequence"))
    return [item for item in hints if item.skill_id]


def _normalize_near_misses(raw_near_misses: Any) -> List[_SkillPackageNearMiss]:
    if not isinstance(raw_near_misses, list):
        return []
    return [
        _SkillPackageNearMiss(skill_id=str(item.get("skill_id", "")), reason=str(item.get("reason", "")))
        for item in raw_near_misses
        if isinstance(item, dict)
    ]


def _normalize_coverage_notes(raw_notes: Any) -> List[_SkillPackageCoverageNote]:
    if not isinstance(raw_notes, list):
        return []
    notes = []
    for item in raw_notes:
        if not isinstance(item, dict):
            continue
        raw_skill_ids = item.get("skill_ids", [])
        if isinstance(raw_skill_ids, str):
            skill_ids = [raw_skill_ids]
        elif isinstance(raw_skill_ids, list):
            skill_ids = [str(value) for value in raw_skill_ids if str(value)]
        else:
            skill_ids = []
        notes.append(
            _SkillPackageCoverageNote(
                requirement_id=str(item.get("requirement_id", item.get("id", ""))),
                status=str(item.get("status", "")),
                reason=str(item.get("reason", "")),
                skill_ids=skill_ids,
            )
        )
    return notes


def _payload_from_result_message(result_message: Any) -> Dict[str, Any]:
    if getattr(result_message, "is_error", False):
        raise RuntimeError(_result_message_error_detail(result_message))
    structured_output = getattr(result_message, "structured_output", None)
    if isinstance(structured_output, dict):
        return structured_output
    if structured_output is not None:
        raise RuntimeError("Claude agent structured output was not a JSON object.")
    for text in (
        getattr(result_message, "_skillnet_assistant_text", ""),
        getattr(result_message, "result", ""),
    ):
        payload = _json_object_from_text(str(text or ""))
        if payload is not None:
            return payload
    raise RuntimeError("Claude agent finished without structured output or JSON assistant text.")


def _result_message_error_detail(result_message: Any) -> str:
    candidates = [
        str(getattr(result_message, "result", "") or "").strip(),
        str(getattr(result_message, "_skillnet_assistant_text", "") or "").strip(),
        str(getattr(result_message, "_skillnet_query_exception", "") or "").strip(),
    ]
    for candidate in candidates:
        if candidate.startswith("API Error:"):
            return candidate
    for candidate in candidates:
        if candidate and candidate.lower() != "success":
            return candidate
    return "Claude agent query failed."


def _unwrap_finish_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(payload.get("result"), str):
        try:
            nested = json.loads(str(payload["result"]))
        except json.JSONDecodeError:
            nested = None
        if isinstance(nested, dict):
            return _unwrap_finish_payload(nested)
    if payload.get("action") == "finish" and isinstance(payload.get("args"), dict):
        return dict(payload["args"])
    return payload


def _build_claude_code_sdk_env(
    *,
    api_key: str,
    base_url: Optional[str],
    model: Optional[str],
    env_file: Optional[Union[str, Path]] = None,
) -> Dict[str, str]:
    env = {key: value for key, value in os.environ.items() if value}
    if env_file:
        env.update(_read_env_file(env_file))
    if api_key:
        env["OPENAI_API_KEY"] = api_key
        env["ANTHROPIC_AUTH_TOKEN"] = api_key
        env["ANTHROPIC_API_KEY"] = api_key
    if base_url:
        env["OPENAI_BASE_URL"] = base_url
        env["OPENAI_API_BASE"] = base_url
        env["ANTHROPIC_BASE_URL"] = _anthropic_base_url(base_url)
    if model:
        env["ANTHROPIC_MODEL"] = _claude_model_name(model)
        env.setdefault("ANTHROPIC_SMALL_FAST_MODEL", env["ANTHROPIC_MODEL"])
        env.setdefault("ANTHROPIC_DEFAULT_SONNET_MODEL", env["ANTHROPIC_MODEL"])
        env.setdefault("ANTHROPIC_DEFAULT_HAIKU_MODEL", env["ANTHROPIC_MODEL"])
        env.setdefault("ANTHROPIC_DEFAULT_OPUS_MODEL", env["ANTHROPIC_MODEL"])
    return env


def _skill_package_json_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "selected_skills": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "skill_id": {"type": "string"},
                        "role": {"type": "string"},
                        "evidence": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "path": {"type": "string"},
                                    "reason": {"type": "string"},
                                },
                                "required": ["path", "reason"],
                            },
                        },
                    },
                    "required": ["skill_id", "role", "evidence"],
                },
            },
            "required_edges": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "before": {"type": "string"},
                        "after": {"type": "string"},
                        "relation_type": {
                            "type": "string",
                            "enum": ["depend_on", "compose_with", "artifact_compatibility", "state_compatibility"],
                        },
                        "evidence_path": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["before", "after", "relation_type", "evidence_path", "reason"],
                },
            },
            "ordered_hints": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"skill_id": {"type": "string"}, "hint": {"type": "string"}},
                    "required": ["skill_id", "hint"],
                },
            },
            "near_misses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"skill_id": {"type": "string"}, "reason": {"type": "string"}},
                    "required": ["skill_id", "reason"],
                },
            },
            "coverage_notes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "requirement_id": {"type": "string"},
                        "status": {"type": "string"},
                        "reason": {"type": "string"},
                        "skill_ids": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["requirement_id", "status", "reason", "skill_ids"],
                },
            },
            "rationale": {"type": "string"},
        },
        "required": ["selected_skills", "required_edges", "ordered_hints", "near_misses", "coverage_notes", "rationale"],
    }


def _planner_output_json_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "required": ["execution_prompt"],
        "properties": {"execution_prompt": {"type": "string"}},
        "additionalProperties": False,
    }


def _normalize_planner_output(planner_output: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(planner_output, dict):
        return planner_output
    normalized = dict(planner_output)
    execution_prompt = normalized.get("execution_prompt")
    if isinstance(execution_prompt, str):
        normalized["execution_prompt"] = _normalize_execution_prompt(execution_prompt)
    return normalized


def _validate_planner_output(planner_output: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if not isinstance(planner_output, dict):
        return ["planner output must be a JSON object"]
    keys = set(planner_output)
    if keys != {"execution_prompt"}:
        errors.append(f"planner output keys must be exactly ['execution_prompt']; got {sorted(keys)}")
    execution_prompt = planner_output.get("execution_prompt")
    if not isinstance(execution_prompt, str) or not execution_prompt.strip():
        errors.append("execution_prompt must be a non-empty string")
    else:
        lowered = execution_prompt.lower()
        for fragment in _FORBIDDEN_EXECUTION_PROMPT_FRAGMENTS:
            if fragment.lower() in lowered:
                errors.append(f"execution_prompt contains forbidden runtime-mechanism wording: {fragment}")
    return errors


def _normalize_execution_prompt(execution_prompt: str) -> str:
    text = execution_prompt.replace("\r\n", "\n").replace("\r", "\n")
    if text.count("\\n") >= 2 and text.count("\n") <= 1:
        text = text.replace("\\r\\n", "\n").replace("\\n", "\n")
    return text


def _source_path(wiki_root: Path, card_path: Path, source: str) -> str:
    if source:
        candidate = (card_path.parent / source).resolve()
    else:
        candidate = wiki_root / "skills" / "sources" / card_path.name
    try:
        return candidate.relative_to(wiki_root.resolve()).as_posix()
    except ValueError:
        return f"skills/sources/{card_path.name}"


def _frontmatter(text: str) -> Dict[str, str]:
    if not text.startswith("---"):
        return {}
    lines = text.splitlines()
    end_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break
    if end_index is None:
        return {}
    metadata: Dict[str, str] = {}
    for line in lines[1:end_index]:
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata


def _bool_value(value: str) -> bool:
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _read_scene_excerpt(wiki_root: Path, rel_path: str, *, max_chars: int = 8000) -> str:
    if not rel_path or not _path_is_inside(wiki_root, rel_path):
        return ""
    path = wiki_root / rel_path
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")[:max_chars]


def _path_is_inside(root: Path, rel_path: str) -> bool:
    if not rel_path:
        return False
    try:
        (root / rel_path).resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def _valid_edge_evidence_path(path: str) -> bool:
    return (
        (path.startswith("edges/") and path.endswith(".jsonl"))
        or (path.startswith("workflows/") and path.endswith(".md"))
        or (path.startswith("skills/cards/") and path.endswith(".md"))
        or (path.startswith("skills/sources/") and path.endswith(".md"))
    )


def _first_text(payload: Dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _json_object_from_text(text: str) -> Optional[Dict[str, Any]]:
    stripped = text.strip()
    if not stripped:
        return None
    candidates = [stripped]
    if "```" in stripped:
        parts = stripped.split("```")
        candidates.extend(part.strip() for part in parts if part.strip())
        candidates.extend(part.removeprefix("json").strip() for part in parts if part.strip().lower().startswith("json"))
    first_brace = stripped.find("{")
    last_brace = stripped.rfind("}")
    if first_brace >= 0 and last_brace > first_brace:
        candidates.append(stripped[first_brace : last_brace + 1])
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _consume_tool_budget(tool_name: str, tool_counts: Dict[str, int], tool_budget: Dict[str, int]) -> Optional[str]:
    total_limit = tool_budget.get("total", 0)
    tool_limit = tool_budget.get(tool_name, 0)
    if total_limit > 0 and tool_counts.get("total", 0) >= total_limit:
        return f"SkillNet orchestration tool budget exceeded: total<={total_limit}"
    if tool_limit > 0 and tool_counts.get(tool_name, 0) >= tool_limit:
        return f"SkillNet orchestration tool budget exceeded: {tool_name}<={tool_limit}"
    tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
    tool_counts["total"] = tool_counts.get("total", 0) + 1
    return None


def _normalize_tool_budget(tool_budget: Optional[Dict[str, int]]) -> Dict[str, int]:
    merged = dict(ORCHESTRATOR_DEFAULT_TOOL_BUDGET)
    if tool_budget:
        for key, value in tool_budget.items():
            if key in ORCHESTRATOR_ALLOWED_TOOLS or key == "total":
                try:
                    merged[key] = max(0, int(value))
                except (TypeError, ValueError):
                    continue
    return merged


def _directory_permission_updates(runtime: Any, roots: Tuple[Path, ...]) -> List[Any]:
    if not roots or not hasattr(runtime, "PermissionUpdate"):
        return []
    return [
        runtime.PermissionUpdate(
            type="addDirectories",
            directories=[str(root) for root in roots],
            destination="session",
        )
    ]


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _assistant_text_parts(message: Any) -> List[str]:
    if type(message).__name__ != "AssistantMessage":
        return []
    parts = []
    for block in getattr(message, "content", []) or []:
        text = getattr(block, "text", "")
        if text:
            parts.append(str(text))
    return parts


def _is_result_message(runtime: Any, message: Any) -> bool:
    result_type = getattr(runtime, "ResultMessage", None)
    if result_type is not None and isinstance(message, result_type):
        return True
    return type(message).__name__ == "ResultMessage"


def _load_sdk_runtime() -> Any:
    try:
        from claude_agent_sdk import ClaudeAgentOptions, query
        from claude_agent_sdk.types import (
            PermissionResultAllow,
            PermissionResultDeny,
            PermissionUpdate,
            ResultMessage,
        )
    except ModuleNotFoundError as exc:
        raise RuntimeError("claude-agent-sdk is required for SkillNet orchestrate") from exc

    class Runtime:
        pass

    Runtime.ClaudeAgentOptions = ClaudeAgentOptions
    Runtime.PermissionResultAllow = PermissionResultAllow
    Runtime.PermissionResultDeny = PermissionResultDeny
    Runtime.PermissionUpdate = PermissionUpdate
    Runtime.ResultMessage = ResultMessage
    Runtime.query = staticmethod(query)
    return Runtime


def _read_env_file(env_file: Union[str, Path]) -> Dict[str, str]:
    path = Path(env_file)
    if not path.exists():
        return {}
    values: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _anthropic_base_url(base_url: str) -> str:
    stripped = base_url.rstrip("/")
    return stripped[:-3] if stripped.endswith("/v1") else stripped


def _claude_model_name(model: str) -> str:
    for prefix in ("openai/responses/", "openai/"):
        if model.startswith(prefix):
            return model[len(prefix):]
    return model


def _skill_name(skill_id: str) -> str:
    return skill_id.split(":", 1)[-1]
