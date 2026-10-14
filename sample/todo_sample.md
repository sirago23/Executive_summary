# Tasks: Billing Record, Phase 1 (Local)

Plan: [plan.md](plan.md). Spec: [SPEC.md](../SPEC.md).

Every task also meets the standing Definition of Done:
- Lint, type check and tests pass.
- Behavior is checked at runtime, not just compiled.
- New behavior has tests that fail without it.
- Error paths are handled.
- No debug code is left in.
- The change stays within the task's scope.
- It is committed with nothing sensitive staged.

Standard checks used below:
- `CHECKS` = `npm run lint && npm run typecheck && npm test`
- `BUILD` = `npm run build`

---

## Phase A: Foundation

### - [ ] Task 1: Scaffold project and tooling

**Description:** Create the Next.js (App Router, TypeScript strict) app in the repo root with Tailwind, ESLint, Prettier, Vitest and Playwright. Add all Phase 1 npm scripts from the spec, `src/lib/config.ts` (reads `DATA_DIR`, default `./data`), `.env.example`, and gitignore entries for `data/` and `.env*` (except `.env.example`). Install `better-sqlite3` and run one smoke query to prove the native module loads on Node 24 and Windows.

**Acceptance criteria:**
- [ ] `npm run dev` serves a placeholder home page on http://localhost:3000.
- [ ] Every Phase 1 script in the spec's Commands section exists. Scripts with nothing to run yet exit 0.
- [ ] `better-sqlite3` loads and runs `select 1` in a Vitest test.

**Verification:**
- [ ] `CHECKS` and `BUILD` pass
- [ ] `git status` shows no `data/`, `.env` or `node_modules/`

**Dependencies:** None
**Files:** `package.json`, `tsconfig.json`, `next.config.ts`, `vitest.config.ts`, `playwright.config.ts`, `src/lib/config.ts`, `.env.example`, `.gitignore`, `src/app/layout.tsx`, `src/app/page.tsx`
**Scope:** M (mostly generated)

### - [ ] Task 2: Extraction spike (Claude reads a slip)

**Description:** Build `extractFromImage()` in `src/lib/extract/`. It sends one image to Claude with a tool schema and returns direction, amount, currency, date, counterparty, slip reference and suggested category. The parser validates the output with Zod, marks missing fields, and converts BE years to CE. Add `npm run extract:sample <file>` to run it on a local image and print the result.

**Acceptance criteria:**
- [ ] Unit tests cover the parser with canned responses: complete, partial (missing fields flagged), malformed (clean error, no throw to caller), BE date to CE.
- [ ] With user approval, a real run on 3-5 samples from `.tmp/samples/` prints correct amount, currency and date for most of them. Results are noted in this file.
- [ ] The API key is read on the server only, from `.env`.

**Verification:**
- [ ] `CHECKS` pass. No real API calls in `npm test`.
- [ ] Manual: real sample run, reviewed with the user (ask first, it costs credits)

**Dependencies:** Task 1
**Files:** `src/lib/extract/extract.ts`, `src/lib/extract/prompt.ts`, `src/lib/extract/parse.ts`, `scripts/extract-sample.ts`, `tests/unit/extract/parse.test.ts`
**Scope:** M

### - [ ] Task 3: Database schema, migrations and category seed

**Description:** Define the Drizzle schema for `records`, `categories` and `fx_rates` as in the spec, generate the first migration, and add a DB client that opens `DATA_DIR/billing.db`. Seed the default income and expense categories, without creating duplicates if the seed runs again.

**Acceptance criteria:**
- [ ] `npm run db:migrate` then `npm run db:seed` creates the DB with 13 default categories. Running the seed twice still gives 13.
- [ ] An integration test helper creates a fresh temp DB per test file.

**Verification:**
- [ ] `CHECKS` pass
- [ ] Manual: delete `data/`, run migrate and seed, and confirm the file and rows exist

**Dependencies:** Task 1
**Files:** `src/lib/db/schema.ts`, `src/lib/db/client.ts`, `drizzle.config.ts`, `scripts/seed.ts`, `tests/helpers/test-db.ts`
**Scope:** M

### - [ ] Checkpoint A
- [ ] `CHECKS` and `BUILD` pass
- [ ] Spike results reviewed with the user: go, or change the prompt or model

---

## Phase B: Records

### - [ ] Task 4: Money and validation utilities

**Description:** Write pure functions: parse a user-typed amount into minor units, format minor units for display (tabular, with currency), and convert to THB (`amountMinor × rate` from a decimal string, rounded half-up, no floats). Add a Zod record input schema shared by the form and the API.

