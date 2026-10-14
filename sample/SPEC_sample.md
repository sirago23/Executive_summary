# Spec: Billing Record

Status: Draft, awaiting approval
Date: 2026-10-14

## Objective

A personal web app for one user (the owner) to record income and expenses without typing them in by hand.

The user uploads a bank transfer slip, or photographs a bill or receipt with their phone. The app reads the image with the Claude vision API and pulls out the amount, currency, date, merchant or counterparty, direction (income or expense) and a category. The user checks the result, fixes anything wrong, and saves it. The app then summarizes the records and shows totals as charts.

Slips and bills can be in Thai or English, and amounts can be in more than one currency.

### User stories

1. As the user, I upload a bank slip image and get a pre-filled record I can confirm in one click.
2. As the user, I take a photo of a paper bill on my phone and get the same pre-filled record.
3. As the user, I add a record by hand when I have no image.
4. As the user, I edit or delete any record, including ones the AI created.
5. As the user, I see where my money went this month in a category chart, and how income compares with expenses over time.
6. As the user, I filter records by date range, category, direction and currency.
7. As the user, I export all my records to a CSV file as a backup.

### Acceptance criteria

- **Upload:** Accepts JPEG, PNG, WebP and HEIC images up to 10 MB. On a phone, the file picker offers the camera.
- **Extraction:** Returns structured fields within 15 seconds for a typical slip. If extraction fails, or a field is not found, the form opens with that field empty and flagged. Nothing is saved silently.
- **Review step:** AI-created records are saved only after the user confirms them. The source image stays linked to the record and can be viewed later.
- **Manual entry:** Every field the AI fills can also be entered and edited by hand.
- **Edit and delete:** Every saved record can be edited or deleted. Deletion asks for confirmation.
- **Categories:** A default set for expense (Food, Transport, Shopping, Bills and Utilities, Health, Entertainment, Housing, Transfer out, Other) and income (Salary, Transfer in, Refund, Other income). The user can add, rename and remove categories. A category that is in use cannot be removed until its records are reassigned.
- **One record per image:** A receipt with several items becomes one record with the total amount and one category.
- **Currency:** Each record stores its original amount and currency (ISO 4217 code), plus an exchange rate to THB and the THB amount. THB records use rate 1.
- **Exchange rate:** For a non-THB record, the app fetches the rate for the record's date from the Frankfurter API (free, no key). The rate shows in the review form and can be overridden by hand. If the fetch fails or the currency is not supported, the form asks for the rate and will not save without one. Changing the date or currency fetches the rate again unless the user has overridden it.
- **Dates:** Shown in the Western calendar (CE), e.g. 14 Oct 2026. Buddhist Era years on slips (e.g. 2569) are converted to CE during extraction.
- **Duplicates:** If a new record has the same amount, date and slip reference number as an existing one, the app warns before saving.
- **Summary:** For a chosen period (default: current month), the app shows total income, total expense and net, all in THB.
- **Charts:** A donut chart of expenses by category, and a bar chart of income vs. expense per month for the last 6 months, all in THB. Both follow the active filters.
- **CSV export:** One button downloads all records (or the filtered set) as UTF-8 CSV with a BOM, so Thai text opens correctly in Excel. Columns: date, direction, category, counterparty, original amount, currency, rate, THB amount, note, slip reference, source.
- **Interface:** Usable on a phone screen (360 px wide) and on desktop.

## Delivery Phases

The work ships in two phases. Phase 2 starts only after Phase 1 meets its success criteria.

### Phase 1: Local

- Build every feature in this spec and run it on the user's PC (`localhost`, plus home-network access from the phone).
- No login.
- Data lives in `./data` on the PC.
- Done when Phase 1 success criteria 1-8 pass.

### Phase 2: Deploy to Railway

- Deploy the same app to the user's existing Railway account as a public web app with HTTPS, so it works from the phone anywhere.
- Add a login (see Phase 2 Deployment). The app must not go public without it.
- Data lives on a Railway volume.
- No feature changes beyond what deployment needs: login, config through environment variables, health check, and moving existing local data.
- Done when Phase 2 success criteria 9-13 pass.

### Out of scope for v1

- Multiple users or accounts
- Login or PIN in Phase 1 (Phase 2 adds a single-user login)
- Splitting a receipt into line items
- Direct bank connections or statement (PDF/CSV) import
- Budgets, alerts and recurring transactions
- Automatic backups (CSV export only)
- Buddhist Era date display
- Hosting anywhere other than Railway, multiple instances, or a separate database server

## Tech Stack

