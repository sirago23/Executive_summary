import copy
import itertools
import json
import re
import subprocess
import sys
from html import unescape
from pathlib import Path

import pytest
import render
import validate

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "minimal.json"
SCRIPT = ROOT / "skill" / "exec-summary" / "scripts" / "render.py"


@pytest.fixture
def data() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def slide_ids(html: str) -> list[str]:
    return re.findall(r'<section class="slide" id="s-([^"]+)"', html)


def test_minimal_deck_has_the_four_slides(data):
    html = render.render_deck(data)
    assert slide_ids(html) == ["title", "goal", "stories", "check"]
    assert "Billing Record" in html
    assert "upload a bank slip image" in html
    assert "SPEC.md" in html


def test_title_slide_lists_the_files_covered(data):
    html = render.render_deck(data)
    assert "2026-10-14" in html
    assert "goal, stories" in html


def title_slide(html: str) -> str:
    return html.split('id="s-title"')[1].split("</section>")[0]


def tiles(html: str) -> list[tuple[str, str]]:
    """(number, label) of every key-number tile on the title slide."""
    return re.findall(
        r'<div class="stat"><b>(\d+)</b><span>([^<]+)</span></div>', title_slide(html)
    )


def test_title_slide_has_a_status_pill_a_name_and_a_tagline(data):
    data["project"]["status"] = "Draft"
    slide = title_slide(render.render_deck(data))
    assert '<span class="pill">Executive summary · Draft</span>' in slide
    assert "<h1>Billing Record</h1>" in slide
    assert 'class="tagline"' in slide


def test_title_pill_has_no_dangling_separator_without_a_status(data):
    data["project"].pop("status", None)
    assert '<span class="pill">Executive summary</span>' in title_slide(render.render_deck(data))


def test_full_deck_tiles_show_stories_phases_tasks_and_checkpoints(data):
    with_tables(data)
    with_plan(data, (3, 4, 3, 4, 3))
    assert tiles(render.render_deck(data)) == [
        (str(len(data["stories"])), "user stories"),
        ("5", "delivery phases"),
        ("17", "tasks"),
        ("1", "checkpoint you approve"),
    ]


def test_spec_only_deck_shows_no_phase_or_task_tile(data):
    with_tables(data)
    data["open_questions"] = ["One?", "Two?"]
    result = tiles(render.render_deck(data))
    assert [label for _, label in result] == [
        "user stories",
        "acceptance criteria",
        "questions for you",
    ]
    assert dict((label, n) for n, label in result)["acceptance criteria"] == "3"


def test_a_count_of_zero_gets_no_tile(data):
    data["stories"] = []
    data["open_questions"] = []
    assert tiles(render.render_deck(data)) == []
    assert 'class="stats"' not in title_slide(render.render_deck(data))


def test_no_more_than_four_tiles_are_shown(data):
    with_tables(data)
    with_plan(data)
    assert len(tiles(render.render_deck(data))) == 4


def test_tile_labels_use_the_singular_for_one(data):
    data["stories"] = data["stories"][:1]
    assert ("1", "user story") in tiles(render.render_deck(data))


def test_the_tiles_are_counted_from_the_data_not_typed(data):
    with_plan(data, (2, 2))
    first = tiles(render.render_deck(data))
    data["phases"][0]["tasks"].append(dict(data["phases"][0]["tasks"][0], id="T1.9"))
    second = tiles(render.render_deck(data))
    assert dict((label, n) for n, label in first)["tasks"] == "4"
    assert dict((label, n) for n, label in second)["tasks"] == "5"


def test_title_footer_lists_each_file_with_its_date_and_contents(data):
    footer = title_slide(render.render_deck(data)).split('<footer class="by">')[1]
    assert '<span class="path">' in footer
    assert "2026-10-14" in footer and "goal, stories" in footer


def test_title_status_date_and_file_fields_are_escaped(data):
    evil = "<img src=x onerror=y>"
    data["project"]["status"] = evil
    data["project"]["date"] = evil
    data["sources"][0]["modified"] = evil
    data["sources"][0]["found"] = [evil]
    assert "<img src=x" not in render.render_deck(data)


def test_absent_sections_drop_their_slides_without_a_warning(data):
    del data["goal"]
    del data["stories"]
    html = render.render_deck(data)
    assert slide_ids(html) == ["title", "check"]
    assert "missing" not in html.lower()


def test_check_slide_always_exists_and_lists_open_questions(data):
    html = render.render_deck(data)
    assert "Which currencies do you use" in html
    assert html.count('type="checkbox"') >= 3
    del data["open_questions"]
    assert "check" in slide_ids(render.render_deck(data))


def test_many_stories_continue_on_more_slides(data):
    base = data["stories"][0]
    data["stories"] = [dict(base, id=f"S{i}") for i in range(14)]
    html = render.render_deck(data)
    assert slide_ids(html) == ["title", "goal", "stories", "stories-2", "stories-3", "check"]
    assert "(continued)" in html


def test_every_text_field_is_escaped(data):
    evil = "<script>alert(1)</script> & <img src=x onerror=y>"
    data["project"]["name"] = evil
    data["project"]["tagline"] = evil
    data["goal"]["text"] = [evil]
    data["stories"][0]["want"] = evil
    data["open_questions"] = [evil]
    data["sources"][0]["found"] = [evil]
    html = render.render_deck(data)
    assert "<script>alert(1)" not in html
    assert "<img src=x" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt; &amp;" in html


def test_deck_is_one_self_contained_file(data):
    html = render.render_deck(data)
    assert "<link" not in html
    assert 'src="http' not in html
    assert "<style>" in html and "<script>" in html


def test_dark_mode_is_a_labelled_switch(data):
    html = render.render_deck(data)
    assert 'role="switch"' in html
    assert 'aria-checked="false"' in html
    assert "Dark mode" in html


def test_invalid_data_is_refused(data):
    del data["project"]
    with pytest.raises(render.InvalidSummary) as exc:
        render.render_deck(data)
    assert "project: missing required field" in str(exc.value)


def run_cli(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=cwd
    )


def test_cli_writes_to_the_default_name(tmp_path):
    r = run_cli(tmp_path, str(FIXTURE))
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "docs" / "exec-summary" / "SPEC.html").is_file()


