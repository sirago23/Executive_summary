# Executive summary skill - Project Rules

Local rules for this project only. The parent WAT `CLAUDE.md` in Downloads also applies; no known conflicts.

## Project
- Name: Executive summary skill
- Purpose: the `exec-summary` Claude Code skill. It turns planning files (spec, plan, todo) into a plain-language slide deck for a non-programmer owner, published as a private Artifact. Details: `SPEC.md`, plan: `tasks/plan.md`, tasks: `tasks/todo.md`, usage: `README.md`.
- Stack: Python 3.10+, standard library only inside `skill/`. Dev tools (`ruff`, `pytest`, `pytest-cov`) are in `requirements-dev.txt`. The deck is one HTML file; Mermaid is its only external script.
- Commands:
  - Tests: `python -m pytest -q` (coverage: `python -m pytest --cov`, must stay at 85% or more)
  - Lint: `python -m ruff check .` and `python -m ruff format --check .`
  - Install the skill: `python tools/install.py [--dry-run] [--yes]`
  - Render a deck: `python skill/exec-summary/scripts/render.py <summary.json>`
  - All script commands: see `SPEC.md` > Commands.
- The `summary.json` format is frozen since Checkpoint C; changing it needs the owner's approval.
- Repo: https://github.com/sirago23/Executive_summary (public, branch `main`).

## Boundaries
- The repo is public. Never commit `.env`, `credentials.json`, `token.json`, `.tmp/` or `node_modules/`.
- Check that nothing sensitive is staged before every push.
- Keep `session-handoff/` and `.tmp/` out of git.

## Review findings
- After a code review or security audit, fix without asking:
  - code review: Critical and Important
  - security audit: Critical, High and Medium
- Fix lower-ranked findings when cheap. Otherwise log them in `tasks/<checkpoint>-review.md` with a one-line reason.
- After fixing, re-run each reproduction from the report and the full test suite, and say which findings are confirmed fixed.
- Still ask first for anything the Boundaries section says to ask about, and for changes to the summary.json format after Checkpoint C.

## Verify before reporting
- After every fix or edit, check the actual result yourself and confirm it is done before telling the user. Tests passing is not enough for a visual change: open the output (for example the deck in the browser) and look at it.
- In the report, say what you checked and what you saw. If you could not check something, say so instead of claiming it is done.

## Token Efficiency

### 1. Milestone handoff
- The user triggers the handoff by running the session-handoff skill. Do not start one unprompted.
- Guideline for the user: hand off about every 20-25 turns or at 70-80k tokens (check with `/context`), at a completed task boundary, not mid-task.
- Before handing off, drop transient logs, exploratory steps and dead hypotheses. Keep one-line conclusions.
- The handoff is saved to `session-handoff/` and must list the spec, plan and key files.
- Resuming a new session: read the newest file in `session-handoff/` (names start with date and time), then the spec, `tasks/plan.md` if they exist, and run `git status`. Do not re-ingest old conversation history.
- Use handoff plus `/clear`, or `/compact`, not both.

### 2. Model routing
Applies only when subagents are used.
- `haiku`: file discovery, glob and regex search, data extraction, log grepping.
- `sonnet`: feature work, API and UI code, tests, standard bug fixes.
- `opus`: system architecture, critical financial or cryptographic logic, concurrency.

### 3. Large output
- A command that produces more than 50 lines of output must be redirected to a file in `.tmp/` (for example `.tmp/build.log`).
- In context, keep only the exit code, a one-line summary (for example `Tests: 48 passed, 0 failed`) and the last 10-20 lines of any failure.
- Read the log file instead of re-running the command.

### 4. Answers
- Chat replies: short and clear, with all necessary information.
- This does not apply to files such as `SPEC.md`, `tasks/plan.md` and review reports, which keep their normal structure.
