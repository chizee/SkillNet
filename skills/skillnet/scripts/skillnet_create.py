#!/usr/bin/env python3
"""Compatibility entrypoint: create via the CLI, with evaluation enabled by default."""
import argparse
import os
import sys

from _skillnet_cli import run_cli


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sources = parser.add_mutually_exclusive_group(required=True)
    sources.add_argument("--github", "-g")
    sources.add_argument("--prompt", "-p")
    sources.add_argument("--office", "-o")
    sources.add_argument("--trajectory", "-t")
    parser.add_argument("--output-dir", "-d", default=os.getenv("SKILLNET_SKILLS_DIR", "./generated_skills"))
    parser.add_argument("--model", "-m")
    parser.add_argument("--max-files", type=int, default=20)
    parser.add_argument("--no-evaluate", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--json-mode", choices=("auto", "on", "off"))
    args = parser.parse_args()
    command = ["create", "--output-dir", os.path.expanduser(args.output_dir), "--max-files", str(args.max_files)]
    for source in ("github", "prompt", "office", "trajectory"):
        value = getattr(args, source)
        if value is not None:
            command.extend([value] if source == "trajectory" else ["--" + source, value])
    command.append("--no-evaluate" if args.no_evaluate else "--evaluate")
    if args.model:
        command.extend(["--model", args.model])
    if args.json_mode:
        command.extend(["--json-mode", args.json_mode])
    if args.json:
        command.append("--json")
    return run_cli(command)


if __name__ == "__main__":
    sys.exit(main())
