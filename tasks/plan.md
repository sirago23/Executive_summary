# Implementation Plan: Executive Summary Skill

Spec: [SPEC.md](../SPEC.md). Task details and checkboxes: [todo.md](todo.md).

## Overview

Build the `exec-summary` Claude Code skill: Python scripts (standard library only) that outline the input files, validate and check Claude's `summary.json`, and render it as one HTML deck, plus the `SKILL.md` that tells Claude how to run them and publish the deck as a private Artifact.

Work is sliced vertically. Task 3 produces a real (small) deck in the browser from a hand-written `summary.json`, and every later task adds a group of slides end to end: schema, validation, rendering and a test. The skill wrapper comes after the slides work, so the first live `/exec-summary` run uses a finished renderer.

## Current State

- The repo has `SPEC.md`, `CLAUDE.md` and `sample/` (`SPEC_sample.md`, `plan_sample.md`, `todo_sample.md`). No code yet. Git is initialized with no commits.
- Python 3.14 and pytest 9.1 are installed. `ruff` and `pytest-cov` are not installed (needed for lint and the coverage target).

## Architecture Decisions

- **`schema/summary.schema.json` is the single source of truth for `summary.json`.** `validate.py` contains a small JSON Schema subset validator (type, required, properties, additionalProperties, items, enum, minItems, maxItems, maxLength), so the schema and the checks cannot drift apart. Cross-field rules that JSON Schema cannot express (edges point to real nodes, every `src` names an input file) are plain Python checks in the same script.
- **Each slide type is one render function** `render_<slide>(data) -> str | None` in `render.py`. It returns `None` when its section is absent, which is how a slide is dropped. The slide order is one list, matching the Slide Catalog in the spec.
- **Escaping happens in one place.** All text goes through `esc()` (HTML) or `mermaid.escape_label()`. Templates never receive raw strings from the JSON.
- **The HTML template has the CSS and JS inlined at render time** from `templates/deck.css` and `templates/deck.js`, so the output is a single file. Mermaid is the only external script (pinned jsdelivr URL).
- **Design tokens are set once in Task 3** (colors for light and dark, type scale, spacing) and reused by every later slide.
- **Output naming and `links.json` live in one module** (`paths.py`), used by `render.py` and by the skill's publish step, so the naming rule exists once.
- **`outline.py` is format-aware, not name-aware.** It reports Markdown structure only (headings with level and line, list items, checkboxes, `Task N` headings, tables). Deciding what a section means is Claude's job in `SKILL.md`.
- **`coverage.py` uses the outline**, not its own parser, so both scripts agree on what a heading is.
- **Commit after every task** that passes its verification, with lint and tests green.

## Dependency Graph

```
T1 Scaffold
 └── T2 outline.py
      └── T3 First deck: schema core + validate + render (title, goal, stories, please check)
           ├── T4 coverage.py
           ├── T5 Table slides (criteria, data, stack, rules, decisions, success, other notes)
           ├── T6 Diagram slides (mermaid.py, architecture, flow)
           ├── T7 Screen slides (wireframe.py, design images)
           └── T8 Plan slides (phases, tasks, checkpoints, risks)
                └── T9 Sample fixtures, both decks render (needs T4-T8)
                     └── T10 SKILL.md, references, install.py, links.json
                          └── T11 Live runs: spec only, then spec + plan + todo
                               └── T12 Accessibility, mobile, print, coverage, README
```

## How to Build

- **One agent, one task at a time, in task order.** Tasks 5 to 8 all edit `render.py`, `summary.schema.json` and the template, so parallel work would conflict.
- **Per task:** build, run `CHECKS`, check the result in a browser where the task has a visual part, tick the box in `todo.md`, then commit.
- **Reviewer sub-agent:** `agent-skills:code-reviewer` at Checkpoints B and C. `agent-skills:security-auditor` at Checkpoint B (HTML and Mermaid escaping, file paths, embedded images).
- **Stop and ask** before: installing `ruff` and `pytest-cov` (Task 1), any dependency inside `skill/`, changing the `summary.json` format after Checkpoint C, publishing an Artifact (Task 11), and writing to `~/.claude/skills` (Task 10).
- **Session handoff:** at a task boundary, as in CLAUDE.md.

## Task List

### Phase A: First deck
- [x] Task 1: Scaffold the repo and tooling
- [x] Task 2: `outline.py` reads any Markdown file's structure
- [x] Task 3: First deck from a hand-written summary.json

### Checkpoint A
- [ ] `CHECKS` pass
- [ ] User opens the first deck and reviews the look, before more slides are built on it

### Phase B: All slides
- [ ] Task 4: `coverage.py`
- [ ] Task 5: Table slides
- [ ] Task 6: Diagram slides
- [ ] Task 7: Screen slides
- [ ] Task 8: Plan slides
- [ ] Task 9: Sample fixtures render both decks

### Checkpoint B
- [ ] Both sample decks render, and validate and coverage pass on them
- [ ] User reviews both sample decks in a browser
- [ ] Code review and security review done, findings fixed or logged

### Phase C: The skill
- [ ] Task 10: SKILL.md, references and install
- [ ] Task 11: Live runs through `/exec-summary`

### Checkpoint C
- [ ] Success criteria 1, 2, 3, 4 and 6 pass
- [ ] Owner reads the full deck (success criterion 5)

### Phase D: Finish
- [ ] Task 12: Accessibility, mobile, print, coverage and README

### Checkpoint: Done
- [ ] Spec success criteria 1-8 all pass
- [ ] User approves

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Claude's plain-language text drifts from the source or invents facts | High | Every item needs a `src` that `coverage.py` checks against the outline. `SKILL.md` and `writing-guide.md` require "Example" labels on anything inferred. The owner can check each source reference. |
| Mermaid fails to draw in the Artifact (load blocked, layout error) | Med | Diagrams are generated from nodes and edges, never hand-written. Every diagram has a table fallback that shows if Mermaid fails to load or throws. Checked in the Artifact in Task 11. |
| Heading detection differs between files (numbering, bold text, setext headings) | Med | `outline.py` handles ATX headings and ignores headings inside code blocks. Tests use both samples and renamed copies. Setext headings are rare in agent-skills files and are out of scope unless a real file needs them. |
| `coverage.py` is too strict and blocks real runs on harmless sections | Med | Skipping a section with a reason is always allowed. The 3-attempt fix loop in `SKILL.md` reports the remaining errors instead of looping. |
| Long sections overflow a slide | Low | Tables split after about 8 rows onto continuation slides. Text fields have `maxLength` in the schema. |
| Personal data from a source file ends up in a published deck | Med | `SKILL.md` forbids it. The deck is a private Artifact. The publish step shows the user the deck path before publishing. |
| Python 3.14 features used that break on 3.10 | Low | ruff `target-version = "py310"`. No newer syntax in `skill/`. |

## Decisions

1. **Dev tools:** `ruff` and `pytest-cov` go in `requirements-dev.txt` and are installed in Task 1, after the user approves. They are dev-only and never needed by the skill itself.
2. **Samples:** The sample files stay in `sample/` and are read directly by the tests. Only the hand-checked `summary.json` files go in `tests/fixtures/billing/`.

## Open Questions

None.
