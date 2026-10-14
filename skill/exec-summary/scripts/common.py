"""Small helpers shared by the scripts, so each rule exists once."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from html import escape
from pathlib import Path

MAX_JSON_BYTES = 2 * 1024 * 1024
SRC_SEPARATOR = " > "
NODE_ID = re.compile(r"[A-Za-z0-9_]+")


def esc(value: object) -> str:
    """HTML-escape a value, quotes included."""
    return escape(str(value), quote=True)


def is_node_id(text: str) -> bool:
    """True for letters, digits and underscore only. `fullmatch`, so a trailing newline fails."""
    return NODE_ID.fullmatch(text) is not None


def is_src_key(key: str) -> bool:
    return key == "src" or key.endswith("_src")


def find_src(value: object, path: str = "") -> Iterator[tuple[str, str]]:
    """Yield (path, text) for every string stored under `src` or a key ending in `_src`."""
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if is_src_key(key) and isinstance(child, str):
                yield child_path, child
            else:
                yield from find_src(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from find_src(child, f"{path}[{index}]")


def load_json(path: str) -> tuple[object, str | None]:
    """Read a JSON file. Returns (data, None), or (None, "<path>: <message>") when it cannot be
    used: missing, too large, not UTF-8, not JSON, or nested so deeply that parsing fails."""
    file = Path(path)
    try:
        if file.stat().st_size > MAX_JSON_BYTES:
            return None, f"{path}: file is larger than {MAX_JSON_BYTES // 1024 // 1024} MB"
        text = file.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return None, f"{path}: file not found"
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"{path}: cannot read file: {exc}"
    try:
        return json.loads(text), None
    except json.JSONDecodeError as exc:
        return None, f"{path}: invalid JSON: {exc}"
    except (RecursionError, ValueError) as exc:
        return None, f"{path}: invalid JSON: {type(exc).__name__}"
