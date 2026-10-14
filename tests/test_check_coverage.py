import json
import subprocess
import sys
from pathlib import Path

import check_coverage as coverage

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "sample"
FIXTURE = ROOT / "tests" / "fixtures" / "minimal.json"
SCRIPT = ROOT / "skill" / "exec-summary" / "scripts" / "check_coverage.py"

SPEC_TEXT = """# Spec

## Objective
Track money.

## User stories
1. As the owner, I upload a slip.
2. As the owner, I export to CSV.

## Code Style
Keep it small.
"""

TODO_TEXT = """# Todo

## Phase 1
### Task 1: A
### Task 2: B
### Checkpoint A
"""


def write(tmp_path: Path, name: str, text: str) -> str:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def write_spec(tmp_path: Path) -> str:
    return write(tmp_path, "SPEC.md", SPEC_TEXT)


def make_summary(spec: str, **changes) -> dict:
    summary = {
        "sources": [{"path": spec}],
        "skipped": [{"src": f"{spec} > Code Style", "reason": "Code conventions."}],
        "goal": {"text": ["Track money."], "src": f"{spec} > Objective"},
        "stories": [
            {"id": "S1", "src": f"{spec} > User stories"},
            {"id": "S2", "src": f"{spec} > User stories"},
        ],
    }
    summary.update(changes)
    return summary


def todo_summary(todo: str, tasks: list[str], skipped=(), checkpoint=True) -> dict:
    summary = {
        "sources": [{"path": todo}],
        "skipped": [{"src": f"{todo} > {h}", "reason": "Not needed."} for h in skipped],
        "phases": [
            {
                "id": "P1",
                "src": f"{todo} > Phase 1",
                "tasks": [{"id": f"T{i}", "src": f"{todo} > {n}"} for i, n in enumerate(tasks)],
            }
        ],
    }
    if checkpoint:
        summary["checkpoints"] = [{"title": "A", "items": ["x"], "src": f"{todo} > Checkpoint A"}]
    return summary


def test_minimal_fixture_passes_with_matching_input(tmp_path):
    spec = tmp_path / "SPEC.md"
    spec.write_text(
        "# Spec\n\n## Objective\nx\n\n## User stories\n1. a\n2. b\n\n## Code Style\ny\n",
        encoding="utf-8",
    )
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    text = json.dumps(data).replace("SPEC.md", str(spec).replace("\\", "\\\\"))
    assert coverage.check(json.loads(text), [str(spec)]) == []


def test_passes_when_every_heading_is_used_or_skipped(tmp_path):
    spec = write_spec(tmp_path)
    assert coverage.check(make_summary(spec), [spec]) == []


def test_fails_naming_a_heading_that_is_neither_used_nor_skipped(tmp_path):
    spec = write_spec(tmp_path)
    errors = coverage.check(make_summary(spec, skipped=[]), [spec])
    assert any("Code Style" in e and "neither used nor skipped" in e for e in errors)


def test_skipped_without_a_reason_does_not_count(tmp_path):
    spec = write_spec(tmp_path)
    summary = make_summary(spec, skipped=[{"src": f"{spec} > Code Style", "reason": "  "}])
    errors = coverage.check(summary, [spec])
    assert any("needs a reason" in e for e in errors)
    assert any("Code Style" in e and "neither used nor skipped" in e for e in errors)


def test_fails_when_a_story_is_missing_with_expected_and_found_counts(tmp_path):
    spec = write_spec(tmp_path)
    summary = make_summary(spec, stories=[{"id": "S1", "src": f"{spec} > User stories"}])
    errors = coverage.check(summary, [spec])
    assert any("stories" in e and "expected 2" in e and "found 1" in e for e in errors)


def test_the_same_story_listed_twice_counts_once(tmp_path):
    spec = write_spec(tmp_path)
    story = {"id": "S1", "src": f"{spec} > User stories"}
    errors = coverage.check(make_summary(spec, stories=[story, dict(story)]), [spec])
    assert any("stories" in e and "expected 2" in e and "found 1" in e for e in errors)


