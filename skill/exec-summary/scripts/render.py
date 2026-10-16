"""Render a summary.json as one self-contained HTML deck.

Usage: render.py <summary.json> [--out <out.html>]

Without --out the file goes to docs/exec-summary/<input names joined with +>.html.
Every slide function returns a list of slides (empty when its section is absent), so a section
that is not in the summary never produces a slide.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from string import Template

from common import esc, load_json
from design_images import find_design_images
from mermaid import to_flowchart
from paths import (
    LINKS_FILE,
    check_out_free,
    check_out_path,
    output_path,
    pick_output,
    read_links,
    register_deck,
)
from validate import validate
from wireframe import render_wireframe

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
STORIES_PER_SLIDE = 6
ROWS_PER_SLIDE = 8
WIREFRAMES_PER_SLIDE = 2
STEPS_PER_SLIDE = 6
RISKS_PER_SLIDE = 5
TASK_SLIDE_BUDGET = 5  # rows on one tasks slide; each phase title counts as one row
TASKS_PER_BLOCK = 4  # tasks of one phase on one slide, so a block fits the budget
CHECKPOINTS_PER_SLIDE = 4
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MERMAID_URL = "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"
MERMAID_SRI = "sha384-rbtjAdnIQE/aQJGEgXrVUlMibdfTSa4PQju4HDhN3sR2PmaKFzhEafuePsl9H/9I"
MERMAID_TAG = (
    f'<script src="{MERMAID_URL}" integrity="{MERMAID_SRI}" crossorigin="anonymous" defer></script>'
)

Slide = tuple[str, str, str]  # (id, title in the contents list, inner HTML)


class InvalidSummary(ValueError):
    """The summary does not pass validate.py."""


def chunks(items: list, size: int) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def src_note(src: str) -> str:
    return f'<p class="src">Source: {esc(src)}</p>'


def suffix(page: int) -> tuple[str, str]:
    """Slide id suffix and title suffix for the page-th slide of a split section."""
    return ("", "") if page == 1 else (f"-{page}", " (continued)")


MAX_TILES = 4


def stat_counts(data: dict) -> list[tuple[int, str, str]]:
    """(count, singular, plural) in build order. Every number is counted from the data."""
    phases = data.get("phases", [])
    return [
        (len(data.get("stories", [])), "user story", "user stories"),
        (len(phases), "delivery phase", "delivery phases"),
        (sum(len(p.get("tasks", [])) for p in phases), "task", "tasks"),
        (len(data.get("checkpoints", [])), "checkpoint you approve", "checkpoints you approve"),
        (
            sum(len(s.get("criteria", [])) for s in data.get("stories", [])),
            "acceptance criterion",
            "acceptance criteria",
        ),
        (len(data.get("risks", [])), "risk", "risks"),
        (len(data.get("open_questions", [])), "question for you", "questions for you"),
    ]


def stat_tiles(data: dict) -> str:
    shown = [(n, one if n == 1 else many) for n, one, many in stat_counts(data) if n > 0]
    if not shown:
        return ""
    tiles = "".join(
        f'<div class="stat"><b>{n}</b><span>{label}</span></div>' for n, label in shown[:MAX_TILES]
    )
    return f'<div class="stats">{tiles}</div>'


def render_title(data: dict) -> list[Slide]:
    project = data["project"]
    pill = " · ".join(
        ["Executive summary", *([esc(project["status"])] if project.get("status") else [])]
    )
    parts = [f'<span class="pill">{pill}</span>', f"<h1>{esc(project['name'])}</h1>"]
    if project.get("tagline"):
        parts.append(f'<p class="tagline">{esc(project["tagline"])}</p>')
    parts.append(stat_tiles(data))
    files = "".join(
        "<li>"
        f'<span class="path">{esc(s["path"])}</span>'
        + (f" · last changed {esc(s['modified'])}" if s.get("modified") else "")
        + (f" · contains {esc(', '.join(s['found']))}" if s.get("found") else "")
        + "</li>"
        for s in data["sources"]
    )
    date = f"<span>{esc(project['date'])}</span>" if project.get("date") else ""
    parts.append(f'<footer class="by"><ul class="files">{files}</ul>{date}</footer>')
    return [("title", "Overview", "".join(parts))]


def render_goal(data: dict) -> list[Slide]:
    goal = data.get("goal")
    if not goal:
        return []
    body = "".join(f"<p>{esc(t)}</p>" for t in goal["text"])
    return [("goal", "The goal", f"<h2>The goal</h2>{body}{src_note(goal['src'])}")]


def story_want(story: dict) -> str:
    """What the story wants, with its reason: the part of the sentence after "I want"."""
    want = story["want"].strip().rstrip(".")
    so = story.get("so", "").strip().rstrip(".")
    ending = f", so that {esc(so)}" if so else ""
    return f"{esc(want)}{ending}."


def render_stories(data: dict) -> list[Slide]:
    stories = data.get("stories")
    if not stories:
        return []
    slides = []
    for page, group in enumerate(chunks(stories, STORIES_PER_SLIDE), start=1):
        id_suffix, title_suffix = suffix(page)
        title = f"What you can do{title_suffix}"
        cards = "".join(
            '<div class="card"><div class="row">'
            f'<span class="id">{esc(s["id"])}</span>'
            f'<span class="as">As {esc(s["as"].strip())}, I want</span></div>'
            f"<p>{story_want(s)}</p>"
            f"{src_note(s['src'])}"
            "</div>"
            for s in group
        )
        slides.append(
            (f"stories{id_suffix}", title, f'<h2>{esc(title)}</h2><div class="cards">{cards}</div>')
        )
    return slides


def table_rows(group: list[tuple[list[str], str]], merge_col: int | None) -> str:
    """HTML rows for one slide. With `merge_col`, neighbouring rows that have the same non-empty
    cell in that column show it once, spanning those rows, and each group starts with a
    stronger top line."""
    out = []
    for index, (cells, src) in enumerate(group):
        tds = ""
        start = merge_col is not None
        for column, cell in enumerate(cells):
            if merge_col != column or not cell:
                tds += f"<td>{cell}</td>"
                continue
            if index and group[index - 1][0][column] == cell:
                start = False
                continue
            span = 1
            while index + span < len(group) and group[index + span][0][column] == cell:
                span += 1
            tds += f'<td rowspan="{span}">{cell}</td>' if span > 1 else f"<td>{cell}</td>"
        row_class = ' class="group-start"' if start else ""
        out.append(f'<tr{row_class}>{tds}<td class="src">{esc(src)}</td></tr>')
    return "".join(out)


def table_slides(
    slide_id: str,
    title: str,
    headers: list[str],
    rows: list[tuple[list[str], str]],
    merge_col: int | None = None,
) -> list[Slide]:
    """Slides for a table. Each row is (cells as escaped HTML, src). A source column is added,
    and the table continues on another slide after ROWS_PER_SLIDE rows."""
    if not rows:
        return []
    head = "".join(f"<th>{esc(h)}</th>" for h in headers) + '<th class="src">Source</th>'
    table_class = ' class="grouped"' if merge_col is not None else ""
    slides = []
    for page, group in enumerate(chunks(rows, ROWS_PER_SLIDE), start=1):
        id_suffix, title_suffix = suffix(page)
        shown = f"{title}{title_suffix}"
        slides.append(
            (
                f"{slide_id}{id_suffix}",
                shown,
                f"<h2>{esc(shown)}</h2><table{table_class}><thead><tr>{head}</tr></thead>"
                f"<tbody>{table_rows(group, merge_col)}</tbody></table>",
            )
        )
    return slides


def render_criteria(data: dict) -> list[Slide]:
    rows = [
        ([f"{esc(s['id'])}: {esc(s['want'])}", esc(criterion)], s.get("criteria_src", s["src"]))
        for s in data.get("stories", [])
        for criterion in s.get("criteria", [])
    ]
    return table_slides(
        "criteria", "How we will know it works", ["Story", "It works when"], rows, merge_col=0
    )


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
            '<div class="mermaid-print" aria-hidden="true"></div>'
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
            f'<span class="id">{esc(p["id"])}</span>'
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
        '<li class="task">'
        f"<strong>{esc(t['title'])}</strong>"
        + (f'<span class="how">{esc(t["you_will_see"])}</span>' if t.get("you_will_see") else "")
        + f'<span class="src">{esc(t["src"])}</span></li>'
        for t in tasks
    )
    return f'<h3>{esc(title)}</h3><ul class="rows">{rows}</ul>'


def render_tasks(data: dict) -> list[Slide]:
    """Tasks grouped by phase. A phase title always sits on the same slide as its tasks."""
    blocks: list[tuple[str, int]] = []
    for phase in data.get("phases", []):
        for page, group in enumerate(chunks(phase.get("tasks", []), TASKS_PER_BLOCK), start=1):
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


def checkpoint_card(c: dict) -> str:
    phase = f'<span class="as">{esc(c["phase"])}</span>' if c.get("phase") else ""
    items = "<ul>" + "".join(f"<li>{esc(i)}</li>" for i in c["items"]) + "</ul>"
    return f'<div class="card"><h3>{esc(c["title"])}</h3>{phase}{items}{src_note(c["src"])}</div>'


def render_checkpoints(data: dict) -> list[Slide]:
    slides = []
    for page, group in enumerate(
        chunks(data.get("checkpoints", []), CHECKPOINTS_PER_SLIDE), start=1
    ):
        id_suffix, title_suffix = suffix(page)
        title = f"Checkpoints you approve{title_suffix}"
        cards = "".join(checkpoint_card(c) for c in group)
        slides.append(
            (
                f"checkpoints{id_suffix}",
                title,
                f'<h2>{esc(title)}</h2><div class="cards">{cards}</div>',
            )
        )
    return slides


def risk_row(r: dict) -> str:
    return (
        '<li class="risk">'
        f'<span class="impact impact-{esc(r["impact"].lower())}">{esc(r["impact"])}</span>'
        f'<div><strong>{esc(r["risk"])}</strong><span class="how">{esc(r["handling"])}</span></div>'
        f'<span class="src">{esc(r["src"])}</span>'
        "</li>"
    )


def render_risks(data: dict) -> list[Slide]:
    slides = []
    for page, group in enumerate(chunks(data.get("risks", []), RISKS_PER_SLIDE), start=1):
        id_suffix, title_suffix = suffix(page)
        title = f"Risks and how they are handled{title_suffix}"
        rows = "".join(risk_row(r) for r in group)
        slides.append(
            (f"risks{id_suffix}", title, f'<h2>{esc(title)}</h2><ul class="rows">{rows}</ul>')
        )
    return slides


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
    return table_slides(
        "success", "How we measure success", headers, rows, merge_col=1 if with_phase else None
    )


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


def check_key(data: dict, text: str) -> str:
    """Storage key for one tick: the deck (project and its files) plus the item's own text, so
    decks of the same project do not share ticks and reordering questions keeps them."""
    sources = sorted(s["path"] for s in data["sources"])
    deck = hashlib.sha1("|".join([data["project"]["name"], *sources]).encode("utf-8")).hexdigest()
    item = hashlib.sha1(text.encode("utf-8")).hexdigest()
    return f"exec-summary:{deck[:10]}:{item[:10]}"


def render_check(data: dict) -> list[Slide]:
    """The closing checklist. It is always built."""
    items: list[str] = []
    if data.get("goal"):
        items.append("The goal describes what I want.")
    if data.get("stories"):
        items.append("The user stories match what I want the system to do.")
    for checkpoint in data.get("checkpoints", []):
        items.append(f"{checkpoint['title']}: {'; '.join(checkpoint['items'])}")
    for question in data.get("open_questions", []):
        items.append(f"Open question: {question}")
    rows = "".join(
        "<li><label>"
        f'<input type="checkbox" data-key="{esc(check_key(data, text))}">'
        f"<span>{esc(text)}</span>"
        "</label></li>"
        for text in items
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


def build_slides(data: dict, images: list[dict] | None = None, left_out: int = 0) -> list[Slide]:
    slides: list[Slide] = []
    for builder in SLIDE_BUILDERS:
        if builder is render_screens:
            slides.extend(builder(data, images or [], left_out))
        else:
            slides.extend(builder(data))
    return slides


def render_deck(
    data: dict, project_dir: Path | None = None, design_dirs: list[str] | None = None
) -> str:
    """Render the deck. Design images come only from `design_dirs`, folders the user named,
    relative to `project_dir` (default: the current folder)."""
    errors = validate(data)
    if errors:
        raise InvalidSummary("\n".join(errors))
    images, left_out = [], 0
    if design_dirs:
        root = project_dir or Path.cwd()
        images, left_out, _ = find_design_images(root, design_dirs, MAX_IMAGE_BYTES)
    slides = build_slides(data, images, left_out)
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
    parser.add_argument(
        "--design-dir",
        action="append",
        default=[],
        help="folder of design images to embed (repeatable). Images are only used when named here.",
    )
    args = parser.parse_args(argv)

    data, problem = load_json(args.summary)
    if problem:
        print(problem, file=sys.stderr)
        return 1
    try:
        html = render_deck(data, project_dir=Path.cwd(), design_dirs=args.design_dir)
    except InvalidSummary as exc:
        print(exc, file=sys.stderr)
        return 1

    sources = [s["path"] for s in data["sources"]]
    links, problem = read_links(LINKS_FILE)
    if problem:
        print(problem, file=sys.stderr)
        return 1
    try:
        out = pick_output(sources, links, args.out, exists=Path.exists)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    protected = [Path(args.summary), *(Path(s["path"]) for s in data["sources"])]
    problems = check_out_path(out, protected)
    if args.out:
        taken = check_out_free(links, out, sources)
        problems += [taken] if taken else []
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1

    if args.design_dir:
        images, left_out, ignored = find_design_images(Path.cwd(), args.design_dir, MAX_IMAGE_BYTES)
        for image in images:
            print(f"design image embedded: {image['file']} (not checked for personal data)")
        for note in ignored:
            print(f"design image ignored: {note}", file=sys.stderr)
        if left_out:
            print(f"design images left out for size: {left_out}", file=sys.stderr)
    simple = output_path(sources)
    if not args.out and out != simple:
        print(
            f"note: {simple} already exists or belongs to other inputs; "
            f"wrote the deck to {out} instead",
            file=sys.stderr,
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8", newline="\n")
    problem = register_deck(LINKS_FILE, out, sources)
    if problem:
        print(f"deck written to {out} but not recorded in links.json: {problem}", file=sys.stderr)
        print(out)
        return 1
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
