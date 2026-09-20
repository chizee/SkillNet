import getpass
import json
import logging
import os
import shutil
import sys
from contextlib import redirect_stdout
from enum import Enum
from importlib.metadata import version
from pathlib import Path
from typing import Any, Optional

import requests
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns

from skillnet_ai.client import SkillNetClient
from skillnet_ai.config import config_path, resolve_settings, save_config, redact
from skillnet_ai.errors import error_details
from skillnet_ai.orchestrator import DEFAULT_ORCHESTRATION_TIMEOUT
from skillnet_ai.analyzer import ScenarioSkillGraphAnalyzer, SkillRelationshipAnalyzer
from skillnet_ai.validation import validate_skill, validate_evaluation, DIMENSIONS

app = typer.Typer(help="SkillNet AI CLI Tool", no_args_is_help=True)
console = Console()


class AnalyzeMode(str, Enum):
    basic = "basic"
    scenario = "scenario"


class RedactedFormatter(logging.Formatter):
    def format(self, record):
        return redact(super().format(record))


@app.callback(invoke_without_command=True)
def main(version_flag: bool = typer.Option(False, "--version", is_eager=True)):
    """Search, download, create and evaluate reusable skills."""
    if version_flag:
        typer.echo(version("skillnet-ai"))
        raise typer.Exit()
    logger = logging.getLogger("skillnet_ai")
    for handler in list(logger.handlers):
        if getattr(handler, "_skillnet_cli", False):
            logger.removeHandler(handler)
    handler = logging.StreamHandler()
    handler._skillnet_cli = True
    handler.setFormatter(RedactedFormatter("%(levelname)s: %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False


def _json_safe(value: Any):
    if hasattr(value, "model_dump"):
        return _json_safe(value.model_dump())
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _model_dump(model: Any) -> dict:
    return _json_safe(model.model_dump() if hasattr(model, "model_dump") else vars(model))


def _emit(data, json_output: bool, *, error=None):
    if json_output:
        # ASCII escapes keep redirected JSON portable in Windows legacy codepages.
        typer.echo(json.dumps({"ok": error is None, "data": _json_safe(data), "error": error}))
    elif error:
        diagnostics = Console(stderr=True)
        diagnostics.print(f"Error: {error['message']}", markup=False)
        diagnostics.print(error["hint"], markup=False)
        if data is not None:
            diagnostics.print_json(data=_json_safe(data))


def _fail(exc, json_output, data=None):
    _emit(data, json_output, error=error_details(exc))
    raise typer.Exit(code=1)


@app.command()
def search(
    q: str = typer.Argument(...),
    mode: str = typer.Option("keyword", help="keyword or vector"),
    category: Optional[str] = typer.Option(None),
    limit: int = typer.Option(20, min=1, max=100),
    page: int = typer.Option(1, min=1),
    min_stars: int = typer.Option(0, min=0),
    sort_by: str = typer.Option("stars"),
    threshold: float = typer.Option(0.8, min=0, max=1),
    json_output: bool = typer.Option(False, "--json"),
):
    """Search SkillNet; no LLM key required."""
    try:
        with redirect_stdout(sys.stderr):
            results = SkillNetClient().search(q, mode=mode, category=category, limit=limit,
                page=page, min_stars=min_stars, sort_by=sort_by, threshold=threshold)
    except Exception as exc:
        _fail(exc, json_output)
    if json_output:
        _emit(results, True)
    elif not results:
        console.print("No results found.")
    else:
        table = Table(title="Search Results", show_lines=True)
        for name in ("Name", "Category", "Stars", "Description", "Evaluation", "URL"):
            table.add_column(name)
        for item in results:
            ratings = "\n".join(f"{d}: {item.evaluation.get(d, {}).get('level', 'N/A')}"
                                for d in DIMENSIONS) if item.evaluation else "N/A"
            table.add_row(item.skill_name, item.category or "", str(item.stars),
                          item.skill_description or "", ratings, item.skill_url or "")
        console.print(table)


@app.command()
def download(
    url: str = typer.Argument(...),
    target_dir: str = typer.Option(".", "--target-dir", "-d"),
    token: Optional[str] = typer.Option(None, "--token", "-t", help="Prefer GITHUB_TOKEN over a shell argument."),
    mirror: Optional[str] = typer.Option(None, "--mirror", "-m"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Replace an existing skill after complete download."),
    json_output: bool = typer.Option(False, "--json"),
):
    """Download and structurally validate a GitHub skill folder."""
    try:
        with redirect_stdout(sys.stderr):
            path = SkillNetClient(github_token=token).download(url, target_dir=target_dir,
                                                             mirror_url=mirror, overwrite=overwrite)
        _emit({"path": path}, json_output)
        if not json_output:
            console.print(f"Downloaded and structurally validated: {path}", markup=False)
    except Exception as exc:
        _fail(exc, json_output)


@app.command()
def create(
    trajectory_file: Optional[Path] = typer.Argument(None),
    github: Optional[str] = typer.Option(None, "--github", "-g"),
    office: Optional[Path] = typer.Option(None, "--office", "-o"),
    prompt: Optional[str] = typer.Option(None, "--prompt", "-p"),
    output_dir: Path = typer.Option(Path("./generated_skills"), "--output-dir", "-d"),
    model: Optional[str] = typer.Option(None, "--model", "-m"),
    max_files: int = typer.Option(50, min=1),
    auto_evaluate: bool = typer.Option(False, "--evaluate/--no-evaluate"),
    json_mode: Optional[str] = typer.Option(None, "--json-mode", help="auto, on or off for evaluation JSON mode."),
    json_output: bool = typer.Option(False, "--json"),
):
    """Create from exactly one source; optionally evaluate the resulting skills."""
    data = {"paths": [], "validation": {}, "evaluations": {}}
    try:
        if sum(x is not None for x in (trajectory_file, github, office, prompt)) != 1:
            raise ValueError("Provide exactly one source: trajectory file, --github, --office or --prompt.")
        kwargs = {"output_dir": output_dir, "model": model, "max_files": max_files}
        if trajectory_file is not None:
            kwargs["trajectory_content"] = trajectory_file.read_text(encoding="utf-8")
            if not kwargs["trajectory_content"].strip():
                raise ValueError("Trajectory file is empty.")
        elif github is not None:
            kwargs["github_url"] = github
        elif office is not None:
            kwargs["office_file"] = str(office)
        else:
            kwargs["prompt"] = prompt
        with redirect_stdout(sys.stderr):
            client = SkillNetClient(json_mode=json_mode)
            paths = client.create(**kwargs)
        data["paths"] = [str(Path(p).resolve()) for p in paths]
        if not paths:
            raise ValueError("No skills were generated. Check the input and model response.")
        for path in data["paths"]:
            data["validation"][path] = validate_skill(path)
        if any(not v["valid"] for v in data["validation"].values()):
            raise ValueError("Generated skills failed structural validation; inspect validation errors and retained paths.")
        if auto_evaluate:
            for path in data["paths"]:
                try:
                    with redirect_stdout(sys.stderr):
                        report = validate_evaluation(client.evaluate(path, model=model))
                    data["evaluations"][path] = {"ok": True, "report": report, "error": None}
                except Exception as exc:
                    data["evaluations"][path] = {"ok": False, "report": None, "error": error_details(exc)}
            if any(not r["ok"] for r in data["evaluations"].values()):
                raise ValueError("Skills were created, but evaluation failed. Retry evaluation on the retained paths.")
    except Exception as exc:
        if not data["paths"]:
            data["paths"] = [str(Path(p).resolve()) for p in getattr(exc, "created_paths", [])]
        _fail(exc, json_output, data)
    _emit(data, json_output)
    if not json_output:
        for path in data["paths"]:
            console.print(f"Created and structurally validated: {path}", markup=False)
            if path in data["evaluations"]:
                _display_evaluation_report(path, data["evaluations"][path]["report"])
        console.print("Model evaluation is advisory; verify the skill on a real task.")


@app.command()
def evaluate(
    target: str = typer.Argument(...),
    name: Optional[str] = typer.Option(None),
    category: Optional[str] = typer.Option(None),
    description: Optional[str] = typer.Option(None),
    model: Optional[str] = typer.Option(None, "--model", "-m"),
    max_workers: int = typer.Option(5, min=1),
    json_mode: Optional[str] = typer.Option(None, "--json-mode"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Evaluate a local skill or GitHub URL through the configured model API."""
    try:
        with redirect_stdout(sys.stderr):
            report = SkillNetClient(json_mode=json_mode).evaluate(target, name=name, category=category,
                description=description, model=model, max_workers=max_workers)
            validate_evaluation(report)
        _emit(report, json_output)
        if not json_output:
            _display_evaluation_report(target, report)
    except Exception as exc:
        _fail(exc, json_output)


@app.command("validate")
def validate_command(
    skill_dir: Path = typer.Argument(...),
    strict: bool = typer.Option(False, "--strict", help="Also fail on portability warnings."),
    json_output: bool = typer.Option(False, "--json"),
):
    """Check skill structure locally, without a model call or script execution."""
    report = validate_skill(skill_dir)
    if not report["valid"] or (strict and report["warnings"]):
        _fail(ValueError("Skill validation found issues."), json_output, report)
    _emit(report, json_output)
    if not json_output:
        console.print("Structure valid.")
        for warning in report["warnings"]:
            console.print(warning, markup=False)


@app.command()
def configure(
    base_url: Optional[str] = typer.Option(None, "--base-url"),
    model: Optional[str] = typer.Option(None, "--model"),
    api_key_env: Optional[str] = typer.Option(None, "--api-key-env", help="Name of an environment variable, not the key."),
    api_key_stdin: bool = typer.Option(False, "--api-key-stdin"),
    github_token_env: Optional[str] = typer.Option(None, "--github-token-env"),
    skillnet_api_url: Optional[str] = typer.Option(None, "--skillnet-api-url"),
    github_mirror: Optional[str] = typer.Option(None, "--github-mirror"),
    json_mode: Optional[str] = typer.Option(None, "--json-mode"),
    interactive: bool = typer.Option(False, "--interactive"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Save optional user settings; prompts only with --interactive."""
    try:
        if api_key_env and api_key_stdin:
            raise ValueError("Choose --api-key-env or --api-key-stdin, not both.")
        updates = {k: v for k, v in {"base_url": base_url, "model": model,
            "skillnet_api_url": skillnet_api_url, "github_mirror": github_mirror,
            "json_mode": json_mode}.items() if v is not None}
        for field, env in (("api_key", api_key_env), ("github_token", github_token_env)):
            if env is not None:
                if not os.environ.get(env):
                    raise ValueError(f"Environment variable {env} is empty or absent.")
                updates[field] = os.environ[env]
        if api_key_stdin:
            key = sys.stdin.readline().strip()
            if not key:
                raise ValueError("No API key supplied on stdin.")
            updates["api_key"] = key
        if interactive:
            if not sys.stdin.isatty():
                raise ValueError("Interactive setup requires a terminal. Use flags, environment variables or stdin.")
            settings = resolve_settings(**updates)
            with redirect_stdout(sys.stderr):
                updates["base_url"] = input(f"Model API base URL [{settings.base_url}]: ").strip() or settings.base_url
                updates["model"] = input(f"Model [{settings.model}]: ").strip() or settings.model
                key_prompt = "API key (Enter to keep existing): " if settings.api_key else "API key (saved in your user config): "
                key = getpass.getpass(key_prompt).strip()
                if key:
                    updates["api_key"] = key
                elif not settings.api_key:
                    raise ValueError("API key is empty; configuration was not saved.")
        if not updates:
            raise ValueError("Provide configuration flags or run skillnet configure --interactive in a terminal.")
        path = save_config(updates)
        _emit({"path": str(path), "updated": sorted(updates)}, json_output)
        if not json_output:
            console.print(f"Saved user configuration: {path}", markup=False)
    except Exception as exc:
        _fail(exc, json_output)


@app.command()
def doctor(
    check_network: bool = typer.Option(False, "--check-network"),
    check_llm: bool = typer.Option(False, "--check-llm", help="Send one small potentially billable model request."),
    json_output: bool = typer.Option(False, "--json"),
):
    """Inspect local setup. Network and LLM checks are opt-in."""
    data = {}
    try:
        settings = resolve_settings()
        data = {"version": version("skillnet-ai"), "python": sys.executable,
                "cli": shutil.which("skillnet"), "config_path": str(config_path()),
                "settings": settings.public(), "checks": {},
                "missing_for_create_evaluate": [] if settings.api_key else ["API_KEY"],
                "hint": "Run configure for missing model settings. Search/public download need no LLM key."}
        with redirect_stdout(sys.stderr):
            if check_network:
                SkillNetClient().search("pdf", limit=1)
                data["checks"]["search"] = "passed"
                response = requests.get("https://api.github.com/rate_limit", timeout=15)
                response.raise_for_status()
                data["checks"]["github"] = "passed"
            if check_llm:
                if not settings.api_key:
                    raise ValueError("API_KEY is required for --check-llm.")
                from openai import OpenAI
                from skillnet_ai.llm import chat_completion
                response = chat_completion(OpenAI(api_key=settings.api_key, base_url=settings.base_url,
                    timeout=30, max_retries=0), model=settings.model,
                    messages=[{"role": "user", "content": "Reply with OK only."}])
                if not response.choices or not response.choices[0].message.content:
                    raise ValueError("Model returned no content.")
                data["checks"]["llm"] = "passed"
        _emit(data, json_output)
        if not json_output:
            console.print_json(data=data)
    except Exception as exc:
        _fail(exc, json_output, data)


@app.command()
def orchestrate(
    q: str = typer.Argument(..., help="The user task query to orchestrate."),
    scene: str = typer.Option("sciatlas", "--scene", help="Preset scene name."),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Claude Agent SDK model to use."),
    timeout: float = typer.Option(DEFAULT_ORCHESTRATION_TIMEOUT, "--timeout", help="Per-stage orchestration timeout in seconds."),
    json_output: bool = typer.Option(False, "--json/--no-json", help="Print raw JSON instead of a Rich summary."),
):
    """
    Recommend scene skills and generate a downstream execution prompt.
    """
    settings = resolve_settings(model=model)
    API_KEY, BASE_URL, model = settings.api_key, settings.base_url, settings.model
    if not API_KEY:
        console.print("[bold red]Error:[/bold red] API_KEY environment variable is not set.")
        raise typer.Exit(code=1)

    try:
        client = SkillNetClient(api_key=API_KEY, base_url=BASE_URL)
        with console.status("[bold green]Orchestrating scene skills...[/bold green]", spinner="dots"):
            result = client.orchestrate(q, scene=scene, model=model, timeout=timeout)

        payload = _model_dump(result)
        if json_output:
            console.print(json.dumps(payload, ensure_ascii=False, indent=2))
            return

        if payload.get("package_url"):
            console.print(f"\n[bold cyan]Skill Collection:[/bold cyan] {payload['package_url']}")

        table = Table(title=f"Selected Skills: {scene}", show_lines=True)
        table.add_column("Skill", style="cyan", no_wrap=True)
        for skill in payload.get("skills", []):
            table.add_row(skill.get("name") or skill.get("skill_id", ""))
        console.print(table)

        console.print(Panel(payload.get("prompt", ""), title="Agent Prompt", border_style="cyan"))
    except Exception as e:
        console.print(f"[bold red]Orchestration Failed:[/bold red] {str(e)}")
        raise typer.Exit(code=1)


def _display_evaluation_report(target_name: str, data: dict):
    """Helper to render the JSON evaluation result into a nice Rich UI."""
    console.print(f"\n[bold underline]Evaluation Report: {os.path.basename(target_name)}[/bold underline]\n")

    # Dimensions to display
    dimensions = ["safety", "completeness", "executability", "maintainability", "cost_awareness"]
    
    # Create a grid of panels
    panels = []
    for dim in dimensions:
        info = data.get(dim, {})
        level = info.get("level", "Unknown")
        reason = info.get("reason", "No details provided.")
        
        # Color coding based on level
        color = "white"
        if "Excellent" in level: color = "green"
        elif "Good" in level: color = "blue"
        elif "Fair" in level: color = "yellow"
        elif "Poor" in level: color = "red"

        panel_content = f"[bold]{level}[/bold]\n\n[dim]{reason}[/dim]"
        panels.append(Panel(panel_content, title=f"[{color}]{dim.title()}[/{color}]", expand=True))

    console.print(Columns(panels, equal=True, expand=True))
    
    # Display Score if present
    overall_score = data.get("overall_score")
    if overall_score:
        score_color = "green" if overall_score >= 8 else "yellow" if overall_score >= 5 else "red"
        console.print(f"\n[bold]Overall Score:[/bold] [{score_color}]{overall_score}/10[/{score_color}]")

    # Summary
    summary = data.get("summary")
    if summary:
        console.print(Panel(summary, title="Executive Summary", border_style="cyan"))


@app.command()
def analyze(
    skills_dir: Path = typer.Argument(..., exists=True, file_okay=False, help="Directory containing multiple skill folders to analyze."),
    save: bool = typer.Option(True, "--save/--no-save", help="Save analysis artifacts."),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="LLM model to use."),
    mode: AnalyzeMode = typer.Option(AnalyzeMode.basic, "--mode", help="Analyze mode."),
    embedding_api_key: Optional[str] = typer.Option(None, "--embedding-api-key", envvar="EMBEDDING_API_KEY", help="Embedding API key for scenario mode."),
    embedding_base_url: Optional[str] = typer.Option(None, "--embedding-base-url", envvar="EMBEDDING_BASE_URL", help="OpenAI-compatible embedding API base URL for scenario mode."),
    embedding_model: Optional[str] = typer.Option(None, "--embedding-model", envvar="EMBEDDING_MODEL", help="Embedding model name for scenario mode."),
    max_workers: int = typer.Option(4, "--max-workers", help="Scenario LLM extraction, verification, and redundancy-review concurrency."),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", help="Scenario artifact directory. Defaults to SKILLS_DIR/skillnet_graph."),
    top_k: int = typer.Option(30, "--top-k", help="Top pre-scenarios retrieved per post-scenario in scenario mode."),
    force: bool = typer.Option(False, "--force/--no-force", help="Recompute scenario artifacts instead of resuming successful rows."),
    timeout: float = typer.Option(120.0, "--timeout", help="Scenario LLM and embedding request timeout in seconds."),
):
    """
    Analyze and map relationships between local skills.
    
    basic mode scans skill descriptions and asks the LLM for relationships.
    scenario mode builds a scenario-level workflow graph for local skills.
    """
    # 1. Validate Environment
    settings = resolve_settings(model=model)
    API_KEY, BASE_URL, model = settings.api_key, settings.base_url, settings.model
    if not API_KEY:
        console.print("[bold red]Error:[/bold red] API_KEY environment variable is not set.")
        raise typer.Exit(code=1)
    mode_value = mode.value if isinstance(mode, AnalyzeMode) else str(mode)
    if mode_value not in {"basic", "scenario"}:
        console.print("[bold red]Error:[/bold red] --mode must be either 'basic' or 'scenario'.")
        raise typer.Exit(code=1)

    try:
        console.print(f"[dim]Scanning directory: {os.path.abspath(skills_dir)}[/dim]")

        if mode_value == "scenario":
            analyzer = ScenarioSkillGraphAnalyzer(
                api_key=API_KEY,
                base_url=BASE_URL,
                model=model,
                embedding_api_key=embedding_api_key,
                embedding_base_url=embedding_base_url,
                embedding_model=embedding_model,
                max_workers=max_workers,
                top_k=top_k,
                timeout=timeout,
                progress_callback=lambda message: console.print(f"[dim]{message}[/dim]"),
            )

            result = analyzer.analyze_local_skills(
                skills_dir=str(skills_dir),
                output_dir=output_dir,
                force=force,
                save_to_file=save,
            )

            graph = result.get("scenario_skill_graph", {})
            meta = graph.get("meta", {})
            result_meta = result.get("meta", {})
            relationships = result.get("relationships", [])
            console.print(
                "\n[bold green]Scenario Analysis Complete![/bold green] "
                f"Nodes: {meta.get('node_count', 0)}, "
                f"Edges: {meta.get('edge_count', 0)}, "
                f"Relationships: {len(relationships)}"
            )
            extraction_failed_count = int(result_meta.get("extraction_failed_count") or 0)
            alignment_failed_count = int(result_meta.get("alignment_failed_count") or 0)
            redundancy_failed_count = int(
                result.get("skill_edge_redundancy_reviews", {})
                .get("meta", {})
                .get("failed_pair_count")
                or 0
            )
            if extraction_failed_count:
                console.print(
                    f"[yellow]Warning:[/yellow] Scenario extraction failed for "
                    f"{extraction_failed_count} skill(s). See skill_scenarios.json for details."
                )
            if alignment_failed_count:
                console.print(
                    f"[yellow]Warning:[/yellow] Scenario verification failed for "
                    f"{alignment_failed_count} candidate alignment(s). See scenario_alignment.json for details."
                )
            if redundancy_failed_count:
                console.print(
                    f"[yellow]Warning:[/yellow] Skill edge redundancy review failed for "
                    f"{redundancy_failed_count} skill pair(s). See skill_edge_redundancy_reviews.json for details."
                )
            if relationships:
                table = Table(show_header=True, header_style="bold magenta", title="Scenario Skill Graph")
                table.add_column("Source Skill", style="cyan", no_wrap=True)
                table.add_column("Relationship", style="bold white", justify="center")
                table.add_column("Target Skill", style="cyan", no_wrap=True)
                table.add_column("Reasoning", style="dim")
                for edge in relationships:
                    table.add_row(
                        edge.get("source", "Unknown"),
                        "[green]COMPOSE WITH[/green]",
                        edge.get("target", "Unknown"),
                        edge.get("reason", ""),
                    )
                console.print(table)
            else:
                console.print("\n[yellow]No scenario handoff relationships detected among the skills found.[/yellow]")
            if save:
                saved_dir = result.get("meta", {}).get("output_dir") or str(output_dir or (skills_dir / "skillnet_graph"))
                console.print(f"\n[dim]Scenario graph artifacts saved to: {saved_dir}[/dim]")
            return

        # 2. Initialize Analyzer
        analyzer = SkillRelationshipAnalyzer(
            api_key=API_KEY,
            base_url=BASE_URL,
            model=model
        )

        # 3. Visual Feedback & Execution
        results = []
        with console.status("[bold green]Reading skills and analyzing relationships...[/bold green]", spinner="earth"):
            results = analyzer.analyze_local_skills(
                skills_dir=str(skills_dir),
                save_to_file=save
            )

        # 4. Handle Empty Results
        if not results:
            console.print("\n[yellow]No strong relationships detected among the skills found.[/yellow]")
            console.print("[dim]Make sure the directory contains subfolders with valid SKILL.md or README.md files.[/dim]")
            return

        # 5. Render Results Table
        console.print(f"\n[bold green]Analysis Complete! Found {len(results)} relationships:[/bold green]\n")

        table = Table(show_header=True, header_style="bold magenta", title="Skill Relationship Graph")
        table.add_column("Source Skill", style="cyan", no_wrap=True)
        table.add_column("Relationship", style="bold white", justify="center")
        table.add_column("Target Skill", style="cyan", no_wrap=True)
        table.add_column("Reasoning", style="dim")

        for edge in results:
            # Color code the relationship types for better readability
            rel_type = edge.get('type', 'unknown')
            rel_style = "white"
            arrow = "->"
            
            if rel_type == "depend_on":
                rel_style = "red"  # Critical dependency
                arrow = "DEPEND ON"
            elif rel_type == "belong_to":
                rel_style = "blue" # Hierarchy
                arrow = "BELONG TO"
            elif rel_type == "compose_with": # pairs_with
                rel_style = "green" # Collaboration
                arrow = "COMPOSE WITH"
            elif rel_type == "similar_to":
                rel_style = "yellow" # Alternative
                arrow = "SIMILAR TO"

            table.add_row(
                edge.get('source', 'Unknown'),
                f"[{rel_style}]{arrow}[/{rel_style}]", 
                edge.get('target', 'Unknown'),
                edge.get('reason', '')
            )

        console.print(table)

        if save:
            console.print(f"\n[dim]Relationship data saved to: {os.path.join(skills_dir, 'relationships.json')}[/dim]")

    except Exception as e:
        console.print(f"\n[bold red]Analysis Failed:[/bold red] {str(e)}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
