import json
import os
import re
import subprocess
import sys
import time
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


def deck(folder: Path, name: str) -> Path:
    """A deck file that exists, as it does when the renderer registers it."""
    path = folder / name
    path.write_text("<html></html>", encoding="utf-8")
    return path


def test_a_deck_is_registered_with_its_inputs_and_keeps_other_entries(tmp_path):
    file = tmp_path / "links.json"
    spec, plan = deck(tmp_path, "SPEC.html"), deck(tmp_path, "plan.html")
    assert paths.register_deck(file, spec, ["SPEC.md"]) is None
    assert paths.register_deck(file, plan, ["plan.md"]) is None
    links, problem = paths.read_links(file)
    assert problem is None
    assert links[spec.as_posix()] == {"sources": ["SPEC.md"], "url": None}
    assert set(links) == {spec.as_posix(), plan.as_posix()}


def test_a_missing_links_file_is_an_empty_list(tmp_path):
    assert paths.read_links(tmp_path / "links.json") == ({}, None)


def test_the_link_is_saved_and_read_back_and_other_decks_are_untouched(tmp_path):
    file = tmp_path / "links.json"
    spec, full = deck(tmp_path, "SPEC.html"), deck(tmp_path, "SPEC+plan.html")
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


def test_out_still_wins_over_the_clash_rule():
    links = {"build/deck.html": {"sources": ["other.md"], "url": None}}
    assert paths.pick_output(["SPEC.md"], links, out="build/deck.html") == Path("build/deck.html")


# --- review fixes: never overwrite, safe writes, normalised keys -----------------------------

SIMPLE = Path("docs/exec-summary/SPEC.html")


def test_an_existing_deck_that_is_not_in_links_is_never_overwritten():
    got = paths.pick_output(["other/SPEC.md"], {}, exists=lambda p: p == SIMPLE)
    assert got == Path("docs/exec-summary/other-SPEC.html")
    assert paths.pick_output(["other/SPEC.md"], {}) == SIMPLE  # nothing on disk: simple name


def test_names_that_differ_only_in_case_count_as_the_same_name():
    links = {"docs/exec-summary/spec.html": {"sources": ["a/spec.md"], "url": None}}
    assert paths.pick_output(["b/SPEC.md"], links) == Path("docs/exec-summary/b-SPEC.html")
    same = paths.pick_output(["a/spec.md"], links)  # the deck's own inputs may keep its name
    assert same == Path("docs/exec-summary/spec.html")


def test_a_second_clash_gets_a_short_hash_and_a_third_a_counter():
    links = {
        "docs/exec-summary/SPEC.html": {"sources": ["a/SPEC.md"], "url": None},
        "docs/exec-summary/x-SPEC.html": {"sources": ["y/SPEC.md"], "url": None},
    }
    got = paths.pick_output(["x/SPEC.md"], links)
    assert re.fullmatch(r"x-SPEC-[0-9a-f]{8}\.html", got.name), got
    links[got.as_posix()] = {"sources": ["z/SPEC.md"], "url": None}
    again = paths.pick_output(["x/SPEC.md"], links)
    assert again.name == got.stem + "-2.html"


def test_a_folder_name_ending_in_a_dash_keeps_its_dash_in_the_name():
    links = {"docs/exec-summary/SPEC.html": {"sources": ["a/SPEC.md"], "url": None}}
    assert paths.pick_output(["x-/SPEC.md"], links).name == "x--SPEC.html"


def test_long_names_hash_the_same_whatever_the_spelling_of_the_path():
    long = "x" * 200 + ".md"
    assert paths.output_path(["./" + long]) == paths.output_path([long])


def test_out_cannot_take_over_a_deck_made_from_other_inputs():
    links = {SIMPLE.as_posix(): {"sources": ["a/SPEC.md"], "url": "https://claude.ai/artifact/A"}}
    problem = paths.check_out_free(links, SIMPLE, ["b/SPEC.md"])
    assert "already holds a deck" in problem and "a/SPEC.md" in problem
    assert paths.check_out_free(links, SIMPLE, ["./a/SPEC.md"]) is None
    assert paths.check_out_free(links, Path("elsewhere/deck.html"), ["b/SPEC.md"]) is None
    upper = Path("docs/exec-summary/spec.HTML")
    assert paths.check_out_free(links, upper, ["b/SPEC.md"]) is not None


def test_keys_ignore_a_leading_dot_and_case_when_a_link_is_looked_up():
    links = {SIMPLE.as_posix(): {"sources": ["SPEC.md"], "url": "https://claude.ai/artifact/A"}}
    assert (
        paths.get_url(links, Path("./docs/exec-summary/SPEC.html"))
        == links[SIMPLE.as_posix()]["url"]
    )
    assert paths.get_url(links, Path("docs/exec-summary/spec.html")) is not None
    assert paths.get_url(links, Path("docs/exec-summary/other.html")) is None


def test_a_hand_edited_link_that_is_not_a_claude_link_is_not_returned():
    links = {SIMPLE.as_posix(): {"sources": ["SPEC.md"], "url": "javascript:alert(1)"}}
    assert paths.get_url(links, SIMPLE) is None


