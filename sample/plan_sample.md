# Implementation Plan: Billing Record, Phase 1 (Local)

Spec: [SPEC.md](../SPEC.md). Task details and checkboxes: [todo.md](todo.md).
Scope: Phase 1 only. Phase 2 (Railway) gets its own plan after the Phase 1 checkpoint passes.

## Overview

Build the full single-user billing app on the user's PC. Records can be added by hand or from a slip or bill photo read by Claude. Every record is converted to THB, and the app shows totals and charts, with CSV export. The app runs on `localhost` and over the home network for phone camera use.

Work is sliced vertically. Each task delivers a path the user can see working, from the database through the API to the UI. The riskiest unknown, how well Claude reads Thai slips, is tested in Task 2 before the app is built around it.

## Architecture Decisions

- **Reads in server components, writes through route handlers.** Pages read the DB directly through `src/lib/db/queries`. Mutations go through `src/app/api/*` route handlers, so they can be tested without the UI and reused in Phase 2.
- **One Zod schema per entity**, shared by the form, the route handler and the AI output parser. No hand-written duplicate types.
- **Money is stored as integer minor units, and rates as decimal strings.** THB conversion is one pure function with half-up rounding, computed on save.
- **All file paths come from `src/lib/config.ts`** (`DATA_DIR`), so Phase 2 only changes an environment variable.
- **AI extraction is behind one function**, `extractFromImage(image) -> ExtractionResult`. Tests mock it. Only `npm run extract:sample` calls the real API.
- **Claude returns structured output through tool use with a JSON schema.** The parser treats every field as optional and flags missing ones.
- **Dates are stored as ISO CE dates.** BE-to-CE conversion happens in the extraction parser, the only place BE dates enter.
- **Filters live in URL query params**, so the list, the dashboard and CSV export share one filter parser and links can be bookmarked.
- **Design tokens are set once in Task 5** (colors, type scale, spacing) and reused everywhere. This prevents a restyle at the end.
- **Commit after every task** that passes its verification, with lint, type check and tests green.

## Dependency Graph

```
T1 Scaffold
 ├── T2 Extraction spike ───────────────────────┐
 └── T3 DB + seed                               │
      └── T4 Money + validation utils           │
           └── T5 Add + list record (THB)       │
                ├── T6 Edit + delete            │
                ├── T7 Categories               │
                ├── T8 Foreign currency + FX    │
                ├── T9 Dashboard totals         │
                │    └── T10 Charts             │
                │         └── T11 Filters ──────┼── T15 CSV export
                └── T12 Image upload + storage  │
                     └── T13 Extract → review → save (needs T2, T8)
                          └── T14 Duplicate warning
T16 Design + states pass (after T15)
T17 E2E suite + LAN check + coverage (last)
```

After T5, these can run in parallel: T6, T7, T8, T9 and T12. In this project they run one at a time, in task order.

## How to Build

- **One agent, one task at a time, in task order.** No parallel builder agents. Tasks 6, 7 and 8 edit the same files (`record-form.tsx`, `records.ts`) and all tasks share one SQLite schema, so parallel work would cause conflicts.
- **Per task:** build, run `CHECKS` (and `BUILD` where listed), verify at runtime, tick the box in `todo.md`, then commit. Nothing sensitive is staged. Start with `/agent-skills:build`.
- **Reviewer sub-agents at each checkpoint** (A to D, and Phase 1 complete), run after the checkpoint checks pass and before moving on:
  - `agent-skills:code-reviewer` after every checkpoint. Findings are fixed or logged before the next phase.
  - `agent-skills:security-auditor` at Checkpoint D (uploads, API key, path handling, data privacy) and at Phase 1 complete.
  - `agent-skills:test-engineer` at Phase 1 complete (test quality and coverage gaps).
- **Model routing** (from CLAUDE.md, applies to sub-agents only): file search goes to `haiku`, feature work and tests to `sonnet`, and the THB conversion and FX rate logic (Tasks 4 and 8) to `opus`.
- **Stop and ask** before: real Claude API calls, a new dependency, a schema change after the first migration, and anything that exposes the app beyond the local network.
- **Session handoff:** hand off at a task boundary (about every 20-25 turns), as in CLAUDE.md. The new session reads the newest handoff, then `tasks/todo.md`, then `git status`.

## Task List

### Phase A: Foundation
- [ ] Task 1: Scaffold project and tooling
- [ ] Task 2: Extraction spike (Claude reads a slip)
- [ ] Task 3: Database schema, migrations and category seed

### Checkpoint A
- [ ] Lint, type check, tests and build pass
- [ ] Spike results reviewed with the user: go, or adjust the approach

### Phase B: Records
- [ ] Task 4: Money and validation utilities
- [ ] Task 5: Add a THB record by hand and see it in the list
- [ ] Task 6: Edit and delete a record
- [ ] Task 7: Manage categories
- [ ] Task 8: Foreign-currency records with automatic THB rate

### Checkpoint B
- [ ] Manual flow works end to end. Data survives a server restart.
- [ ] User reviews the look of the list and form

### Phase C: Insights
- [ ] Task 9: Dashboard totals for a period
- [ ] Task 10: Category donut and monthly bar charts
- [ ] Task 11: Filters for list and dashboard

### Checkpoint C
- [ ] Dashboard totals match a hand calculation on seeded data (success criterion 4)

### Phase D: Capture
- [ ] Task 12: Upload or photograph an image and store it
- [ ] Task 13: Extract, review and save a record from an image
- [ ] Task 14: Duplicate warning

### Checkpoint D
- [ ] Real extraction run on 10 sample slips and bills, with user approval for cost (success criterion 2)
- [ ] BE-dated slip saves with the correct CE date (success criterion 5)

### Phase E: Finish
- [ ] Task 15: CSV export
- [ ] Task 16: Design, empty, loading and error states, plus accessibility pass
- [ ] Task 17: Full E2E suite, phone-over-LAN check and coverage

### Checkpoint: Phase 1 complete
- [ ] Spec success criteria 1-8 all pass
- [ ] User approves. Then `/agent-skills:plan` for Phase 2.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Claude misreads Thai slips (amount, BE date, direction) | High | Task 2 spike on real slips before building the flow. Review step always required. Prompt tuned in the spike. |
| HEIC photos: prebuilt `sharp` cannot decode HEVC-based HEIC, and the Claude API does not accept HEIC | Med | iOS Safari usually converts to JPEG on upload. Task 12 tests a real HEIC file. If it fails, add `heic-convert` (new dependency, ask first). |
| `better-sqlite3` native build on Node 24 / Windows | Med | Task 1 installs it and runs a smoke query first. Fallback: pin to Node 22 LTS. |
| Frankfurter lacks a currency or a weekend date | Low | Weekend dates use the previous working day's rate. Unsupported currency forces manual rate entry (spec rule). |
| Windows Firewall blocks the phone from reaching port 3000 | Low | Task 17 documents the firewall rule in the README. |
| API cost from repeated real extraction runs | Low | Real calls only through `npm run extract:sample`, always with user approval. Automated tests are mocked. |
| Real slips leaking into the public repo | High | Real samples live in `.tmp/samples/` (gitignored). Fixtures are synthetic only. Staged diff checked before every push. |

## Decisions

1. **Sample slips:** The user adds real slips and bills to `.tmp/samples/`: 3-5 before Task 2, and about 10 total by Checkpoint D. They are never committed.
2. **API key:** The user has one and pastes it into `.env` at Task 2. The exact per-image price is checked before the first paid run.

## Open Questions

None.
