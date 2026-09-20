#!/usr/bin/env python3
"""Compatibility entrypoint for the shared offline structural validator."""
import argparse
import sys

from _skillnet_cli import run_cli


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_dir")
    parser.add_argument("--strict", action="store_true", help="Fail on portability warnings as well as errors.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    command = ["validate", args.skill_dir]
    if args.strict:
        command.append("--strict")
    if args.json:
        command.append("--json")
    return run_cli(command)


if __name__ == "__main__":
    sys.exit(main())