| Concern | Choice |
|---|---|
| Framework | Next.js (App Router), TypeScript, strict mode |
| Runtime | Node.js 20 LTS or newer |
| Database | SQLite file through `better-sqlite3` and Drizzle ORM (migrations with `drizzle-kit`) |
| AI extraction | Anthropic TypeScript SDK (`@anthropic-ai/sdk`), Claude vision with a tool or JSON schema for structured output. The model ID is set in `.env` (default `claude-sonnet-5-5`). |
| Exchange rates | Frankfurter API (`https://api.frankfurter.app`), called from the server with built-in `fetch`; rates cached in SQLite per date and currency |
| Validation | Zod, shared by API routes, forms and the AI output parser |
| Charts | Recharts |
| Styling | Tailwind CSS with a small set of design tokens (see Design Direction) |
| Image handling | `sharp` to convert HEIC to JPEG and downscale to max 2000 px before sending to the API |
| Tests | Vitest (unit and integration), Playwright (end-to-end) |

Exact package versions are pinned in `package.json` at setup time.

### Runtime and access (Phase 1)

- The app runs locally on the user's PC.
- All file locations come from `DATA_DIR` (default `./data`), so Phase 2 can point it at a Railway volume without code changes.
- To use the phone camera, the phone opens the app over the home network (`npm run dev:lan`). Camera capture uses `<input type="file" accept="image/*" capture="environment">`, which works over plain HTTP.
- The app binds to the local network only and has no login. Anyone on the home network can open it. Remote access is out of scope for v1.
- Internet access is needed for AI extraction and exchange rates. Manual entry of THB records works offline.

### Phase 2 Deployment (Railway)

**Why Railway fits:** It builds and runs a Node/Next.js app from the GitHub repo, provides HTTPS on a `*.up.railway.app` domain, and offers persistent volumes, so SQLite and uploaded images survive redeploys. A database server is not needed at this scale.

**Setup**
- One Railway service, deployed from the `main` branch of `sirago23/Billing_record`.
- One volume mounted at `/data`, with `DATA_DIR=/data`. The SQLite DB and uploads live there.
- Exactly one replica. SQLite on a volume cannot be shared between instances.
- Start command: `npm run start:prod`, which runs migrations and then `next start`, listening on Railway's `PORT`.
- Health check: `GET /api/health` returns 200 when the DB is reachable.
- `better-sqlite3` and `sharp` are native modules. The build must use the Linux image Railway provides, and the first deploy verifies they load.

**Environment variables (set in Railway, never in the repo)**
```
ANTHROPIC_API_KEY      # Claude API key
ANTHROPIC_MODEL        # default claude-sonnet-5-5
DATA_DIR=/data
APP_PASSWORD_HASH      # hash of the login password
SESSION_SECRET         # random 32+ byte string for signing session cookies
```

**Login (single user)**
- One password, set through `APP_PASSWORD_HASH`. There are no usernames or sign-up.
- On success, the app sets a signed, `HttpOnly`, `Secure`, `SameSite=Lax` session cookie that lasts 30 days.
- Every page, API route and uploaded image requires a valid session, except `/login` and `/api/health`.
- After 5 failed attempts in 15 minutes, login is blocked for 15 minutes.
- A logout button clears the session.
- `npm run hash-password` prints a hash to paste into Railway.

**Moving local data**
- A one-time script copies the Phase 1 SQLite DB and uploads to the Railway volume. The method (Railway CLI or a temporary upload route) is chosen during planning.
- After the move, record counts and dashboard totals match the local copy.

**Backup in production**
- The CSV export button remains the main backup.
- Railway volume backups are turned on if the user's plan includes them.

**Cost**
- Railway bills by usage on top of the plan. One small always-on service with a small volume is expected to stay within the entry plan. The user confirms this before deploying.

## Commands

```
Install:      npm install
Dev:          npm run dev              # http://localhost:3000
Dev on LAN:   npm run dev:lan          # next dev -H 0.0.0.0, for phone access
Build:        npm run build
Start:        npm run start
Start (prod): npm run start:prod       # Phase 2: db migrate, then next start -p $PORT
Hash pass:    npm run hash-password    # Phase 2: print APP_PASSWORD_HASH
Lint:         npm run lint
Type check:   npm run typecheck        # tsc --noEmit
Unit tests:   npm test                 # vitest run
Coverage:     npm test -- --coverage
E2E tests:    npm run test:e2e         # playwright test
DB migrate:   npm run db:migrate       # drizzle-kit migrate
DB generate:  npm run db:generate      # drizzle-kit generate, after schema changes
Seed:         npm run db:seed          # default categories
```

