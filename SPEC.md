# Spec: Executive Summary Skill

Status: Draft, awaiting approval
Date: 2026-10-14

## Objective

A Claude Code skill, `exec-summary`, that turns planning files into an executive summary presentation for a non-programmer. The user names the files when they run it, for example `/exec-summary SPEC.md` or `/exec-summary docs/spec.md tasks/plan.md tasks/todo.md`. File names are never fixed: the skill decides what each file contains from its content, and builds only the slides that content supports.

Typical inputs are the files agent-skills makes (a spec, a plan and a todo list), but they can have any name and can be summarized at different times. For example, the owner can check the spec alone as soon as it is written, and run the skill again later on the spec plus the plan.

The project owner reads the presentation to check that the planned system is what they want before any code is written. It shows the user stories and acceptance criteria in plain English. Technical content is shown as an architecture diagram, a flow chart and simple tables. Screens are shown as example wireframes.

The output is one self-contained `.html` file, published as a private Claude Artifact so the owner gets a link they can open and share.

### Users

- **Owner (primary reader):** knows what they want the system to do, but not how code works. Reads the deck, approves or asks for changes.
- **Claude (operator):** runs the skill on the files the owner names, writes the summary content, runs the scripts and publishes.

### User stories

1. As the owner, I type `/exec-summary` followed by one or more file names and get a link to a presentation of those files.
2. As the owner, I can summarize just my spec right after it is written, before any plan exists, and get a deck that covers only the spec.
3. As the owner, I read in plain English what the system will do for me: the goal, the user stories and how each one will be checked (acceptance criteria).
4. As the owner, I see the parts of the system and how they connect in an architecture diagram, without needing to know the technology names.
5. As the owner, I follow a flow chart of what happens step by step when I use the main feature.
6. As the owner, I see example wireframes of the main screens, so I can picture the app.
7. As the owner, I see the build phases, the checkpoints where I must approve something, and the risks, in simple tables.
8. As the owner, I can check any statement against the source file and section it came from.
9. As the owner, when I run `/exec-summary` again on the same files after they change, the same link shows the new version.

### Acceptance criteria

- **Inputs:** The skill takes one or more file paths after the command, relative to the current project or absolute, in any order. Markdown (`.md`) and plain text (`.txt`) are accepted. A path that does not exist, or a file of another type, stops the run with a message naming it. With no paths, the skill lists the likely planning files it finds (Markdown files whose name or first heading mentions spec, plan, todo or tasks) and asks the user which to use. It never picks files on its own.
- **Content-driven slides:** Claude reads each file and records what kinds of content it found (for example user stories, acceptance criteria, tech stack, data model, phases, tasks, checkpoints, risks, rules, success criteria). A slide is built only when its content exists in the given files. A spec alone gives a deck without phase and task slides; a todo alone gives a deck of phases, tasks and checkpoints. The deck does not warn about files that were not given.
- **Sections the skill does not recognize:** A section that fits none of the slide types is still shown, as a plain-language "Other notes" slide, unless Claude records it as skipped with a reason (for example "code example, not useful to the owner").
- **Plain language:** Every slide aimed at the owner uses everyday words. A technical term appears only with a short plain explanation the first time, for example "SQLite (a database stored in one file on your computer)". Code, file paths and commands do not appear on owner slides.
- **Completeness:** Every section heading in the input files is either the source of at least one deck item or listed as skipped with a reason. Every user story, task and checkpoint found in the inputs appears in the deck. A script checks this against the files and the build fails if anything is dropped.
- **No invention:** The deck contains only facts from the input files. Every content item carries a source reference (file and section heading). Anything Claude infers, such as a wireframe layout, is labelled "Example".
- **Diagrams:** At least one architecture diagram (system parts and connections) and one flow chart (main user journey). Diagrams are written as structured data (nodes and edges) and the renderer converts them to Mermaid, so Claude never writes raw Mermaid syntax.
- **Wireframes:** If the project has images in `design/`, `docs/design/` or `mockups/`, the deck shows them. Otherwise it shows 2-4 grayscale HTML wireframes of the main screens, built from a fixed set of components and labelled "Example layout, not the final design".
- **Tables:** Phases and checkpoints, tech stack (each choice with a plain explanation), risks, decisions already made, out of scope, and "what the AI will ask you before doing".
- **Review aid:** A final "Please check" slide lists the checkpoints the owner must approve and the open questions. Each item has a checkbox whose state is kept in the viewer's browser only.
- **Format:** Slide-style sections, one topic per slide, with a contents list, arrow-key navigation and a print layout of one slide per page (so "Print to PDF" works). Readable at 360 px wide and on desktop. Light and dark mode.
- **Output name:** Derived from the inputs, so different file sets give different decks. One file gives `docs/exec-summary/<file name>.html` (for example `SPEC.html`). Several files give `docs/exec-summary/<name1>+<name2>+....html` in the order given (for example `SPEC+plan+todo.html`). `--out <path>` overrides it.
- **Publishing:** The HTML is published as a private Claude Artifact. Each output file has its own Artifact link, saved in `docs/exec-summary/links.json` (output path to URL), so re-running on the same files updates the same link, and a spec-only deck and a full deck keep separate links.
- **Sources slide:** The title slide lists the files the deck covers, with each file's last-modified date, so the owner knows what they are looking at.
- **Language:** English.
- **Size and speed:** The HTML file stays under 2 MB without design images. The scripts finish in under 5 seconds.