def test_cli_name_follows_the_sources(tmp_path, data):
    data["sources"].append({"path": "tasks/plan.md"})
    summary = tmp_path / "s.json"
    summary.write_text(json.dumps(data), encoding="utf-8")
    r = run_cli(tmp_path, str(summary))
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "docs" / "exec-summary" / "SPEC+plan.html").is_file()


def test_cli_out_wins(tmp_path):
    r = run_cli(tmp_path, str(FIXTURE), "--out", "build/deck.html")
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "build" / "deck.html").is_file()
    assert not (tmp_path / "docs" / "exec-summary" / "SPEC.html").exists()
    links = json.loads((tmp_path / "docs/exec-summary/links.json").read_text(encoding="utf-8"))
    assert list(links) == ["build/deck.html"]  # a custom output is recorded too


def test_cli_refuses_invalid_summary_and_writes_nothing(tmp_path, data):
    del data["project"]
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(data), encoding="utf-8")
    r = run_cli(tmp_path, str(bad))
    assert r.returncode == 1
    assert "project: missing required field" in r.stderr
    assert not (tmp_path / "docs").exists()


def test_render_does_not_modify_input(data):
    before = copy.deepcopy(data)
    render.render_deck(data)
    assert data == before


# --- Task 5: table slides -------------------------------------------------------------------


SRC = "SPEC.md > User stories"


def with_tables(data: dict) -> dict:
    data["stories"][0]["criteria"] = ["The record is saved.", "The total matches the slip."]
    data["stories"][1]["criteria"] = ["The CSV opens in Excel."]
    data["data"] = [
        {
            "name": "Record",
            "plain": "One income or expense.",
            "fields": ["date", "amount"],
            "src": SRC,
        }
    ]
    data["stack"] = [
        {"part": "Storage", "choice": "SQLite", "plain": "A database in one file.", "src": SRC}
    ]
    data["rules"] = {
        "always": ["Run the tests."],
        "ask_first": ["Add a package."],
        "never": ["Delete a record without asking."],
        "src": SRC,
    }
    data["decisions"] = [{"text": "One user only.", "src": SRC}]
    data["out_of_scope"] = [{"text": "Multiple currencies.", "src": SRC}]
    data["success"] = [{"text": "A record takes under 30 seconds.", "phase": "Phase 1", "src": SRC}]
    data["notes"] = [{"title": "Backups", "text": ["Copy the file weekly."], "src": SRC}]
    return data


def test_table_slides_render_in_catalog_order(data):
    html = render.render_deck(with_tables(data))
    assert slide_ids(html) == [
        "title",
        "goal",
        "stories",
        "criteria",
        "data",
        "stack",
        "rules",
        "decisions",
        "out-of-scope",
        "success",
        "notes",
        "check",
    ]


def test_each_table_slide_shows_its_content_and_source(data):
    html = render.render_deck(with_tables(data))
    for text in [
        "The total matches the slip.",
        "One income or expense.",
        "A database in one file.",
        "Run the tests.",
        "Add a package.",
        "Delete a record without asking.",
        "One user only.",
        "Multiple currencies.",
        "A record takes under 30 seconds.",
        "Copy the file weekly.",
    ]:
        assert text in html
    assert (
        html.count("Source: SPEC.md &gt; User stories")
        + html.count('<td class="src">SPEC.md &gt; User stories')
        >= 9
    )


def test_table_slides_are_dropped_when_their_section_is_absent(data):
    html = render.render_deck(data)
    for sid in ["criteria", "data", "stack", "rules", "decisions", "out-of-scope", "success"]:
        assert sid not in slide_ids(html)
    assert "notes" not in slide_ids(html)


def test_a_story_without_criteria_adds_no_criteria_row(data):
    data["stories"][0]["criteria"] = ["Only one."]
    html = render.render_deck(data)
    assert slide_ids(html).count("criteria") == 1
    assert html.count("Only one.") == 1


def test_twenty_rows_split_into_three_slides_with_continued_titles(data):
    data["stories"][0]["criteria"] = [f"Criterion {i}" for i in range(20)]
    html = render.render_deck(data)
    ids = slide_ids(html)
    assert [i for i in ids if i.startswith("criteria")] == ["criteria", "criteria-2", "criteria-3"]
    assert html.count("(continued)") >= 2
    assert "Criterion 19" in html


def test_notes_get_one_slide_each(data):
    data["notes"] = [
        {"title": "First", "text": ["a"], "src": SRC},
        {"title": "Second", "text": ["b"], "src": SRC},
    ]
    ids = slide_ids(render.render_deck(data))
    assert ids[-3:] == ["notes", "notes-2", "check"]


def test_table_fields_are_escaped(data):
    evil = "<script>alert(1)</script>"
    with_tables(data)
    data["stack"][0]["plain"] = evil
    data["rules"]["never"] = [evil]
    data["out_of_scope"][0]["text"] = evil
    data["notes"][0]["title"] = evil
    data["stories"][0]["criteria"] = [evil]
    html = render.render_deck(data)
    assert "<script>alert(1)" not in html
    assert html.count("&lt;script&gt;alert(1)&lt;/script&gt;") >= 5


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        ("stack.0.plain", None, "stack[0].plain: missing required field"),
        ("rules.extra", "x", "rules.extra: unknown field"),
        ("out_of_scope.0.src", "OTHER.md > A", "out_of_scope[0].src"),
        ("success.0.text", 5, "success[0].text: expected string, got integer"),
    ],
)
def test_validation_catches_bad_table_data(data, path, value, message):
    with_tables(data)
    keys = path.split(".")
    target = data
    for key in keys[:-1]:
        target = target[int(key)] if key.isdigit() else target[key]
    last = int(keys[-1]) if keys[-1].isdigit() else keys[-1]
    if value is None:
        del target[last]
    else:
        target[last] = value
    with pytest.raises(render.InvalidSummary) as exc:
        render.render_deck(data)
    assert message in str(exc.value)


# --- Task 6: diagram slides -----------------------------------------------------------------

MERMAID_URL = "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"


def with_diagrams(data: dict) -> dict:
    data["diagrams"] = [
        {
            "id": "arch",
            "kind": "architecture",
            "title": "How it fits together",
            "nodes": [
                {"id": "app", "label": "The app", "group": "Your computer"},
                {"id": "db", "label": "Your records", "group": "Your computer"},
            ],
            "edges": [{"from": "app", "to": "db", "label": "saves"}],
            "src": SRC,
        },
        {
            "id": "flow",
            "kind": "flow",
            "title": "Adding a record",
            "nodes": [{"id": "up", "label": "Upload a photo"}, {"id": "ok", "label": "Confirm"}],
            "edges": [{"from": "up", "to": "ok"}],
            "src": SRC,
        },
    ]
    return data


