"""Where a deck is written, and which Artifact link belongs to it.

One place for the naming rule and for `links.json`, used by render.py and by the publish step.

Usage:
  paths.py url <out.html>              print the saved Artifact link of a deck (nothing if none)
  paths.py set-url <out.html> <url>    save the link after publishing
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from collections.abc import Callable, Iterator
from pathlib import Path

from common import load_json

DEFAULT_DIR = Path("docs") / "exec-summary"
LINKS_FILE = DEFAULT_DIR / "links.json"
LINK_PREFIX = "https://claude.ai/"
LOCK_WAIT = 3.0  # seconds to wait for another run to finish writing links.json
LOCK_STALE = 60.0  # a lock older than this is left over from a crashed run
MAX_NAME = 120
MAX_NAME_TRIES = 1000
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


def _digest(sources: list[str]) -> str:
    """Short hash of the inputs, the same whatever their slash or `./` spelling."""
    joined = "|".join(map(normalize_source, sources))
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:8]


def _join(names: list[str], sources: list[str], base: Path) -> Path:
    name = "+".join(names) or "deck"
    if len(name) > MAX_NAME:
        name = f"{name[: MAX_NAME - 9]}-{_digest(sources)}"
    return base / f"{name}.html"


def _key(path: Path | str) -> str:
    """How a deck path is written in links.json: normalised, forward slashes."""
    return Path(os.path.normpath(path)).as_posix()


def output_path(sources: list[str], out: str | None = None, base: Path = DEFAULT_DIR) -> Path:
    """Output file for a set of input files: `--out` wins, else the names joined with `+`."""
    if out:
        return Path(out)
    return _join([_stem(s) for s in sources], sources, base)


def _same_inputs(entry: dict, sources: list[str]) -> bool:
    return [normalize_source(s) for s in entry["sources"]] == [normalize_source(s) for s in sources]


def _entry(links: dict, path: Path | str) -> dict | None:
    """The links.json entry of a deck path, ignoring case (Windows and macOS do)."""
    wanted = _key(path).casefold()
    for key, entry in links.items():
        if _key(key).casefold() == wanted:
            return entry
    return None


def pick_output(
    sources: list[str],
    links: dict,
    out: str | None = None,
    base: Path = DEFAULT_DIR,
    exists: Callable[[Path], bool] = lambda path: False,
) -> Path:
    """Like `output_path`, but a name already used by another deck is not reused: one made
    from other inputs (an entry in links.json), or one that is on disk but not recorded
    (`exists` says so). The first deck keeps its simple name; a later clash gets its folders
    added (`other-SPEC.html`), then a short hash of the inputs, then a counter."""
    if out:
        return Path(out)

    def free(path: Path) -> bool:
        entry = _entry(links, path)
        return _same_inputs(entry, sources) if entry else not exists(path)

    simple = output_path(sources, base=base)
    if free(simple):
        return simple
    qualified = _join([_qualified_stem(s) for s in sources], sources, base)
    if free(qualified):
        return qualified
    stem = f"{qualified.stem}-{_digest(sources)}"
    for number in range(1, MAX_NAME_TRIES):
        candidate = qualified.with_name(f"{stem}.html" if number == 1 else f"{stem}-{number}.html")
        if free(candidate):
            return candidate
    raise ValueError(f"no free name for a deck of {sources[0]} in {base}")


def check_out_free(links: dict, out: Path, sources: list[str]) -> str | None:
    """Error when `--out` names a deck that was made from other inputs, whose saved link
    would otherwise be lost. A deck of the same inputs, or an unknown path, is fine."""
    entry = _entry(links, out)
    if entry and not _same_inputs(entry, sources):
        return (
            f"--out: {out} already holds a deck made from {entry['sources']}; choose another name"
        )
    return None


# --- links.json: output path -> {"sources": [...], "url": link or null} -------------------------


def _check_links(data: object) -> str | None:
    if not isinstance(data, dict):
        return "expected an object of decks"
    for key, entry in data.items():
        ok = isinstance(entry, dict) and {"sources", "url"} <= set(entry)
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


@contextlib.contextmanager
def _locked(file: Path) -> Iterator[None]:
    """One run at a time may change links.json. A lock file left by a crashed run is ignored
    after LOCK_STALE seconds; waiting longer than LOCK_WAIT is an error."""
    lock = file.with_name(file.name + ".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + LOCK_WAIT
    while True:
        try:
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            break
        except FileExistsError:
            with contextlib.suppress(OSError):
                if time.time() - lock.stat().st_mtime > LOCK_STALE:
                    lock.unlink()
                    continue
            if time.monotonic() > deadline:
                raise OSError(f"{lock} is in use by another run; try again") from None
            time.sleep(0.05)
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)


def _write_links(file: Path, links: dict) -> None:
    """Write through a temp file in the same folder, then swap it in. The temp file is removed
    when anything fails."""
    text = json.dumps(links, indent=2, sort_keys=True) + "\n"
    handle, name = tempfile.mkstemp(dir=file.parent, prefix=file.name + ".", suffix=".tmp")
    temp = Path(name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        temp.replace(file)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


def _update(file: Path, change: Callable[[dict], str | None]) -> str | None:
    """Read links.json, let `change` edit it, write it back. Returns a message when something
    goes wrong (unreadable file, lock, disk), never a traceback; the file is then left as it was."""
    try:
        with _locked(file):
            links, problem = read_links(file)
            problem = problem or change(links)
            if problem:
                return problem
            _write_links(file, links)
    except OSError as exc:
        return f"{file}: cannot save: {exc}"
    return None


def register_deck(file: Path, out: Path, sources: list[str]) -> str | None:
    """Record which inputs a deck was made from. Keeps its saved link when the inputs are the
    same, and every other deck's entry, except an entry with no link whose file is gone.
    Returns an error message, or None."""
    key = _key(out)

    def change(links: dict) -> None:
        old = _entry(links, key)
        keep = old["url"] if old and _same_inputs(old, sources) else None
        for other in [k for k in links if _key(k).casefold() == key.casefold()]:
            del links[other]
        for other in [k for k, e in links.items() if not e["url"] and not Path(k).exists()]:
            del links[other]
        links[key] = {"sources": list(sources), "url": keep}

    return _update(file, change)


def set_url(file: Path, out: Path, url: str) -> str | None:
    """Save the Artifact link of a registered deck. Returns an error message, or None."""
    if not _is_claude_link(url):
        return f"link must start with {LINK_PREFIX}"

    def change(links: dict) -> str | None:
        entry = _entry(links, out)
        if entry is None:
            return f"{_key(out)}: deck is not registered in {file} (render it first)"
        entry["url"] = url
        return None

    return _update(file, change)


def _is_claude_link(url: object) -> bool:
    return (
        isinstance(url, str) and url.startswith(LINK_PREFIX) and not any(c.isspace() for c in url)
    )


def get_url(links: dict, out: Path) -> str | None:
    """The saved link of a deck, if it is a claude.ai link (a hand-edited file is not trusted)."""
    entry = _entry(links, out)
    return entry["url"] if entry and _is_claude_link(entry["url"]) else None


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
        else:
            print(f"no saved link for {argv[1]}", file=sys.stderr)
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
