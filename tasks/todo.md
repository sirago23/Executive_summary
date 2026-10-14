# Tasks: Executive Summary Skill

Plan: [plan.md](plan.md). Spec: [SPEC.md](../SPEC.md).

Every task also meets the standing Definition of Done:
- Lint and tests pass.
- Behavior is checked by running it, not just by tests (open the HTML where there is one).
- New behavior has tests that fail without it.
- Error paths are handled, with `path.to.field: message` errors and exit code 1.
- No debug code is left in.
- The change stays within the task's scope.
- It is committed with nothing sensitive staged.

Standard checks used below:
- `CHECKS` = `ruff check . && python -m pytest`
- `S` = `skill/exec-summary/scripts`

---

## Phase A: First deck

### - [x] Task 1: Scaffold the repo and tooling

**Description:** Create the folder layout from the spec's Project Structure, `pyproject.toml` (pytest settings, ruff with `target-version = "py310"`, coverage settings for `S`), `requirements-dev.txt` (pytest, pytest-cov, ruff, pinned), and `.gitignore` (`.tmp/`, `session-handoff/`, `.env*`, `__pycache__/`, `.pytest_cache/`, `.coverage`, `docs/exec-summary/` in this repo). Ask before installing the dev tools.

**Acceptance criteria:**
- [ ] `ruff check .` and `python -m pytest` run (pytest finds a placeholder test and passes).
- [ ] `python -m pytest --cov` reports coverage for `S`.

**Verification:**
- [ ] `CHECKS` pass
- [ ] `git status` shows no `.tmp/` or cache folders

**Dependencies:** None
**Files:** `pyproject.toml`, `requirements-dev.txt`, `.gitignore`, `tests/test_placeholder.py`, `skill/exec-summary/` (empty folders with `.gitkeep`)
**Scope:** S

### - [x] Task 2: `outline.py` reads any Markdown file's structure

**Description:** Write `outline.py <file> [<file> ...]`. For each file it prints JSON with the path as given, last-modified date, and a list of sections: heading text, level, line, and counts and texts of list items, numbered items, checkboxes (checked or not) and tables. It flags `Task N:` headings and headings that contain "Checkpoint". Headings inside fenced code blocks are ignored. Missing paths and non-`.md`/`.txt` files exit 1 with the path named.