def test_diagram_slides_come_after_screens_and_before_data(data):
    with_tables(data)
    with_diagrams(data)
    ids = slide_ids(render.render_deck(data))
    assert ids.index("architecture") < ids.index("flow") < ids.index("data")
    assert ids.index("criteria") < ids.index("architecture")


def test_diagram_is_drawn_from_nodes_and_edges_never_raw_mermaid(data):
    html = render.render_deck(with_diagrams(data))
    assert '<pre class="mermaid">flowchart TB' in html
    assert "subgraph g_1" in html
    assert 'n_app -->|"saves"| n_db' in unescape(html)


def test_every_diagram_has_a_table_fallback(data):
    html = render.render_deck(with_diagrams(data))
    assert html.count('class="diagram-fallback" hidden') == 2
    assert "<th>From</th><th>To</th>" in html
    assert "Upload a photo" in html and "saves" in html


def test_mermaid_loads_only_from_the_pinned_url_and_only_with_diagrams(data):
    assert "mermaid@" not in render.render_deck(data)
    html = render.render_deck(with_diagrams(data))
    assert html.count(MERMAID_URL) == 1
    assert 'integrity="sha384-' in html
    assert re.findall(r'<script[^>]+src="([^"]+)"', html) == [MERMAID_URL]


def test_two_architecture_diagrams_get_numbered_slides(data):
    with_diagrams(data)
    data["diagrams"].append(dict(data["diagrams"][0], id="arch2", title="Second"))
    ids = slide_ids(render.render_deck(data))
    assert ids.count("architecture") == 1 and "architecture-2" in ids


def test_diagram_text_is_escaped_in_html_and_mermaid(data):
    evil = '<script>alert(1)</script> "q"'
    with_diagrams(data)
    d = data["diagrams"][0]
    d["title"] = evil
    d["nodes"][0]["label"] = evil
    d["nodes"][0]["group"] = evil
    d["edges"][0]["label"] = evil
    html = render.render_deck(data)
    assert "<script>alert(1)" not in html
    assert "#lt;script#gt;" in html


def test_diagrams_are_dropped_when_absent(data):
    ids = slide_ids(render.render_deck(data))
    assert "architecture" not in ids and "flow" not in ids


# --- Task 7: screen slides ------------------------------------------------------------------

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7\x9a\xa0\xa0"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def with_screens(data: dict) -> dict:
    data["screens"] = [
        {
            "title": "Home",
            "blocks": [
                {"type": "header", "label": "Billing Record"},
                {"type": "stats", "label": "Money in, Money out"},
                {"type": "button", "label": "Add a record"},
            ],
            "src": SRC,
        },
        {"title": "Add record", "blocks": [{"type": "form", "label": "Amount, Date"}]},
    ]
    return data


def test_screens_slide_sits_between_criteria_and_architecture(data):
    with_tables(data)
    with_diagrams(data)
    with_screens(data)
    ids = slide_ids(render.render_deck(data))
    assert ids.index("criteria") < ids.index("screens") < ids.index("architecture")


def test_wireframes_show_with_an_example_label_and_two_fit_one_slide(data):
    html = render.render_deck(with_screens(data))
    assert slide_ids(html).count("screens") == 1
    assert html.count("Example layout, not the final design") == 2
    assert "Add a record" in html and "Money out" in html


def test_more_than_two_screens_continue_on_another_slide(data):
    with_screens(data)
    data["screens"] += [dict(data["screens"][1], title=f"S{i}") for i in range(3)]
    ids = slide_ids(render.render_deck(data))
    assert [i for i in ids if i.startswith("screens")] == ["screens", "screens-2", "screens-3"]


def test_unknown_block_type_fails_validation(data):
    with_screens(data)
    data["screens"][0]["blocks"][0]["type"] = "video"
    with pytest.raises(render.InvalidSummary) as exc:
        render.render_deck(data)
    assert "screens[0].blocks[0].type: must be one of" in str(exc.value)


def test_no_screens_and_no_design_dirs_means_no_slide(data, tmp_path):
    assert "screens" not in slide_ids(render.render_deck(data, project_dir=tmp_path))


def make_design(tmp_path: Path, folder: str = "design", names=("home.png", "add.png")) -> Path:
    (tmp_path / folder).mkdir(parents=True)
    for name in names:
        (tmp_path / folder / name).write_bytes(PNG)
    return tmp_path


def deck_with_design(data: dict, tmp_path: Path, folders=("design",)) -> str:
    return render.render_deck(data, project_dir=tmp_path, design_dirs=list(folders))


def test_a_design_folder_is_not_read_unless_the_user_names_it(data, tmp_path):
    make_design(tmp_path)
    html = render.render_deck(with_screens(data), project_dir=tmp_path)
    assert "data:image" not in html
    assert html.count("Example layout, not the final design") == 2


@pytest.mark.parametrize("folder", ["design", "docs/design", "mockups"])
def test_design_images_replace_wireframes(data, tmp_path, folder):
    make_design(tmp_path, folder)
    html = deck_with_design(with_screens(data), tmp_path, [folder])
    assert html.count("data:image/png;base64,") == 2
    assert "Example layout" not in html
    assert "screens" in slide_ids(html)


def test_design_images_make_a_slide_even_without_screens(data, tmp_path):
    make_design(tmp_path)
    assert "screens" in slide_ids(deck_with_design(data, tmp_path))


def test_other_file_types_in_the_design_folder_are_ignored(data, tmp_path):
    make_design(tmp_path, names=("notes.txt", "run.exe", "home.png"))
    assert deck_with_design(data, tmp_path).count("data:image/png;base64,") == 1


def test_a_file_that_is_not_really_an_image_is_not_embedded(data, tmp_path):
    make_design(tmp_path, names=("home.png",))
    (tmp_path / "design" / "fake.png").write_text("password=hunter2", encoding="utf-8")
    (tmp_path / "design" / "fake.jpg").write_text("password=hunter2", encoding="utf-8")
    (tmp_path / "design" / "fake.webp").write_bytes(b"RIFF....nope")
    html = deck_with_design(data, tmp_path)
    assert html.count("data:image/") == 1
    assert "aHVudGVy" not in html  # base64 of "hunter"


