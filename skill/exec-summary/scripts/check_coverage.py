"""Check that a summary.json drops nothing from the files it summarizes.

Usage: check_coverage.py <summary.json> <file> [<file> ...]

Every heading (level 2 and deeper) must be the source of some item or listed in `skipped` with a
reason. Every `src` must name a given file and one of its headings. The user stories, tasks and
checkpoints found in the files must all be in the summary. Prints one error per line as
`path.to.field: message` on stderr and exits 1 when anything is wrong.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import outline

SRC_SEPARATOR = " > "


def _norm(text: str) -> str:
    return " ".join(text.split()).casefold()


def load_outlines(paths: list[str]) -> dict[str, list[dict]]:
    """Map each file path, as given, to its sections."""
    return {path: outline.outline_file(path)["sections"] for path in paths}


def expected_counts(outlines: dict[str, list[dict]]) -> dict[str, int]:
    """Count stories, tasks and checkpoints. The largest count in any one file wins, so a plan
    and a todo that both list the same checkpoints are not counted twice."""
    counts = {"stories": 0, "tasks": 0, "checkpoints": 0}
    for sections in outlines.values():
        stories = sum(
            len(s["numbered_items"]) for s in sections if "user stor" in s["heading"].lower()
        )
        tasks = sum(1 for s in sections if s["is_task"])
        checkpoints = sum(1 for s in sections if s["is_checkpoint"])
        counts["stories"] = max(counts["stories"], stories)
        counts["tasks"] = max(counts["tasks"], tasks)
        counts["checkpoints"] = max(counts["checkpoints"], checkpoints)
    return counts


def found_counts(summary: dict) -> dict[str, int]:
    phases = [p for p in summary.get("phases", []) if isinstance(p, dict)]
    return {
        "stories": len(summary.get("stories", [])),
        "tasks": sum(len(p.get("tasks", [])) for p in phases),
        "checkpoints": len(summary.get("checkpoints", [])),
    }


def _find_src(value: object, path: str):
    """Yield (path, text) for every string stored under a key named `src`."""
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if (key == "src" or key.endswith("_src")) and isinstance(child, str):
                yield child_path, child
            else:
                yield from _find_src(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _find_src(child, f"{path}[{index}]")


def _split_src(text: str) -> tuple[str, str]:
    file_part, _, heading = text.partition(SRC_SEPARATOR)
    return file_part.strip(), heading.strip()


def check(summary: dict, paths: list[str]) -> list[str]:
    """Return a list of error messages. An empty list means nothing was dropped."""
    outlines = load_outlines(paths)
    headings = {
        path: {_norm(s["heading"]) for s in sections} for path, sections in outlines.items()
    }
    errors: list[str] = []
    used: set[tuple[str, str]] = set()

    def note_src(field: str, text: str) -> None:
        file_part, heading = _split_src(text)
        if file_part not in outlines:
            errors.append(f'{field}: "{file_part}" is not one of the given files')
        elif _norm(heading) not in headings[file_part]:
            errors.append(f'{field}: no heading "{heading}" in {file_part}')
        else:
            used.add((file_part, _norm(heading)))

    for field, text in _find_src(summary, ""):
        if not field.startswith("skipped["):
            note_src(field, text)

    for index, item in enumerate(summary.get("skipped", [])):
        field = f"skipped[{index}]"
        if not isinstance(item, dict) or not isinstance(item.get("src"), str):
            continue
        reason = item.get("reason")
        has_reason = isinstance(reason, str) and bool(reason.strip())
        before = set(used)
        note_src(f"{field}.src", item["src"])
        if not has_reason:
            used.intersection_update(before)

    for path, sections in outlines.items():
        for section in sections:
            if section["level"] >= 2 and (path, _norm(section["heading"])) not in used:
                errors.append(
                    f'{path}: heading "{section["heading"]}" (line {section["line"]}) '
                    "is neither used nor skipped"
                )

    expected, found = expected_counts(outlines), found_counts(summary)
    for kind, want in expected.items():
        if found[kind] < want:
            errors.append(f"{kind}: expected {want}, found {found[kind]}")
    return errors


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: check_coverage.py <summary.json> <file> [<file> ...]", file=sys.stderr)
        return 1
    summary_path, inputs = argv[0], argv[1:]
    problems = outline.check_paths(inputs)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    try:
        summary = json.loads(Path(summary_path).read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        print(f"{summary_path}: file not found", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"{summary_path}: invalid JSON: {exc}", file=sys.stderr)
        return 1
    errors = check(summary, inputs)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
