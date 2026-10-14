"""Where a deck is written. One place for the naming rule, used by render.py."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

DEFAULT_DIR = Path("docs") / "exec-summary"
MAX_NAME = 120
# Windows treats these as devices, whatever the extension.
RESERVED = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{n}" for n in range(1, 10)),
    *(f"lpt{n}" for n in range(1, 10)),
}


def _stem(source: str) -> str:
    name = re.split(r"[\\/]", source)[-1]
    stem = name.rsplit(".", 1)[0] if "." in name.strip(".") else name
    stem = re.sub(r"[^A-Za-z0-9._-]", "_", stem) or "deck"
    return f"_{stem}" if stem.split(".")[0].casefold() in RESERVED else stem


def output_path(sources: list[str], out: str | None = None, base: Path = DEFAULT_DIR) -> Path:
    """Output file for a set of input files: `--out` wins, else the names joined with `+`."""
    if out:
        return Path(out)
    name = "+".join(_stem(s) for s in sources) or "deck"
    if len(name) > MAX_NAME:
        digest = hashlib.sha1("+".join(sources).encode("utf-8")).hexdigest()[:8]
        name = f"{name[: MAX_NAME - 9]}-{digest}"
    return base / f"{name}.html"


def check_out_path(out: Path, protected: list[Path]) -> list[str]:
    """Problems with writing the deck to `out`. It must be a `.html` file and must not be one of
    the files the user gave (the summary or a source), which the tool never edits."""
    errors = []
    if out.suffix.lower() != ".html":
        errors.append(f"--out: {out} must end in .html")
    target = out.resolve()
    for path in protected:
        if path.resolve() == target:
            errors.append(f"--out: {out} is one of the input files and will not be overwritten")
    return errors
