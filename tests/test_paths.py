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


# --- links.json: one Artifact link per deck, and names that do not clash -----------------------

LINKS = Path("docs/exec-summary/links.json")


def test_a_deck_is_registered_with_its_inputs_and_keeps_other_entries(tmp_path):
    file = tmp_path / "links.json"
    assert paths.register_deck(file, Path("docs/exec-summary/SPEC.html"), ["SPEC.md"]) is None
    assert paths.register_deck(file, Path("docs/exec-summary/plan.html"), ["plan.md"]) is None
    links, problem = paths.read_links(file)
    assert problem is None
    assert links["docs/exec-summary/SPEC.html"] == {"sources": ["SPEC.md"], "url": None}
    assert set(links) == {"docs/exec-summary/SPEC.html", "docs/exec-summary/plan.html"}


def test_a_missing_links_file_is_an_empty_list(tmp_path):
    assert paths.read_links(tmp_path / "links.json") == ({}, None)


def test_the_link_is_saved_and_read_back_and_other_decks_are_untouched(tmp_path):
    file = tmp_path / "links.json"
    spec, full = Path("docs/exec-summary/SPEC.html"), Path("docs/exec-summary/SPEC+plan.html")
    paths.register_deck(file, spec, ["SPEC.md"])
    paths.register_deck(file, full, ["SPEC.md", "plan.md"])
    assert paths.set_url(file, spec, "https://claude.ai/artifact/abc") is None
    links, _ = paths.read_links(file)
    assert paths.get_url(links, spec) == "https://claude.ai/artifact/abc"
    assert paths.get_url(links, full) is None
    paths.set_url(file, full, "https://claude.ai/artifact/def")
    links, _ = paths.read_links(file)
    assert paths.get_url(links, spec) == "https://claude.ai/artifact/abc"


def test_registering_again_keeps_the_saved_link(tmp_path):
    file = tmp_path / "links.json"
    out = Path("docs/exec-summary/SPEC.html")
    paths.register_deck(file, out, ["SPEC.md"])
    paths.set_url(file, out, "https://claude.ai/artifact/abc")
    paths.register_deck(file, out, ["SPEC.md"])
    links, _ = paths.read_links(file)
    assert paths.get_url(links, out) == "https://claude.ai/artifact/abc"


def test_only_claude_ai_links_are_saved(tmp_path):
    file = tmp_path / "links.json"
    out = Path("docs/exec-summary/SPEC.html")
    paths.register_deck(file, out, ["SPEC.md"])
    for bad in ["http://claude.ai/artifact/a", "https://evil.example/x", "javascript:alert(1)", ""]:
        assert "https://claude.ai/" in (paths.set_url(file, out, bad) or ""), bad
    assert paths.set_url(file, Path("never/registered.html"), "https://claude.ai/a") is not None
    links, _ = paths.read_links(file)
    assert paths.get_url(links, out) is None


def test_a_broken_links_file_is_reported_and_never_overwritten(tmp_path):
    file = tmp_path / "links.json"
    file.write_text("{not json", encoding="utf-8")
    links, problem = paths.read_links(file)
    assert links == {} and "invalid JSON" in problem
    assert paths.register_deck(file, Path("a.html"), ["a.md"]) is not None
    assert file.read_text(encoding="utf-8") == "{not json"
    file.write_text("[1, 2]", encoding="utf-8")
    assert paths.read_links(file)[1] is not None
    file.write_text('{"a.html": "oops"}', encoding="utf-8")
    assert paths.read_links(file)[1] is not None


def test_same_inputs_keep_the_same_name(tmp_path):
    links = {"docs/exec-summary/SPEC.html": {"sources": ["SPEC.md"], "url": None}}
    assert paths.pick_output(["./SPEC.md"], links) == Path("docs/exec-summary/SPEC.html")
    assert paths.pick_output(["SPEC.md"], {}) == Path("docs/exec-summary/SPEC.html")


def test_a_different_folder_with_the_same_file_name_gets_its_folder_in_the_name():
    links = {"docs/exec-summary/SPEC.html": {"sources": ["docs/SPEC.md"], "url": None}}
    assert paths.pick_output(["other/SPEC.md"], links) == Path("docs/exec-summary/other-SPEC.html")
    assert paths.pick_output(["docs/SPEC.md"], links) == Path("docs/exec-summary/SPEC.html")
    sources = ["other\\sub/SPEC.md", "other/plan.md"]
    assert paths.pick_output(sources, links) == Path("docs/exec-summary/SPEC+plan.html")  # free
    links["docs/exec-summary/SPEC+plan.html"] = {"sources": ["x/SPEC.md", "x/plan.md"], "url": None}
    got = paths.pick_output(sources, links)
    assert got == Path("docs/exec-summary/other-sub-SPEC+other-plan.html")


def test_the_first_deck_keeps_its_name_even_if_it_is_a_clash_later():
    links = {
        "docs/exec-summary/SPEC.html": {"sources": ["docs/SPEC.md"], "url": None},
        "docs/exec-summary/other-SPEC.html": {"sources": ["other/SPEC.md"], "url": None},
    }
    assert paths.pick_output(["docs/SPEC.md"], links) == Path("docs/exec-summary/SPEC.html")
    assert paths.pick_output(["other/SPEC.md"], links) == Path("docs/exec-summary/other-SPEC.html")


def test_a_clash_on_the_folder_name_too_gets_a_short_hash():
    links = {
        "docs/exec-summary/SPEC.html": {"sources": ["a/SPEC.md"], "url": None},
        "docs/exec-summary/x-SPEC.html": {"sources": ["x/SPEC.md"], "url": None},
    }
    got = paths.pick_output(["x-/SPEC.md"], links)  # folder "x-" cleans to "x-", so "x--SPEC"
    assert got.name.endswith(".html") and got != Path("docs/exec-summary/SPEC.html")
    links["docs/exec-summary/x-SPEC.html"] = {"sources": ["y/SPEC.md"], "url": None}
    clash = paths.pick_output(["x/SPEC.md"], links)
    assert clash not in (Path("docs/exec-summary/SPEC.html"), Path("docs/exec-summary/x-SPEC.html"))


def test_out_still_wins_over_the_clash_rule():
    links = {"build/deck.html": {"sources": ["other.md"], "url": None}}
    assert paths.pick_output(["SPEC.md"], links, out="build/deck.html") == Path("build/deck.html")
