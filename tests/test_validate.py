import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
import validate

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "minimal.json"
SCRIPT = ROOT / "skill" / "exec-summary" / "scripts" / "validate.py"


@pytest.fixture
def data() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_fixture_is_valid(data):
    assert validate.validate(data) == []


def test_missing_required_sections(data):
    del data["project"]
    del data["skipped"]
    errors = validate.validate(data)
    assert "project: missing required field" in errors
    assert "skipped: missing required field" in errors


def test_nested_missing_field_has_full_path(data):
    del data["stories"][1]["want"]
    assert "stories[1].want: missing required field" in validate.validate(data)


def test_wrong_type(data):
    data["project"]["name"] = 42
    assert "project.name: expected string, got integer" in validate.validate(data)


def test_bool_is_not_an_integer_or_string(data):
    data["project"]["name"] = True
    assert "project.name: expected string, got boolean" in validate.validate(data)


def test_unknown_field(data):
    data["stories"][0]["colour"] = "red"
    data["wizard"] = {}
    errors = validate.validate(data)
    assert "stories[0].colour: unknown field" in errors
    assert "wizard: unknown field" in errors


def test_length_and_count_limits(data):
    data["project"]["name"] = "x" * 81
    data["goal"]["text"] = []
    errors = validate.validate(data)
    assert "project.name: longer than 80 characters" in errors
    assert "goal.text: needs at least 1 items" in errors


def test_empty_string_is_rejected_where_required(data):
    data["skipped"][0]["reason"] = ""
    assert "skipped[0].reason: shorter than 1 characters" in validate.validate(data)


def test_src_naming_an_unlisted_file_fails(data):
    data["stories"][0]["src"] = "OTHER.md > User stories"
    errors = validate.validate(data)
    assert 'stories[0].src: "OTHER.md" is not listed in sources' in errors


def test_src_without_heading_fails(data):
    data["goal"]["src"] = "SPEC.md"
    errors = validate.validate(data)
    assert 'goal.src: must look like "<file> > <heading>"' in errors


def test_skipped_src_is_checked_too(data):
    data["skipped"][0]["src"] = "nowhere.md > Code Style"
    assert any(e.startswith("skipped[0].src:") for e in validate.validate(data))


def test_root_must_be_an_object():
    assert validate.validate([]) == ["$: expected object, got array"]


def test_cli_ok_and_failure(tmp_path, data):
    ok = subprocess.run([sys.executable, str(SCRIPT), str(FIXTURE)], capture_output=True, text=True)
    assert ok.returncode == 0

    del data["project"]
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(data), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPT), str(bad)], capture_output=True, text=True)
    assert r.returncode == 1
    assert "project: missing required field" in r.stderr


def test_cli_invalid_json_and_missing_file(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text("{ nope", encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPT), str(broken)], capture_output=True, text=True)
    assert r.returncode == 1
    assert "invalid JSON" in r.stderr

    r = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path / "none.json")], capture_output=True, text=True
    )
    assert r.returncode == 1
    assert "none.json" in r.stderr


def test_validate_does_not_modify_input(data):
    before = copy.deepcopy(data)
    validate.validate(data)
    assert data == before
