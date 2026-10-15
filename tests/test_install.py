from pathlib import Path

import install


def make_source(root: Path) -> Path:
    src = root / "skill" / "exec-summary"
    (src / "scripts").mkdir(parents=True)
    (src / "SKILL.md").write_text("---\nname: exec-summary\n---\n", encoding="utf-8")
    (src / "scripts" / "render.py").write_text("print('x')\n", encoding="utf-8")
    (src / "scripts" / "__pycache__").mkdir()
    (src / "scripts" / "__pycache__" / "render.cpython-314.pyc").write_bytes(b"junk")
    (src / "references").mkdir()
    (src / "references" / ".gitkeep").write_text("", encoding="utf-8")
    return src


def run(src: Path, dest: Path, *args: str) -> int:
    return install.main([*args, "--dest", str(dest)], source=src)


def test_a_fresh_install_copies_the_skill_without_cache_or_placeholder_files(tmp_path, capsys):
    src, dest = make_source(tmp_path), tmp_path / "home" / "skills" / "exec-summary"
    assert run(src, dest) == 0
    assert (dest / "SKILL.md").read_text(encoding="utf-8") == "---\nname: exec-summary\n---\n"
    assert (dest / "scripts" / "render.py").is_file()
    assert not (dest / "scripts" / "__pycache__").exists()
    assert not (dest / "references" / ".gitkeep").exists()
    assert "add: SKILL.md" in capsys.readouterr().out


def test_dry_run_lists_files_and_writes_nothing(tmp_path, capsys):
    src, dest = make_source(tmp_path), tmp_path / "exec-summary"
    assert run(src, dest, "--dry-run") == 0
    out = capsys.readouterr().out
    assert "add: SKILL.md" in out and "add: scripts/render.py" in out
    assert not dest.exists()


def test_running_again_with_no_change_does_nothing(tmp_path, capsys):
    src, dest = make_source(tmp_path), tmp_path / "exec-summary"
    run(src, dest)
    capsys.readouterr()
    assert run(src, dest) == 0
    assert "up to date" in capsys.readouterr().out


def test_an_older_copy_is_shown_then_replaced_only_with_yes(tmp_path, capsys):
    src, dest = make_source(tmp_path), tmp_path / "exec-summary"
    run(src, dest)
    (src / "scripts" / "render.py").write_text("print('new')\n", encoding="utf-8")
    (src / "scripts" / "extra.py").write_text("x = 1\n", encoding="utf-8")
    (dest / "old.txt").write_text("stale", encoding="utf-8")
    capsys.readouterr()

    assert run(src, dest) == 1  # shows the changes, changes nothing
    out = capsys.readouterr()
    assert "change: scripts/render.py" in out.out
    assert "add: scripts/extra.py" in out.out
    assert "remove: old.txt" in out.out
    assert "--yes" in out.err
    assert (dest / "scripts" / "render.py").read_text(encoding="utf-8") == "print('x')\n"
    assert (dest / "old.txt").exists()

    assert run(src, dest, "--yes") == 0
    assert (dest / "scripts" / "render.py").read_text(encoding="utf-8") == "print('new')\n"
    assert (dest / "scripts" / "extra.py").is_file()
    assert not (dest / "old.txt").exists()


def test_a_dry_run_on_an_older_copy_changes_nothing_even_with_yes(tmp_path):
    src, dest = make_source(tmp_path), tmp_path / "exec-summary"
    run(src, dest)
    (src / "SKILL.md").write_text("changed", encoding="utf-8")
    assert run(src, dest, "--dry-run", "--yes") == 0
    assert (dest / "SKILL.md").read_text(encoding="utf-8") != "changed"


def test_a_source_without_skill_md_is_refused(tmp_path, capsys):
    src, dest = make_source(tmp_path), tmp_path / "exec-summary"
    (src / "SKILL.md").unlink()
    assert run(src, dest) == 1
    assert "SKILL.md" in capsys.readouterr().err
    assert not dest.exists()


def test_the_destination_must_be_a_folder_named_exec_summary_unless_default(tmp_path, capsys):
    src = make_source(tmp_path)
    for bad in [tmp_path / "docs", tmp_path]:
        assert run(src, bad) == 1, bad
    assert "exec-summary" in capsys.readouterr().err


def test_the_default_destination_is_under_the_home_skills_folder(tmp_path):
    assert install.default_dest(tmp_path) == tmp_path / ".claude" / "skills" / "exec-summary"


def test_the_real_skill_folder_installs(tmp_path):
    # Real skill folder to a temp folder: shows what would be installed, writes nothing real.
    dest = tmp_path / "exec-summary"
    real = Path(install.__file__).resolve().parent.parent / "skill" / "exec-summary"
    if (real / "SKILL.md").exists():
        assert install.main(["--dest", str(dest)], source=real) == 0
        assert (dest / "scripts" / "render.py").is_file()
        assert (dest / "templates" / "deck.css").is_file()