def test_fails_on_src_with_unknown_heading(tmp_path):
    spec = write_spec(tmp_path)
    summary = make_summary(spec, goal={"text": ["x"], "src": f"{spec} > Nope"})
    errors = coverage.check(summary, [spec])
    assert any("goal.src" in e and "Nope" in e for e in errors)


def test_fails_on_src_with_unknown_file(tmp_path):
    spec = write_spec(tmp_path)
    summary = make_summary(spec, goal={"text": ["x"], "src": "OTHER.md > Objective"})
    errors = coverage.check(summary, [spec])
    assert any("goal.src" in e and "OTHER.md" in e for e in errors)


def test_heading_match_ignores_case_and_spacing(tmp_path):
    spec = write_spec(tmp_path)
    summary = make_summary(spec, goal={"text": ["x"], "src": f"{spec} >  objective "})
    assert coverage.check(summary, [spec]) == []


def test_todo_sample_needs_17_tasks_and_5_checkpoints():
    todo = str(SAMPLE / "todo_sample.md")
    expected = coverage.expected_counts(coverage.load_outlines([todo]))
    assert expected == {"stories": 0, "tasks": 17, "checkpoints": 5}


def test_spec_sample_has_seven_stories():
    spec = str(SAMPLE / "SPEC_sample.md")
    expected = coverage.expected_counts(coverage.load_outlines([spec]))
    assert expected["stories"] == 7


def test_task_and_checkpoint_counts_come_from_summary(tmp_path):
    todo = write(tmp_path, "todo.md", TODO_TEXT)
    errors = coverage.check(todo_summary(todo, ["Task 1: A"], checkpoint=False), [todo])
    assert any("tasks" in e and "expected 2" in e and "found 1" in e for e in errors)
    assert any("checkpoints" in e and "expected 1" in e and "found 0" in e for e in errors)


def test_checkpoints_in_the_summary_are_counted(tmp_path):
    todo = write(tmp_path, "todo.md", "# Todo\n\n## Checkpoint A\n\n## Checkpoint B\n")
    checkpoint = {"title": "A", "items": ["x"], "src": f"{todo} > Checkpoint A"}
    summary = {"sources": [{"path": todo}], "skipped": [], "checkpoints": [checkpoint]}
    errors = coverage.check(summary, [todo])
    assert any("checkpoints" in e and "expected 2" in e and "found 1" in e for e in errors)
    assert not any("neither used" in e and "Checkpoint A" in e for e in errors)


def test_criteria_src_counts_as_a_use_of_that_heading(tmp_path):
    spec = write(tmp_path, "SPEC.md", "# S\n\n## User stories\n1. a\n\n## Acceptance criteria\nx\n")
    story = {
        "id": "S1",
        "src": f"{spec} > User stories",
        "criteria_src": f"{spec} > Acceptance criteria",
    }
    summary = {"sources": [{"path": spec}], "skipped": [], "stories": [story]}
    assert coverage.check(summary, [spec]) == []
    story["criteria_src"] = f"{spec} > Nope"
    assert any("stories[0].criteria_src" in e for e in coverage.check(summary, [spec]))


# --- review findings: ways the check used to be satisfied while dropping content -------------


def test_a_task_cannot_be_skipped_and_one_task_listed_twice_does_not_hide_it(tmp_path):
    todo = write(tmp_path, "todo.md", TODO_TEXT)
    summary = todo_summary(todo, ["Task 1: A", "Task 1: A"], skipped=["Task 2: B"])
    errors = coverage.check(summary, [todo])
    assert any("Task 2: B" in e and "cannot be skipped" in e for e in errors)
    assert any("tasks" in e and "expected 2" in e and "found 1" in e for e in errors)


def test_a_checkpoint_cannot_be_skipped(tmp_path):
    todo = write(tmp_path, "todo.md", TODO_TEXT)
    summary = todo_summary(
        todo, ["Task 1: A", "Task 2: B"], skipped=["Checkpoint A"], checkpoint=False
    )
    errors = coverage.check(summary, [todo])
    assert any("Checkpoint A" in e and "cannot be skipped" in e for e in errors)