## Project Structure

```
src/
  app/                    # Next.js routes (pages and API route handlers)
    page.tsx              # Dashboard: summary + charts
    records/              # Record list, detail, edit
    upload/               # Upload or capture, then review form
    categories/           # Manage categories
    api/                  # Route handlers (records, categories, extract, images)
  components/             # UI components (presentational, no data access)
  lib/
    db/                   # Drizzle schema, client, queries
    extract/              # Claude vision call, prompt, response parsing
    fx/                   # Exchange rate fetch and cache
    export/               # CSV export
    images/               # Upload storage, HEIC conversion, resizing
    summary/              # Totals and chart data aggregation (pure functions)
    validation/           # Zod schemas
tests/
  unit/                   # Vitest unit tests, mirrors src/lib
  integration/            # API route tests against a temp SQLite DB
  fixtures/               # Sample slips (synthetic or redacted only)
e2e/                      # Playwright tests
drizzle/                  # Generated migrations
scripts/                  # Command-line scripts: db seed, extract:sample, hash-password (Phase 2)
tasks/                    # plan.md and todo.md
.tmp/                     # Local scratch and real sample slips (gitignored)
data/                     # SQLite DB and uploaded images (gitignored)
```

## Data Model (v1)

```
records
  id              integer primary key
  direction       'income' | 'expense'
  amount_minor    integer        # original amount in the currency's minor unit (satang, cents)
  currency        text           # ISO 4217, e.g. THB, USD
  fx_rate         text           # THB per 1 unit of currency, decimal string; "1" for THB
  fx_source       'auto' | 'manual'
  amount_thb_minor integer       # amount in satang, rounded half-up; used for all totals
  occurred_at     text           # ISO date in CE (time optional)
  counterparty    text null      # merchant, payer or payee
  category_id     integer -> categories.id
  note            text null
  slip_ref        text null      # bank reference number, used for duplicate check
  image_path      text null      # relative path under data/uploads
  source          'ai' | 'manual'
  created_at, updated_at

categories
  id              integer primary key
  name            text unique per direction
  direction       'income' | 'expense'
  sort_order      integer

fx_rates                         # cache, so each date and currency is fetched once
  date            text
  currency        text
  rate            text           # THB per 1 unit, decimal string
  primary key (date, currency)
```

Money is stored as integers in minor units. Rates are stored as decimal strings. Floats are never used for amounts. The THB amount is computed once when the record is saved, and again only when the amount, currency or rate changes.

## Code Style

- TypeScript strict. No `any`. Use `unknown` and narrow it.
- Files are kebab-case. React components are PascalCase. Functions and variables are camelCase.
- Server-only code (DB, Anthropic SDK, file system) lives in `src/lib` and never ends up in client components.
- Validate at every boundary (request body, AI output, form input) with Zod.
- Keep functions small and pure where possible. Aggregation logic has no I/O.
- Prettier defaults with ESLint (`next/core-web-vitals` + `@typescript-eslint`).

Example:

```ts
// src/lib/summary/totals.ts
import type { RecordRow } from "@/lib/db/schema";

export type Totals = {
  incomeThbMinor: number;
  expenseThbMinor: number;
  netThbMinor: number;
};

export function totals(records: RecordRow[]): Totals {
  let incomeThbMinor = 0;
  let expenseThbMinor = 0;

  for (const r of records) {
    if (r.direction === "income") incomeThbMinor += r.amountThbMinor;
    else expenseThbMinor += r.amountThbMinor;
  }

  return {
    incomeThbMinor,
    expenseThbMinor,
    netThbMinor: incomeThbMinor - expenseThbMinor,
  };
}
```

## Design Direction

The goal is a clean, quiet, practical tool that does not look AI-generated.

- **Palette:** Neutral background and text, one accent color for primary actions. Income and expense use a muted green and a muted red, always paired with a sign or label and never shown by color alone.
- **Avoid:** Gradients, glassmorphism, glowing shadows, emoji in the UI, oversized rounded cards everywhere, stock illustrations and filler marketing copy.
- **Typography:** One sans-serif family. Tabular numerals for all amounts. A clear size hierarchy with no more than 3 sizes per screen.
- **Layout:** Dense but readable lists. The dashboard puts numbers first and charts second. The primary action (Add record) is always reachable in one tap on mobile.
- **Charts:** At most 6 category colors. Smaller categories are grouped into "Other". Every chart has direct labels or a legend with values.
- **States:** Every screen has designed empty, loading and error states.
- **Accessibility:** WCAG 2.1 AA contrast, full keyboard use, visible focus and labelled form fields.

