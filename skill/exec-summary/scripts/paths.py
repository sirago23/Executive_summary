"""Where a deck is written, and which Artifact link belongs to it.

One place for the naming rule and for `links.json`, used by render.py and by the publish step.

Usage:
  paths.py url <out.html>              print the saved Artifact link of a deck (nothing if none)
  paths.py set-url <out.html> <url>    save the link after publishing
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from common import load_json

DEFAULT_DIR = Path("docs") / "exec-summary"
LINKS_FILE = DEFAULT_DIR / "links.json"
LINK_PREFIX = "https://claude.ai/"
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


def normalize_source(source: str) -> str:
    """The same path spelling for comparing: forward slashes, no leading `./`."""
    text = source.replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return text


def _qualified_stem(source: str) -> str:
    """File stem with its folders in front, `other/sub/SPEC.md` -> `other-sub-SPEC`."""
    *folders, _ = normalize_source(source).split("/")
    clean = [re.sub(r"[^A-Za-z0-9._-]", "_", f) for f in folders if f not in ("", ".")]
    return "-".join([*clean, _stem(source)])


def _join(names: list[str], sources: list[str], base: Path) -> Path:
    name = "+".join(names) or "deck"
    if len(name) > MAX_NAME:
        digest = hashlib.sha1("+".join(sources).encode("utf-8")).hexdigest()[:8]
        name = f"{name[: MAX_NAME - 9]}-{digest}"
    return base / f"{name}.html"


def output_path(sources: list[str], out: str | None = None, base: Path = DEFAULT_DIR) -> Path:
    """Output file for a set of input files: `--out` wins, else the names joined with `+`."""
    if out:
        return Path(out)
    return _join([_stem(s) for s in sources], sources, base)


def _same_inputs(entry: dict, sources: list[str]) -> bool:
    return [normalize_source(s) for s in entry["sources"]] == [normalize_source(s) for s in sources]


def pick_output(
    sources: list[str], links: dict, out: str | None = None, base: Path = DEFAULT_DIR
) -> Path:
    """Like `output_path`, but a name already used by a deck made from other inputs is not
    reused. The first deck keeps its simple name; a later clash gets its folders added
    (`other-SPEC.html`), and if even that is taken, a short hash of the inputs."""
    if out:
        return Path(out)

    def free(path: Path) -> bool:
        entry = links.get(path.as_posix())
        return entry is None or _same_inputs(entry, sources)

    simple = output_path(sources, base=base)
    if free(simple):
        return simple
    qualified = _join([_qualified_stem(s) for s in sources], sources, base)
    if free(qualified):
        return qualified
    digest = hashlib.sha1("|".join(map(normalize_source, sources)).encode("utf-8")).hexdigest()[:8]
    return qualified.with_name(f"{qualified.stem}-{digest}.html")


# --- links.json: output path -> {"sources": [...], "url": link or null} -------------------------


def _check_links(data: object) -> str | None:
    if not isinstance(data, dict):
        return "expected an object of decks"
    for key, entry in data.items():
        ok = isinstance(entry, dict) and set(entry) == {"sources", "url"}
        ok = (
            ok
            and isinstance(entry["sources"], list)
            and all(isinstance(s, str) for s in entry["sources"])
        )
        ok = ok and (entry["url"] is None or isinstance(entry["url"], str))
        if not ok:
            return f'{key}: expected {{"sources": [paths], "url": link or null}}'
    return None


def read_links(file: Path) -> tuple[dict, str | None]:
    """The saved decks, or ({}, message) when the file cannot be used. A missing file is empty."""
    if not file.exists():
        return {}, None
    data, problem = load_json(str(file))
    if problem is None:
        shape = _check_links(data)
        problem = f"{file}: {shape}" if shape else None
    return ({}, problem) if problem else (data, None)


def _write_links(file: Path, links: dict) -> None:
    file.parent.mkdir(parents=True, exist_ok=True)
    temp = file.with_name(file.name + ".tmp")
    text = json.dumps(links, indent=2, sort_keys=True) + "\n"
    temp.write_text(text, encoding="utf-8", newline="\n")
    temp.replace(file)


def register_deck(file: Path, out: Path, sources: list[str]) -> str | None:
    """Record which inputs a deck was made from. Keeps its saved link when the inputs are the
    same, and every other deck's entry. Returns an error message, or None."""
    links, problem = read_links(file)
    if problem:
        return problem
    key = out.as_posix()
    old = links.get(key)
    keep = old["url"] if old and _same_inputs(old, sources) else None
    links[key] = {"sources": list(sources), "url": keep}
    _write_links(file, links)
    return None


def set_url(file: Path, out: Path, url: str) -> str | None:
    """Save the Artifact link of a registered deck. Returns an error message, or None."""
    if not url.startswith(LINK_PREFIX) or any(c.isspace() for c in url):
        return f"link must start with {LINK_PREFIX}"
    links, problem = read_links(file)
    if problem:
        return problem
    key = out.as_posix()
    if key not in links:
        return f"{key}: deck is not registered in {file} (render it first)"
    links[key]["url"] = url
    _write_links(file, links)
    return None


def get_url(links: dict, out: Path) -> str | None:
    entry = links.get(out.as_posix())
    return entry["url"] if entry else None


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


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "url":
        links, problem = read_links(LINKS_FILE)
        if problem:
            print(problem, file=sys.stderr)
            return 1
        url = get_url(links, Path(argv[1]))
        if url:
            print(url)
        return 0
    if len(argv) == 3 and argv[0] == "set-url":
        problem = set_url(LINKS_FILE, Path(argv[1]), argv[2])
        if problem:
            print(problem, file=sys.stderr)
            return 1
        return 0
    print(__doc__.split("Usage:")[1].strip(), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
