# Executive summary skill - Project Rules

Local rules for this project only. The parent WAT `CLAUDE.md` in Downloads also applies; no known conflicts.

## Project
- Name: Executive summary skill
- Purpose, stack and commands: not defined yet. Fill in after `/agent-skills:spec` and `/agent-skills:plan`.
- Repo: https://github.com/sirago23/Executive_summary (public, branch `main`).

## Boundaries
- The repo is public. Never commit `.env`, `credentials.json`, `token.json`, `.tmp/` or `node_modules/`.
- Check that nothing sensitive is staged before every push.
- Keep `session-handoff/` and `.tmp/` out of git.

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
