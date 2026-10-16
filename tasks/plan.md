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
- **`check_coverage.py` uses the outline**, not its own parser, so both scripts agree on what a heading is.
- **Commit after every task** that passes its verification, with lint and tests green.

## Dependency Graph

```
T1 Scaffold
 └── T2 outline.py
      └── T3 First deck: schema core + validate + render (title, goal, stories, please check)
           ├── T4 check_coverage.py
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
- [x] `CHECKS` pass
- [x] User opens the first deck and reviews the look, before more slides are built on it

### Phase B: All slides
- [x] Task 4: `check_coverage.py`
- [x] Task 5: Table slides
- [x] Task 6: Diagram slides
- [x] Task 7: Screen slides
- [x] Task 8: Plan slides
- [x] Task 9: Sample fixtures render both decks

### Checkpoint B
- [x] Both sample decks render, and validate and coverage pass on them
- [x] User reviews both sample decks in a browser
- [x] Code review and security review done, findings fixed or logged

### Phase C: The skill
- [x] Task 10: SKILL.md, references and install
- [x] Task 11: Live runs through `/exec-summary`

### Checkpoint C (approved by the owner 2026-10-15)
- [x] Success criteria 1, 2, 3, 4 and 6 pass
- [x] Owner reads the full deck (success criterion 5)

### Phase D: Finish
- [x] Task 12: Accessibility, mobile, print, coverage and README

### Checkpoint: Done
- [x] Spec success criteria 1-8 all pass
- [x] User approves (2026-10-15)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Claude's plain-language text drifts from the source or invents facts | High | Every item needs a `src` that `check_coverage.py` checks against the outline. `SKILL.md` and `writing-guide.md` require "Example" labels on anything inferred. The owner can check each source reference. |
| Mermaid fails to draw in the Artifact (load blocked, layout error) | Med | Diagrams are generated from nodes and edges, never hand-written. Every diagram has a table fallback that shows if Mermaid fails to load or throws. Checked in the Artifact in Task 11. |
| Heading detection differs between files (numbering, bold text, setext headings) | Med | `outline.py` handles ATX headings and ignores headings inside code blocks. Tests use both samples and renamed copies. Setext headings are rare in agent-skills files and are out of scope unless a real file needs them. |
| `check_coverage.py` is too strict and blocks real runs on harmless sections | Med | Skipping a section with a reason is always allowed. The 3-attempt fix loop in `SKILL.md` reports the remaining errors instead of looping. |
| Long sections overflow a slide | Low | Tables split after about 8 rows onto continuation slides. Text fields have `maxLength` in the schema. |
| Personal data from a source file ends up in a published deck | Med | `SKILL.md` forbids it. The deck is a private Artifact. The publish step shows the user the deck path before publishing. |
| Python 3.14 features used that break on 3.10 | Low | ruff `target-version = "py310"`. No newer syntax in `skill/`. |

## Decisions

1. **Dev tools:** `ruff` and `pytest-cov` go in `requirements-dev.txt` and are installed in Task 1, after the user approves. They are dev-only and never needed by the skill itself.
2. **Samples:** The sample files stay in `sample/` and are read directly by the tests. Only the hand-checked `summary.json` files go in `tests/fixtures/billing/`.

## Open Questions

None.

---

# v1.1: Keynote redesign

Spec: [SPEC-redesign.md](../SPEC-redesign.md) (approved 2026-10-16). Tasks: [todo.md](todo.md), Phases E and F.

## Overview

Restyle every slide type in the "Keynote" look the owner chose (Option C on the preview page), while keeping one slide on screen at a time, the same content and the frozen `summary.json` format. The title slide gains up to 4 key-number tiles counted from the data. Every slide must fit a 1280 × 650 window without scrolling.

## Current State

- The look lives almost entirely in `templates/deck.css` (708 lines, light and dark tokens, print rules). `render.py` emits the markup; most slide types already use shared classes (`cards`, `card`, `steps`, `grouped`, `impact`, `checks`, `src`).
- The active slide has `min-height: calc(100vh - 120px)` and grows with its content, so a long slide scrolls the page.
- Slide limits today: 6 stories, 8 table rows, 2 wireframes, 6 steps, a task budget of 10 rows per slide.
- Mermaid draws with its built-in `default` and `dark` themes, plus a second light copy for printing.
- Tests check contrast from the CSS tokens, the size limits (by matching CSS strings) and many CSS rules by text.

## Architecture Decisions

- **CSS first.** Most of the redesign is new tokens and rules in `deck.css`. `render.py` changes only where the layout needs new markup: the title slide tiles, and row cards for risks, tasks, checkpoints and "please check". Existing class names stay where they still fit, so tests keep their meaning.
- **Tiles are counted in `render.py`** from fields that already exist (stories, phases, tasks inside phases, checkpoints, criteria inside stories, risks, open questions). No new `summary.json` field, so no format change.
- **Fit by splitting, never by shrinking.** The active slide fills the window below the bar. Slides that are too tall at 1280 × 650 get lower per-slide limits (the constants above) so they continue on a "(continued)" slide. As a last resort the slide scrolls inside itself; the page never does.
- **Mermaid uses the `base` theme** with colours read from the CSS tokens when it draws, so diagrams follow light and dark. The print copy uses the light token values.
- **Print stays light**, and the title glow is dropped in print. Cards get a hairline border in print, because browsers often leave out background colours on paper.
- **Every task ends with Claude's browser check.** Claude renders the sample decks, opens them with Playwright, takes screenshots in light and dark (and at 360 px or print where the task says), looks at them and fixes problems before reporting. The report says what was checked and what was seen. The owner's own look comes at Checkpoint E2 and v1.1 Done (the owner skips E1).
- **The order is risk first.** The frame and fit (the hardest requirement) come in the first task, with a measurement of every slide's height, so the later tasks know their limits early.

## Dependency Graph

```
Task 13 tokens, frame, bar, tables, fit measurement
   ├── Task 14 title slide + tiles
   ├── Task 15 stories + risks as cards
   ├── Task 16 phases, tasks, checkpoints, please check
   ├── Task 17 diagrams + wireframes
   └── Task 17b text-only slides: split stage / launch stage (added at E2)
           └── Task 18 fit pass: limits tuned, 360 px, print, keyboard   (needs 14-17)
                   └── Task 19 docs, install, republish, review