## Testing Strategy

- **Unit (Vitest):** Aggregation (totals, category breakdown, monthly series), money parsing and formatting, THB conversion and rounding, Buddhist Era to CE conversion, the AI response parser (valid, partial and malformed outputs), the duplicate check, CSV output (escaping, BOM, Thai text) and Zod schemas.
- **Integration (Vitest):** API routes against a temporary SQLite DB, covering record CRUD, category rules (no deleting an in-use category), the extract route with the Anthropic client mocked, and the rate fetch with Frankfurter mocked (success, unsupported currency, network failure, cache hit).
- **E2E (Playwright):** Upload a fixture image with a mocked extraction, review, save, see it in the list and on the dashboard. Manual add, edit and delete. A USD record with a mocked rate shows the right THB total. CSV export downloads a file. Run once at a mobile viewport.
- **Real AI calls:** Not part of the automated suite. A separate script, `npm run extract:sample`, runs one real extraction on a fixture, run by hand only, because it costs API credits.
- **Coverage target:** 80% lines for `src/lib`. No target for UI components.
- **Fixtures:** Synthetic or fully redacted slips only. Never real account numbers or names.

## Boundaries

**Always**
- Run lint, type check and unit tests before every commit.
- Validate all input and all AI output with Zod before it touches the database.
- Keep the API key in `.env` and read it on the server only.
- Store money as integer minor units.
- Check `git status` and the staged diff for secrets and personal data before every push (the repo is public).

**Ask first**
- Adding a dependency not listed in this spec.
- Changing the database schema after the first migration.
- Running anything that makes real Claude API calls (it costs credits).
- Changing the default model ID or the extraction prompt in ways that affect cost.
- Exposing the app beyond the local network in Phase 1.
- Every Railway action: creating the service or volume, setting variables, deploying, and moving data.
- Anything that adds Railway cost (more replicas, bigger volume, paid add-ons).

**Never**
- Commit `.env`, `data/`, uploaded images, the SQLite DB, `.tmp/`, `session-handoff/` or `node_modules/`.
- Commit real slips, receipts or any personal financial data, including as test fixtures.
- Send images anywhere other than the Anthropic API. The rate API receives only a date and a currency code.
- Save an AI-extracted record without the user confirming it.
- Delete or skip failing tests to get to green.
- Deploy publicly without the login in place and tested.
- Run more than one replica against the SQLite volume.

## Success Criteria

**Phase 1**

1. From a phone on the home network, the user can photograph a bill and save a correct record in under 30 seconds, including the review step.
2. On a test set of 10 sample slips and bills (Thai and English), the AI gets amount, currency and date right in at least 9, and suggests a sensible category in at least 8. Errors can be fixed in the review form.
3. All CRUD operations work for records and categories, and data persists across restarts.
4. The dashboard THB totals match a hand calculation for the seeded test data, including records in other currencies.
5. A Thai slip dated in BE is saved and shown with the correct CE date.
6. The CSV export opens in Excel with Thai text intact and THB amounts matching the dashboard.
7. Lint, type check, unit, integration and E2E suites all pass. `src/lib` coverage is at least 80%.
8. No secrets or personal data appear anywhere in git history.

**Phase 2**

9. The app is live on a Railway HTTPS URL, and the user can photograph a bill on mobile data (not home Wi-Fi) and save it.
10. Without a session, every page, API route and image URL redirects to `/login` or returns 401. This is verified by an automated test and by hand on the live URL.
11. Records and images survive a redeploy and a service restart.
12. Migrated data matches the local copy (record count and dashboard totals).
13. No secrets appear in the repo, build logs or client bundles. The API key is read on the server only.

## Decisions (resolved 2026-10-14)

1. **Currency:** All totals and charts in THB. Non-THB records are converted with a rate from the Frankfurter API, which the user can override.
2. **Dates:** Shown in CE. BE years on slips are converted during extraction.
3. **Access:** Phase 1 has no PIN or login and runs on the home network only. Phase 2 adds a single-password login because the app becomes public.
6. **Phases:** Phase 1 is local. Phase 2 deploys to the user's Railway account with SQLite on a volume.
4. **Receipts:** One record per image, total amount only.
5. **Backup:** Manual CSV export button.

7. **Phase 2 login:** Single password with a 30-day session cookie. No Google sign-in or 2FA.
8. **Phase 2 domain:** The free `*.up.railway.app` address. No custom domain.

## Open Questions

None.
