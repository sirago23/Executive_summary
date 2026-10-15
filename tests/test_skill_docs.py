import json
import re
from pathlib import Path

import validate

SKILL = Path(__file__).resolve().parent.parent / "skill" / "exec-summary"
SKILL_MD = (SKILL / "SKILL.md").read_text(encoding="utf-8")
FORMAT_MD = (SKILL / "references" / "summary-format.md").read_text(encoding="utf-8")
SCHEMA = json.loads((SKILL / "schema" / "summary.schema.json").read_text(encoding="utf-8"))


def test_skill_md_has_the_name_and_a_description_that_triggers_on_the_command():
    front = SKILL_MD.split("---")[1]
    assert re.search(r"^name: exec-summary$", front, re.M)
    description = re.search(r"^description: (.+)$", front, re.M).group(1)
    assert "/exec-summary" in description and "executive summary" in description.lower()


def test_every_script_skill_md_names_exists_and_every_pipeline_script_is_named():
    named = set(re.findall(r"scripts/(\w+\.py)", SKILL_MD))
    for script in named:
        assert (SKILL / "scripts" / script).is_file(), script
    assert {"outline.py", "validate.py", "check_coverage.py", "render.py", "paths.py"} <= named


def test_every_reference_skill_md_points_to_exists():
    named = set(re.findall(r"references/([\w-]+\.md)", SKILL_MD))
    assert named == {"writing-guide.md", "summary-format.md", "design-rules.md"}
    for name in named:
        assert (SKILL / "references" / name).is_file(), name


def test_skill_md_states_the_rules_the_owner_relies_on():
    for phrase in [
        "at most 3 times",
        "Tasks and checkpoints cannot be skipped",
        "tasks written only as checkboxes are not counted",
        "--design-dir",
        "not checked for personal data",
        "private",
        "Edit any input file",
    ]:
        assert phrase.lower() in SKILL_MD.lower(), phrase


def test_the_example_in_the_format_guide_is_valid():
    block = re.search(r"```json\n(.*?)```", FORMAT_MD, re.S).group(1)
    assert validate.validate(json.loads(block)) == []


def test_the_format_guide_lists_every_schema_section_and_nothing_else():
    table = FORMAT_MD.split("## Fields")[1].split("## Limits")[0]
    listed = set(re.findall(r"^\| `(\w+)`(?:, `(\w+)`)?", table, re.M))
    names = {name for pair in listed for name in pair if name}
    assert names == set(SCHEMA["properties"])
