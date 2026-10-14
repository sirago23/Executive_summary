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


def test_a_phase_title_is_never_cut_off_from_its_tasks(data):
    html = render.render_deck(with_plan(data, (3, 4, 3, 4, 3)))
    for slide in tasks_slides(html):
        body = slide.split("</h2>", 1)[1]
        assert body.startswith("<h3>"), "a tasks slide must open with a phase title"
        for block in body.split("<h3>")[1:]:
            assert "<td>" in block, "every phase title has task rows under it"


def test_a_phase_with_many_tasks_continues_with_its_title_repeated(data):
    html = render.render_deck(with_plan(data, (12,)))
    assert html.count("Phase 1 title (continued)") == 1
    assert all(f"Task 1.{t} title" in html for t in range(1, 13))


def test_checkpoints_slide_lists_what_you_approve(data):
    html = render.render_deck(with_plan(data))
    assert "Review the look." in html and "Checkpoint A" in html


def test_risk_impact_is_text_as_well_as_color(data):
    html = render.render_deck(with_plan(data))
    assert '<span class="impact impact-high">High</span>' in html
    assert '<span class="impact impact-low">Low</span>' in html


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
    assert (
        "I want to upload a bank slip image and get a filled-in record I can confirm in one click."
        in html
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
