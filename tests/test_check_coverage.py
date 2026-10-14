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


def write_spec(tmp_path: Path) -> str:
    path = tmp_path / "SPEC.md"
    path.write_text(SPEC_TEXT, encoding="utf-8")
    return str(path)


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
    summary = make_summary(spec, skipped=[])
    errors = coverage.check(summary, [spec])
    assert any("Code Style" in e and "neither used nor skipped" in e for e in errors)


def test_skipped_without_a_reason_does_not_count(tmp_path):
    spec = write_spec(tmp_path)
    summary = make_summary(spec, skipped=[{"src": f"{spec} > Code Style", "reason": "  "}])
    errors = coverage.check(summary, [spec])
    assert any("Code Style" in e for e in errors)


def test_fails_when_a_story_is_missing_with_expected_and_found_counts(tmp_path):
    spec = write_spec(tmp_path)
    summary = make_summary(spec, stories=[{"id": "S1", "src": f"{spec} > User stories"}])
    errors = coverage.check(summary, [spec])
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
    todo = tmp_path / "todo.md"
    todo.write_text(
        "# Todo\n\n## Phase 1\n### Task 1: A\n### Task 2: B\n### Checkpoint 1\n",
        encoding="utf-8",
    )
    path = str(todo)
    summary = {
        "sources": [{"path": path}],
        "skipped": [],
        "phases": [
            {
                "id": "P1",
                "src": f"{path} > Phase 1",
                "tasks": [{"id": "T1", "src": f"{path} > Task 1: A"}],
            }
        ],
    }
    errors = coverage.check(summary, [path])
    assert any("tasks" in e and "expected 2" in e and "found 1" in e for e in errors)
    assert any("checkpoints" in e and "expected 1" in e and "found 0" in e for e in errors)


def test_checkpoints_in_the_summary_are_counted(tmp_path):
    todo = tmp_path / "todo.md"
    todo.write_text("# Todo\n\n## Checkpoint A\n\n## Checkpoint B\n", encoding="utf-8")
    path = str(todo)
    checkpoint = {"title": "A", "items": ["x"], "src": f"{path} > Checkpoint A"}
    summary = {"sources": [{"path": path}], "skipped": [], "checkpoints": [checkpoint]}
    errors = coverage.check(summary, [path])
    assert any("checkpoints" in e and "expected 2" in e and "found 1" in e for e in errors)
    assert not any("Checkpoint A" in e for e in errors)


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, check=False
    )


def test_cli_ok_and_failure_exit_codes(tmp_path):
    spec = write_spec(tmp_path)
    good = tmp_path / "good.json"
    good.write_text(json.dumps(make_summary(spec)), encoding="utf-8")
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(make_summary(spec, skipped=[])), encoding="utf-8")

    ok = run_cli(str(good), spec)
    assert ok.returncode == 0
    assert ok.stdout.strip() == "OK"

    fail = run_cli(str(bad), spec)
    assert fail.returncode == 1
    assert "Code Style" in fail.stderr


def test_cli_rejects_missing_input_and_bad_arguments(tmp_path):
    summary = tmp_path / "s.json"
    summary.write_text("{}", encoding="utf-8")
    missing = run_cli(str(summary), str(tmp_path / "nope.md"))
    assert missing.returncode == 1
    assert "nope.md" in missing.stderr
    assert run_cli().returncode == 1


def test_criteria_src_counts_as_a_use_of_that_heading(tmp_path):
    spec = tmp_path / "SPEC.md"
    spec.write_text("# S\n\n## User stories\n1. a\n\n## Acceptance criteria\nx\n", encoding="utf-8")
    path = str(spec)
    story = {
        "id": "S1",
        "src": f"{path} > User stories",
        "criteria_src": f"{path} > Acceptance criteria",
    }
    summary = {"sources": [{"path": path}], "skipped": [], "stories": [story]}
    assert coverage.check(summary, [path]) == []
    story["criteria_src"] = f"{path} > Nope"
    assert any("stories[0].criteria_src" in e for e in coverage.check(summary, [path]))
