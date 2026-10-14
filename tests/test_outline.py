import json
import shutil
import subprocess
import sys
from pathlib import Path

import outline

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "sample"
SCRIPT = ROOT / "skill" / "exec-summary" / "scripts" / "outline.py"


def section(data: dict, heading: str) -> dict:
    matches = [s for s in data["sections"] if s["heading"] == heading]
    assert matches, f"no section {heading!r}"
    return matches[0]


def test_spec_sample_has_seven_user_stories():
    data = outline.outline_file(SAMPLE / "SPEC_sample.md")
    assert len(section(data, "User stories")["numbered_items"]) == 7


def test_todo_sample_has_17_tasks_and_checkpoints():
    data = outline.outline_file(SAMPLE / "todo_sample.md")
    tasks = [s for s in data["sections"] if s["is_task"]]
    checkpoints = [s for s in data["sections"] if s["is_checkpoint"]]
    assert len(tasks) == 17
    assert len(checkpoints) == 5
    assert tasks[0]["heading"] == "Task 1: Scaffold project and tooling"


def test_task_checkboxes_are_counted():
    data = outline.outline_file(SAMPLE / "todo_sample.md")
    task1 = section(data, "Task 1: Scaffold project and tooling")
    assert len(task1["checkboxes"]) == 5
    assert all(not c["checked"] for c in task1["checkboxes"])


def test_renamed_copy_gives_same_sections(tmp_path):
    copy = tmp_path / "docs" / "my-requirements.txt"
    copy.parent.mkdir()
    shutil.copy(SAMPLE / "SPEC_sample.md", copy)
    a = outline.outline_file(SAMPLE / "SPEC_sample.md")["sections"]
    b = outline.outline_file(copy)["sections"]
    assert a == b


def test_headings_inside_code_blocks_are_ignored():
    text = "# Title\n\n## Real\n\n```\n# comment\n## also comment\n```\n\n## Next\n"
    headings = [s["heading"] for s in outline.outline_text(text)]
    assert headings == ["Title", "Real", "Next"]


def test_tilde_fences_and_list_items_in_code_ignored():
    text = "## A\n\n~~~\n- not an item\n1. nor this\n~~~\n\n- real item\n"
    sec = outline.outline_text(text)[0]
    assert sec["list_items"] == ["real item"]
    assert sec["numbered_items"] == []


def test_lists_checkboxes_and_tables():
    text = (
        "## S\n\n- one\n* two\n  - nested\n1. first\n2) second\n"
        "- [ ] open\n- [x] done\n- [X] done too\n\n"
        "| a | b |\n|---|---|\n| 1 | 2 |\n\n| c |\n| - |\n| 3 |\n"
    )
    sec = outline.outline_text(text)[0]
    assert sec["list_items"] == ["one", "two", "nested"]
    assert sec["numbered_items"] == ["first", "second"]
    assert sec["checkboxes"] == [
        {"text": "open", "checked": False},
        {"text": "done", "checked": True},
        {"text": "done too", "checked": True},
    ]
    assert sec["tables"] == 2


def test_heading_text_strips_checkbox_prefix_and_hashes():
    text = "### - [ ] Task 3: Do it ##\n\n## Checkpoint A\n\n## Phase C: Insights\n"
    secs = outline.outline_text(text)
    assert secs[0]["heading"] == "Task 3: Do it"
    assert secs[0]["is_task"] is True
    assert secs[0]["level"] == 3
    assert secs[1]["is_checkpoint"] is True
    assert secs[2]["is_task"] is False and secs[2]["is_checkpoint"] is False


def test_line_numbers_are_one_based():
    secs = outline.outline_text("intro\n\n## First\n\ntext\n## Second\n")
    assert [s["line"] for s in secs] == [3, 6]


def test_text_before_first_heading_is_ignored():
    assert outline.outline_text("- orphan item\n\nplain\n") == []


def test_cli_prints_json_for_several_files():
    spec, todo = str(SAMPLE / "SPEC_sample.md"), str(SAMPLE / "todo_sample.md")
    r = subprocess.run([sys.executable, str(SCRIPT), spec, todo], capture_output=True, text=True)
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert [f["path"] for f in out["files"]] == [spec, todo]
    assert out["files"][0]["modified"].count("-") == 2


def test_cli_missing_file_exits_1_naming_the_path():
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "nope/missing.md"], capture_output=True, text=True
    )
    assert r.returncode == 1
    assert "nope/missing.md" in r.stderr
    assert r.stdout == ""


def test_cli_rejects_other_file_types(tmp_path):
    pdf = tmp_path / "spec.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    r = subprocess.run([sys.executable, str(SCRIPT), str(pdf)], capture_output=True, text=True)
    assert r.returncode == 1
    assert str(pdf) in r.stderr
    assert ".md" in r.stderr


def test_cli_without_paths_exits_1():
    r = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
    assert r.returncode == 1
    assert "usage" in r.stderr.lower()
