# Checkpoint C review log

Code review (`agent-skills:code-reviewer`) of Phase C, commits b1c8d2e to 2e4be8d: 0 Critical, 5 Important, 11 Suggestions. The raw report is in `.tmp/review-code-phase-c.md` (not committed).

Rule used: code review Critical and Important are fixed without asking. Suggestions are fixed when cheap, otherwise logged here with a reason.

## Fixed

| Finding | Fix | Proved by |
|---|---|---|
| I1: `install.py` deleted the file it had just written when a name differed only in case (Windows, macOS) | Names are matched ignoring case, so a case-only difference is one `change`; removes run before writes | `test_install.py` (case test); by hand: `skill.md` becomes `SKILL.md` with the new text |
| I2: a link or junction inside the destination let install write and delete outside it | Destinations holding a link (symlink or junction) are refused before anything is read; every write and delete checks the resolved path is inside the destination; files are written to a temp name and swapped in | `test_install.py` (junction test runs here; the file-symlink test needs a privilege this machine lacks and skips); by hand: junction refused, outside files untouched |
| I3: `pick_output` only knew decks recorded in `links.json`, so an unrecorded deck on disk (or a case variant) could be overwritten | A name is also taken when the file exists on disk; names are compared ignoring case; the render prints a note when it picked another name | `test_paths.py`, `test_render.py`; by hand: an existing `SPEC.html` was kept and the deck went to `other-SPEC.html` |
| I4: `--out` onto a recorded deck of other inputs erased its saved link | `--out` onto a deck made from other inputs is refused (`check_out_free`) | `test_paths.py`, `test_render.py`; by hand: refused, link still saved |
| I5: unsafe `links.json` write (no lock, fixed temp name, traceback on a write error, deck written but unrecorded) | A lock file (stale after 60 s, wait 3 s), a unique temp file that is removed on failure, `fsync`, write errors become a message; when recording fails the deck path is still printed with a clear message | `test_paths.py` (failed write, lock, stale lock), `test_render.py`; by hand: stuck lock gave the message and the deck path |
| S1: SKILL.md said both "absolute paths allowed" and "paths relative to the project" | Step 1 now says to use the project-relative spelling everywhere | `test_skill_docs.py` still passes |
| S2: long-name hash used un-normalised paths | The hash uses normalised paths | `test_paths.py` |
| S3: the hash fallback was never checked | A counter is added until a free name is found; an error after 1000 tries | `test_paths.py` |
| S4: `paths.py url` printed nothing and exited 0 with no hint | Prints "no saved link for ..." on stderr (stdout stays empty); `./` and `..` in the path are normalised | `test_paths.py` CLI tests |
| S5: one extra key in a `links.json` entry blocked every render, and SKILL.md did not say what to do | Extra keys are ignored; SKILL.md says to report a `links.json` problem and never edit or delete it | `test_paths.py`; SKILL.md |
| S6: `get_url` trusted the file | Only `https://claude.ai/` links are returned | `test_paths.py` |
| S7: entries for deleted decks reserved their names forever | An entry with no link whose file is gone is dropped when another deck is recorded | `test_paths.py` |
| S9: traceback when `--dest` is a file | A message | `test_install.py` |
| S10: weak tests | Exact names asserted for the clash tiers; the "or True" assertion removed; the real-folder install test asserts instead of skipping; overlap, file destination, link, case and CLI tests added | the tests themselves |
| S11 (docs): second clash and the printed path | SKILL.md step 7 says folders, then hash, then counter, and to use the printed path as printed | SKILL.md |

## Logged, not fixed

| Item | Why |
|---|---|
| S8: `install.py` is not atomic (a failure part-way leaves a half-updated copy; `change` shows no diff) | The list is shown first and `--yes` is required. A copy-to-temp-folder-and-swap is a bigger change for a rare failure. Revisit if an install ever fails part-way |
| S10: no test that runs the exact command lines written in SKILL.md | The test would need to rewrite placeholders for every command. `test_skill_docs.py` already checks every script name; the CLI tests cover `url`, `set-url` and `render` |
| S10: no test for two runs writing at once | The lock is tested with a held lock and a stale lock; a real two-process race is timing-dependent and would be flaky |
| S11: `paths.py` mixes the naming rule and the registry; the character-cleaning regex appears twice | Works and is tested; split into `links.py` when the module grows again |
| The file-symlink test is skipped on this machine | Creating a file symlink needs a Windows privilege. The same code path is covered by the junction test and by reading the code. It runs on a machine that allows symlinks |