### Out of scope for v1

- Running automatically through a hook (manual `/exec-summary` only)
- Thai or bilingual output
- Canva, Google Slides or PowerPoint export
- AI-generated images
- Editing the spec or plan from the deck, or sending comments back into the files
- Summaries of anything other than the agent-skills spec, plan and todo files

## How It Works

```
/exec-summary <file> [<file> ...] [--out <path>]
  1. Check the paths exist (no paths: list candidates and ask)
  2. scripts/outline.py    <files>                       (headings, list items, checkboxes, task headings per file, as JSON)
  3. Claude reads the files and the outline, and writes .tmp/exec-summary/summary.json
                                                         (plain English, a source on every item, skipped sections with reasons)
  4. scripts/validate.py   summary.json                  (shape and required fields)
  5. scripts/check_coverage.py   summary.json <files>          (every heading used or skipped, nothing dropped)
  6. scripts/render.py     summary.json -> docs/exec-summary/<name>.html
  7. Claude publishes the HTML as a private Artifact and saves the URL in links.json
```

Claude does the judgment (plain-language rewriting, choosing diagram nodes, screen layouts). The scripts do everything deterministic (checking, counting, drawing, HTML). This follows the WAT split in the parent `CLAUDE.md`.

If step 3 or 4 fails, Claude fixes `summary.json` and runs the scripts again, at most 3 times, then reports the remaining errors to the user.

## Tech Stack

| Concern | Choice |
|---|---|
| Skill format | Claude Code skill: `SKILL.md` with frontmatter, plus `scripts/`, `templates/`, `references/` |
| Scripts | Python 3.10+, standard library only, so the skill runs in any project without installing packages |
| Content format | `summary.json`, described by `schema/summary.schema.json` (documentation) and checked by `validate.py` |
| HTML | `string.Template` and `html.escape` from the standard library; CSS and JS inlined into one file |
| Diagrams | Mermaid, loaded from `cdn.jsdelivr.net/npm/mermaid@11.4.1` (pinned). If it fails to load, the diagram's node and edge list shows as a table instead |
| Wireframes | Plain HTML and CSS boxes from a fixed component set |
| Publishing | Claude Artifact tool (private by default) |
| Tests | pytest (dev only) |
| Lint | ruff (dev only) |

## Commands