```

Tasks 14-17 only depend on Task 13 and touch different render functions, but they share `deck.css`, so they are built one after another.

## Task List

### Phase E: Keynote look
- [ ] Task 13: Keynote tokens, slide frame, top bar and tables
- [ ] Task 14: Title slide with key-number tiles

### Checkpoint E1
- [ ] Tests and lint pass
- [ ] Claude's browser check of the frame, the bar, a table slide and the title slide in light and dark (no owner review here, by the owner's choice on 2026-10-16; Claude continues to Task 15)

- [ ] Task 15: Stories and risks as cards
- [ ] Task 16: Phases, tasks, checkpoints and "please check"
- [ ] Task 17: Diagrams and wireframes in the Keynote look

### Checkpoint E2
- [ ] Tests and lint pass
- [x] Owner reviews both sample decks, every slide type, in light and dark

- [x] Task 17b: Text-only slides as "split stage" (text-heavy) and "launch stage" (very short), from the owner's E2 review

### Phase F: Fit and finish
- [x] Task 18: Every slide fits 1280 × 650; 360 px, print and keyboard checks
- [ ] Task 19: Design rules, spec, install, republish and code review

### Checkpoint: v1.1 Done
- [x] `SPEC-redesign.md` success criteria 1-8 all pass, with one exception for criterion 3: the two example-screens slides scroll inside their frame at 1280 x 650 (723 and 803 px of 560; they fit at 1920 x 1000). Checked 2026-10-16; the owner chose the two-side-by-side layout and approved the published decks.
- [x] Owner approves the published decks (2026-10-16)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Long slides (8-row tables with long cells, task lists) do not fit 650 px high | High | Measured in Task 13 before anything else is restyled. Per-slide limits are lowered in Task 18 so slides continue; text is never shrunk. In-slide scroll as the last resort. |
| The Artifact viewer on claude.ai gives the page less height than the browser window | Med | Checked on the published links in Task 19. If needed, the owner decides between a smaller fit target and accepting in-slide scroll there. |
| Mermaid `base` theme colours read poorly in dark mode or print | Med | Colours come from the same tokens the contrast tests check. Diagrams checked in light, dark and print in Task 17. The table fallback stays. |
| Tests that match old CSS text break and get "fixed" by weakening them | Med | Each changed test keeps the same check against the new values (contrast stays AA, sizes stay capped). No test is deleted to get to green. |
| Card backgrounds disappear when printed | Low | Print rules give cards and tiles a hairline border. Checked with Print to PDF in Task 18. |
| The redesign quietly changes content or the JSON format | Low | No change to the schema, `validate.py` or `check_coverage.py`. Existing fixtures re-render without edits; sample tests stay green. |

## Decisions

1. **Where the tasks go:** appended to the existing `tasks/plan.md` and `tasks/todo.md` (v1 is complete), numbered on from Task 12 so `/build` picks them up in order.
2. **Fit check tooling:** done by Claude with the Playwright browser it already has. No new dev dependency; the check is a short script run in the page, and its results are written into the task notes.
3. **Text-only slides (owner, 2026-10-16, at E2):** split stage for text-heavy slides, launch stage for very short ones, picked by `render.py` from the text length. Numbered 17b so Tasks 18 and 19 keep their numbers.

## Open Questions

None.