**Acceptance criteria:**
- [ ] Unit tests: "1,234.50" → 123450, invalid input rejected, USD 10.00 at rate "36.4521" → 36452 satang, half-up at .5, THB rate "1" gives the same value back.
- [ ] Record schema rejects a zero or negative amount, a bad currency code, an invalid date and an unknown direction.

**Verification:**
- [ ] `CHECKS` pass

**Dependencies:** Task 3
**Files:** `src/lib/money.ts`, `src/lib/validation/record.ts`, `tests/unit/money.test.ts`, `tests/unit/validation/record.test.ts`
**Scope:** S

### - [ ] Task 5: Add a THB record by hand and see it in the list

**Description:** First full vertical slice. Build the app shell (nav, mobile-friendly layout, "Add record" always reachable) and the design tokens from the spec's Design Direction. Add `POST /api/records` and `GET /api/records`, the add-record form (THB only for now), and the records list page, newest first.

**Acceptance criteria:**
- [ ] The user adds an expense or income record with amount, date, category, counterparty and note, and it appears at the top of the list.
- [ ] Invalid input shows field-level errors and saves nothing.
- [ ] Records survive a dev server restart.

**Verification:**
- [ ] `CHECKS` pass. Integration test for POST and GET against a temp DB.
- [ ] E2E: add a record, then see it in the list
- [ ] Manual: check the look at 360 px and on desktop

**Dependencies:** Task 4
**Files:** `src/app/layout.tsx`, `src/app/api/records/route.ts`, `src/app/records/page.tsx`, `src/app/records/new/page.tsx`, `src/components/record-form.tsx`, `src/lib/db/queries/records.ts`
**Scope:** M

### - [ ] Task 6: Edit and delete a record

**Description:** Add `PATCH` and `DELETE /api/records/[id]`, an edit page that reuses the record form, and delete with a confirmation dialog.

**Acceptance criteria:**
- [ ] Editing any field saves it and the list shows the new value. `updated_at` changes.
- [ ] Delete asks for confirmation. Cancel keeps the record, and confirm removes it.
- [ ] Editing or deleting a missing id returns 404 and the UI shows a message.

**Verification:**
- [ ] `CHECKS` pass. Integration tests for PATCH, DELETE and 404.
- [ ] E2E: edit, then delete

**Dependencies:** Task 5
**Files:** `src/app/api/records/[id]/route.ts`, `src/app/records/[id]/edit/page.tsx`, `src/components/confirm-dialog.tsx`, `src/lib/db/queries/records.ts`
**Scope:** M

### - [ ] Task 7: Manage categories

**Description:** Add a categories page and API: list by direction, add, rename, reorder and remove. A category that is in use cannot be removed until its records are moved to another category of the same direction.

**Acceptance criteria:**
- [ ] Add and rename work. Duplicate names within the same direction are rejected.
- [ ] Removing an in-use category asks the user to pick a replacement, moves its records, then removes it.
- [ ] The record form shows only categories that match the chosen direction.

**Verification:**
- [ ] `CHECKS` pass. Integration tests for the in-use rule and the move.
- [ ] Manual: rename a category and see the new name on existing records

**Dependencies:** Task 5
**Files:** `src/app/categories/page.tsx`, `src/app/api/categories/route.ts`, `src/app/api/categories/[id]/route.ts`, `src/lib/db/queries/categories.ts`, `src/components/record-form.tsx`
**Scope:** M

### - [ ] Task 8: Foreign-currency records with automatic THB rate

**Description:** Add a currency picker to the record form. For non-THB records, the server fetches the rate for the record's date from Frankfurter, caches it in `fx_rates`, and shows it in the form. The user can override it. If the fetch fails or the currency is unsupported, the user must enter a rate before saving. Changing the date or currency fetches again unless the rate was overridden.

**Acceptance criteria:**
- [ ] A USD record gets an auto rate and a correct THB amount. `fx_source` is `auto`.
- [ ] An overridden rate is saved with `fx_source = manual` and is not replaced when the date changes.
- [ ] A network failure or unsupported currency blocks saving until a rate is entered. The same date and currency is fetched only once (cache hit).

**Verification:**
- [ ] `CHECKS` pass. Frankfurter mocked for success, weekend date, unsupported currency, failure and cache hit.
- [ ] Manual: one live USD record (free API, no key)

**Dependencies:** Task 5
**Files:** `src/lib/fx/rates.ts`, `src/app/api/fx/route.ts`, `src/components/record-form.tsx`, `tests/integration/fx.test.ts`
**Scope:** M