def test_an_extra_key_in_an_entry_is_ignored_and_a_missing_one_is_an_error(tmp_path):
    file = tmp_path / "links.json"
    entry = {"sources": ["a.md"], "url": None, "note": "kept by hand"}
    file.write_text(json.dumps({"a.html": entry}), encoding="utf-8")
    assert paths.read_links(file)[1] is None
    file.write_text(json.dumps({"a.html": {"sources": ["a.md"]}}), encoding="utf-8")
    assert paths.read_links(file)[1] is not None


def test_a_failed_write_is_a_message_not_a_traceback_and_leaves_no_temp_file(tmp_path, monkeypatch):
    file = tmp_path / "links.json"

    def refuse(self, target):
        raise PermissionError("held open by another program")

    monkeypatch.setattr(Path, "replace", refuse)
    problem = paths.register_deck(file, Path("a.html"), ["a.md"])
    assert "cannot save" in problem and "held open" in problem
    assert sorted(p.name for p in tmp_path.iterdir()) == []


def test_two_runs_at_once_do_not_overwrite_each_other_and_a_stuck_lock_is_reported(
    tmp_path, monkeypatch
):
    file = tmp_path / "links.json"
    monkeypatch.setattr(paths, "LOCK_WAIT", 0.2)
    lock = tmp_path / "links.json.lock"
    lock.write_text("", encoding="utf-8")
    problem = paths.register_deck(file, Path("a.html"), ["a.md"])
    assert "in use" in problem and not file.exists()
    old = time.time() - 3600  # a lock left behind by a crashed run is ignored
    os.utime(lock, (old, old))
    assert paths.register_deck(file, Path("a.html"), ["a.md"]) is None
    assert not lock.exists() and file.exists()


def test_entries_for_decks_that_no_longer_exist_are_dropped_unless_they_hold_a_link(tmp_path):
    file = tmp_path / "links.json"
    gone, kept = tmp_path / "gone.html", tmp_path / "kept.html"
    here = tmp_path / "new.html"
    here.write_text("x", encoding="utf-8")
    paths.register_deck(file, gone, ["a.md"])
    paths.register_deck(file, kept, ["b.md"])
    paths.set_url(file, kept, "https://claude.ai/artifact/K")
    paths.register_deck(file, here, ["c.md"])
    links, _ = paths.read_links(file)
    assert set(links) == {kept.as_posix(), here.as_posix()}


def run_paths(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(Path(paths.__file__)), *args], capture_output=True, text=True, cwd=cwd
    )


def project_with_link(tmp_path: Path) -> None:
    folder = tmp_path / "docs" / "exec-summary"
    folder.mkdir(parents=True)
    out = Path("docs/exec-summary/SPEC.html")
    (tmp_path / out).write_text("<html></html>", encoding="utf-8")
    assert paths.register_deck(folder / "links.json", out, ["SPEC.md"]) is None
    assert paths.set_url(folder / "links.json", out, "https://claude.ai/artifact/AAA") is None


def test_cli_url_prints_the_saved_link_whatever_the_spelling_of_the_path(tmp_path):
    project_with_link(tmp_path)
    for spelling in ["docs/exec-summary/SPEC.html", "./docs/exec-summary/SPEC.html"]:
        result = run_paths(tmp_path, "url", spelling)
        assert result.returncode == 0 and result.stdout.strip() == "https://claude.ai/artifact/AAA"


def test_cli_url_says_on_stderr_when_there_is_no_saved_link(tmp_path):
    project_with_link(tmp_path)
    result = run_paths(tmp_path, "url", "docs/exec-summary/other.html")
    assert result.returncode == 0 and result.stdout == ""
    assert "no saved link" in result.stderr
    empty = tmp_path / "empty"
    empty.mkdir()
    again = run_paths(empty, "url", "docs/exec-summary/SPEC.html")
    assert again.returncode == 0 and again.stdout == "" and "no saved link" in again.stderr


def test_cli_set_url_saves_and_refuses_bad_input(tmp_path):
    project_with_link(tmp_path)
    ok = run_paths(
        tmp_path, "set-url", "docs/exec-summary/SPEC.html", "https://claude.ai/artifact/BBB"
    )
    assert ok.returncode == 0
    assert run_paths(tmp_path, "url", "docs/exec-summary/SPEC.html").stdout.strip().endswith("BBB")
    bad = run_paths(tmp_path, "set-url", "docs/exec-summary/SPEC.html", "http://evil.example/x")
    assert bad.returncode == 1 and "claude.ai" in bad.stderr
    unknown = run_paths(tmp_path, "set-url", "docs/exec-summary/none.html", "https://claude.ai/a")
    assert unknown.returncode == 1 and "not registered" in unknown.stderr
    assert run_paths(tmp_path, "url", "docs/exec-summary/SPEC.html").stdout.strip().endswith("BBB")


def test_cli_with_the_wrong_arguments_prints_usage_and_fails(tmp_path):
    for args in [(), ("url",), ("set-url", "a.html"), ("nope", "a.html")]:
        result = run_paths(tmp_path, *args)
        assert result.returncode == 1 and "set-url" in result.stderr, args
