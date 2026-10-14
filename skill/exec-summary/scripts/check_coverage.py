"""Check that a summary.json drops nothing from the files it summarizes.

Usage: check_coverage.py <summary.json> <file> [<file> ...]

The summary is validated first. Then:
- the files given here must be exactly the files listed in `sources`;
- every heading (level 2 and deeper) must be the source of some item or be listed in `skipped`
  with a reason, and every `src` must name a given file and one of its headings;
- every `Task N` heading and every `Checkpoint ...` heading found must be the source of a task
  or checkpoint. They cannot be skipped, except a heading that repeats one already shown from
  another file (a plan and a todo that list the same checkpoints);
- every user story found must be in `stories`.

Two sections with the same heading text are told apart by `#2`, `#3` ... after the heading, for
example `SPEC.md > Notes#2`. Stories are counted from numbered or `As ...` items under a
"User stories" heading and from `Story N` headings; tasks written only as checkboxes (not as
`Task N` headings) are not counted. Prints one error per line as `path.to.field: message` on
stderr and exits 1 when anything is wrong.
"""

from __future__ import annotations

import re
import sys
from pathlib import PureWindowsPath

import outline
from common import SRC_SEPARATOR, find_src, load_json
from validate import validate

OCCURRENCE = re.compile(r"^(.*\S)\s*#(\d+)$")
AS_ITEM = re.compile(r"^as\s", re.IGNORECASE)
TASK_SRC = re.compile(r"^phases\[\d+\]\.tasks\[\d+\]\.src$")
CHECKPOINT_SRC = re.compile(r"^checkpoints\[\d+\]\.src$")

Target = tuple[str, tuple[str, int]]  # (file key, (normalised heading, occurrence))


def _norm(text: str) -> str:
    return " ".join(text.split()).casefold()


def _key(path: str) -> str:
    """One spelling for a path: forward slashes, no leading `./`."""
    return PureWindowsPath(path.strip()).as_posix()


def load_outlines(paths: list[str]) -> dict[str, list[dict]]:
    """Map each file path (normalised) to its sections."""
    return {_key(path): outline.outline_file(path)["sections"] for path in paths}


def _story_count(sections: list[dict]) -> int:
    count = sum(1 for s in sections if s["is_story"])
    for s in sections:
        if "user stor" in s["heading"].lower():
            count += len(s["numbered_items"])
            count += sum(1 for item in s["list_items"] if AS_ITEM.match(item))
    return count


def expected_counts(outlines: dict[str, list[dict]]) -> dict[str, int]:
    """Stories (largest count in any one file), and distinct task and checkpoint headings."""
    tasks, checkpoints = set(), set()
    stories = 0
    for sections in outlines.values():
        stories = max(stories, _story_count(sections))
        tasks.update(_norm(s["heading"]) for s in sections if s["is_task"])
        checkpoints.update(_norm(s["heading"]) for s in sections if s["is_checkpoint"])
    return {"stories": stories, "tasks": len(tasks), "checkpoints": len(checkpoints)}


def _occurrences(sections: list[dict]) -> list[tuple[tuple[str, int], dict]]:
    """Each section with (normalised heading, occurrence among identical headings)."""
    seen: dict[str, int] = {}
    out = []
    for section in sections:
        text = _norm(section["heading"])
        seen[text] = seen.get(text, 0) + 1
        out.append(((text, seen[text]), section))
    return out


def _dicts(value: object) -> list[dict]:
    return [v for v in value if isinstance(v, dict)] if isinstance(value, list) else []


def _heading_names(outlines: dict[str, list[dict]], flag: str) -> dict[str, str]:
    return {_norm(s["heading"]): s["heading"] for sec in outlines.values() for s in sec if s[flag]}


