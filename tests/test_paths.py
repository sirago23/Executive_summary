from pathlib import Path

import paths


def test_one_input_uses_its_file_name():
    assert paths.output_path(["SPEC.md"]) == Path("docs/exec-summary/SPEC.html")


def test_folders_are_dropped_from_the_name():
    assert paths.output_path(["docs/my spec.txt"]) == Path("docs/exec-summary/my_spec.html")


def test_windows_separators_are_dropped_too():
    assert paths.output_path(["tasks\\plan.md"]) == Path("docs/exec-summary/plan.html")


def test_several_inputs_are_joined_in_the_order_given():
    got = paths.output_path(["SPEC.md", "tasks/plan.md", "tasks/todo.md"])
    assert got == Path("docs/exec-summary/SPEC+plan+todo.html")
    got = paths.output_path(["tasks/plan.md", "SPEC.md"])
    assert got == Path("docs/exec-summary/plan+SPEC.html")


def test_out_overrides_the_name():
    assert paths.output_path(["SPEC.md"], out="build/deck.html") == Path("build/deck.html")


def test_unsafe_characters_are_replaced():
    assert paths.output_path(["a:b*c.md"]) == Path("docs/exec-summary/a_b_c.html")


def test_very_long_names_are_shortened_but_stay_distinct():
    a = paths.output_path(["x" * 200 + "1.md"])
    b = paths.output_path(["x" * 200 + "2.md"])
    assert len(a.name) <= 130
    assert a != b


def test_windows_device_names_are_not_used_as_file_names():
    for name in ["CON.md", "nul.txt", "Com1.md", "LPT9.md", "aux.tar.md"]:
        got = paths.output_path([name])
        assert got.stem.casefold().split(".")[0] not in paths.RESERVED, name
    assert paths.output_path(["console.md"]) == Path("docs/exec-summary/console.html")


def test_out_path_must_be_html_and_not_an_input(tmp_path):
    spec = tmp_path / "SPEC.md"
    spec.write_text("x", encoding="utf-8")
    assert paths.check_out_path(tmp_path / "deck.html", [spec]) == []
    assert paths.check_out_path(tmp_path / "DECK.HTML", [spec]) == []
    assert any(
        "must end in .html" in e for e in paths.check_out_path(tmp_path / "deck.txt", [spec])
    )
    assert any("input files" in e for e in paths.check_out_path(spec, [spec]))
    same = tmp_path / "sub" / ".." / "SPEC.md"
    assert any("input files" in e for e in paths.check_out_path(same, [spec]))