**Acceptance criteria:**
- [ ] On `sample/SPEC_sample.md`, the "User stories" section has 7 numbered items.
- [ ] On `sample/todo_sample.md`, 17 task headings and 5 checkpoint headings are found.
- [ ] A copy of a sample under a different name and folder gives the same sections.
- [ ] `# comments` inside code blocks (for example in the spec's Commands block) are not reported as headings.

**Verification:**
- [ ] `CHECKS` pass. `tests/test_outline.py` covers the above plus a missing file and a `.pdf` path.
- [ ] Manual: run it on all three samples and read the JSON

**Dependencies:** Task 1
**Files:** `S/outline.py`, `tests/test_outline.py`
**Scope:** M

### - [x] Task 3: First deck from a hand-written summary.json

**Description:** The first full vertical slice. Write the core of `summary.schema.json` (`project`, `sources`, `skipped`, `goal`, `stories`, `open_questions`), `validate.py` with the JSON Schema subset validator and the "every `src` names a listed source" rule, `paths.py` (output name from input names, `--out`), and `render.py` with the template, design tokens (light and dark), contents list, arrow-key navigation and slides 1 (title, files covered), 2 (goal), 3 (stories) and 18 (please check, checkboxes in localStorage with try/catch). Add a small hand-written `tests/fixtures/minimal.json`.

**Acceptance criteria:**
- [ ] `validate.py` passes the fixture and fails with clear messages on a missing `project`, a wrong type, an unknown field and a `src` naming an unlisted file.
- [ ] `render.py` writes one HTML file containing only the four slides. Absent sections drop their slides without a warning.
- [ ] Output names: one input `SPEC.md` gives `docs/exec-summary/SPEC.html`; inputs `SPEC.md tasks/plan.md` give `SPEC+plan.html`; `--out` wins.
- [ ] Any field containing `<script>` or `&` renders escaped.

**Verification:**
- [ ] `CHECKS` pass. Tests: `test_validate.py`, `test_paths.py`, `test_render.py`.
- [ ] Manual: open the deck in a browser at desktop width and 360 px, in light and dark mode

**Dependencies:** Task 2
**Files:** `skill/exec-summary/schema/summary.schema.json`, `S/validate.py`, `S/paths.py`, `S/render.py`, `skill/exec-summary/templates/deck.html`, `deck.css`, `deck.js`, `tests/fixtures/minimal.json`, tests
**Scope:** M

### - [ ] Checkpoint A
- [ ] `CHECKS` pass
- [ ] User reviews the look of the first deck. Changes to tokens and layout happen now, before more slides use them.

---

## Phase B: All slides

### - [x] Task 4: `check_coverage.py`

**Description:** Write `check_coverage.py <summary.json> <file> [<file> ...]`. It runs the outline on the inputs and checks that every heading (level 2 and deeper) is either the heading part of some `src` or listed in `skipped` with a non-empty reason; that every `src` names a real file and heading from the inputs; and that the counts of user stories, task headings and checkpoint headings in the inputs are matched in `summary.json`.

**Acceptance criteria:**
- [ ] Passes on `minimal.json` with its matching input.
- [ ] Fails, naming the heading, when a section is neither used nor skipped.
- [ ] Fails when a story, task or checkpoint is missing, giving the expected and found counts.
- [ ] Fails on a `src` with an unknown file or heading.

**Verification:**
- [ ] `CHECKS` pass. `tests/test_check_coverage.py`.

**Dependencies:** Task 3
**Files:** `S/check_coverage.py`, `tests/test_check_coverage.py`
**Scope:** M

### - [x] Task 5: Table slides

**Description:** Add schema, validation and render functions for slides 4 (acceptance criteria per story), 8 (data, simplified), 9 (tech stack with plain explanations), 14 (rules: always / ask first / never), 15 (decisions and out of scope), 16 (success criteria) and 17 (other notes). Tables split onto continuation slides after 8 rows.

**Acceptance criteria:**
- [ ] Each slide renders from fixture data and is dropped when its section is absent.
- [ ] A 20-row table becomes 3 slides with "(continued)" titles.
- [ ] Every item shows its source reference in small text.

**Verification:**
- [ ] `CHECKS` pass. One render test per slide.
- [ ] Manual: browser check at 360 px

**Dependencies:** Task 3
**Files:** `summary.schema.json`, `S/render.py`, `deck.css`, `tests/test_render.py`
**Scope:** M

### - [x] Task 6: Diagram slides

**Description:** Write `mermaid.py` (`escape_label`, `to_flowchart` with node groups as subgraphs). Add `diagrams` to the schema (at most 12 nodes, edges must reference existing nodes) and slides 6 (architecture) and 7 (flow). Load Mermaid from the pinned jsdelivr URL. If Mermaid fails to load or throws, show a nodes-and-edges table in place of the diagram.

**Acceptance criteria:**
- [ ] Labels with quotes, new lines, brackets and `<script>` are escaped. Node ids are restricted to `[A-Za-z0-9_]`.
- [ ] Validation fails on an edge to a missing node and on 13 nodes.
- [ ] Both diagrams draw in a browser. With the network off, the fallback tables show.

**Verification:**
- [ ] `CHECKS` pass. `tests/test_mermaid.py`, plus validate and render tests.
- [ ] Manual: browser check online and offline

**Dependencies:** Task 3
**Files:** `S/mermaid.py`, `summary.schema.json`, `S/validate.py`, `S/render.py`, `deck.js`, tests
**Scope:** M

### - [x] Task 7: Screen slides

**Description:** Write `wireframe.py`, which turns a screen's blocks (`header`, `nav`, `stats`, `chart`, `list`, `form`, `button`, `text`, `image`) into grayscale HTML, and add slide 5. If the project has images in `design/`, `docs/design/` or `mockups/` (PNG, JPEG, WebP, SVG as image only), embed them as data URIs instead, up to 5 MB in total. Every wireframe has the label "Example layout, not the final design".

**Acceptance criteria:**
- [ ] Each block type renders. An unknown block type fails validation.
- [ ] With a `design/` folder of images, those images show and no wireframes are drawn.
- [ ] Images over the 5 MB total are left out with a note on the slide. Image paths cannot leave the project folder.

**Verification:**
- [ ] `CHECKS` pass. `tests/test_wireframe.py`, plus a render test with a temp `design/` folder.
- [ ] Manual: browser check of 2 wireframes at 360 px and desktop

**Dependencies:** Task 3
**Files:** `S/wireframe.py`, `summary.schema.json`, `S/render.py`, `deck.css`, tests
**Scope:** M

### - [x] Task 8: Plan slides

**Description:** Add schema, validation and render functions for slides 10 (phases and timeline as a simple step strip), 11 (tasks by phase: title and what the owner will see working), 12 (checkpoints the owner approves) and 13 (risks with High/Med/Low as text plus color).

**Acceptance criteria:**
- [ ] Each slide renders from fixture data and is dropped when absent.
- [ ] 17 tasks across 5 phases split over slides without cutting a phase's title off from its tasks.
- [ ] Impact labels are readable without color.

**Verification:**
- [ ] `CHECKS` pass. Render tests per slide.
- [ ] Manual: browser check

**Dependencies:** Task 3
**Files:** `summary.schema.json`, `S/render.py`, `deck.css`, `tests/test_render.py`
**Scope:** M

### - [x] Task 9: Sample fixtures render both decks

**Description:** Write the two hand-checked fixtures from the samples, following the spec's plain-language rules: `tests/fixtures/billing/spec.json` (spec only) and `tests/fixtures/billing/full.json` (spec, plan and todo). Add `tests/test_sample.py`, which validates, checks coverage and renders both, and writes the decks to `.tmp/sample/`.

**Acceptance criteria:**
- [ ] The spec-only deck has no phase, task, checkpoint or risk slides.
- [ ] The full deck has all 7 stories, 5 phases, 17 tasks, 5 checkpoints, 2 diagrams and at least 2 wireframes, and is under 2 MB.
- [ ] Validate and coverage pass on both.

**Verification:**
- [ ] `CHECKS` pass
- [ ] Manual: user opens both decks from `.tmp/sample/`

**Dependencies:** Tasks 4-8
**Files:** `tests/fixtures/billing/spec.json`, `tests/fixtures/billing/full.json`, `tests/test_sample.py`
**Scope:** M

### - [ ] Checkpoint B
- [ ] `CHECKS` pass
- [ ] User reviews both sample decks
- [ ] `agent-skills:code-reviewer` and `agent-skills:security-auditor` run, and findings are fixed or logged

---

## Phase C: The skill

### - [ ] Task 10: SKILL.md, references and install

**Description:** Write `SKILL.md` (name `exec-summary`, a description that triggers on "/exec-summary" and "executive summary of <files>", and the steps from the spec's How It Works, including the no-paths case and the 3-attempt fix loop). Write `references/writing-guide.md` (plain-language rules, a jargon glossary seeded from the samples, the "Example" label rule, no personal data) and `references/summary-format.md` (field guide with a short example). Write `tools/install.py`, which copies `skill/exec-summary` to `~/.claude/skills/exec-summary` and replaces an older copy only after showing what will change. Add `links.json` read and write to `paths.py`.

**Acceptance criteria:**
- [ ] `SKILL.md` names every script with its exact command and says when to stop and ask.
- [ ] `install.py` copies the folder; running it again updates it; `--dry-run` lists files only.
- [ ] `paths.py` saves and reads one link per output path and keeps other entries.

**Verification:**
- [ ] `CHECKS` pass. Tests for `install.py` (into a temp home) and `links.json`.
- [ ] Manual: install (ask first), then the skill shows up in a new session's skill list

**Dependencies:** Task 9
**Files:** `skill/exec-summary/SKILL.md`, `references/writing-guide.md`, `references/summary-format.md`, `tools/install.py`, `S/paths.py`, tests
**Scope:** M

### - [ ] Task 11: Live runs through `/exec-summary`

**Description:** Run the installed skill as a user would, in this repo: first `/exec-summary sample/SPEC_sample.md`, then `/exec-summary sample/SPEC_sample.md sample/plan_sample.md sample/todo_sample.md`. Ask before each publish. Then change one line in a copy of the spec and re-run to check the same link updates. Fix the skill instructions where Claude's run needed manual help, and note what was learned in `SKILL.md`.

**Acceptance criteria:**
- [ ] Success criterion 1: spec-only run gives a link in one run, with no phase or task slides.
- [ ] Success criterion 2: full run gives a separate link with all stories, phases, tasks and checkpoints.
- [ ] Success criteria 3 and 4: diagrams draw in the Artifact; at least 2 wireframes, labelled.
- [ ] Success criterion 6: re-run updates the same link, and the other deck's link is unchanged.

**Verification:**
- [ ] Manual: user opens both links
- [ ] `CHECKS` pass after any fixes

**Dependencies:** Task 10
**Files:** `skill/exec-summary/SKILL.md`, `references/*` (fixes only)
**Scope:** M

### - [ ] Checkpoint C
- [ ] Success criteria 1, 2, 3, 4 and 6 pass
- [ ] Success criterion 5: the owner reads the full deck and confirms they understand it without asking about terms
- [ ] `agent-skills:code-reviewer` run, and findings are fixed or logged
- [ ] `summary.json` format is frozen from here (changes need approval)

---

## Phase D: Finish

### - [ ] Task 12: Accessibility, mobile, print, coverage and README

**Description:** Check every slide type against the spec's Design Direction: WCAG AA contrast in both themes, keyboard navigation and visible focus, 360 px layout, and a print stylesheet with one slide per page. Bring `S` coverage to at least 85%. Write `README.md` (what it does, install, usage with examples, the spec-only and full workflows, where outputs go).

**Acceptance criteria:**
- [ ] Print to PDF of the full sample deck gives one slide per page with nothing cut off.
- [ ] Keyboard alone moves through slides and ticks checkboxes. Focus is visible.
- [ ] `python -m pytest --cov` shows at least 85% for `S`.

**Verification:**
- [ ] `CHECKS` pass
- [ ] Manual: print preview, 360 px and dark mode check with the user

**Dependencies:** Task 11
**Files:** `deck.css`, `deck.js`, tests, `README.md`
**Scope:** M

### - [ ] Checkpoint: Done
- [ ] Spec success criteria 1-8 all pass
- [ ] User approves