def test_a_repeated_checkpoint_in_a_second_file_may_be_skipped(tmp_path):
    plan = write(tmp_path, "plan.md", "# Plan\n\n## Checkpoint A\nx\n")
    todo = write(tmp_path, "todo.md", "# Todo\n\n## Checkpoint A\nx\n")
    summary = {
        "sources": [{"path": plan}, {"path": todo}],
        "skipped": [{"src": f"{todo} > Checkpoint A", "reason": "Same as in the plan."}],
        "checkpoints": [{"title": "A", "items": ["x"], "src": f"{plan} > Checkpoint A"}],
    }
    assert coverage.check(summary, [plan, todo]) == []


def test_tasks_in_two_files_are_added_together_not_maxed(tmp_path):
    plan = write(tmp_path, "plan.md", "# P\n\n### Task 1: A\n### Task 2: B\n")
    todo = write(tmp_path, "todo.md", "# T\n\n### Task 3: C\n### Task 4: D\n")
    expected = coverage.expected_counts(coverage.load_outlines([plan, todo]))
    assert expected["tasks"] == 4


def test_a_file_with_no_level_two_headings_is_an_error(tmp_path):
    notes = write(tmp_path, "notes.txt", "Just some text.\nNo headings at all.\n")
    errors = coverage.check({"sources": [{"path": notes}], "skipped": []}, [notes])
    assert any("no headings at level 2" in e for e in errors)
    h1_only = write(tmp_path, "one.md", "# Title\n\nText only.\n")
    errors = coverage.check({"sources": [{"path": h1_only}], "skipped": []}, [h1_only])
    assert any("no headings at level 2" in e for e in errors)


def test_identical_headings_need_their_own_src(tmp_path):
    notes = write(tmp_path, "n.md", "# N\n\n## Notes\na\n\n## Notes\nb\n")
    summary = {"sources": [{"path": notes}], "skipped": []}
    summary["notes"] = [{"title": "A", "text": ["a"], "src": f"{notes} > Notes"}]
    errors = coverage.check(summary, [notes])
    assert any('heading "Notes#2"' in e and "neither used nor skipped" in e for e in errors)
    summary["notes"].append({"title": "B", "text": ["b"], "src": f"{notes} > Notes#2"})
    assert coverage.check(summary, [notes]) == []


def test_a_plain_checkpoints_heading_is_not_a_checkpoint(tmp_path):
    text = "# T\n\n## Checkpoints\nWhy.\n\n## Reviewer checkpoint policy\nx\n"
    todo = write(tmp_path, "t.md", text)
    assert coverage.expected_counts(coverage.load_outlines([todo]))["checkpoints"] == 0


def test_stories_written_as_as_bullets_or_story_headings_are_counted(tmp_path):
    text = "# S\n\n## User stories\n- As a user, I do a.\n- As a user, I do b.\n"
    bullets = write(tmp_path, "b.md", text)
    assert coverage.expected_counts(coverage.load_outlines([bullets]))["stories"] == 2
    text = "# S\n\n### Story 1\nx\n### Story 2\ny\n### Story 3\nz\n"
    headings = write(tmp_path, "h.md", text)
    assert coverage.expected_counts(coverage.load_outlines([headings]))["stories"] == 3


def test_command_line_files_and_sources_must_match(tmp_path):
    spec = write_spec(tmp_path)
    other = write(tmp_path, "OTHER.md", "# O\n\n## Part\nx\n")
    errors = coverage.check(make_summary(spec), [spec, other])
    assert any("OTHER.md" in e and "not listed in sources" in e for e in errors)
    summary = make_summary(spec, sources=[{"path": spec}, {"path": "missing.md"}])
    errors = coverage.check(summary, [spec])
    assert any("missing.md" in e and "not given on the command line" in e for e in errors)


