# exec-summary

A Claude Code skill that turns planning files (a spec, a plan, a task list) into a short slide-style
presentation for a project owner who knows what they want but not how code works. The owner reads it
and checks that the planned system is what they want, before any code is written.

- Plain language, no jargon. Every item names the file and heading it came from (a quiet "Source" column).
- One self-contained HTML file: works offline, in light and dark, on a phone (360 px) and in print (one slide per page).
- Published as a **private** Claude Artifact. Re-running on the same files updates the same link.

Claude does the judgment (wording, diagram nodes, screen sketches). Python scripts do the rest
(checking, counting, drawing, HTML). Nothing is installed beyond Python 3.10+ and the standard library.

## Install

```
python tools/install.py --dry-run     # list what would be copied
python tools/install.py               # copy skill/exec-summary to ~/.claude/skills/exec-summary
python tools/install.py --yes         # replace an older installed copy
```

An older copy is replaced only with `--yes`. Running `install.py` again says "up to date" when nothing changed.

## Use

In any project, in Claude Code, name the files:

```
/exec-summary SPEC.md
/exec-summary SPEC.md tasks/plan.md tasks/todo.md
```

Or ask in words: "make an executive summary of SPEC.md for the owner".

| You give | You get |
|---|---|
| a spec only | goal, stories, criteria, screens, diagrams, data, stack, rules, decisions, success. No phase or task slides. |
| spec + plan + todo | all of the above, plus phases, tasks, checkpoints and risks |

Claude only reads the files you name. It asks before using design images, before publishing and before
sharing the link. It never edits your files, and it leaves out secrets and personal data.

### What happens in a run

1. `outline.py` reads each file's structure (headings, lists, checkboxes, `Task N` headings).
2. Claude writes `.tmp/exec-summary/<name>.json` in plain language, with a `src` on every item.
3. `validate.py` checks the shape; `check_coverage.py` checks that every heading was used or skipped (with a reason) and no story, task or checkpoint was dropped.
4. `render.py` writes the deck to `docs/exec-summary/<name>.html` (for example `SPEC.html`, or `SPEC+plan+todo.html`).
5. After you agree, Claude publishes it as a private Artifact and saves the link in `docs/exec-summary/links.json`.

### Where things go

| What | Where | In git? |
|---|---|---|
| the deck | `docs/exec-summary/<name>.html` | no |
| saved Artifact links | `docs/exec-summary/links.json` | no |
| Claude's summary file | `.tmp/exec-summary/<name>.json` | no |
| the skill | `skill/exec-summary/` (installed to `~/.claude/skills/exec-summary`) | yes |

## Run the scripts by hand

```
python skill/exec-summary/scripts/outline.py <file> [<file> ...]
python skill/exec-summary/scripts/validate.py <summary.json>
python skill/exec-summary/scripts/check_coverage.py <summary.json> <file> [<file> ...]
python skill/exec-summary/scripts/render.py <summary.json> [--out <out.html>] [--design-dir <folder>]
python skill/exec-summary/scripts/paths.py url <deck.html>              # saved Artifact link, if any
python skill/exec-summary/scripts/paths.py set-url <deck.html> <link>   # save it after publishing
```

Try it on the samples in `sample/`: `python -m pytest tests/test_sample.py` also writes both sample decks
to `.tmp/sample/`.

## Develop

```
pip install -r requirements-dev.txt     # ruff and pytest-cov, development only
python -m ruff check . ; python -m ruff format --check .
python -m pytest -q
python -m pytest --cov                   # fails below 85% for skill/exec-summary/scripts
```

- `SPEC.md` is the source of truth; `tasks/plan.md` and `tasks/todo.md` hold the plan and progress.
- The `summary.json` format (`skill/exec-summary/schema/summary.schema.json`) is frozen; changing it needs the owner's approval.
- Deck look and rules: `skill/exec-summary/references/design-rules.md`. Template: `skill/exec-summary/templates/`.
- The repo is public. Never commit `.env`, `credentials.json`, `token.json`, `.tmp/` or `docs/exec-summary/`.