```
Install skill:  python tools/install.py            # copy skill/exec-summary to ~/.claude/skills/exec-summary
Outline:        python skill/exec-summary/scripts/outline.py <file> [<file> ...]
Validate:       python skill/exec-summary/scripts/validate.py <summary.json>
Coverage:       python skill/exec-summary/scripts/check_coverage.py <summary.json> <file> [<file> ...]
Render:         python skill/exec-summary/scripts/render.py <summary.json> [--out <out.html>]
Tests:          python -m pytest
Lint:           ruff check .
Sample deck:    python -m pytest tests/test_sample.py   # also writes the sample decks to .tmp/sample/
```

## Project Structure

```
skill/exec-summary/          # The skill. This folder is what gets installed.
  SKILL.md                   # Trigger, steps, rules for Claude
  references/
    writing-guide.md         # Plain-language rules and a jargon-to-plain glossary
    summary-format.md        # Field-by-field guide to summary.json with a short example
  schema/
    summary.schema.json      # JSON Schema of summary.json
  scripts/
    outline.py               # Markdown structure of each input file (headings, lists, checkboxes) as JSON
    validate.py              # Shape and required-field checks
    check_coverage.py              # Every input heading used or skipped; stories, tasks, checkpoints all present
    render.py                # summary.json -> one HTML file
    mermaid.py               # Node/edge data -> Mermaid text, with label escaping
    wireframe.py             # Screen description -> HTML wireframe
  templates/
    deck.html, deck.css, deck.js
tools/
  install.py                 # Copies the skill into ~/.claude/skills
tests/
  fixtures/billing/          # Hand-checked summary.json files for the samples (spec only; spec + plan + todo)
  test_validate.py, test_check_coverage.py, test_mermaid.py, test_wireframe.py, test_render.py, test_sample.py
sample/                      # Sample inputs (Billing Record project): SPEC_sample.md, plan_sample.md, todo_sample.md
.tmp/                        # Scratch output (gitignored)
```

In a target project, the skill writes `.tmp/exec-summary/summary.json` (scratch), `docs/exec-summary/<name>.html` (the deck) and `docs/exec-summary/links.json` (Artifact links per deck).

## Slide Catalog

Slides appear in this order, and only when the content they need was found in the input files, whatever the file is called. The "Typical source" column shows where that content usually is in agent-skills files; it is a hint, not a rule.

| # | Slide | Built when the inputs contain | Typical source |
|---|---|---|---|
| 1 | Title: project name, one-line goal, status, files covered | always | any |
| 2 | The problem and the goal, in 3-5 plain sentences | an objective, overview or purpose | spec Objective, plan Overview |
| 3 | Who uses it and what they can do (user stories as cards) | user stories or feature list | spec User stories |
| 4 | How we will know it works (criteria per story, as a table) | acceptance criteria | spec, todo |
| 5 | Example screens (wireframes or design images) | screens, UI or design notes, or user-facing features | spec Design Direction, stories |
| 6 | How it works: architecture diagram | system parts, tech stack, structure or architecture decisions | spec Tech Stack, plan Architecture |
| 7 | Step by step: flow chart of the main journey | a described user journey or process | spec Objective, stories |
| 8 | What information it keeps (simplified, no column types) | a data model | spec Data Model |
| 9 | Building blocks: tech stack with plain explanations | a tech stack | spec Tech Stack |
| 10 | Delivery phases and timeline | phases or milestones | spec Delivery Phases, plan Task List |
| 11 | Tasks by phase (task title, what you will see working) | a task list | todo, plan |
| 12 | Checkpoints you approve | checkpoints or approval steps | plan, todo |
| 13 | Risks and how they are handled | risks | plan |
| 14 | Rules the AI follows (always / asks you first / never) | boundaries or rules | spec Boundaries, plan How to Build |
| 15 | Decisions made and not included | decisions or out-of-scope lists | spec |
| 16 | How we measure success | success criteria | spec |
| 17 | Other notes | sections that fit none of the above and are not skipped | any |
| 18 | Please check: approvals and open questions, with checkboxes | always | any |

## summary.json (outline)

