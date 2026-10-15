"""Install the exec-summary skill into ~/.claude/skills so it works in every project.

Usage: install.py [--dry-run] [--yes] [--dest <folder>]

A fresh install copies the skill. When an older copy exists, the files that will be added,
changed or removed are listed first, and nothing is replaced unless you pass --yes.
--dry-run only lists. --dest must be a folder named exec-summary (default:
~/.claude/skills/exec-summary). A destination that holds a link (symbolic link or junction) is
refused, so nothing outside it can be written or deleted.
"""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import sys
from pathlib import Path

SKILL_NAME = "exec-summary"
SKIP_DIRS = {"__pycache__"}
SKIP_FILES = {".gitkeep"}
SKIP_SUFFIXES = {".pyc"}


def default_dest(home: Path | None = None) -> Path:
    return (home or Path.home()) / ".claude" / "skills" / SKILL_NAME


def is_link(path: Path) -> bool:
    """A symbolic link, or a Windows junction (which `is_symlink` does not report)."""
    if path.is_symlink():
        return True
    attributes = getattr(os.lstat(path), "st_file_attributes", 0)
    return bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def find_links(root: Path) -> list[str]:
    """Relative paths of every link under `root`. Linked folders are not entered."""
    found = []
    for folder, dirs, files in os.walk(root, followlinks=False):
        here = Path(folder)
        for name in [*dirs, *files]:
            if is_link(here / name):
                found.append((here / name).relative_to(root).as_posix())
        dirs[:] = [d for d in dirs if not is_link(here / d)]
    return sorted(found)


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
    """(action, relative path) for every file that differs: add, change or remove. Names are
    matched ignoring case, because Windows and macOS treat `skill.md` and `SKILL.md` as one
    file; a name that differs only in case is a change, not an add plus a remove."""
    wanted = skill_files(source)
    present = skill_files(dest) if dest.is_dir() else {}
    by_fold = {name.casefold(): name for name in present}
    steps = []
    for name, path in wanted.items():
        actual = by_fold.get(name.casefold())
        if actual is None:
            steps.append(("add", name))
        elif actual != name or path.read_bytes() != present[actual].read_bytes():
            steps.append(("change", name))
    wanted_fold = {name.casefold() for name in wanted}
    steps += [("remove", name) for name in present if name.casefold() not in wanted_fold]
    return steps


def _inside(dest: Path, target: Path) -> Path:
    """`target` if it is inside `dest` once links are resolved, else an error."""
    try:
        target.resolve().relative_to(dest.resolve())
    except ValueError:
        raise ValueError(f"{target}: outside {dest}, not touched") from None
    return target


def _prune(dest: Path, name: str) -> None:
    """Remove folders emptied by deleting `name`, up to (not including) `dest`."""
    folder = (dest / name).parent
    while folder != dest and folder.is_dir() and not any(folder.iterdir()):
        folder.rmdir()
        folder = folder.parent


def apply(source: Path, dest: Path, steps: list[tuple[str, str]]) -> None:
    files = skill_files(source)
    present = skill_files(dest) if dest.is_dir() else {}
    by_fold = {name.casefold(): name for name in present}
    removes = [name for action, name in steps if action == "remove"]
    writes = [name for action, name in steps if action != "remove"]
    for name in removes:
        _inside(dest, dest / name).unlink()
        _prune(dest, name)
    for name in writes:
        old = by_fold.get(name.casefold())
        if old is not None and old != name:
            _inside(dest, dest / old).unlink()
        target = _inside(dest, dest / name)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + ".new")
        shutil.copyfile(files[name], temp)
        temp.replace(target)


def check_dest(source: Path, dest: Path) -> str | None:
    if dest.name != SKILL_NAME:
        return f"--dest: the folder must be named {SKILL_NAME}, got {dest.name or dest}"
    if dest.exists() and not dest.is_dir():
        return f"--dest: {dest} exists and is not a folder"
    if dest.exists() and is_link(dest):
        return f"--dest: {dest} is a link and will not be used"
    resolved, src = dest.resolve(), source.resolve()
    if resolved == src or src in resolved.parents or resolved in src.parents:
        return f"--dest: {dest} overlaps the skill source folder"
    if dest.is_dir():
        links = find_links(dest)
        if links:
            return (
                f"--dest: {dest} contains a link ({links[0]}); remove it first, nothing was changed"
            )
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
    try:
        apply(source, dest, steps)
    except (OSError, ValueError) as exc:
        print(f"install stopped: {exc}", file=sys.stderr)
        return 1
    print(f"installed to {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