### - [ ] Checkpoint B
- [ ] `CHECKS` and `BUILD` pass. All E2E tests so far pass.
- [ ] Manual add, edit, delete, categories and foreign currency all work, and survive a restart
- [ ] User reviews the look of the list and form

---

## Phase C: Insights

### - [ ] Task 9: Dashboard totals for a period

**Description:** Write pure summary functions over THB amounts and a dashboard home page with a period picker (default: current month). It shows total income, total expense and net, numbers first.

**Acceptance criteria:**
- [ ] Totals match a hand calculation on a seeded set that mixes THB and USD.
- [ ] Changing the period updates the totals. An empty period shows zeros and an empty state, not an error.

**Verification:**
- [ ] `CHECKS` pass. Unit tests for the summary functions.
- [ ] Manual: compare the dashboard to the seeded set by hand

**Dependencies:** Task 8
**Files:** `src/lib/summary/totals.ts`, `src/app/page.tsx`, `src/components/period-picker.tsx`, `tests/unit/summary/totals.test.ts`
**Scope:** M

### - [ ] Task 10: Category donut and monthly bar charts

**Description:** Add chart data functions (expense by category, top 5 plus "Other" when there are more than 6; income vs. expense per month for the last 6 months) and Recharts components on the dashboard, with direct labels or a legend showing values.

**Acceptance criteria:**
- [ ] With 9 expense categories, the donut shows 5 named slices plus "Other", and the values add up to the expense total.
- [ ] The bar chart always shows 6 months, including empty months as zero.
- [ ] Charts are readable at 360 px.

**Verification:**
- [ ] `CHECKS` pass. Unit tests for the grouping and month series.
- [ ] Manual: visual check on mobile and desktop

**Dependencies:** Task 9
**Files:** `src/lib/summary/charts.ts`, `src/components/category-donut.tsx`, `src/components/monthly-bars.tsx`, `src/app/page.tsx`, `tests/unit/summary/charts.test.ts`
**Scope:** M

### - [ ] Task 11: Filters for list and dashboard

**Description:** Add one filter parser for URL query params (date range, category, direction, currency) used by the records list and the dashboard, plus a compact filter bar.

**Acceptance criteria:**
- [ ] Each filter narrows the list, totals and charts the same way.
- [ ] Filters live in the URL. Reload or a shared link keeps them. Invalid params are ignored, not errors.
- [ ] A "Clear" control resets everything.

**Verification:**
- [ ] `CHECKS` pass. Unit tests for the filter parser.
- [ ] E2E: filter by category, and the list and totals change

**Dependencies:** Task 10
**Files:** `src/lib/filters.ts`, `src/components/filter-bar.tsx`, `src/app/page.tsx`, `src/app/records/page.tsx`, `tests/unit/filters.test.ts`
**Scope:** M

### - [ ] Checkpoint C
- [ ] `CHECKS` and `BUILD` pass
- [ ] Success criterion 4: dashboard THB totals match a hand calculation, including foreign-currency records

---

## Phase D: Capture

### - [ ] Task 12: Upload or photograph an image and store it

**Description:** Build the upload page with a file input that offers the camera on phones. The server accepts JPEG, PNG, WebP and HEIC up to 10 MB, converts to JPEG, downscales to at most 2000 px, and stores the file under `DATA_DIR/uploads/` with a random name. Add an image route to view stored images.

**Acceptance criteria:**
- [ ] A JPEG, PNG, WebP and a real HEIC file each upload and display. Over 10 MB or a non-image file is rejected with a clear message.
- [ ] Stored images are at most 2000 px on the long side, and file names are not guessable.
- [ ] The image route rejects path traversal (`../`).

**Verification:**
- [ ] `CHECKS` pass. Tests for validation, resize and path handling.
- [ ] Manual: real HEIC from an iPhone, or a sample file. If `sharp` cannot decode it, stop and ask before adding `heic-convert`.

**Dependencies:** Task 5
**Files:** `src/lib/images/store.ts`, `src/app/upload/page.tsx`, `src/app/api/images/route.ts`, `src/app/api/images/[name]/route.ts`, `tests/unit/images/store.test.ts`
**Scope:** M

### - [ ] Task 13: Extract, review and save a record from an image

**Description:** Connect upload to `extractFromImage()` through `POST /api/extract`, then open the record form pre-filled with the result. Missing fields are empty and flagged. The record saves with `source = ai` and the linked image only when the user confirms. A non-THB result gets an auto rate (Task 8). The record detail shows the source image.