```json
{
  "project": { "name": "", "tagline": "", "status": "", "date": "" },
  "sources": [{ "path": "SPEC.md", "modified": "2026-10-14", "found": ["stories", "criteria", "stack", "data", "rules", "success"] }],
  "skipped": [{ "src": "SPEC.md > Code Style", "reason": "" }],
  "notes": [{ "title": "", "text": [""], "src": "" }],
  "goal": { "text": [""], "src": "SPEC.md > Objective" },
  "stories": [{ "id": "S1", "as": "", "want": "", "so": "", "criteria": [""], "src": "" }],
  "screens": [{ "title": "", "example": true, "blocks": [{ "type": "header|nav|stats|chart|list|form|button|image|text", "label": "" }] }],
  "diagrams": [{ "id": "", "kind": "architecture|flow", "title": "", "nodes": [{ "id": "", "label": "", "group": "" }], "edges": [{ "from": "", "to": "", "label": "" }], "src": "" }],
  "data": [{ "name": "", "plain": "", "fields": [""], "src": "" }],
  "stack": [{ "part": "", "choice": "", "plain": "", "src": "" }],
  "phases": [{ "id": "", "title": "", "goal": "", "tasks": [{ "id": "", "title": "", "you_will_see": "", "src": "" }], "src": "" }],
  "checkpoints": [{ "title": "", "phase": "", "items": [""], "src": "" }],
  "risks": [{ "risk": "", "impact": "High|Med|Low", "handling": "", "src": "" }],
  "rules": { "always": [""], "ask_first": [""], "never": [""], "src": "" },
  "decisions": [{ "text": "", "src": "" }],
  "out_of_scope": [{ "text": "", "src": "" }],
  "success": [{ "text": "", "phase": "", "src": "" }],
  "open_questions": [""]
}
```

Only `project`, `sources` and `skipped` are required. Every other section is optional, and leaving one out drops its slide. Each `src` has the form `<path> > <heading>`, with the path exactly as given on the command line. The full field list and limits (for example at most 12 nodes per diagram) live in `schema/summary.schema.json`.

## Code Style

- Python 3.10+, standard library only in `skill/`. Type hints on every function.
- Small pure functions. File I/O only in each script's `main()`.
- Every string from `summary.json` is escaped before it goes into HTML or Mermaid. No raw HTML from the JSON.
- Scripts exit 0 on success and 1 on failure, and print errors as `path.to.field: message`, one per line.
- snake_case for files, functions and variables.

Example:

```python
# skill/exec-summary/scripts/mermaid.py
def escape_label(text: str) -> str:
    """Make a node or edge label safe inside Mermaid quotes."""
    return text.replace('"', "#quot;").replace("\n", " ").strip()


def to_flowchart(nodes: list[dict], edges: list[dict], direction: str = "LR") -> str:
    lines = [f"flowchart {direction}"]
    for n in nodes:
        lines.append(f'  {n["id"]}["{escape_label(n["label"])}"]')
    for e in edges:
        label = f'|"{escape_label(e["label"])}"|' if e.get("label") else ""
        lines.append(f"  {e['from']} -->{label} {e['to']}")
    return "\n".join(lines)
```

## Design Direction

- Calm, document-like slides. Neutral background, dark text, one accent color.
- One sans-serif family, at most 3 text sizes per slide. Large slide titles, short bullet text.
- Tables with clear headers and zebra rows. No more than about 8 rows per slide; longer tables continue on the next slide.
- Wireframes are grayscale boxes with labels, clearly different from a real design.
- Status labels (High/Med/Low, phase) use text plus color, never color alone.
- Avoid gradients, glow, emoji and stock illustrations.
- WCAG 2.1 AA contrast in both light and dark mode. Full keyboard navigation.

## Testing Strategy

