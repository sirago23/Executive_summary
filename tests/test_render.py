import copy
import json
import re
import subprocess
import sys
from html import unescape
from pathlib import Path

import pytest
import render

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
    assert not (tmp_path / "docs").exists()


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
