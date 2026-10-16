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

### - [x] Checkpoint A
- [x] `CHECKS` pass
- [x] User reviews the look of the first deck. Changes to tokens and layout happen now, before more slides use them.

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

### - [x] Checkpoint B
- [x] `CHECKS` pass
- [x] User reviews both sample decks
- [x] `agent-skills:code-reviewer` and `agent-skills:security-auditor` run, and findings are fixed or logged

---

## Phase C: The skill

### - [x] Task 10: SKILL.md, references and install

**Description:** Write `SKILL.md` (name `exec-summary`, a description that triggers on "/exec-summary" and "executive summary of <files>", and the steps from the spec's How It Works, including the no-paths case and the 3-attempt fix loop). Write `references/writing-guide.md` (plain-language rules, a jargon glossary seeded from the samples, the "Example" label rule, no personal data) and `references/summary-format.md` (field guide with a short example). Write `tools/install.py`, which copies `skill/exec-summary` to `~/.claude/skills/exec-summary` and replaces an older copy only after showing what will change. Add `links.json` read and write to `paths.py`. `SKILL.md` must also carry the notes at the end of `tasks/checkpoint-b-review.md` (limits of the coverage check, path spelling, asking before using design images). Write `references/design-rules.md` with the owner's chosen deck standard, and point to it from `SKILL.md`: content comes first, and source info is smaller (12 px), narrower (14% of the table) and lighter; repeated cell values in a table show once, spanning their rows; deck width capped at 1280 px; text sizes at most 22 px body, 18 px small, 44 px titles; calm style, grayscale wireframes, status as text plus color. Tests for these rules already exist in `tests/test_render.py`. Same-named inputs from different folders: the first deck keeps its simple name, a clashing one gets its folder added (`other-SPEC.html`); `links.json` records each deck's input files to detect a clash.

**Acceptance criteria:**
- [ ] `SKILL.md` names every script with its exact command and says when to stop and ask.
- [ ] `install.py` copies the folder; running it again updates it; `--dry-run` lists files only.
- [ ] `paths.py` saves and reads one link per output path and keeps other entries.

**Verification:**
- [ ] `CHECKS` pass. Tests for `install.py` (into a temp home) and `links.json`.
- [ ] Manual: install (ask first), then the skill shows up in a new session's skill list

**Dependencies:** Task 9
**Files:** `skill/exec-summary/SKILL.md`, `references/writing-guide.md`, `references/summary-format.md`, `references/design-rules.md`, `tools/install.py`, `S/paths.py`, tests
**Scope:** M

### - [x] Task 11: Live runs through `/exec-summary`

**Description:** Run the installed skill as a user would, in this repo: first `/exec-summary sample/SPEC_sample.md`, then `/exec-summary sample/SPEC_sample.md sample/plan_sample.md sample/todo_sample.md`. Ask before each publish. Then change one line in a copy of the spec and re-run to check the same link updates. Fix the skill instructions where Claude's run needed manual help, and note what was learned in `SKILL.md`.

**Acceptance criteria:**
- [ ] Success criterion 1: spec-only run gives a link in one run, with no phase or task slides.
- [ ] Success criterion 2: full run gives a separate link with all stories, phases, tasks and checkpoints.
- [ ] Success criteria 3 and 4: diagrams draw in the Artifact; at least 2 wireframes, labelled.
- [ ] Success criterion 6: re-run updates the same link, and the other deck's link is unchanged.

**Verification:**
- [ ] Manual: user opens both links
- [ ] `CHECKS` pass after any fixes

**Result (2026-10-15):** Both decks ran through the installed skill with no fixes to `summary.json` (validate and coverage passed the first time). Spec only: 25 slides, no phase, task, checkpoint or risk slides. Full: 34 slides, 7 stories, 5 phases, 17 tasks, 5 checkpoints, 7 risks. Both decks: 2 diagrams drawn locally and 3 labelled wireframes. Two private Artifacts with separate saved links. A one-line change to the spec, then a re-run, updated the same link (Version 2) and left the other deck's link alone; the real text was then restored (Version 3). Skill fixes from the run are in `SKILL.md`. Still for the owner: open both links and confirm the diagrams draw inside the Artifact (a private Artifact cannot be opened by a script).

**Dependencies:** Task 10
**Files:** `skill/exec-summary/SKILL.md`, `references/*` (fixes only)
**Scope:** M

### - [x] Checkpoint C
- [x] Success criteria 1, 2, 3, 4 and 6 pass
- [x] Success criterion 5: the owner reads the full deck and confirms they understand it without asking about terms
- [x] `agent-skills:code-reviewer` run, and findings are fixed or logged (see `tasks/checkpoint-c-review.md`)
- [x] `summary.json` format is frozen from here (changes need approval) Frozen on 2026-10-15.

---

## Phase D: Finish

### - [x] Task 12: Accessibility, mobile, print, coverage and README

**Description:** Check every slide type against the spec's Design Direction: WCAG AA contrast in both themes, keyboard navigation and visible focus, 360 px layout, and a print stylesheet with one slide per page. Bring `S` coverage to at least 85%. Write `README.md` (what it does, install, usage with examples, the spec-only and full workflows, where outputs go).

**Acceptance criteria:**
- [x] Print to PDF of the full sample deck gives one slide per page with nothing cut off.
- [x] Keyboard alone moves through slides and ticks checkboxes. Focus is visible.
- [x] `python -m pytest --cov` shows at least 85% for `S`.

**Verification:**
- [x] `CHECKS` pass
- [x] Manual: print preview, 360 px and dark mode check with the user (owner approved 2026-10-15)

**Dependencies:** Task 11
**Files:** `deck.css`, `deck.js`, tests, `README.md`
**Scope:** M

### - [x] Checkpoint: Done
- [x] Spec success criteria 1-8 all pass
- [x] User approves (2026-10-15)

## Deferred (owner's choice, not done)
- **Git purge of the old Gmail address (decided 2026-10-15: not now).** The address is still in local-only leftovers: branch `backup-before-rewrite` and `refs/original/*`. `origin/main` is clean (noreply address only). To purge: `git branch -D backup-before-rewrite`, delete every ref under `refs/original/`, `git reflog expire --expire=now --all`, `git gc --prune=now`. Then `git log --all --format=%ae | sort -u` should list only the noreply address.

---

# v1.1: Keynote redesign

Spec: [SPEC-redesign.md](../SPEC-redesign.md) (approved 2026-10-16). Plan: [plan.md](plan.md) > v1.1. The standing Definition of Done at the top of this file applies. In addition, every task:
- gets Claude's browser check before it is reported done: Claude renders the sample decks, opens them with Playwright, takes screenshots in light and dark mode, looks at them, fixes what is wrong and says in the report what was checked and what was seen (`CLAUDE.md` > Verify before reporting). Tests passing is not enough;
- keeps one slide on screen at a time, the same content and the frozen `summary.json` format;
- never shrinks text below the size rules and never weakens a test.

`T` = `skill/exec-summary/templates`. Sample decks: `python -m pytest tests/test_sample.py` writes them to `.tmp/sample/`.

## Phase E: Keynote look

### - [x] Task 13: Keynote tokens, slide frame, top bar and tables

**Description:** Replace the colour tokens in `T/deck.css` with the Keynote set from the spec (light and dark, every token defined first on `:root`). Restyle the slide frame (14 px corners, one soft shadow, `--surface` slide on `--bg`), the top bar (pill buttons, counter, Contents, dark mode switch) and every table (hairline rows, no zebra stripes, small uppercase headers). Make the active slide fill the window below the bar, at most 1280 px wide, and scroll inside itself if its content is taller. Then measure both sample decks at 1280 × 650 and write down every slide that is too tall, so Task 18 knows what to split.

**Acceptance criteria:**
- [x] Every slide type picks up the new tokens in light and dark, with no colour left from the old palette.
- [x] Contrast tests in `tests/test_deck_template.py` check the new tokens and still require WCAG AA (body, muted, source text, impact text) in light, dark and print.
- [x] On a desktop window the page itself never scrolls; a too-tall slide scrolls inside its frame, and the bar stays put.
- [x] A list of slides taller than 650 px (deck, slide id, height) is written in this task's Result note.

**Verification:**
- [x] `CHECKS` pass
- [x] Claude's browser check (Playwright screenshots, looked at before reporting): both sample decks at 1280 × 650 in light and dark; a table slide and the bar look like the preview

**Dependencies:** None (v1 done)
**Files:** `T/deck.css`, `T/deck.html`, `tests/test_deck_template.py`, `tests/test_render.py`
**Scope:** M

**Result (2026-10-16):** Keynote tokens (light, dark, print), 14 px slide frame with one soft shadow, pill bar and buttons, hairline tables with small uppercase headers, impact badges (dot plus word) from the `--hi/--med/--lo` tokens. On a desktop window the page never scrolls: the bar stays put and the active slide scrolls inside its frame. The source column's 0.85 opacity was dropped, because muted text at that opacity was under AA (4.43 on white, 4.21 on a card); source stays 12 px, weight 400, `--muted`. Tests: 316 passed, coverage 87%, ruff clean. Seen in the browser at 1280 x 650, light and dark: criteria table and risks slide look like the preview.

Slides taller than the 560 px slide area at 1280 x 650 (page height is 650; heights are the slide's scroll height), for Task 18 to split or tune:
- Full deck (35 slides, 16 tall): stories 673, criteria 643, criteria-2 657, screens 703, screens-2 783, architecture 589, flow 936, stack 582, tasks 893, tasks-2 734, risks 612, rules 946, decisions 717, decisions-2 582, out-of-scope 582, success 595.
- Spec-only deck (25 slides, 12 tall): stories 673, criteria 643, criteria-2 657, screens 703, screens-2 783, architecture 589, flow 936, stack 582, rules 946, decisions 717, out-of-scope 582, success 595.
- Card styles in Tasks 14-17 will change these numbers; Task 18 measures again.

### - [x] Task 14: Title slide with key-number tiles

**Description:** Rebuild the title slide as in the preview: a pill "Executive summary · <status>", the project name (at most 84 px), the tagline in muted text, up to 4 tiles and a footer with the files covered and the date. `render.py` counts the tiles from the data in this order, skipping zeros: user stories, delivery phases, tasks, checkpoints you approve, acceptance criteria, risks, questions for you. A soft accent glow sits in the top-right of this slide only, and is dropped in print.

**Acceptance criteria:**
- [x] The full sample deck shows 7 user stories, 5 phases, 17 tasks, 5 checkpoints. The spec-only deck shows no phase or task tile.
- [x] Tests: counts match the data, zeros are skipped, at most 4 tiles, the minimal fixture (few fields) still renders, every value is escaped.
- [x] The only `gradient` in the CSS is on the title slide, and the size test allows 84 px only for the project name.

**Verification:**
- [x] `CHECKS` pass
- [x] Claude's browser check (Playwright screenshots, looked at before reporting): title slide of both sample decks in light and dark, and at 360 px

**Dependencies:** Task 13
**Files:** `S/render.py`, `T/deck.css`, `tests/test_render.py`
**Scope:** S

**Result (2026-10-16):** The title slide is a pill ("Executive summary · status"), the project name (up to 84 px, this slide only), the tagline, up to 4 tiles and a footer. Tiles are counted in `render.py` (`stat_counts`), singular for 1, zeros skipped. The footer lists each file with its last-changed date and contents, so the old "This summary covers" table is gone and no information was dropped. The glow is the only `radial-gradient`, on `#s-title`, and print drops it. Tests: 330 passed, coverage 87%, ruff clean. Seen in the browser: full deck shows 7 user stories, 5 delivery phases, 17 tasks, 5 checkpoints you approve (light and dark at 1280 x 650); spec-only deck shows 7 user stories and 17 acceptance criteria, no phase or task tile; at 360 px two columns of tiles, no sideways scroll. A first 360 px look found the phone rule losing to the base rule (four narrow columns); fixed and covered by a test.

### - [x] Checkpoint E1
- [x] `CHECKS` pass
- [x] Claude's browser check of the frame, the bar, a table slide and the title slide in light and dark (no owner review here, by the owner's choice on 2026-10-16; Claude continues to Task 15)

### - [x] Task 15: Stories and risks as cards

**Description:** Stories become cards in a 2-column grid: the "S1" pill, the "As <who>, I want" label and the want text in semi-bold. Risks become row cards: an impact badge (dot plus the word High / Med / Low, coloured with `--hi` / `--med` / `--lo` on their `-bg` tokens), the risk in semi-bold, the handling in muted text below and the source on the right.

**Acceptance criteria:**
- [x] Both slides match the preview in light and dark; the impact word is always visible (not colour alone).
- [x] Badge text meets AA on its badge background in light, dark and print (new contrast test).
- [x] Source text, escaping and "(continued)" splitting work as before (existing tests pass, new markup tests added).

**Verification:**
- [x] `CHECKS` pass
- [x] Claude's browser check (Playwright screenshots, looked at before reporting): stories and risks slides of the full sample deck at 1280 × 650 and 360 px

**Dependencies:** Task 13
**Files:** `S/render.py`, `T/deck.css`, `tests/test_render.py`, `tests/test_deck_template.py`
**Scope:** M

**Result (2026-10-16):** Stories are cards in a 2-column grid (id pill, "As <who>, I want" label, the want text in semi-bold, source quiet below). Risks are row cards (impact badge with dot and word, risk in semi-bold, handling in muted text, source on the right) in a list, no table, 5 per slide (`RISKS_PER_SLIDE`, new) with "(continued)". The existing story-sentence test now checks the visible text, because the sentence is split across two elements on purpose. The impact contrast test from Task 13 already covers the badge in light, dark and print; print gives cards, risk rows and tiles a hairline border. Tests: 337 passed, coverage 87%, ruff clean. Seen in the browser at 1280 x 650 (light and dark): stories 568 of 560 px, risks 568 of 560 px, so each scrolls 8 px inside its frame; Task 18 tunes the limits. At 360 px: risk rows stack, no sideways scroll. The full deck is now 36 slides (risks continue on a second slide).

### - [x] Task 16: Phases, tasks, checkpoints and "please check"

**Description:** Phases become a step strip of cards with the phase id in an accent pill. Tasks show the phase title, then each task as a row card: title in semi-bold, "You will see" text in muted below. Checkpoints become cards with their items as a short list. "Please check" becomes cards with real checkboxes, keeping their localStorage state and keyboard behaviour.

**Acceptance criteria:**
- [x] All four slide types match the Keynote look in light and dark.
- [x] A phase title is never separated from its tasks across slides (existing test passes).
- [x] Checkboxes still tick by keyboard and keep their state after reload (existing tests pass; checked in the browser).

**Verification:**
- [x] `CHECKS` pass
- [x] Claude's browser check (Playwright screenshots, looked at before reporting): these slides in the full sample deck, keyboard only for the checkboxes

**Dependencies:** Task 13
**Files:** `S/render.py`, `T/deck.css`, `tests/test_render.py`
**Scope:** M

**Result (2026-10-16):** Phases are a strip of cards with the phase id in an accent pill (the old "Step N" counter is gone). Tasks are row cards under the phase title (title in semi-bold, "what you will see" muted below, source at the right). Checkpoints are 2-column cards (title, phase, items as a list, source), 4 per slide (`CHECKPOINTS_PER_SLIDE`). "Please check" items are cards; the 20 px checkbox, localStorage and key handling are unchanged. New limits: `TASKS_PER_BLOCK = 4`, `TASK_SLIDE_BUDGET = 5` (lowered from 8 and 10, first guess for Task 18). All source notes are now 12 px (11 px on a phone), as the spec says; before, notes inside cards were 18 px. Tests: 346 passed, coverage 87%, ruff clean. Two existing tests changed with their markup and keep their meaning: the phase-title test now looks for task rows instead of table cells, and the "phase continues" test derives the count from `TASKS_PER_BLOCK`.

Seen in the browser at 1280 x 650: phases and tasks fit (each tasks slide 560 of 560, but there are now 6 of them, so Task 18 should raise the budget); checkpoints 584 of 560, checkpoints-2 fits, risks 568 of 560, check slide 646 of 560 (scrolls inside its frame). Keyboard only on "Please check": Tab to a box, Space ticks it, Tab to the next, Space again, the focus ring shows; after a reload both ticks were still set. A first look found the risks slide at 1478 px (my shared source-column rule put the risk source in the wrong column); fixed, and a test now locks the placement.

### - [x] Task 17: Diagrams and wireframes in the Keynote look

**Description:** Mermaid draws with the `base` theme and `themeVariables` read from the CSS tokens at draw time, so diagrams match light and dark; the print copy uses the light values. The diagram fallback table uses the new table style. Wireframes stay grayscale with their "Example layout, not the final design" label, inside a card.

**Acceptance criteria:**
- [x] Both diagrams draw in light and dark with token colours; switching mode redraws them; print shows the light copy.
- [x] With Mermaid blocked, the fallback tables show in the new style.
- [x] Tests: the `base` theme and token-based colours are in `deck.js`; wireframe label unchanged.

**Verification:**
- [x] `CHECKS` pass
- [x] Claude's browser check (Playwright screenshots, looked at before reporting): both diagram slides online and offline, light and dark; the screens slide

**Dependencies:** Task 13
**Files:** `T/deck.js`, `T/deck.css`, `tests/test_deck_template.py`
**Scope:** S

**Result (2026-10-16):** Mermaid draws with the `base` theme. `diagramTheme(mode)` in `deck.js` reads the colours from the deck's own CSS tokens (surface, card, text, muted, accent, accent-soft, line); for the print copy it flips `data-theme` to light for an instant and puts it back, so print always gets the light values. Switching the Dark mode switch redraws the diagrams. Wireframes sit in a card, stay grayscale and keep their "Example layout, not the final design" label; print gives them a hairline border. The fallback table already used the new table style. Tests: 351 passed, coverage 87%, ruff clean.

A first look found that setting `themeVariables.fontFamily` makes Mermaid drop the font from the whole diagram, so labels turned monospace (the `<pre>` font) and 11 of 16 were cut off. I compared with the v1 deck rendered from the earlier commit (proper font, 6 of 16 flagged by the same measure, which is a measuring artefact, nothing is cut off on screen). The font line is removed and a test now forbids it.

Seen in the browser at 1280 x 650, online: both diagrams draw (state "drawn", picture and print copy present) in light and dark, text complete and readable, `data-theme` unchanged after drawing. Offline (Mermaid script removed): the fallback table shows in the new style. Screens slide: grayscale wireframes in cards with the label. The stale `.tmp/sample/offline.html` from an earlier session was in the old look; it is regenerated from the current deck.

### - [x] Checkpoint E2
- [x] `CHECKS` pass (351 passed, coverage 87%, ruff clean, 2026-10-16)
- [x] Owner reviews both sample decks, every slide type, in light and dark (approved 2026-10-16 after two changes; first finding 2026-10-16: text-only slides look too plain, so Task 17b was added; the owner reviews the rest after it)

### - [x] Task 17b: Text-only slides as "split stage" and "launch stage"

**Description:** The Goal slide and the notes slides (for example "The build plan in short", "Phase 1: run it on your PC") are plain text on white. The owner chose from three previews (https://claude.ai/artifact/C9EHdg17Tc9UV9B8nJZwy8, 2026-10-16): **Option B, split stage**, for text-heavy slides and **Option C, launch stage**, for very short ones. `render.py` picks the style from the text itself, so no `summary.json` change:
- **Short** (all paragraphs together 280 characters or fewer, first guess): launch stage. Dark stage in both modes, centred, eyebrow, title up to 64 px, a short accent rule, the paragraphs as centred lines (first one in the main text colour, the rest muted), source at the bottom, a soft accent glow at the top.
- **Otherwise:** split stage. Left: a solid accent panel with the eyebrow, the title (44 px) and the source. Right: one row per paragraph, with an accent dot and hairlines between rows; the first sentence of each paragraph is semi-bold in the main text colour, the rest muted.
- The eyebrow is the part of the source after the last " > " (for example "Overview"); with no " > " there is no eyebrow.
- Print: both styles print light (the launch stage uses the light tokens and drops its glow; the split panel gets a hairline border instead of the solid fill if the fill does not print).

**Acceptance criteria:**
- [x] In the full sample deck, "The build plan in short" uses the split stage and "Phase 1: run it on your PC" uses the launch stage, in light and dark.
- [x] Contrast tests: text on the accent panel (title, eyebrow, source) and every launch-stage colour pass WCAG AA in light, dark and print.
- [x] Size and gradient tests updated to the new spec rules: 64 px allowed only for the launch-stage title, glows allowed only on the title slide and the launch stage.
- [x] Render tests: the 280-character threshold picks the style (just under, just over); the eyebrow comes from the source; a source with no " > " has no eyebrow; the first-sentence split handles a paragraph with one sentence and text with abbreviations like "e.g."; all text stays escaped.
- [x] 360 px: the split stage stacks (panel on top), nothing scrolls sideways.

**Verification:**
- [x] `CHECKS` pass, coverage 85% or more
- [x] Claude's browser check (Playwright screenshots, looked at before reporting): both styles in light and dark at 1280 × 650 and 360 px, and in print preview

**Dependencies:** Task 13
**Files:** `S/render.py`, `T/deck.css`, `tests/test_render.py`, `tests/test_deck_template.py`, `SPEC-redesign.md`
**Scope:** M

**Owner changes after the first look (2026-10-16):** the launch stage now uses the deck's own theme colours instead of a dark stage (it did not blend in), and the example screens are back to the old layout, two side by side with blocks in one column (`WIREFRAMES_PER_SLIDE` 2). Trade-off: at 1280 x 650 the two example-screens slides scroll inside their frame (723 and 803 px of 560); at 1920 x 1000 nothing scrolls. This relaxes Task 18's "no slide scrolls" for those two slides, by the owner's choice.

**Result (2026-10-16):** `render_text_stage` in `render.py` renders the Goal slide and every notes slide: total text up to `LAUNCH_STAGE_CHARS = 280` gives the launch stage, longer text the split stage (first sentence of each paragraph in bold; "e.g." and similar do not end a sentence; the eyebrow is the last part of the source). In the full sample deck the Goal slide and 5 notes are split, 2 notes are launch. CSS: four `--stage*` tokens (dark in both modes, light in print), `.slide:has(> .stage)` has no padding so the stage fills the frame, the dot ring is an outline (no second box-shadow). `test_sample.py` "other notes" test now compares visible text because the first sentence is wrapped in bold (same intent, nothing weakened). Tests: 366 passed, coverage 87%, ruff clean.

Seen in the browser: at 1280 x 650 all 8 stage slides of the full deck have scroll height equal to the 560 px slide area (no scrolling); both styles in light and dark (dark: light-blue panel with dark text, readable); at 360 px the split stage stacks with the panel on top and the page does not scroll sideways (345 of 360 px; launch 360 of 360); print emulation shows both styles light, the panel with a soft fill and hairline, no glow. Not checked: Print to PDF page count (Task 18).


## Phase F: Fit and finish

### - [x] Task 18: Every slide fits 1280 × 650; 360 px, print and keyboard checks

**Description:** Measure every slide of both sample decks at 1280 × 650 and 1920 × 1000. Where a slide is too tall, lower its per-slide limit in `render.py` (`STORIES_PER_SLIDE`, `ROWS_PER_SLIDE`, `STEPS_PER_SLIDE`, `TASK_SLIDE_BUDGET`, or a new limit for risk cards) so it continues on a "(continued)" slide. Never reduce text size. Then check 360 px, Print to PDF and keyboard-only use.

**Acceptance criteria:**
- [x] At 1280 × 650, no slide of either sample deck scrolls (measured with a script in the page; numbers in the Result note).
- [x] 360 px: nothing scrolls sideways except a wide table inside its own box.
- [x] Print to PDF: one slide per page, light colours, nothing cut off. Keyboard: arrows, Home, End, checkboxes, visible focus.
- [x] Updated split tests for any changed limit; sample tests still find all 7 stories, 5 phases, 17 tasks, 5 checkpoints.

**Verification:**
- [x] `CHECKS` pass, coverage 85% or more
- [x] Claude's browser check (Playwright screenshots, looked at before reporting): the measurements above, a PDF page count equal to the slide count

**Dependencies:** Tasks 14-17
**Files:** `S/render.py`, `T/deck.css`, `tests/test_render.py`, `tests/test_sample.py`
**Scope:** M

**Result (2026-10-16):** Limits lowered in `render.py`: `ROWS_PER_SLIDE` 8 to 6, `WIREFRAMES_PER_SLIDE` 2 to 1, `RISKS_PER_SLIDE` 5 to 4, `CHECKPOINTS_PER_SLIDE` 4 to 3. New: `CHECKS_PER_SLIDE = 5` (the "Please check" slide now continues as `check-2`; the hint line is only on the first page), `RULE_ITEMS_PER_SLIDE = 9` (the Always / Asks you first / Never groups are packed into slides, a group is never split), `FLOW_SIDEWAYS_NODES = 4` (a step-by-step flow with more boxes is drawn left to right with narrow boxes, so text stays readable). `TASK_SLIDE_BUDGET` stays 5: the fullest task slide is 467 px of 512, so a budget of 6 would not fit. CSS: table cell padding 10 to 8 px, the example screen's blocks sit in two columns on desktop, and a tall diagram is scaled to the window (`max-height: calc(100dvh - 245px)`), never scrolled. Text sizes were not reduced anywhere. Tests changed with their limits (four tests now derive their numbers from the constants); new tests cover rules packing, the check slide paging, flow direction and the new CSS. Tests: 371 passed, coverage 87%, ruff clean.

Measured in the browser (scroll height against the slide area, every slide of both sample decks): 1280 x 650 full 48 slides and spec 32 slides, 0 too tall; 1366 x 680 and 1920 x 1000 also 0 too tall. Before: 15 of 40 slides too tall in the full deck, 11 of 25 in the spec deck. 360 px: no slide of either deck scrolls sideways. Print (Print to PDF, A4 landscape, `pdfinfo`): 48 pages for 48 slides and 32 for 32; pages looked at: light colours, nothing cut off, the launch stage prints without its glow and the split panel as a hairline box. Keyboard: arrows, Home and End move between slides; a tick box takes focus with Tab, Space ticks it, a 2.4 px focus ring shows, ArrowLeft still moves to the previous slide, ticks are kept after a reload.

Notes: a long flow leaves empty space below it (the diagram is only as tall as it needs to be). The deck is now 48 slides (was 40) because of the lower limits; the owner may prefer a different trade-off at the v1.1 review. While checking print, a first PDF showed one page only because the browser tool was still set to screen media from an earlier call; not a deck fault (the earlier v1 PDFs had the same 1-page result when produced that way).


### - [ ] Task 19: Design rules, spec, install, republish and code review

**Description:** Rewrite `references/design-rules.md` for the Keynote look (sizes, tiles, cards, the one glow, fit by splitting). Point `SPEC.md` > Design Direction to `SPEC-redesign.md`, and update `README.md` if it describes the look. Run `agent-skills:code-reviewer` on the v1.1 changes and handle findings per `CLAUDE.md`. Ask before installing the skill (`python tools/install.py`, shows the changes first) and before republishing both sample decks to their existing Artifact links.

**Acceptance criteria:**
- [x] `design-rules.md` matches what the CSS and tests enforce; `SPEC.md` points to the redesign.
- [x] Review findings fixed or logged in `tasks/v1.1-review.md`.
- [ ] The installed skill is up to date, and both Artifact links show the Keynote decks (same URLs, new version).

**Verification:**
- [ ] `CHECKS` pass; `python tools/install.py` says "up to date"
- [ ] Owner check: you open both links on a laptop, checks one slide fits and the diagrams draw

**Dependencies:** Task 18
**Files:** `skill/exec-summary/references/design-rules.md`, `SPEC.md`, `README.md`, `tasks/v1.1-review.md`
**Scope:** S

**Progress (2026-10-16):** docs done (`design-rules.md`, `SPEC.md`, `README.md`) and the code review done (`tasks/v1.1-review.md`). Still open, each waits for the owner's OK: `python tools/install.py`, republishing both sample Artifacts, and the owner check on the published links.

### - [ ] Checkpoint: v1.1 Done
- [ ] `SPEC-redesign.md` success criteria 1-8 all pass
- [ ] Owner approves the published decks
