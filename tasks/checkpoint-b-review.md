# Checkpoint B review log

Code review (`agent-skills:code-reviewer`) and security audit (`agent-skills:security-auditor`) of Phase B, commits 63f099f to c87e524. Fixes are in the commits "Checkpoint B fixes". Raw reports are in `.tmp/` (not committed).

Rule used: code review Critical and Important, and security Critical, High and Medium, are fixed without asking. Lower items are fixed when cheap, otherwise logged here.

## Fixed

| Finding | Fix | Proved by |
|---|---|---|
| Sec M1: design images read from the current folder, judged by name, links followed | Folders are read only when named with `--design-dir`. Content is checked (PNG, JPEG, WebP signatures; SVG with no script, entity or external reference). Links and files outside the project are skipped. Captions are "Design image N". The run lists what was embedded | `test_render.py` design tests, `design_images.py` |
| Sec M2: `--out` could overwrite any file | Must end in `.html` and cannot be the summary or a source file | `test_paths.py`, `test_render.py` CLI tests |
| Sec L1: node id regex accepted a trailing newline | `fullmatch`, one shared rule in `common.py` | `test_validate.py`, `test_mermaid.py` |
| Sec L2: quadratic heading regex | Linear match, 2 MB file cap | `test_outline.py` (60,000 spaces in under 1 s) |
| Sec L3: tracebacks on hostile JSON | One `load_json` with a 2 MB cap and messages for deep nesting and huge numbers | `test_check_coverage.py`, `test_validate.py`, `test_render.py` |
| Sec L4: absolute paths and image names could reach the deck | `sources[].path` must be project-relative without `..`. Image names are not shown | `test_validate.py` |
| Sec L5: gitignore gaps | Added `credentials.json`, `token.json`, `*.pem`, `*.key`, `node_modules/` | |
| Sec I1, I2, I3 | Windows device names are renamed; CSP meta tag (diagrams checked in a browser); a test that fails when the Mermaid URL changes without a reviewed SRI hash | `test_paths.py`, `test_render.py` |
| Code I1: coverage check satisfied while dropping tasks | Task and checkpoint headings cannot be skipped (except a repeat of one shown from another file). Found tasks and checkpoints are counted by distinct heading, and missing ones are named | `test_check_coverage.py` |
| Code I2: file with no headings passes | Error: nothing can be checked | same |
| Code I3: identical headings merged | `Heading#2` selects the second one; each needs its own source | same |
| Code I4: fragile counts | `Checkpoint` must start the heading; tasks and checkpoints are the union over files; stories from numbered or `As ...` items and `Story N` headings | same, `test_outline.py` |
| Code I5: tracebacks in check_coverage | Validates first; unreadable inputs give messages | same |
| Code I6: files vs `sources` | Must match exactly; slash and `./` spelling is normalised | same |
| Code I7: check slide omitted checkpoints; tick keys collide | Checkpoints added; keys are a hash of the deck (project and sources) and the item text | `test_render.py`, `test_sample.py` |
| Code I8: OS theme change did not redraw diagrams | Redraws on that change too | Browser check |
| Code I9: print in dark mode | Print palette is always light, and each diagram has a light copy drawn for print | Browser check (print emulation) |
| Code I10: raw Mermaid text before drawing; failed draw cannot recover | "Drawing" text until drawn; table after a failure or 8 s; a later successful draw replaces the table | Browser check (online, blocked script) |
| Code I11: weak tests | Wireframe types compared with the schema; schema keyword guard; hostile text in every field; sample tests use `esc` and check notes in the deck; dead placeholder test removed | |
| Code S1, S3, S7 | Shared `common.py`; duplicate ids rejected; whitespace-only text rejected; `impact` class escaped | |

## Logged, not fixed

| Item | Why |
|---|---|
| Code S2: table cells are "already escaped" by convention | Every caller escapes and the hostile-text test covers all fields. A wrapper type is a refactor for later |
| Code S4: `to_flowchart(direction=...)` never varies; `suffix` title part unused | Harmless. Revisit when a flow needs left-to-right |
| Code S5: `render.py` uses the current folder as the project folder | Now only matters for `--design-dir`, which is explicit. Run from the project root |
| Code S6: `docs/SPEC.md` and `other/SPEC.md` share an output name | Needs a project-level decision when `links.json` is built (Task 10) |
| Code S7: phase with no tasks has no heading on the tasks slide | It still shows on the phases slide |
| Code S7: arrow keys while a button has focus | Kept on purpose: after clicking Next, the arrow keys must still work |
| Code S9: criteria table repeats the story text per row | Cosmetic |
| Schema fields nothing reads (`screens[].example`) | Kept for the spec's format |
| No automated tests of `deck.js` | Checked by hand in a browser each time. A test runner for it is not worth a dependency now |
| Sec I4: commit author email is public in history | Your call. GitHub offers a noreply address |

## To carry into Task 10 (SKILL.md)

- Limits of `check_coverage.py`: tasks written only as checkboxes are not counted; stories are counted from a "User stories" heading or `Story N` headings; two files that repeat the same checkpoints are shown once.
- The same path spelling in `sources`, every `src` and the command line (slashes and `./` are normalised). Paths must be relative to the project.
- Ask the user before using design images, then pass `--design-dir`. Say that images are not checked for personal data.
