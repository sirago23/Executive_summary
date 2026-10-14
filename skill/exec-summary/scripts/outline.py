"""Print the Markdown structure of one or more files as JSON.

Usage: outline.py <file> [<file> ...]

The script reports structure only (headings, list items, checkboxes, tables). What a section
means is decided by the caller.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

ALLOWED_SUFFIXES = {".md", ".txt"}

HEADING = re.compile(r"^(#{1,6})\s+(\S.*)$")
CLOSING_HASHES = re.compile(r"\s#+$")
CHECKPOINT_HEADING = re.compile(r"^checkpoint\b", re.IGNORECASE)
STORY_HEADING = re.compile(r"^(user\s+)?stor(y|ies)\s*[:#.\-]?\s*\d+", re.IGNORECASE)
MAX_FILE_BYTES = 2 * 1024 * 1024
CHECKBOX_PREFIX = re.compile(r"^[-*+]\s+\[[ xX]\]\s+")
BULLET = re.compile(r"^\s*[-*+]\s+(.*\S)\s*$")
CHECKBOX = re.compile(r"^\[([ xX])\]\s+(.*\S)\s*$")
NUMBERED = re.compile(r"^\s*\d+[.)]\s+(.*\S)\s*$")
TABLE_SEPARATOR = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")
TASK_HEADING = re.compile(r"^Task\s+\d+", re.IGNORECASE)


def _new_section(heading: str, level: int, line: int) -> dict:
    return {
        "heading": heading,
        "level": level,
        "line": line,
        "list_items": [],
        "numbered_items": [],
        "checkboxes": [],
        "tables": 0,
        "is_task": bool(TASK_HEADING.match(heading)),
        "is_checkpoint": bool(CHECKPOINT_HEADING.match(heading)),
        "is_story": bool(STORY_HEADING.match(heading)),
    }


def outline_text(text: str) -> list[dict]:
    """Return the sections of a Markdown text. Text before the first heading is ignored."""
    sections: list[dict] = []
    fence: str | None = None
    previous = ""
    for number, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        marker = stripped[:3]
        if marker in ("```", "~~~"):
            if fence is None:
                fence = marker
            elif marker == fence:
                fence = None
            previous = ""
            continue
        if fence is not None:
            continue

        heading = HEADING.match(raw)
        if heading:
            title = heading.group(2).rstrip()
            closing = CLOSING_HASHES.search(title)
            if closing:
                title = title[: closing.start()].rstrip()
            title = CHECKBOX_PREFIX.sub("", title).strip()
            sections.append(_new_section(title, len(heading.group(1)), number))
            previous = raw
            continue
        if not sections:
            previous = raw
            continue

        current = sections[-1]
        bullet = BULLET.match(raw)
        numbered = NUMBERED.match(raw)
        if bullet:
            box = CHECKBOX.match(bullet.group(1))
            if box:
                current["checkboxes"].append(
                    {"text": box.group(2), "checked": box.group(1) in "xX"}
                )
            else:
                current["list_items"].append(bullet.group(1))
        elif numbered:
            current["numbered_items"].append(numbered.group(1))
        elif "|" in raw and "|" in previous and TABLE_SEPARATOR.match(raw):
            current["tables"] += 1
        previous = raw
    return sections


def outline_file(path: str | Path) -> dict:
    p = Path(path)
    text = p.read_text(encoding="utf-8-sig")
    modified = datetime.fromtimestamp(p.stat().st_mtime).date().isoformat()
    return {"path": str(path), "modified": modified, "sections": outline_text(text)}


def check_paths(paths: list[str]) -> list[str]:
    errors = []
    for path in paths:
        p = Path(path)
        if not p.is_file():
            errors.append(f"{path}: file not found")
        elif p.suffix.lower() not in ALLOWED_SUFFIXES:
            errors.append(f"{path}: unsupported file type, only .md and .txt are accepted")
        elif p.stat().st_size > MAX_FILE_BYTES:
            errors.append(f"{path}: file is larger than {MAX_FILE_BYTES // 1024 // 1024} MB")
    return errors


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: outline.py <file> [<file> ...]", file=sys.stderr)
        return 1
    errors = check_paths(argv)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    result = {"files": [outline_file(path) for path in argv]}
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
