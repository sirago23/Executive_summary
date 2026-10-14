"""Where a deck is written. One place for the naming rule, used by render.py."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

DEFAULT_DIR = Path("docs") / "exec-summary"
MAX_NAME = 120


def _stem(source: str) -> str:
    name = re.split(r"[\\/]", source)[-1]
    stem = name.rsplit(".", 1)[0] if "." in name.strip(".") else name
    return re.sub(r"[^A-Za-z0-9._-]", "_", stem) or "deck"


def output_path(sources: list[str], out: str | None = None, base: Path = DEFAULT_DIR) -> Path:
    """Output file for a set of input files: `--out` wins, else the names joined with `+`."""
    if out:
        return Path(out)
    name = "+".join(_stem(s) for s in sources) or "deck"
    if len(name) > MAX_NAME:
        digest = hashlib.sha1("+".join(sources).encode("utf-8")).hexdigest()[:8]
        name = f"{name[: MAX_NAME - 9]}-{digest}"
    return base / f"{name}.html"
