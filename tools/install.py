"""Install the exec-summary skill into ~/.claude/skills so it works in every project.

Usage: install.py [--dry-run] [--yes] [--dest <folder>]

A fresh install copies the skill. When an older copy exists, the files that will be added,
changed or removed are listed first, and nothing is replaced unless you pass --yes.
--dry-run only lists. --dest must be a folder named exec-summary (default:
~/.claude/skills/exec-summary).
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

SKILL_NAME = "exec-summary"
SKIP_DIRS = {"__pycache__"}
SKIP_FILES = {".gitkeep"}
SKIP_SUFFIXES = {".pyc"}


def default_dest(home: Path | None = None) -> Path:
    return (home or Path.home()) / ".claude" / "skills" / SKILL_NAME


def skill_files(root: Path) -> dict[str, Path]:
    """Files of a skill folder by relative path (forward slashes), without caches."""
    files = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if not path.is_file() or path.is_symlink():
            continue
        if SKIP_DIRS & set(relative.parts) or path.name in SKIP_FILES:
            continue
        if path.suffix in SKIP_SUFFIXES:
            continue
        files[relative.as_posix()] = path
    return files


def plan(source: Path, dest: Path) -> list[tuple[str, str]]:
    """(action, relative path) for every file that differs: add, change or remove."""
    wanted = skill_files(source)
    present = skill_files(dest) if dest.is_dir() else {}
    steps = []
    for name, path in wanted.items():
        if name not in present:
            steps.append(("add", name))
        elif path.read_bytes() != present[name].read_bytes():
            steps.append(("change", name))
    steps += [("remove", name) for name in present if name not in wanted]
    return steps


def apply(source: Path, dest: Path, steps: list[tuple[str, str]]) -> None:
    files = skill_files(source)
    for action, name in steps:
        target = dest / name
        if action == "remove":
            target.unlink()
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(files[name], target)
    for folder in sorted((p for p in dest.rglob("*") if p.is_dir()), reverse=True):
        if not any(folder.iterdir()):
            folder.rmdir()


def check_dest(source: Path, dest: Path) -> str | None:
    if dest.name != SKILL_NAME:
        return f"--dest: the folder must be named {SKILL_NAME}, got {dest.name or dest}"
    if dest.is_symlink():
        return f"--dest: {dest} is a link and will not be used"
    resolved, src = dest.resolve(), source.resolve()
    if resolved == src or src in resolved.parents or resolved in src.parents:
        return f"--dest: {dest} overlaps the skill source folder"
    return None


def main(argv: list[str], source: Path | None = None) -> int:
    parser = argparse.ArgumentParser(prog="install.py", description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="list the files and change nothing")
    parser.add_argument("--yes", action="store_true", help="replace an older copy")
    parser.add_argument("--dest", type=Path, default=None)
    args = parser.parse_args(argv)

    source = source or Path(__file__).resolve().parent.parent / "skill" / SKILL_NAME
    dest = args.dest or default_dest()
    if not (source / "SKILL.md").is_file():
        print(f"{source / 'SKILL.md'}: file not found, nothing to install", file=sys.stderr)
        return 1
    problem = check_dest(source, dest)
    if problem:
        print(problem, file=sys.stderr)
        return 1

    steps = plan(source, dest)
    if not steps:
        print(f"{dest}: up to date")
        return 0
    for action, name in steps:
        print(f"{action}: {name}")
    if args.dry_run:
        print(f"dry run: nothing written to {dest}")
        return 0
    if dest.is_dir() and any(action != "add" for action, _ in steps) and not args.yes:
        print(
            "an older copy exists: review the list above and run again with --yes", file=sys.stderr
        )
        return 1
    apply(source, dest, steps)
    print(f"installed to {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
