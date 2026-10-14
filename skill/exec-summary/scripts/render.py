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
ROWS_PER_SLIDE = 8

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


def table_slides(
    slide_id: str, title: str, headers: list[str], rows: list[tuple[list[str], str]]
) -> list[Slide]:
    """Slides for a table. Each row is (cells as escaped HTML, src). A source column is added,
    and the table continues on another slide after ROWS_PER_SLIDE rows."""
    if not rows:
        return []
    head = "".join(f"<th>{esc(h)}</th>" for h in [*headers, "Source"])
    slides = []
    for page, group in enumerate(chunks(rows, ROWS_PER_SLIDE), start=1):
        id_suffix, title_suffix = suffix(page)
        body = "".join(
            "<tr>"
            + "".join(f"<td>{cell}</td>" for cell in cells)
            + f'<td class="src">{esc(src)}</td></tr>'
            for cells, src in group
        )
        shown = f"{title}{title_suffix}"
        slides.append(
            (
                f"{slide_id}{id_suffix}",
                shown,
                f"<h2>{esc(shown)}</h2><table><thead><tr>{head}</tr></thead>"
                f"<tbody>{body}</tbody></table>",
            )
        )
    return slides


def render_criteria(data: dict) -> list[Slide]:
    rows = [
        ([f"{esc(s['id'])}: {esc(s['want'])}", esc(criterion)], s["src"])
        for s in data.get("stories", [])
        for criterion in s.get("criteria", [])
    ]
    return table_slides("criteria", "How we will know it works", ["Story", "It works when"], rows)


def render_data(data: dict) -> list[Slide]:
    rows = [
        ([esc(d["name"]), esc(d["plain"]), esc(", ".join(d.get("fields", [])))], d["src"])
        for d in data.get("data", [])
    ]
    return table_slides(
        "data", "What information it keeps", ["Item", "What it is", "Details"], rows
    )


def render_stack(data: dict) -> list[Slide]:
    rows = [
        ([esc(s["part"]), esc(s["choice"]), esc(s["plain"])], s["src"])
        for s in data.get("stack", [])
    ]
    return table_slides("stack", "Building blocks", ["Part", "Choice", "What it means"], rows)


RULE_GROUPS = [("always", "Always"), ("ask_first", "Asks you first"), ("never", "Never")]


def render_rules(data: dict) -> list[Slide]:
    rules = data.get("rules")
    if not rules:
        return []
    cards = "".join(
        f'<div class="card"><h3>{label}</h3><ul>'
        + "".join(f"<li>{esc(item)}</li>" for item in rules[key])
        + "</ul></div>"
        for key, label in RULE_GROUPS
        if rules.get(key)
    )
    title = "Rules the AI follows"
    body = f'<h2>{title}</h2><div class="cards">{cards}</div>{src_note(rules["src"])}'
    return [("rules", title, body)]


def render_decisions(data: dict) -> list[Slide]:
    rows = [([esc(d["text"])], d["src"]) for d in data.get("decisions", [])]
    return table_slides("decisions", "Decisions already made", ["Decision"], rows)


def render_out_of_scope(data: dict) -> list[Slide]:
    rows = [([esc(d["text"])], d["src"]) for d in data.get("out_of_scope", [])]
    return table_slides("out-of-scope", "Not included", ["Left out on purpose"], rows)


def render_success(data: dict) -> list[Slide]:
    items = data.get("success", [])
    with_phase = any(s.get("phase") for s in items)
    rows = [
        ([esc(s["text"])] + ([esc(s.get("phase", ""))] if with_phase else []), s["src"])
        for s in items
    ]
    headers = ["Success looks like"] + (["Phase"] if with_phase else [])
    return table_slides("success", "How we measure success", headers, rows)


def render_notes(data: dict) -> list[Slide]:
    slides = []
    for page, note in enumerate(data.get("notes", []), start=1):
        id_suffix, _ = suffix(page)
        body = "".join(f"<p>{esc(t)}</p>" for t in note["text"])
        slides.append(
            (
                f"notes{id_suffix}",
                note["title"],
                f"<h2>{esc(note['title'])}</h2>{body}{src_note(note['src'])}",
            )
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


SLIDE_BUILDERS = [
    render_title,
    render_goal,
    render_stories,
    render_criteria,
    render_data,
    render_stack,
    render_rules,
    render_decisions,
    render_out_of_scope,
    render_success,
    render_notes,
    render_check,
]


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
