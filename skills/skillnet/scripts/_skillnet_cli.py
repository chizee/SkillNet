"""Resolve the installed CLI without assuming its Python environment."""
import importlib.util
import shutil
import subprocess
import sys


def run_cli(arguments):
    executable = shutil.which("skillnet")
    if executable:
        command = [executable]
    elif importlib.util.find_spec("skillnet_ai") is not None:
        command = [sys.executable, "-m", "skillnet_ai"]
    else:
        print("skillnet-ai >= 0.1.1 is required. Read references/setup.md for isolated installation.", file=sys.stderr)
        return 1
    try:
        probe = subprocess.run(command + ["--version"], capture_output=True, text=True, timeout=15)
        release = tuple(int(n) for n in probe.stdout.strip().split(".")[:3]) if probe.returncode == 0 else ()
        if release < (0, 1, 1):
            print("Upgrade the selected skillnet CLI to >= 0.1.1; see references/setup.md.", file=sys.stderr)
            return 1
        return subprocess.run(command + arguments).returncode
    except (OSError, ValueError, subprocess.TimeoutExpired):
        print("Cannot run the selected skillnet CLI. Check skillnet --version and references/setup.md.", file=sys.stderr)
        return 1
