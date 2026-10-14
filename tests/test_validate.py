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


# --- Task 6: diagrams -----------------------------------------------------------------------


def diagram(**changes) -> dict:
    base = {
        "id": "arch",
        "kind": "architecture",
        "title": "How it fits together",
        "nodes": [{"id": "app", "label": "The app"}, {"id": "db", "label": "Your records"}],
        "edges": [{"from": "app", "to": "db", "label": "saves"}],
        "src": "SPEC.md > Tech Stack",
    }
    base.update(changes)
    return base


def test_valid_diagram_passes(data):
    data["diagrams"] = [diagram()]
    assert validate.validate(data) == []


def test_edge_to_a_missing_node_fails_with_its_path(data):
    data["diagrams"] = [diagram(edges=[{"from": "app", "to": "ghost"}])]
    errors = validate.validate(data)
    assert 'diagrams[0].edges[0].to: no node with id "ghost"' in errors


def test_edge_from_a_missing_node_fails(data):
    data["diagrams"] = [diagram(edges=[{"from": "ghost", "to": "db"}])]
    assert 'diagrams[0].edges[0].from: no node with id "ghost"' in validate.validate(data)


def test_thirteen_nodes_fail_and_twelve_pass(data):
    twelve = [{"id": f"n{i}", "label": "x"} for i in range(12)]
    data["diagrams"] = [diagram(nodes=twelve, edges=[])]
    assert validate.validate(data) == []
    data["diagrams"] = [diagram(nodes=[*twelve, {"id": "n12", "label": "x"}], edges=[])]
    assert "diagrams[0].nodes: has more than 12 items" in validate.validate(data)


@pytest.mark.parametrize("bad", ["a-b", "a b", "a;b", "é", ""])
def test_node_ids_are_letters_digits_and_underscore_only(data, bad):
    data["diagrams"] = [diagram(nodes=[{"id": bad, "label": "x"}], edges=[])]
    errors = validate.validate(data)
    assert any(e.startswith("diagrams[0].nodes[0].id") for e in errors)


def test_duplicate_node_ids_fail(data):
    nodes = [{"id": "a", "label": "x"}, {"id": "a", "label": "y"}]
    data["diagrams"] = [diagram(nodes=nodes, edges=[])]
    assert 'diagrams[0].nodes[1].id: duplicate node id "a"' in validate.validate(data)


def test_unknown_kind_and_unlisted_src_fail(data):
    data["diagrams"] = [diagram(kind="sketch", src="OTHER.md > A")]
    errors = validate.validate(data)
    assert any(e.startswith("diagrams[0].kind: must be one of") for e in errors)
    assert any(e.startswith("diagrams[0].src") for e in errors)


def test_screen_blocks_need_a_known_type_and_a_label(data):
    data["screens"] = [{"title": "Home", "blocks": [{"type": "video", "label": "x"}]}]
    assert any(e.startswith("screens[0].blocks[0].type") for e in validate.validate(data))
    data["screens"] = [{"title": "Home", "blocks": [{"type": "text"}]}]
    assert "screens[0].blocks[0].label: missing required field" in validate.validate(data)


def test_screens_are_limited_to_six(data):
    screen = {"title": "S", "blocks": [{"type": "text", "label": "x"}]}
    data["screens"] = [screen] * 7
    assert "screens: has more than 6 items" in validate.validate(data)


# --- review fixes -----------------------------------------------------------------------------


def test_a_node_id_with_a_trailing_newline_is_rejected(data):
    data["diagrams"] = [diagram(nodes=[{"id": "a\n", "label": "x"}], edges=[])]
    assert any(e.startswith("diagrams[0].nodes[0].id") for e in validate.validate(data))


@pytest.mark.parametrize(
    "path",
    [
        "C:\\Users\\me\\SPEC.md",
        "/home/me/SPEC.md",
        "..\\SPEC.md",
        "docs/../../SPEC.md",
        "\\\\srv\\x\\a.md",
    ],
)
def test_source_paths_must_be_inside_the_project(data, path):
    data["sources"][0]["path"] = path
    errors = validate.validate(data)
    assert any(e.startswith("sources[0].path: use a path inside the project") for e in errors)


def test_relative_source_paths_are_fine(data):
    data["sources"][0]["path"] = "docs/specs/SPEC.md"
    data["goal"]["src"] = "docs/specs/SPEC.md > Objective"
    data["stories"][0]["src"] = data["stories"][1]["src"] = "docs/specs/SPEC.md > User stories"
    data["skipped"][0]["src"] = "docs/specs/SPEC.md > Code Style"
    assert validate.validate(data) == []


def test_a_text_field_of_only_spaces_is_empty(data):
    data["goal"]["text"] = ["   "]
    assert "goal.text[0]: must not be only spaces" in validate.validate(data)


def test_duplicate_ids_are_rejected(data):
    data["stories"][1]["id"] = data["stories"][0]["id"]
    assert 'stories[1].id: duplicate id "S1"' in validate.validate(data)
    task = {"id": "T1", "title": "x", "src": "SPEC.md > User stories"}
    phase = {"title": "P", "src": "SPEC.md > User stories"}
    data["phases"] = [dict(phase, id="P1", tasks=[task]), dict(phase, id="P1", tasks=[task])]
    errors = validate.validate(data)
    assert 'phases[1].id: duplicate id "P1"' in errors
    assert 'phases[1].tasks[0].id: duplicate id "T1"' in errors
    data["diagrams"] = [diagram(), diagram()]
    assert 'diagrams[1].id: duplicate id "arch"' in validate.validate(data)


def test_cli_hostile_json_is_a_message_not_a_traceback(tmp_path):
    deep = tmp_path / "deep.json"
    deep.write_text("[" * 100000, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(deep)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 1
    assert "Traceback" not in result.stderr and "invalid JSON" in result.stderr


def test_every_schema_keyword_is_one_validate_py_supports():
    supported = {
        "type", "required", "properties", "additionalProperties", "items", "enum",
        "minItems", "maxItems", "minLength", "maxLength", "$comment",
    }  # fmt: skip

    def walk(node, path):
        if isinstance(node, dict):
            for key, child in node.items():
                if key == "properties":
                    for name, sub in child.items():
                        walk(sub, f"{path}.{name}")
                else:
                    assert key in supported, f"{path}: unsupported schema keyword {key!r}"
                    if key == "items":
                        walk(child, f"{path}[]")

    walk(validate.load_schema(), "$")


def test_wireframe_block_types_match_the_schema():
    import wireframe

    schema = validate.load_schema()
    block = schema["properties"]["screens"]["items"]["properties"]["blocks"]["items"]
    assert list(wireframe.BLOCK_TYPES) == block["properties"]["type"]["enum"]