def test_real_jpeg_and_webp_are_embedded(data, tmp_path):
    (tmp_path / "design").mkdir()
    (tmp_path / "design" / "a.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"0" * 10)
    (tmp_path / "design" / "b.webp").write_bytes(b"RIFF\x00\x00\x00\x00WEBPVP8 ")
    html = deck_with_design(data, tmp_path)
    assert "data:image/jpeg;base64," in html and "data:image/webp;base64," in html


SAFE_SVG = '<svg xmlns="http://www.w3.org/2000/svg"><rect width="4" height="4"/></svg>'


def test_a_plain_svg_is_embedded_as_an_image_only(data, tmp_path):
    (tmp_path / "design").mkdir()
    (tmp_path / "design" / "logo.svg").write_text(SAFE_SVG, encoding="utf-8")
    html = deck_with_design(data, tmp_path)
    assert "data:image/svg+xml;base64," in html
    assert "<svg" not in html
    assert "<img " in html


@pytest.mark.parametrize(
    "svg",
    [
        '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>',
        '<svg xmlns="http://www.w3.org/2000/svg"><foreignObject/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:x="http://www.w3.org/1999/xlink">'
        '<image x:href="http://evil.example/a.png"/></svg>',
        '<!DOCTYPE svg [<!ENTITY a "aaaa">]><svg xmlns="http://www.w3.org/2000/svg">&a;</svg>',
        "<svg",
    ],
)
def test_an_unsafe_svg_is_not_embedded(data, tmp_path, svg):
    (tmp_path / "design").mkdir()
    (tmp_path / "design" / "bad.svg").write_text(svg, encoding="utf-8")
    assert "data:image" not in deck_with_design(data, tmp_path)


def test_images_over_the_size_limit_are_left_out_with_a_note(data, tmp_path, monkeypatch):
    make_design(tmp_path, names=("a.png", "b.png", "c.png"))
    monkeypatch.setattr(render, "MAX_IMAGE_BYTES", len(PNG) * 2)
    html = deck_with_design(data, tmp_path)
    assert html.count("data:image/png;base64,") == 2
    assert "1 more image was left out" in html


def link_dir(link: Path, target: Path) -> bool:
    """Make `link` point at `target`. False when this machine does not allow links."""
    try:
        link.symlink_to(target, target_is_directory=True)
        return True
    except OSError:
        made = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True, check=False
        )
        return made.returncode == 0


