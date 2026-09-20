"""Build the canonical skill directory as a ZIP; no host-specific prompt copies."""
import argparse
from pathlib import Path
import zipfile

from skillnet_ai.validation import validate_skill


def package_skill(source: Path, output: Path):
    validation = validate_skill(source)
    if not validation["valid"]:
        raise ValueError(validation["errors"])
    output = output.resolve()
    if output.is_relative_to(source.resolve()):
        raise ValueError("Write the ZIP outside the source skill directory.")
    files = [p for p in sorted(source.rglob("*")) if p.is_file()
             and not any(part.startswith(".") or part == "__pycache__" for part in p.relative_to(source).parts)
             and p.suffix not in {".pyc", ".pyo"}]
    if any(p.is_symlink() for p in files):
        raise ValueError("Skill archives must contain regular files, not symlinks.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            entry = zipfile.ZipInfo("skillnet/" + path.relative_to(source).as_posix(), (2020, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, path.read_bytes())
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[2] / "skills" / "skillnet"
    print(package_skill(source, args.output))