def test_path_spelling_differences_do_not_matter(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write(tmp_path, "SPEC.md", SPEC_TEXT)
    (tmp_path / "docs").mkdir()
    write(tmp_path, "docs/plan.md", "# P\n\n## Part\nx\n")
    story = {"src": "SPEC.md > User stories"}
    summary = {
        "sources": [{"path": "SPEC.md"}, {"path": "docs\\plan.md"}],
        "skipped": [
            {"src": "SPEC.md > Code Style", "reason": "Code."},
            {"src": "docs/plan.md > Part", "reason": "Not needed."},
        ],
        "goal": {"text": ["x"], "src": "./SPEC.md > Objective"},
        "stories": [dict(story, id="S1"), dict(story, id="S2")],
    }
    assert coverage.check(summary, ["./SPEC.md", "docs/plan.md"]) == []


# --- command line ----------------------------------------------------------------------------


def run_cli(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=cwd, check=False
    )


def valid_summary() -> dict:
    story = {"as": "the owner", "src": "SPEC.md > User stories"}
    return {
        "project": {"name": "Demo"},
        "sources": [{"path": "SPEC.md"}],
        "skipped": [{"src": "SPEC.md > Code Style", "reason": "Code conventions."}],
        "goal": {"text": ["Track money."], "src": "SPEC.md > Objective"},
        "stories": [
            dict(story, id="S1", want="to upload"),
            dict(story, id="S2", want="to export"),
        ],
    }


def test_cli_ok_and_failure_exit_codes(tmp_path):
    write(tmp_path, "SPEC.md", SPEC_TEXT)
    good = tmp_path / "good.json"
    good.write_text(json.dumps(valid_summary()), encoding="utf-8")
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(dict(valid_summary(), skipped=[])), encoding="utf-8")

    ok = run_cli(tmp_path, "good.json", "SPEC.md")
    assert ok.returncode == 0, ok.stderr
    assert ok.stdout.strip() == "OK"

    fail = run_cli(tmp_path, "bad.json", "SPEC.md")
    assert fail.returncode == 1
    assert "Code Style" in fail.stderr


def test_cli_rejects_missing_input_and_bad_arguments(tmp_path):
    summary = tmp_path / "s.json"
    summary.write_text("{}", encoding="utf-8")
    missing = run_cli(tmp_path, "s.json", "nope.md")
    assert missing.returncode == 1
    assert "nope.md" in missing.stderr
    assert run_cli(tmp_path).returncode == 1


def test_cli_reports_a_malformed_summary_without_a_traceback(tmp_path):
    write(tmp_path, "SPEC.md", SPEC_TEXT)
    broken = dict(
        valid_summary(),
        phases=[{"id": "P", "title": "x", "tasks": None, "src": "SPEC.md > Objective"}],
    )
    for name, content in {"tasks-null.json": broken, "list.json": []}.items():
        (tmp_path / name).write_text(json.dumps(content), encoding="utf-8")
        result = run_cli(tmp_path, name, "SPEC.md")
        assert result.returncode == 1, name
        assert "Traceback" not in result.stderr, name
        assert result.stderr.strip(), name


def test_cli_reports_unreadable_input_files_without_a_traceback(tmp_path):
    (tmp_path / "SPEC.md").write_bytes(b"# S\n\n## Objective\n\xff\xfe\x00bad\n")
    (tmp_path / "s.json").write_text(json.dumps(valid_summary()), encoding="utf-8")
    result = run_cli(tmp_path, "s.json", "SPEC.md")
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert "cannot read" in result.stderr


def test_cli_hostile_json_gives_a_message_not_a_traceback(tmp_path):
    write(tmp_path, "SPEC.md", SPEC_TEXT)
    (tmp_path / "deep.json").write_text("[" * 100000, encoding="utf-8")
    (tmp_path / "big.json").write_text('{"a": ' + "9" * 5001 + "}", encoding="utf-8")
    for name in ("deep.json", "big.json"):
        result = run_cli(tmp_path, name, "SPEC.md")
        assert result.returncode == 1, name
        assert "Traceback" not in result.stderr, name
        assert "invalid JSON" in result.stderr, name