def check(summary: dict, paths: list[str]) -> list[str]:
    """Return a list of error messages. An empty list means nothing was dropped."""
    outlines = load_outlines(paths)
    indexes = {key: dict(_occurrences(sections)) for key, sections in outlines.items()}
    errors: list[str] = []

    listed = {_key(s["path"]) for s in _dicts(summary.get("sources")) if "path" in s}
    for key in sorted(set(outlines) - listed):
        errors.append(f'sources: "{key}" is given on the command line but not listed in sources')
    for key in sorted(listed - set(outlines)):
        errors.append(f'sources: "{key}" is listed in sources but not given on the command line')
    for key, sections in outlines.items():
        if not any(s["level"] >= 2 for s in sections):
            errors.append(
                f"{key}: no headings at level 2 or deeper, so nothing can be checked. "
                "Add headings to the file."
            )

    def resolve(field: str, text: str) -> Target | None:
        file_part, _, heading = text.partition(SRC_SEPARATOR)
        key = _key(file_part)
        if key not in outlines:
            errors.append(f'{field}: "{file_part.strip()}" is not one of the given files')
            return None
        found = (_norm(heading), 1)
        if found not in indexes[key]:
            match = OCCURRENCE.match(heading.strip())
            if match:
                found = (_norm(match.group(1)), int(match.group(2)))
        if found not in indexes[key]:
            errors.append(f'{field}: no heading "{heading.strip()}" in {file_part.strip()}')
            return None
        return key, found

    used: set[Target] = set()
    shown_tasks: set[str] = set()
    shown_checkpoints: set[str] = set()
    for field, text in find_src(summary):
        if field.startswith("skipped["):
            continue
        target = resolve(field, text)
        if target:
            used.add(target)
            if TASK_SRC.match(field):
                shown_tasks.add(target[1][0])
            elif CHECKPOINT_SRC.match(field):
                shown_checkpoints.add(target[1][0])

    for index, item in enumerate(_dicts(summary.get("skipped"))):
        field = f"skipped[{index}].src"
        before = len(errors)
        target = resolve(field, item["src"]) if isinstance(item.get("src"), str) else None
        if not target or len(errors) != before:
            continue
        section, text = indexes[target[0]][target[1]], target[1][0]
        reason = item.get("reason")
        if not (isinstance(reason, str) and reason.strip()):
            errors.append(f"{field}: a skipped section needs a reason")
        elif section["is_task"] and text not in shown_tasks:
            errors.append(f'{field}: "{section["heading"]}" is a task and cannot be skipped')
        elif section["is_checkpoint"] and text not in shown_checkpoints:
            errors.append(f'{field}: "{section["heading"]}" is a checkpoint and cannot be skipped')
        else:
            used.add(target)

    for key, sections in outlines.items():
        for (text, number), section in _occurrences(sections):
            if section["level"] >= 2 and (key, (text, number)) not in used:
                name = section["heading"] + (f"#{number}" if number > 1 else "")
                errors.append(
                    f'{key}: heading "{name}" (line {section["line"]}) is neither used nor skipped'
                )

    for kind, flag, shown in (
        ("tasks", "is_task", shown_tasks),
        ("checkpoints", "is_checkpoint", shown_checkpoints),
    ):
        wanted = _heading_names(outlines, flag)
        missing = [name for text, name in wanted.items() if text not in shown]
        if missing:
            errors.append(
                f"{kind}: expected {len(wanted)}, found {len(wanted) - len(missing)} "
                f"(missing: {'; '.join(missing)})"
            )

    stories = expected_counts(outlines)["stories"]
    found_stories = len({s.get("id") for s in _dicts(summary.get("stories"))})
    if found_stories < stories:
        errors.append(f"stories: expected {stories}, found {found_stories}")
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
    summary, problem = load_json(summary_path)
    if problem:
        print(problem, file=sys.stderr)
        return 1
    errors = validate(summary)
    if not errors:
        try:
            errors = check(summary, inputs)
        except (OSError, UnicodeDecodeError) as exc:
            errors = [f"cannot read an input file: {exc}"]
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