**Acceptance criteria:**
- [ ] Upload, then a pre-filled review form within 15 s. Saving creates one record linked to the image.
- [ ] If extraction fails, the form still opens with the image and empty fields. Nothing is saved without confirmation.
- [ ] Leaving the review without saving creates no record.

**Verification:**
- [ ] `CHECKS` pass. Integration test for `/api/extract` with Claude mocked.
- [ ] E2E (mocked extraction): upload a fixture, review, save, then see it in the list and dashboard
- [ ] Manual: one real slip end to end (ask first)

**Dependencies:** Tasks 2, 8, 12
**Files:** `src/app/api/extract/route.ts`, `src/app/upload/review/page.tsx`, `src/components/record-form.tsx`, `src/app/records/[id]/page.tsx`, `tests/integration/extract.test.ts`
**Scope:** M

### - [ ] Task 14: Duplicate warning

**Description:** Before saving, check for an existing record with the same amount, date and slip reference. If one exists, show a warning with a link to it and let the user save anyway or cancel.

**Acceptance criteria:**
- [ ] Uploading the same slip twice shows the warning on the second save.
- [ ] Records without a slip reference never trigger the warning.

**Verification:**
- [ ] `CHECKS` pass. Unit and integration tests for the match rule.

**Dependencies:** Task 13
**Files:** `src/lib/db/queries/records.ts`, `src/app/api/records/duplicates/route.ts`, `src/components/record-form.tsx`, `tests/integration/duplicates.test.ts`
**Scope:** S

### - [ ] Checkpoint D
- [ ] `CHECKS` and `BUILD` pass
- [ ] Success criterion 2: real run on 10 samples (ask first). Amount, currency and date correct on at least 9, category sensible on at least 8. Results recorded here.
- [ ] Success criterion 5: a BE-dated Thai slip saves with the correct CE date

---

## Phase E: Finish

### - [ ] Task 15: CSV export

**Description:** Add `GET /api/export.csv`, which applies the current filters and returns UTF-8 CSV with a BOM and the spec's columns, plus an Export button on the records page.

**Acceptance criteria:**
- [ ] Opens in Excel with Thai text intact. Commas, quotes and new lines in notes are escaped correctly.
- [ ] The THB total of the CSV equals the dashboard total for the same filters.

**Verification:**
- [ ] `CHECKS` pass. Unit tests for escaping and the BOM.
- [ ] Manual: open in Excel (success criterion 6)

**Dependencies:** Task 11
**Files:** `src/lib/export/csv.ts`, `src/app/api/export.csv/route.ts`, `src/app/records/page.tsx`, `tests/unit/export/csv.test.ts`
**Scope:** S

### - [ ] Task 16: Design, empty, loading and error states, plus accessibility pass

**Description:** Go through every screen against the spec's Design Direction. Fill in missing empty, loading and error states, and check contrast (WCAG AA), keyboard use, visible focus, form labels and the 360 px layout. Remove anything that looks templated.

**Acceptance criteria:**
- [ ] Every screen has designed empty, loading and error states.
- [ ] Keyboard-only use works for add, edit, delete, upload and filters.
- [ ] No gradients, glow, emoji or filler copy remain. The user signs off on the look.

**Verification:**
- [ ] `CHECKS` and `BUILD` pass
- [ ] Manual: walkthrough with the user at mobile and desktop widths

**Dependencies:** Task 15
**Files:** components and pages across `src/` (cap the edits at about 5 files per commit)
**Scope:** M

### - [ ] Task 17: Full E2E suite, phone-over-LAN check and coverage

**Description:** Fill gaps in the Playwright suite (run once at a 360 px viewport), confirm `src/lib` coverage is at least 80%, and test the phone over home Wi-Fi with `npm run dev:lan`. Write a README covering setup, `.env`, commands and the Windows Firewall rule for port 3000.

**Acceptance criteria:**
- [ ] All E2E tests pass on desktop and mobile viewports.
- [ ] `npm test -- --coverage` shows at least 80% lines for `src/lib`.
- [ ] Success criterion 1: from the phone on Wi-Fi, photograph a bill and save it in under 30 seconds.

**Verification:**
- [ ] `CHECKS`, `BUILD` and `npm run test:e2e` pass
- [ ] Manual: phone test with the user

**Dependencies:** Task 16
**Files:** `e2e/*.spec.ts`, `playwright.config.ts`, `README.md`
**Scope:** M

### - [ ] Checkpoint: Phase 1 complete
- [ ] Spec success criteria 1-8 all pass
- [ ] Git history has no secrets or personal data (success criterion 8)
- [ ] User approves. Next step: plan Phase 2 (Railway).
