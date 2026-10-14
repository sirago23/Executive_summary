import copy
import json
import re
import subprocess
import sys
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
