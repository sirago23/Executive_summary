"""The two Billing Record sample decks: validate, check coverage, render, write to .tmp/sample/."""

import json
import re
from pathlib import Path

import check_coverage
import pytest
import render
import validate

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures" / "billing"
OUT = ROOT / ".tmp" / "sample"

SPEC = "sample/SPEC_sample.md"
PLAN = "sample/plan_sample.md"
TODO = "sample/todo_sample.md"

CASES = {
    "spec": [SPEC],
    "full": [SPEC, PLAN, TODO],
}
PLAN_SLIDES = {"phases", "tasks", "tasks-2", "tasks-3", "checkpoints", "risks"}


@pytest.fixture(autouse=True)
def in_project_root(monkeypatch):
    """Source paths in the fixtures are relative to the project root."""
    monkeypatch.chdir(ROOT)


def load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def build(name: str) -> tuple[dict, str]:
    data = load(name)
    html = render.render_deck(data)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.html").write_text(html, encoding="utf-8", newline="\n")
    return data, html


def slide_ids(html: str) -> list[str]:
    return re.findall(r'<section class="slide" id="s-([^"]+)"', html)


@pytest.mark.parametrize("name", CASES)
def test_fixture_passes_validate(name):
    assert validate.validate(load(name)) == []


@pytest.mark.parametrize("name", CASES)
def test_fixture_passes_coverage_against_the_sample_files(name):
    assert check_coverage.check(load(name), CASES[name]) == []


@pytest.mark.parametrize("name", CASES)
def test_deck_is_under_two_megabytes(name):
    _, html = build(name)
    assert len(html.encode("utf-8")) < 2 * 1024 * 1024


def test_spec_only_deck_has_no_plan_slides():
    _, html = build("spec")
    ids = set(slide_ids(html))
    assert not ids & PLAN_SLIDES
    for wanted in ["goal", "stories", "criteria", "screens", "architecture", "flow", "data"]:
        assert wanted in ids
    for wanted in ["stack", "rules", "success"]:
        assert wanted in ids


def test_spec_only_deck_shows_all_seven_stories_with_criteria():
    data, html = build("spec")
    assert len(data["stories"]) == 7
    for story in data["stories"]:
        assert story["id"] in html
        for criterion in story["criteria"]:
            assert render.esc(criterion) in html


def test_full_deck_has_everything_the_spec_asks_for():
    data, html = build("full")
    assert len(data["stories"]) == 7
    assert len(data["phases"]) == 5
    assert sum(len(p["tasks"]) for p in data["phases"]) == 17
    assert len(data["checkpoints"]) == 5
    assert len(data["diagrams"]) == 2
    assert len(data["screens"]) >= 2
    ids = set(slide_ids(html))
    assert {"phases", "tasks", "checkpoints", "risks", "architecture", "flow"} <= ids
    for phase in data["phases"]:
        assert render.esc(phase["title"]) in html
        for task in phase["tasks"]:
            assert render.esc(task["title"]) in html
    assert html.count("Example layout, not the final design") >= 2


def test_full_deck_lists_all_three_files_on_the_title_slide():
    _, html = build("full")
    for path in CASES["full"]:
        assert path in html


def test_decks_show_other_notes_for_sections_that_fit_no_slide():
    data, html = build("spec")
    assert any("Runtime and access" in n["src"] for n in data["notes"])
    for note in data["notes"]:
        assert render.esc(note["title"]) in html
        for line in note["text"]:
            assert render.esc(line) in html


def test_full_deck_check_slide_lists_every_checkpoint():
    data, html = build("full")
    check = html.split('id="s-check"')[1]
    for checkpoint in data["checkpoints"]:
        assert render.esc(checkpoint["title"]) in check


def test_spec_only_and_full_decks_do_not_share_tick_keys():
    spec_keys = set(re.findall(r'data-key="([^"]+)"', build("spec")[1]))
    full_keys = set(re.findall(r'data-key="([^"]+)"', build("full")[1]))
    assert spec_keys and full_keys and not spec_keys & full_keys
