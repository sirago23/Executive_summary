"""Render a summary.json as one self-contained HTML deck.

Usage: render.py <summary.json> [--out <out.html>]

Without --out the file goes to docs/exec-summary/<input names joined with +>.html.
Every slide function returns a list of slides (empty when its section is absent), so a section
that is not in the summary never produces a slide.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from html import escape
from pathlib import Path
from string import Template

from mermaid import to_flowchart
from paths import output_path
from validate import validate
from wireframe import render_wireframe

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
STORIES_PER_SLIDE = 6
ROWS_PER_SLIDE = 8
WIREFRAMES_PER_SLIDE = 2
STEPS_PER_SLIDE = 6
TASK_SLIDE_BUDGET = 10  # rows on one tasks slide; each phase title counts as one row
MAX_IMAGE_BYTES = 5 * 1024 * 1024
DESIGN_FOLDERS = ("design", "docs/design", "mockups")
IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}
MERMAID_URL = "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"
MERMAID_SRI = "sha384-rbtjAdnIQE/aQJGEgXrVUlMibdfTSa4PQju4HDhN3sR2PmaKFzhEafuePsl9H/9I"
MERMAID_TAG = (
    f'<script src="{MERMAID_URL}" integrity="{MERMAID_SRI}" crossorigin="anonymous" defer></script>'
)

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


def find_design_images(project_dir: Path | None) -> tuple[list[dict], int]:
    """Images in the project's design folders as data URIs, and how many were left out.

    Only files directly inside the folders count, and every file must resolve to a place inside
    the project folder. Images are embedded until MAX_IMAGE_BYTES is reached.
    """
    if project_dir is None:
        return [], 0
    root = project_dir.resolve()
    images: list[dict] = []
    left_out = 0
    total = 0
    for folder in DESIGN_FOLDERS:
        directory = (root / folder).resolve()
        if not directory.is_dir() or not directory.is_relative_to(root):
            continue
        for path in sorted(directory.iterdir()):
            kind = IMAGE_TYPES.get(path.suffix.lower())
            real = path.resolve()
            if kind is None or not real.is_file() or not real.is_relative_to(root):
                continue
            size = real.stat().st_size
            if total + size > MAX_IMAGE_BYTES:
                left_out += 1
                continue
            total += size
            encoded = base64.b64encode(real.read_bytes()).decode("ascii")
            images.append({"name": path.stem, "uri": f"data:{kind};base64,{encoded}"})
    return images, left_out


def left_out_note(count: int) -> str:
    if not count:
        return ""
    many = count != 1
    return (
        f'<p class="src">{count} more image{"s" if many else ""} '
        f"{'were' if many else 'was'} left out because the deck would get too large.</p>"
    )


def render_screens(data: dict, images: list[dict], left_out: int) -> list[Slide]:
    if images:
        slides = []
        for page, image in enumerate(images, start=1):
            id_suffix, title_suffix = suffix(page)
            title = f"Screens{title_suffix}"
            note = left_out_note(left_out) if page == len(images) else ""
            body = (
                f"<h2>{esc(title)}</h2>"
                f'<figure class="design"><img src="{esc(image["uri"])}" alt="{esc(image["name"])}">'
                f"<figcaption>{esc(image['name'])}</figcaption></figure>{note}"
            )
            slides.append((f"screens{id_suffix}", title, body))
        return slides

    screens = data.get("screens", [])
    note = left_out_note(left_out)
    if not screens:
        return [("screens", "Screens", f"<h2>Screens</h2>{note}")] if note else []
    slides = []
    groups = chunks(screens, WIREFRAMES_PER_SLIDE)
    for page, group in enumerate(groups, start=1):
        id_suffix, title_suffix = suffix(page)
        title = f"Example screens{title_suffix}"
        sources = "".join(src_note(s["src"]) for s in group if s.get("src"))
        closing = note if page == len(groups) else ""
        body = (
            f"<h2>{esc(title)}</h2>"
            f'<div class="wireframes">{"".join(render_wireframe(s) for s in group)}</div>'
            f"{sources}{closing}"
        )
        slides.append((f"screens{id_suffix}", title, body))
    return slides


def diagram_fallback(diagram: dict) -> str:
    """Nodes and edges as plain HTML, shown when Mermaid cannot load or draw."""
    labels = {n["id"]: n["label"] for n in diagram["nodes"]}
    rows = "".join(
        f"<tr><td>{esc(labels[e['from']])}</td><td>{esc(labels[e['to']])}</td>"
        f"<td>{esc(e.get('label', ''))}</td></tr>"
        for e in diagram["edges"]
    )
    parts = esc(", ".join(labels.values()))
    return (
        '<div class="diagram-fallback" hidden>'
        "<p>The picture could not be drawn here. The same information as a list:</p>"
        f"<p>Parts: {parts}</p>"
        "<table><thead><tr><th>From</th><th>To</th><th>What happens</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )


def diagram_slides(data: dict, kind: str, slide_id: str) -> list[Slide]:
    slides = []
    shown = [d for d in data.get("diagrams", []) if d["kind"] == kind]
    for page, diagram in enumerate(shown, start=1):
        id_suffix, _ = suffix(page)
        mermaid_text = to_flowchart(diagram["nodes"], diagram["edges"])
        body = (
            f"<h2>{esc(diagram['title'])}</h2>"
            f'<div class="diagram"><pre class="mermaid">{esc(mermaid_text)}</pre>'
            f"{diagram_fallback(diagram)}</div>{src_note(diagram['src'])}"
        )
        slides.append((f"{slide_id}{id_suffix}", diagram["title"], body))
    return slides


def render_architecture(data: dict) -> list[Slide]:
    return diagram_slides(data, "architecture", "architecture")


def render_flow(data: dict) -> list[Slide]:
    return diagram_slides(data, "flow", "flow")


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


def render_phases(data: dict) -> list[Slide]:
    phases = data.get("phases", [])
    slides = []
    for page, group in enumerate(chunks(phases, STEPS_PER_SLIDE), start=1):
        id_suffix, title_suffix = suffix(page)
        title = f"Delivery phases{title_suffix}"
        steps = "".join(
            '<li class="step">'
            f"<strong>{esc(p['title'])}</strong>"
            + (f"<span>{esc(p['goal'])}</span>" if p.get("goal") else "")
            + f'<span class="src">Source: {esc(p["src"])}</span></li>'
            for p in group
        )
        slides.append(
            (f"phases{id_suffix}", title, f'<h2>{esc(title)}</h2><ol class="steps">{steps}</ol>')
        )
    return slides


def task_block(title: str, tasks: list[dict]) -> str:
    rows = "".join(
        f"<tr><td>{esc(t['title'])}</td><td>{esc(t.get('you_will_see', ''))}</td>"
        f'<td class="src">{esc(t["src"])}</td></tr>'
        for t in tasks
    )
    return (
        f"<h3>{esc(title)}</h3><table><thead><tr><th>Task</th><th>What you will see working</th>"
        f"<th>Source</th></tr></thead><tbody>{rows}</tbody></table>"
    )


def render_tasks(data: dict) -> list[Slide]:
    """Tasks grouped by phase. A phase title always sits on the same slide as its tasks."""
    blocks: list[tuple[str, int]] = []
    for phase in data.get("phases", []):
        for page, group in enumerate(chunks(phase.get("tasks", []), ROWS_PER_SLIDE), start=1):
            _, title_suffix = suffix(page)
            blocks.append((task_block(f"{phase['title']}{title_suffix}", group), len(group) + 1))
    pages: list[list[str]] = []
    used = TASK_SLIDE_BUDGET
    for html, cost in blocks:
        if used + cost > TASK_SLIDE_BUDGET:
            pages.append([])
            used = 0
        pages[-1].append(html)
        used += cost
    slides = []
    for page, parts in enumerate(pages, start=1):
        id_suffix, title_suffix = suffix(page)
        title = f"Tasks by phase{title_suffix}"
        slides.append((f"tasks{id_suffix}", title, f"<h2>{esc(title)}</h2>{''.join(parts)}"))
    return slides


def render_checkpoints(data: dict) -> list[Slide]:
    rows = []
    for c in data.get("checkpoints", []):
        name = f"<strong>{esc(c['title'])}</strong>"
        if c.get("phase"):
            name += f"<br>{esc(c['phase'])}"
        items = "<ul>" + "".join(f"<li>{esc(i)}</li>" for i in c["items"]) + "</ul>"
        rows.append(([name, items], c["src"]))
    return table_slides("checkpoints", "Checkpoints you approve", ["Checkpoint", "You check"], rows)


def render_risks(data: dict) -> list[Slide]:
    rows = [
        (
            [
                esc(r["risk"]),
                f'<span class="impact impact-{r["impact"].lower()}">{esc(r["impact"])}</span>',
                esc(r["handling"]),
            ],
            r["src"],
        )
        for r in data.get("risks", [])
    ]
    return table_slides(
        "risks", "Risks and how they are handled", ["Risk", "Impact", "Handled by"], rows
    )


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
    render_screens,
    render_architecture,
    render_flow,
    render_data,
    render_stack,
    render_phases,
    render_tasks,
    render_checkpoints,
    render_risks,
    render_rules,
    render_decisions,
    render_out_of_scope,
    render_success,
    render_notes,
    render_check,
]


def build_slides(data: dict, project_dir: Path | None = None) -> list[Slide]:
    images, left_out = find_design_images(project_dir)
    slides: list[Slide] = []
    for builder in SLIDE_BUILDERS:
        if builder is render_screens:
            slides.extend(builder(data, images, left_out))
        else:
            slides.extend(builder(data))
    return slides


def render_deck(data: dict, project_dir: Path | None = None) -> str:
    errors = validate(data)
    if errors:
        raise InvalidSummary("\n".join(errors))
    slides = build_slides(data, project_dir)
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
        mermaid=MERMAID_TAG if data.get("diagrams") else "",
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
        html = render_deck(data, project_dir=Path.cwd())
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