- **Unit (pytest):**
  - `validate.py`: a valid file passes; missing required fields, wrong types, unknown block types, edges that point to missing nodes and diagrams over the node limit fail with clear messages.
  - `outline.py`: finds headings, list items, checkboxes and task headings in each sample file, and works whatever the file is named (tests copy the samples to other names).
  - `check_coverage.py`: passes when every heading is used or skipped; fails, naming the heading, when a section is neither; finds 7 user stories in the spec sample and 17 tasks and 5 checkpoints in the todo sample, and fails when one is missing from `summary.json`. A `src` that names a file or heading not in the inputs fails.
  - `mermaid.py`: quotes, new lines, brackets and `<script>` in labels are escaped; output parses as a valid flowchart header and node/edge lines.
  - `wireframe.py`: each block type renders; unknown types are rejected.
  - `render.py`: every slide type renders; an absent section drops its slide with no warning; the output name follows the input names, and `--out` overrides it; HTML special characters in any field are escaped.
- **Sample tests:** Two fixtures from the Billing Record samples, each with a hand-checked `summary.json`:
  - **Spec only** (`sample/SPEC_sample.md`): the deck has the story, criteria, screens, architecture, data, stack, rules and success slides, and no phase, task or checkpoint slides.
  - **Spec, plan and todo** (all three samples): the deck also has phases, all 17 tasks, checkpoints and risks, two diagrams and at least two wireframes, and is under 2 MB.
- **Manual:**
  - Open the sample deck in a browser at 360 px and desktop widths, in light and dark mode; check that the diagrams draw and that Print to PDF gives one slide per page.
  - Plain-language check: the owner reads the sample deck and confirms they can explain what the Billing Record app does, its phases and what they must approve.
- **Coverage target:** 85% lines for `skill/exec-summary/scripts/`.

## Boundaries

**Always**
- Use only the files the user named. Take every fact from them and attach its source reference.
- Label anything inferred (wireframes, simplified diagrams) as "Example".
- Run `validate.py` and `check_coverage.py` before rendering, and render only when both pass.
- Publish as a private Artifact and reuse the saved URL on re-runs.
- Run lint and tests before every commit in this repo.

**Ask first**
- Adding any dependency to `skill/` (it must stay standard library only).
- Changing the `summary.json` format after v1 ships (existing decks depend on it).
- Publishing to anything other than a private Artifact, or sharing the link.

**Never**
- Edit any input file.
- Read or summarize files the user did not name, or guess which files to use when none are named.
- Put secrets, `.env` values, real names, account numbers or personal data in the deck, even if a source file contains them.
- Let Claude write raw Mermaid or raw HTML into `summary.json`.
- Load scripts from anywhere other than the pinned jsdelivr Mermaid URL.
- Delete or skip failing tests to get to green.

## Success Criteria

1. `/exec-summary sample/SPEC_sample.md` produces a published Artifact link in one run, with no manual fixes to `summary.json`, and the deck has no phase or task slides.
2. `/exec-summary sample/SPEC_sample.md sample/plan_sample.md sample/todo_sample.md` produces a separate link whose deck contains all 7 user stories with their acceptance criteria, all 5 phases, all 17 tasks and all checkpoints. `check_coverage.py` passes.
3. The architecture diagram and the flow chart draw without errors in the Artifact.
4. At least 2 wireframes appear, each labelled as an example.
5. The owner reads the full sample deck and says they understand what the app does, how it will be built and what they need to approve, without asking what a technical term means.
6. Re-running on the same files after one changes updates that deck's link, and leaves other decks' links alone.
7. Every unit and sample test passes, ruff is clean, and script coverage is at least 85%.
8. The deck works at 360 px, in light and dark mode, and prints to PDF one slide per page.

## Decisions (resolved 2026-10-14)

1. **Output:** One self-contained HTML file, published as a private Claude Artifact. Canva and Google Slides were considered and left out: diagrams there are harder to keep accurate, and they need extra accounts or credits.
2. **Language:** English.
3. **Trigger:** Manual, through `/exec-summary <files>` (or "make the executive summary of <files>"), at any stage. No hook.
4. **Inputs:** Named by the user on each run, with no fixed file names. Slides follow the content found, not the file names.
5. **Mockups:** Use design images if the project has them. Otherwise draw HTML wireframes, labelled as examples.
6. **Install location:** This repo holds the source. `tools/install.py` copies the skill to `~/.claude/skills/exec-summary`, so it works in every project.

## Open Questions

None.
