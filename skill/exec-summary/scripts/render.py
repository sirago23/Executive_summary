"""Render a summary.json as one self-contained HTML deck.

Usage: render.py <summary.json> [--out <out.html>]

Without --out the file goes to docs/exec-summary/<input names joined with +>.html.
Every slide function returns a list of slides (empty when its section is absent), so a section
that is not in the summary never produces a slide.
"""

from __future__ import annotations

import argparse
import json
import sys
from html import escape
from pathlib import Path
from string import Template

from paths import output_path
from validate import validate

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
STORIES_PER_SLIDE = 6

Slide = tuple[str, str, str]  # (id, title in the contents list, inner HTML)


class InvalidSummary(ValueError):
    """The summary does not pass validate.py."""


def esc(value: object) -> str:
    return escape(str(value), quote=True)


def chunks(items: list, size: int) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def src_note(src: str) -> str:
    return f'<p class="src">Source: {esc(src)}</p>'


def suffix(page: int) -> tuple[str, str]:
    """Slide id suffix and title suffix for the page-th slide of a split section."""
    return ("", "") if page == 1 else (f"-{page}", " (continued)")


def render_title(data: dict) -> list[Slide]:
    project = data["project"]
    parts = [f"<h1>{esc(project['name'])}</h1>"]
    if project.get("tagline"):
        parts.append(f'<p class="tagline">{esc(project["tagline"])}</p>')
    meta = " · ".join(esc(project[k]) for k in ("status", "date") if project.get(k))
    if meta:
        parts.append(f"<p>{meta}</p>")
    rows = "".join(
        "<tr>"
        f"<td>{esc(s['path'])}</td>"
        f"<td>{esc(s.get('modified', ''))}</td>"
        f"<td>{esc(', '.join(s.get('found', [])))}</td>"
        "</tr>"
        for s in data["sources"]
    )
    parts.append(
        "<h3>This summary covers</h3>"
        "<table><thead><tr><th>File</th><th>Last changed</th><th>Contains</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )
    return [("title", "Overview", "".join(parts))]


def render_goal(data: dict) -> list[Slide]:
    goal = data.get("goal")
    if not goal:
        return []
    body = "".join(f"<p>{esc(t)}</p>" for t in goal["text"])
    return [("goal", "The goal", f"<h2>The goal</h2>{body}{src_note(goal['src'])}")]


def story_sentence(story: dict) -> str:
    want = story["want"].strip().rstrip(".")
    so = story["so"].strip().rstrip(".")
    return f"As {esc(story['as'].strip())}, I want {esc(want)}, so that {esc(so)}."


def render_stories(data: dict) -> list[Slide]:
    stories = data.get("stories")
    if not stories:
        return []
    slides = []
    for page, group in enumerate(chunks(stories, STORIES_PER_SLIDE), start=1):
        id_suffix, title_suffix = suffix(page)
        title = f"What you can do{title_suffix}"
        cards = "".join(
            '<div class="card">'
            f'<span class="id">{esc(s["id"])}</span>'
            f"<p>{story_sentence(s)}</p>"
            f"{src_note(s['src'])}"
            "</div>"
            for s in group
        )
        slides.append(
            (f"stories{id_suffix}", title, f'<h2>{esc(title)}</h2><div class="cards">{cards}</div>')
        )
    return slides


def render_check(data: dict) -> list[Slide]:
    """The closing checklist. It is always built."""
    name = data["project"]["name"]
    items: list[tuple[str, str]] = []
    if data.get("goal"):
        items.append(("goal", "The goal describes what I want."))
    if data.get("stories"):
        items.append(("stories", "The user stories match what I want the system to do."))
    for index, question in enumerate(data.get("open_questions", []), start=1):
        items.append((f"question-{index}", f"Open question: {question}"))
    rows = "".join(
        "<li><label>"
        f'<input type="checkbox" data-key="{esc("exec-summary:" + name + ":" + key)}">'
        f"<span>{esc(text)}</span>"
        "</label></li>"
        for key, text in items
    )
    body = (
        "<h2>Please check</h2>"
        "<p>Tick each item once you have checked it. Ticks are saved in this browser only.</p>"
        f'<ul class="checks">{rows}</ul>'
    )
    return [("check", "Please check", body)]


SLIDE_BUILDERS = [render_title, render_goal, render_stories, render_check]


def build_slides(data: dict) -> list[Slide]:
    slides: list[Slide] = []
    for builder in SLIDE_BUILDERS:
        slides.extend(builder(data))
    return slides


def render_deck(data: dict) -> str:
    errors = validate(data)
    if errors:
        raise InvalidSummary("\n".join(errors))
    slides = build_slides(data)
    toc = "\n".join(
        f'      <li><a href="#s-{esc(sid)}">{esc(title)}</a></li>' for sid, title, _ in slides
    )
    sections = "\n".join(
        f'<section class="slide" id="s-{esc(sid)}">{inner}</section>' for sid, _, inner in slides
    )
    template = Template((TEMPLATE_DIR / "deck.html").read_text(encoding="utf-8"))
    return template.substitute(
        title=esc(data["project"]["name"]),
        css=(TEMPLATE_DIR / "deck.css").read_text(encoding="utf-8"),
        js=(TEMPLATE_DIR / "deck.js").read_text(encoding="utf-8"),
        toc=toc,
        slides=sections,
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="render.py", description=__doc__.splitlines()[0])
    parser.add_argument("summary")
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    try:
        data = json.loads(Path(args.summary).read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        print(f"{args.summary}: file not found", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"{args.summary}: invalid JSON: {exc}", file=sys.stderr)
        return 1

    try:
        html = render_deck(data)
    except InvalidSummary as exc:
        print(exc, file=sys.stderr)
        return 1

    out = output_path([s["path"] for s in data["sources"]], args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8", newline="\n")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