def test_design_folders_cannot_leave_the_project_folder(data, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.png").write_bytes(PNG)
    project = tmp_path / "project"
    project.mkdir()
    if not link_dir(project / "design", outside):
        pytest.skip("cannot link folders here")
    assert "data:image" not in deck_with_design(data, project)
    assert "data:image" not in deck_with_design(data, project, [str(outside)])
    assert "data:image" not in deck_with_design(data, project, ["../outside"])


def test_a_link_to_a_file_inside_the_project_is_not_embedded(data, tmp_path, monkeypatch):
    make_design(tmp_path, names=("home.png", "linked.png"))  # linked.png stands in for a link
    monkeypatch.setattr(Path, "is_symlink", lambda self: self.name == "linked.png")
    assert deck_with_design(data, tmp_path).count("data:image/png;base64,") == 1


def test_image_captions_do_not_reveal_file_names_or_paths(data, tmp_path):
    (tmp_path / "design").mkdir()
    (tmp_path / "design" / "john_smith_account.png").write_bytes(PNG)
    html = deck_with_design(data, tmp_path)
    assert 'alt="Design image 1"' in html
    assert "john_smith" not in html
    assert str(tmp_path) not in html


def deck_json(tmp_path: Path, data: dict) -> str:
    path = tmp_path / "summary.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path.name


def test_cli_lists_embedded_images_and_ignored_files(data, tmp_path):
    make_design(tmp_path, names=("home.png",))
    (tmp_path / "design" / "fake.png").write_text("nope", encoding="utf-8")
    result = run_cli(tmp_path, deck_json(tmp_path, data), "--design-dir", "design")
    assert result.returncode == 0, result.stderr
    assert "design image embedded: home.png" in result.stdout
    assert "fake.png" in result.stderr


def test_cli_without_design_dir_embeds_nothing(data, tmp_path):
    make_design(tmp_path)
    result = run_cli(tmp_path, deck_json(tmp_path, data))
    assert result.returncode == 0, result.stderr
    assert "design image" not in result.stdout


@pytest.mark.parametrize("target", ["SPEC.md", "summary.json", "deck.txt", "notes"])
def test_cli_refuses_an_out_path_that_is_an_input_or_not_html(data, tmp_path, target):
    (tmp_path / "SPEC.md").write_text("# keep me\n", encoding="utf-8")
    name = deck_json(tmp_path, data)
    before = (tmp_path / "SPEC.md").read_text(encoding="utf-8")
    result = run_cli(tmp_path, name, "--out", target)
    assert result.returncode == 1
    assert "--out" in result.stderr
    assert (tmp_path / "SPEC.md").read_text(encoding="utf-8") == before
    assert not (tmp_path / "deck.txt").exists() and not (tmp_path / "notes").exists()


def test_cli_hostile_json_gives_a_message_not_a_traceback(tmp_path):
    (tmp_path / "deep.json").write_text("[" * 100000, encoding="utf-8")
    result = run_cli(tmp_path, "deep.json")
    assert result.returncode == 1
    assert "Traceback" not in result.stderr and "invalid JSON" in result.stderr


def test_the_mermaid_url_and_its_hash_change_together():
    """Bumping the Mermaid version needs a new SRI hash. This fails until both are reviewed."""
    assert render.MERMAID_URL == "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"
    assert (
        render.MERMAID_SRI
        == "sha384-rbtjAdnIQE/aQJGEgXrVUlMibdfTSa4PQju4HDhN3sR2PmaKFzhEafuePsl9H/9I"
    )


def test_the_deck_has_a_content_security_policy_that_only_allows_the_pinned_cdn(data):
    html = render.render_deck(data)
    policy = re.search(r'Content-Security-Policy" content="([^"]+)"', html).group(1)
    assert "default-src 'none'" in policy
    assert "https://cdn.jsdelivr.net" in policy
    assert "connect-src" not in policy and "'unsafe-eval'" not in policy


# --- Task 8: plan slides --------------------------------------------------------------------


def make_phases(counts: list[int]) -> list[dict]:
    phases = []
    for p, count in enumerate(counts, start=1):
        phases.append(
            {
                "id": f"P{p}",
                "title": f"Phase {p} title",
                "goal": f"Goal of phase {p}",
                "tasks": [
                    {
                        "id": f"T{p}.{t}",
                        "title": f"Task {p}.{t} title",
                        "you_will_see": f"What you see for {p}.{t}",
                        "src": SRC,
                    }
                    for t in range(1, count + 1)
                ],
                "src": SRC,
            }
        )
    return phases


def with_plan(data: dict, counts=(3, 4, 3, 4, 3)) -> dict:
    data["phases"] = make_phases(list(counts))
    data["checkpoints"] = [
        {
            "title": "Checkpoint A",
            "phase": "Phase 1 title",
            "items": ["Review the look."],
            "src": SRC,
        }
    ]
    data["risks"] = [
        {
            "risk": "Reading slips fails.",
            "impact": "High",
            "handling": "Confirm by hand.",
            "src": SRC,
        },
        {"risk": "Dates are wrong.", "impact": "Low", "handling": "Show the date.", "src": SRC},
    ]
    return data


def tasks_slides(html: str) -> list[str]:
    parts = re.split(r'(?=<section class="slide" id="s-)', html)
    return [p for p in parts if p.startswith('<section class="slide" id="s-tasks')]


def test_plan_slides_follow_the_stack_and_come_before_rules(data):
    with_tables(data)
    with_plan(data)
    ids = slide_ids(render.render_deck(data))
    assert ids.index("stack") < ids.index("phases") < ids.index("tasks")
    assert ids.index("tasks") < ids.index("checkpoints") < ids.index("risks") < ids.index("rules")


def test_phases_slide_is_a_step_strip_with_goals_and_sources(data):
    html = render.render_deck(with_plan(data))
    assert html.count('<li class="step">') == 5
    assert "Goal of phase 3" in html and "Phase 5 title" in html


def test_seventeen_tasks_in_five_phases_are_all_shown_and_split_over_slides(data):
    html = render.render_deck(with_plan(data, (3, 4, 3, 4, 3)))
    slides = tasks_slides(html)
    assert len(slides) >= 2
    for p, count in enumerate((3, 4, 3, 4, 3), start=1):
        for t in range(1, count + 1):
            assert f"Task {p}.{t} title" in html
            assert f"What you see for {p}.{t}" in html


def test_each_phase_is_a_step_card_with_its_id_in_a_pill(data):
    html = render.render_deck(with_plan(data))
    assert '<li class="step"><span class="id">P1</span><strong>Phase 1 title</strong>' in html
    assert html.count('<span class="id">P') == 5


def test_each_task_is_a_row_card_with_title_what_you_see_and_source(data):
    html = render.render_deck(with_plan(data, (3, 4, 3, 4, 3)))
    slides = "".join(tasks_slides(html))
    assert "<table" not in slides
    assert slides.count('<li class="task">') == 17
    first = slides.split('<li class="task">')[1]
    assert first.startswith("<strong>Task 1.1 title</strong>")
    assert '<span class="how">What you see for 1.1</span>' in first
    assert f'<span class="src">{SRC.replace(">", "&gt;")}</span>' in first


def test_no_tasks_slide_holds_more_rows_than_the_budget(data):
    html = render.render_deck(with_plan(data, (3, 4, 3, 4, 3, 12)))
    for slide in tasks_slides(html):
        rows = slide.count('<li class="task">') + slide.count("<h3>")
        assert rows <= render.TASK_SLIDE_BUDGET


def test_checkpoints_are_cards_with_their_items_as_a_short_list(data):
    html = render.render_deck(with_plan(data))
    slide = html.split('id="s-checkpoints"')[1].split("</section>")[0]
    assert "<table" not in slide
    card = slide.split('<div class="card">')[1]
    assert card.startswith("<h3>Checkpoint A</h3>")
    assert '<span class="as">Phase 1 title</span>' in card
    assert "<ul><li>Review the look.</li></ul>" in card
    assert 'class="src"' in card


def test_many_checkpoints_continue_on_more_slides_and_none_is_lost(data):
    with_plan(data)
    base = data["checkpoints"][0]
    data["checkpoints"] = [dict(base, title=f"Checkpoint {i}") for i in range(9)]
    html = render.render_deck(data)
    assert "checkpoints-2" in slide_ids(html) and "checkpoints-3" in slide_ids(html)
    for i in range(9):
        assert html.count(f"<h3>Checkpoint {i}</h3>") == 1


def test_a_phase_title_is_never_cut_off_from_its_tasks(data):
    html = render.render_deck(with_plan(data, (3, 4, 3, 4, 3)))
    for slide in tasks_slides(html):
        body = slide.split("</h2>", 1)[1]
        assert body.startswith("<h3>"), "a tasks slide must open with a phase title"
        for block in body.split("<h3>")[1:]:
            assert 'class="task"' in block, "every phase title has task rows under it"


def test_a_phase_with_many_tasks_continues_with_its_title_repeated(data):
    html = render.render_deck(with_plan(data, (12,)))
    blocks = -(-12 // render.TASKS_PER_BLOCK)  # ceiling: how many pieces the phase falls into
    assert blocks >= 2
    assert html.count("Phase 1 title (continued)") == blocks - 1
    assert all(f"Task 1.{t} title" in html for t in range(1, 13))


def test_checkpoints_slide_lists_what_you_approve(data):
    html = render.render_deck(with_plan(data))
    assert "Review the look." in html and "Checkpoint A" in html


def test_risk_impact_is_text_as_well_as_color(data):
    html = render.render_deck(with_plan(data))
    assert '<span class="impact impact-high">High</span>' in html
    assert '<span class="impact impact-low">Low</span>' in html


def risk_slides(html: str) -> list[str]:
    parts = re.split(r'(?=<section class="slide" id="s-)', html)
    return [p for p in parts if p.startswith('<section class="slide" id="s-risks')]


def test_a_story_is_a_card_with_an_id_pill_a_label_and_the_want_in_its_own_line(data):
    html = render.render_deck(data)
    story = data["stories"][0]
    card = re.search(r'<div class="card"><div class="row">.*?</div></div>', html, flags=re.S).group(
        0
    )
    assert f'<span class="id">{story["id"]}</span>' in card
    assert f'<span class="as">As {render.esc(story["as"].strip())}, I want</span>' in card
    assert "<p>to upload a bank slip image" in card
    assert 'class="src"' in card


def test_risks_are_row_cards_with_the_impact_word_first_and_no_table(data):
    html = render.render_deck(with_plan(data))
    slide = risk_slides(html)[0]
    assert "<table" not in slide
    assert slide.count('<li class="risk">') == 2
    first = slide.split('<li class="risk">')[1]
    assert first.startswith('<span class="impact impact-high">High</span>')
    assert "<strong>Reading slips fails.</strong>" in first
    assert '<span class="how">Confirm by hand.</span>' in first
    assert f'<span class="src">{SRC.replace(">", "&gt;")}</span>' in first


def test_many_risks_continue_on_more_slides_and_none_is_lost(data):
    with_plan(data)
    base = data["risks"][0]
    data["risks"] = [dict(base, risk=f"Risk number {i}.") for i in range(13)]
    html = render.render_deck(data)
    slides = risk_slides(html)
    assert len(slides) == 3
    assert "(continued)" in slides[1] and "(continued)" in slides[2]
    for i in range(13):
        assert html.count(f"Risk number {i}.") == 1


def test_risk_text_and_source_are_escaped_in_the_cards(data):
    evil = "<script>alert(1)</script>"
    with_plan(data)
    data["risks"][0]["risk"] = evil
    data["risks"][0]["handling"] = evil
    html = render.render_deck(data)
    assert "<script>alert(1)" not in html
    assert risk_slides(html)[0].count("&lt;script&gt;") == 2


def test_plan_slides_are_dropped_when_absent(data):
    ids = slide_ids(render.render_deck(data))
    for sid in ["phases", "tasks", "checkpoints", "risks"]:
        assert sid not in ids


def test_plan_fields_are_escaped(data):
    evil = "<script>alert(1)</script>"
    with_plan(data)
    data["phases"][0]["title"] = evil
    data["phases"][0]["goal"] = evil
    data["phases"][0]["tasks"][0]["you_will_see"] = evil
    data["checkpoints"][0]["items"] = [evil]
    data["risks"][0]["handling"] = evil
    html = render.render_deck(data)
    assert "<script>alert(1)" not in html
    assert html.count("&lt;script&gt;alert(1)&lt;/script&gt;") >= 5


@pytest.mark.parametrize(
    ("edit", "message"),
    [
        (lambda d: d["risks"][0].update(impact="Huge"), "risks[0].impact: must be one of"),
        (lambda d: d["phases"][0]["tasks"][0].pop("src"), "phases[0].tasks[0].src: missing"),
        (lambda d: d["phases"][0]["tasks"][0].update(src="X.md > A"), "phases[0].tasks[0].src"),
        (lambda d: d["checkpoints"][0].pop("items"), "checkpoints[0].items: missing"),
    ],
)
def test_plan_validation(data, edit, message):
    with_plan(data)
    edit(data)
    with pytest.raises(render.InvalidSummary) as exc:
        render.render_deck(data)
    assert message in str(exc.value)


# --- Task 9 prerequisites: optional "so", criteria_src --------------------------------------


def test_a_story_without_so_reads_as_a_plain_sentence(data):
    del data["stories"][0]["so"]
    html = render.render_deck(data)
    card = re.search(r'<div class="card">.*?</p>', html, flags=re.S).group(0)
    text = " ".join(re.sub(r"<[^>]+>", " ", card).split())  # what the reader sees
    assert (
        "I want to upload a bank slip image and get a filled-in record I can confirm in one click."
        in text
    )
    assert "so that None" not in html


def test_criteria_rows_use_criteria_src_when_given(data):
    data["stories"][0]["criteria"] = ["It works."]
    data["stories"][0]["criteria_src"] = "SPEC.md > Acceptance criteria"
    html = render.render_deck(data)
    assert '<td class="src">SPEC.md &gt; Acceptance criteria</td>' in html
    data["stories"][0]["criteria_src"] = "OTHER.md > Acceptance criteria"
    with pytest.raises(render.InvalidSummary) as exc:
        render.render_deck(data)
    assert "stories[0].criteria_src" in str(exc.value)


# --- review fixes: check slide, hostile input everywhere, print copy ---------------------------


def test_check_slide_lists_each_checkpoint_with_what_to_approve(data):
    html = render.render_deck(with_plan(data))
    check = html.split('id="s-check"')[1]
    assert "Checkpoint A: Review the look." in check


def test_tick_keys_are_scoped_to_the_deck_and_survive_reordering(data):
    pattern = r'data-key="([^"]+)"><span>([^<]+)</span>'
    data["open_questions"] = ["First?", "Second?"]
    first = {text: key for key, text in re.findall(pattern, render.render_deck(data))}
    data["open_questions"] = ["Second?", "First?"]
    again = {text: key for key, text in re.findall(pattern, render.render_deck(data))}
    assert again == first
    data["sources"].append({"path": "tasks/plan.md"})
    other = re.findall(r'data-key="([^"]+)"', render.render_deck(data))
    assert other and not set(other) & set(first.values())


def test_each_diagram_has_a_light_copy_for_printing(data):
    html = render.render_deck(with_diagrams(data))
    assert html.count('<div class="mermaid-print" aria-hidden="true"></div>') == 2


def test_the_only_external_script_is_the_pinned_mermaid_tag(data):
    html = render.render_deck(with_diagrams(data))
    assert re.findall(r'<script[^>]+src="([^"]+)"', html) == [MERMAID_URL]
    assert 'src="http' not in html.replace(MERMAID_URL, "")
    assert "<link" not in html


UNIQUE = itertools.count()
EVIL = "<script>alert(1)</script><img src=x onerror=y> & \" '"
KEEP = {"src", "criteria_src", "path", "kind", "type", "impact", "from", "to", "modified", "date"}


def make_hostile(value, key=None, parent=None):
    """Copy of `value` with every free-text string replaced by EVIL."""
    if isinstance(value, dict):
        return {k: make_hostile(v, k, value) for k, v in value.items()}
    if isinstance(value, list):
        return [make_hostile(v, key, parent) for v in value]
    if isinstance(value, str) and key not in KEEP:
        if key == "id":  # ids are short, and node ids must stay plain
            return value if parent is not None and "label" in parent else f'<b>{next(UNIQUE)}</b>&"'
        return EVIL
    return value


def test_hostile_text_in_every_field_is_escaped(data):
    with_tables(data)
    with_diagrams(data)
    with_screens(data)
    with_plan(data)
    data["open_questions"] = ["Which?"]
    hostile = make_hostile(data)
    assert validate.validate(hostile) == []
    html = render.render_deck(hostile)
    assert "<script>alert(1)" not in html
    assert "<img src=x" not in html
    assert html.count("&lt;script&gt;alert(1)&lt;/script&gt;") > 20
    assert len(re.findall(r"<script", html)) == 2  # the pinned Mermaid tag and deck.js


# --- criteria table groups rows by story --------------------------------------------------------


def test_a_story_is_written_once_for_all_of_its_criteria_rows(data):
    data["stories"][0]["criteria"] = ["One.", "Two.", "Three."]
    data["stories"][1]["criteria"] = ["Four."]
    html = render.render_deck(data)
    table = html.split('id="s-criteria"')[1].split("</section>")[0]
    story_one = render.esc("S1: " + data["stories"][0]["want"])
    assert table.count(story_one) == 1
    assert 'rowspan="3"' in table
    assert table.count("<tr") - 1 == 4  # header row plus one row per criterion
    for text in ["One.", "Two.", "Three.", "Four."]:
        assert text in table


def test_a_story_split_across_slides_is_repeated_at_the_top_of_the_next_one(data):
    data["stories"][0]["criteria"] = [f"Criterion {i}" for i in range(10)]
    html = render.render_deck(data)
    story_one = render.esc("S1: " + data["stories"][0]["want"])
    first = html.split('id="s-criteria"')[1].split("</section>")[0]
    second = html.split('id="s-criteria-2"')[1].split("</section>")[0]
    assert first.count(story_one) == 1 and 'rowspan="8"' in first
    assert second.count(story_one) == 1 and 'rowspan="2"' in second


def test_other_tables_are_not_merged(data):
    with_tables(data)
    html = render.render_deck(data)
    assert "rowspan" not in html.split('id="s-stack"')[1].split("</section>")[0]


def test_success_rows_of_the_same_phase_show_the_phase_once(data):
    data["success"] = [
        {"text": f"Goal {i}.", "phase": phase, "src": SRC}
        for i, phase in enumerate(["Phase 1", "Phase 1", "Phase 1", "Phase 2"])
    ]
    html = render.render_deck(data)
    table = html.split('id="s-success"')[1].split("</section>")[0]
    assert table.count("Phase 1") == 1 and 'rowspan="3"' in table
    assert table.count("Phase 2") == 1
    assert table.count("<tr") - 1 == 4
    for i in range(4):
        assert f"Goal {i}." in table


def test_success_without_phases_has_no_merged_cells(data):
    data["success"] = [{"text": "One.", "src": SRC}, {"text": "Two.", "src": SRC}]
    html = render.render_deck(data)
    assert "rowspan" not in html.split('id="s-success"')[1].split("</section>")[0]


# --- design rules the owner chose: content first, source quiet, width capped ---------------------


def css_rule(html: str, selector: str) -> str:
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", html)
    assert match, f"no CSS rule for {selector}"
    return match.group(1)


def test_every_table_with_sources_ends_with_a_quiet_source_column(data):
    with_tables(data)
    with_plan(data)
    html = render.render_deck(data)
    assert "<th>Source</th>" not in html
    sourced = [t for t in re.findall(r"<table.*?</table>", html, flags=re.S) if "Source" in t]
    assert len(sourced) >= 5
    for table in sourced:
        header = re.search(r"<thead>.*?</thead>", table, flags=re.S).group(0)
        assert header.endswith('<th class="src">Source</th></tr></thead>')
        assert 'class="src"' in table.split("<tbody>")[1]


def test_the_source_column_is_narrow_small_and_light(data):
    html = render.render_deck(data)
    rule = css_rule(html, "th.src,\ntd.src")
    assert int(re.search(r"width:\s*(\d+)%", rule).group(1)) <= 14
    assert float(re.search(r"font-size:\s*([\d.]+)rem", rule).group(1)) <= 0.75
    assert "font-weight: 400" in rule and "var(--muted)" in rule


def test_deck_width_and_text_sizes_stay_at_the_chosen_limits(data):
    html = render.render_deck(data)
    assert "max-width: 1280px" in css_rule(html, "#deck")
    assert "2.75rem)" in html and "1.375rem)" in html and "1.125rem)" in html


# --- links.json is kept up to date by the CLI ----------------------------------------------------


def summary_for(tmp_path: Path, data: dict, source: str, name: str) -> str:
    data["sources"] = [{"path": source}]
    for key in list(data):
        if key not in ("project", "sources", "skipped"):
            del data[key]
    data["skipped"] = []
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return name


def test_cli_registers_the_deck_in_links_json(tmp_path, data):
    name = summary_for(tmp_path, data, "docs/SPEC.md", "a.json")
    assert run_cli(tmp_path, name).returncode == 0
    links = json.loads((tmp_path / "docs/exec-summary/links.json").read_text(encoding="utf-8"))
    assert links == {"docs/exec-summary/SPEC.html": {"sources": ["docs/SPEC.md"], "url": None}}


def test_cli_gives_a_same_named_file_in_another_folder_its_own_deck_and_keeps_the_first(
    tmp_path, data
):
    first = summary_for(tmp_path, data, "docs/SPEC.md", "a.json")
    second = summary_for(tmp_path, data, "other/SPEC.md", "b.json")
    assert run_cli(tmp_path, first).returncode == 0
    assert run_cli(tmp_path, second).returncode == 0
    decks = tmp_path / "docs" / "exec-summary"
    assert (decks / "SPEC.html").is_file() and (decks / "other-SPEC.html").is_file()
    again = run_cli(tmp_path, first)  # the first deck is rebuilt in place, not renamed
    assert again.returncode == 0 and (decks / "SPEC.html").is_file()
    links = json.loads((decks / "links.json").read_text(encoding="utf-8"))
    assert set(links) == {"docs/exec-summary/SPEC.html", "docs/exec-summary/other-SPEC.html"}


def test_cli_stops_on_a_broken_links_file_and_writes_no_deck(tmp_path, data):
    name = summary_for(tmp_path, data, "SPEC.md", "a.json")
    folder = tmp_path / "docs" / "exec-summary"
    folder.mkdir(parents=True)
    (folder / "links.json").write_text("{broken", encoding="utf-8")
    result = run_cli(tmp_path, name)
    assert result.returncode == 1 and "links.json" in result.stderr
    assert not (folder / "SPEC.html").exists()
    assert (folder / "links.json").read_text(encoding="utf-8") == "{broken"


# --- review fixes: never overwrite another deck, tell the owner about a rename ---------------


def test_cli_does_not_overwrite_a_deck_that_is_not_in_links_json_and_says_why(tmp_path, data):
    folder = tmp_path / "docs" / "exec-summary"
    folder.mkdir(parents=True)
    (folder / "SPEC.html").write_text("MINE, made earlier", encoding="utf-8")
    name = summary_for(tmp_path, data, "other/SPEC.md", "b.json")
    result = run_cli(tmp_path, name)
    assert result.returncode == 0, result.stderr
    assert (folder / "SPEC.html").read_text(encoding="utf-8") == "MINE, made earlier"
    assert (folder / "other-SPEC.html").is_file()
    assert "SPEC.html" in result.stderr and "wrote" in result.stderr
    assert result.stdout.strip().endswith("other-SPEC.html")


def test_cli_out_onto_a_deck_of_other_inputs_is_refused_and_its_link_is_kept(tmp_path, data):
    first = summary_for(tmp_path, data, "docs/SPEC.md", "a.json")
    assert run_cli(tmp_path, first).returncode == 0
    links_file = tmp_path / "docs" / "exec-summary" / "links.json"
    links = json.loads(links_file.read_text(encoding="utf-8"))
    links["docs/exec-summary/SPEC.html"]["url"] = "https://claude.ai/artifact/AAA"
    links_file.write_text(json.dumps(links), encoding="utf-8")
    second = summary_for(tmp_path, data, "other/SPEC.md", "b.json")
    result = run_cli(tmp_path, second, "--out", "docs/exec-summary/SPEC.html")
    assert result.returncode == 1 and "already holds a deck" in result.stderr
    after = json.loads(links_file.read_text(encoding="utf-8"))
    assert after["docs/exec-summary/SPEC.html"]["url"] == "https://claude.ai/artifact/AAA"
    assert after["docs/exec-summary/SPEC.html"]["sources"] == ["docs/SPEC.md"]


def test_cli_still_prints_the_deck_path_when_links_json_cannot_be_saved(tmp_path, data):
    name = summary_for(tmp_path, data, "SPEC.md", "a.json")
    folder = tmp_path / "docs" / "exec-summary"
    folder.mkdir(parents=True)
    (folder / "links.json.lock").write_text("", encoding="utf-8")  # another run is writing
    result = run_cli(tmp_path, name)
    assert result.returncode == 1
    assert "SPEC.html" in result.stderr and "not recorded" in result.stderr
    assert (folder / "SPEC.html").is_file()


# --- Task 17b: text-only slides as launch stage (short) or split stage (long) ---


def note_slide(text: list[str], src: str = "plan.md > Overview", title: str = "Plan") -> str:
    ((_, _, inner),) = render.render_notes({"notes": [{"title": title, "text": text, "src": src}]})
    return inner


def test_a_short_note_is_a_launch_stage_with_eyebrow_title_rule_lines_and_source():
    inner = note_slide(["Run it on your PC.", "No login."], title="Phase 1")
    assert 'class="stage launch"' in inner
    assert '<span class="eyebrow">Overview</span>' in inner
    assert "<h2>Phase 1</h2>" in inner
    assert '<span class="rule"></span>' in inner
    assert '<div class="lines"><p>Run it on your PC.</p><p>No login.</p></div>' in inner
    assert inner.endswith('<p class="src">Source: plan.md &gt; Overview</p></div>')


def test_a_long_note_is_a_split_stage_with_a_panel_and_one_row_per_paragraph():
    pad = " " + "word " * 60
    inner = note_slide(["First part. More words here." + pad, "Second part."], title="Plan")
    assert 'class="stage split"' in inner
    assert '<div class="panel"><span class="eyebrow">Overview</span><h2>Plan</h2>' in inner
    assert (
        '<ul class="points"><li><span><strong>First part.</strong> More words here. word' in inner
    )
    assert "<li><span><strong>Second part.</strong></span></li>" in inner
    assert inner.count("<li>") == 2


def test_the_launch_threshold_is_280_characters_in_total():
    just_under = "x" * 279 + "."  # 280
    just_over = "x" * 280 + "."  # 281
    assert 'class="stage launch"' in note_slide([just_under])
    assert 'class="stage split"' in note_slide([just_over])
    assert 'class="stage launch"' in note_slide(["a" * 100, "b" * 100, "c" * 80])
    assert 'class="stage split"' in note_slide(["a" * 100, "b" * 100, "c" * 81])


@pytest.mark.parametrize(
    ("src", "eyebrow"),
    [
        ("a.md > Phase 1: Local", "Phase 1: Local"),
        ("a.md > Goal > Why", "Why"),
        ("a.md", None),
    ],
)
def test_the_eyebrow_is_the_part_of_the_source_after_the_last_arrow(src, eyebrow):
    inner = note_slide(["Short."], src=src)
    if eyebrow is None:
        assert "eyebrow" not in inner
    else:
        assert f'<span class="eyebrow">{eyebrow}</span>' in inner


def test_the_first_sentence_split_handles_one_sentence_and_abbreviations():
    one = note_slide(["x" * 300])
    assert f"<strong>{'x' * 300}</strong>" in one
    abbr = note_slide(["Use a tool, e.g. Task 2, first. Then wait." + " y" * 150])
    assert "<strong>Use a tool, e.g. Task 2, first.</strong> Then wait." in abbr


def test_the_goal_slide_uses_the_same_stages_and_keeps_its_id_and_title(data):
    html = render.render_deck(data)
    assert 'id="s-goal"' in html
    goal = html.split('id="s-goal"')[1].split("</section>")[0]
    assert 'class="stage launch"' in goal and "<h2>The goal</h2>" in goal
    data["goal"]["text"] = ["A long sentence. " * 12] * 2
    goal = render.render_deck(data).split('id="s-goal"')[1].split("</section>")[0]
    assert 'class="stage split"' in goal


def test_stage_text_is_escaped_in_both_styles():
    evil = "<script>alert(1)</script>"
    for text in ([evil], [evil + " x" * 200]):
        inner = note_slide(text, src=f"a.md > {evil}", title=evil)
        assert "<script>" not in inner
        assert inner.count("&lt;script&gt;") >= 3
