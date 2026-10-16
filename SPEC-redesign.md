# Spec: Deck redesign, "Keynote" look (v1.1)

Status: draft, open questions answered, awaiting the owner's approval (2026-10-16).
Parent spec: [SPEC.md](SPEC.md). This spec changes only the look of the deck. Everything in `SPEC.md` still applies unless a section below replaces it. When this spec is approved and built, the "Design Direction" section of `SPEC.md` and `skill/exec-summary/references/design-rules.md` are updated to match it.

## Objective

The owner tested `/exec-summary` in other projects and is happy with the content. The deck should now look like a presentation given to executives: more polished, premium and modern, and still easy to read.

The owner compared three styles on the same sample slides (Boardroom, Annual report, Keynote; preview: https://claude.ai/artifact/KLN6zW4he6VjT6qbPpbMix) and chose **Option C, Keynote**.

**User:** the project owner, a non-programmer, reading the deck on a laptop or desktop screen, sometimes on a phone, and sometimes presenting it to others.

**What stays the same:**
- One slide on screen at a time. The owner moves with Previous / Next, the arrow keys, Home / End and the Contents menu. The deck is never one long scrolling page.
- The content: the same slides in the same order (Slide Catalog in `SPEC.md`), the same words, the same `summary.json` format (frozen since Checkpoint C).
- One self-contained HTML file published as a private Artifact. Mermaid stays the only external script.
- No new tools, installs or dependencies, for the skill or for the person running it.

**User stories:**
1. As the owner, I open a deck and it looks like a polished executive presentation, so I am comfortable showing it to others.
2. As the owner, I see one slide at a time and it fits my laptop screen without scrolling, so I can focus on one topic.
3. As the owner, the title slide shows the key numbers at a glance (for example 7 user stories, 5 phases, 17 tasks, 5 checkpoints).
4. As the owner, I can still read every slide easily in light and dark mode, on a phone and on paper.

## The Keynote look

Reference: Option C on the preview page. It applies to every slide type, not only the three shown there.

**Colour tokens** (light / dark). The full list lives in `deck.css`; these are the starting values from the preview:

| Token | Light | Dark | Used for |
|---|---|---|---|
| `--bg` | `#eef1f6` | `#080b12` | page behind the slide |
| `--surface` (slide) | `#ffffff` | `#0e1320` | the slide itself |
| `--text` | `#0f1729` | `#f3f5fa` | main text |
| `--muted` | `#54607a` | `#a8b1c5` | labels, source text |
| `--accent` | `#2453c8` | `#84abff` | ids, pills, links, focus ring |
| `--accent-soft` | `#e9effd` | `#1b2747` | pill and title glow background |
| `--card` | `#f4f6fb` | `#161d2e` | cards, stat tiles, risk rows |
| `--line` | `#e2e6ee` | `#263049` | hairlines, table rules |
| `--hi` / `--med` / `--lo` | `#b8232c` / `#a14f00` / `#1d7148` | `#ff9c9c` / `#ffc27a` / `#80e0aa` | impact text |
| `--hi-bg` / `--med-bg` / `--lo-bg` | `#fdecec` / `#fdf1e3` / `#e6f5ec` | `#3a1a20` / `#3a2a16` / `#163325` | impact badge background |

**Type:** one system sans-serif family (as now, no downloaded fonts). Titles bold (700-750) with tight letter spacing (about -0.025em). Body text regular, card text semi-bold. Numbers use tabular figures.

**Sizes** (replace the current limits in `design-rules.md`):
- Slide titles at most 44 px. **Exceptions:** the project name on the title slide, at most 84 px; the title of a launch-stage text slide (see below), at most 64 px.
- Body text at most 22 px; small text at most 18 px; source text 12 px (11 px on a phone), as now.
- Stat tile numbers on the title slide at most 44 px.
- At most three text sizes on one slide, not counting source text and the slide counter.

**Shapes:** slide corners 14 px, cards and tiles 12 px, pills fully round. No shadows inside the slide. One soft shadow on the slide frame.

**Glows:** a soft accent glow in the top-right corner of the title slide, and one at the top of a launch-stage text slide. No other gradients, glows, emoji or stock pictures.

### Text-only slides (added 2026-10-16, owner's choice at Checkpoint E2)

The Goal slide and the notes slides have only a title, paragraphs and a source. Previews: https://claude.ai/artifact/C9EHdg17Tc9UV9B8nJZwy8 (Option B and Option C). The renderer picks the style from the text, with no new `summary.json` field:
- **Launch stage** (all paragraphs together 280 characters or fewer): centred, in the deck's own colours so it blends with the other slides (light or dark with the mode); an eyebrow, the title up to 64 px, a short accent rule, the paragraphs as centred lines, the source at the bottom, a soft accent glow at the top like the title slide's. Prints without the glow.
- **Split stage** (longer text): a solid accent panel on the left with the eyebrow, the title and the source; one row per paragraph on the right, the first sentence of each in semi-bold, the rest muted. Stacks on a phone.
- The eyebrow is the last part of the source (after the last " > ").

### Slide-by-slide treatment

| Slide | Keynote treatment |
|---|---|
| 1 Title | Pill "Executive summary · <status>", huge project name, tagline in muted text, a row of up to 4 **stat tiles**, a footer line with the files covered and the date |
| 2 Goal, notes | Launch stage or split stage, see "Text-only slides" |
| 3 Stories | Cards in a 2-column grid: "S1" pill, "As <who>, I want" label, the want text in semi-bold |
| 4 Criteria | Table restyled: hairline rows, no zebra stripes, the story shown once spanning its rows (as now) |
| 5 Screens | Wireframes stay grayscale and labelled "Example layout, not the final design", inside a card |
| 6-7 Diagrams | Mermaid with the `base` theme and colours taken from the tokens, light and dark; fallback table restyled |
| 8, 9, 14-17 Tables | Same table style as slide 4 |
| 10 Phases | A step strip of cards, one per phase, with the phase id in an accent pill |
| 11 Tasks | Phase title, then each task as a row card: title in semi-bold, "You will see" text in muted below |
| 12 Checkpoints | Cards with the checkpoint title and its items as a short list |
| 13 Risks | Row cards: impact badge (dot plus the word High / Med / Low), the risk in semi-bold, the handling in muted below, source on the right |
| 18 Please check | Cards with real checkboxes; checked items keep their state in localStorage (as now) |

**Stat tiles** (title slide): counted from `summary.json`, never typed by Claude. Show up to 4 tiles, in this order, skipping any that are 0: user stories, delivery phases, tasks, checkpoints you approve, acceptance criteria, risks, questions for you. A spec-only deck therefore shows stories, criteria, risks or questions instead of phases and tasks.

**Top bar:** restyled to match (pill buttons, the slide counter, Contents, the dark mode switch). Same controls and keyboard behaviour as now.

### One slide at a time, fitting the screen

- The active slide fills the window below the top bar, at most 1280 px wide.
- On a laptop or desktop window of at least 1280 × 650 px (a 1366 × 768 laptop screen with the browser bars), every slide of both sample decks fits with no scrolling.
- To make long slides fit, the renderer may put fewer rows or cards on one slide and continue on a "(continued)" slide, as tables already do. It never shrinks text below the sizes above.
- If a slide is still too tall (very long text in a real project), the slide scrolls inside itself; the top bar stays in place.
- On a phone (under 720 px wide) a slide may be taller than the screen and scrolls; nothing scrolls sideways at 360 px except a wide table inside its own box.

## Tech Stack

No change: Python 3.10+ standard library in `skill/`, one HTML file with inline CSS and JS, Mermaid from the pinned jsdelivr URL. No web fonts, no new libraries, no images in the template.

## Commands

No change (see `SPEC.md` > Commands and `CLAUDE.md`):

```
Tests:    python -m pytest -q
Coverage: python -m pytest --cov            (85% or more)
Lint:     python -m ruff check .  &&  python -m ruff format --check .
Render:   python skill/exec-summary/scripts/render.py <summary.json>
Install:  python tools/install.py [--dry-run] [--yes]
```

## Project Structure

Files this change touches:

```
skill/exec-summary/templates/deck.css     -> new tokens and styles (most of the work)
skill/exec-summary/templates/deck.html    -> top bar markup if needed
skill/exec-summary/templates/deck.js      -> Mermaid base theme colours; in-slide scroll fallback
skill/exec-summary/scripts/render.py      -> title slide stat tiles, card markup for stories, tasks, risks, checkpoints, please check; rows per slide if needed for fit
skill/exec-summary/references/design-rules.md -> rewritten for the Keynote look
SPEC.md                                   -> Design Direction points here
tests/test_deck_template.py, tests/test_render.py -> updated and new tests
```

Not touched: `schema/summary.schema.json`, `validate.py`, `check_coverage.py`, `outline.py`, `mermaid.py`, `wireframe.py` (except styling hooks), `SKILL.md` (except a one-line pointer if needed).

## Code Style

As in `SPEC.md`. For CSS: every colour is a token defined first on `:root`, redefined in the two dark blocks (`prefers-color-scheme` guarded by `:not([data-theme="light"])`, and `[data-theme="dark"]`). Components use tokens only, never literal colours.

```css
.risk .badge { color: var(--hi); background: var(--hi-bg); }
.risk .badge::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
```

Render functions stay small and pure; every string from `summary.json` is escaped as now.

## Testing Strategy

- **Update** the existing contrast tests in `tests/test_deck_template.py` to the new tokens: body, muted and source text, impact text on the slide and on its badge background, all WCAG AA in light, dark and print.
- **Update** `test_deck_width_and_text_sizes_stay_at_the_chosen_limits` to the new size limits, including the 84 px title-slide exception.
- **New render tests:**
  - stat tiles: the counts match the data; zero counts are skipped; at most 4 tiles; a spec-only fixture shows no phase or task tile.
  - stories, tasks, risks, checkpoints and please-check render as cards, with source text and escaping intact.
  - the only `gradient` in the CSS is on the title slide.
  - Mermaid is initialised with the `base` theme and token colours.
- **Keep passing:** all existing render, sample, coverage and security tests (escaping, CSP, no external scripts besides Mermaid). Coverage stays at 85% or more.
- **Browser checks (by Claude, with Playwright, then by the owner):**
  - both sample decks at 1280 × 650 and 1920 × 1000: every slide fits with no scrolling (script: compare each active slide's height to the window).
  - 360 px wide: nothing scrolls sideways.
  - light and dark mode; diagrams draw in both.
  - Print to PDF: one slide per page, light colours, nothing cut off.
  - keyboard only: arrows, Home, End, checkboxes, visible focus.

## Boundaries

**Always**
- Keep one slide on screen at a time.
- Keep the content and the `summary.json` format exactly as they are.
- Show status as words plus colour.
- Look at the result in a browser before reporting it done (see `CLAUDE.md` > Verify before reporting).

**Ask first**
- Any change to the `summary.json` format, including a new field for the stat tiles.
- Adding a web font or any file the deck loads from outside.
- Changing a token value so a contrast test has to be relaxed.

**Never**
- Add dependencies to `skill/`, or ask the user to install anything.
- Shrink text below the size rules to make a slide fit.
- Turn the deck into one long scrolling page.
- Delete or weaken a test to get to green.

## Success Criteria

1. Both sample decks render in the Keynote look on every slide type, and the owner approves them in light and dark mode.
2. Navigation is one slide at a time, as before: Previous / Next, arrows, Home / End, Contents.
3. At a 1280 × 650 window, every slide of both sample decks fits with no scrolling.
4. The title slide shows up to 4 correct stat tiles, counted from the data.
5. WCAG AA contrast in light, dark and print, checked by tests; keyboard use and visible focus work.
6. 360 px: no sideways scrolling. Print: one slide per page, nothing cut off.
7. All tests pass, ruff is clean, coverage is 85% or more, and `summary.json` is unchanged (existing decks re-render without edits).
8. Both published sample Artifacts are re-rendered and updated at their existing links.

## Decisions (resolved 2026-10-16)

1. **Fit target:** 1280 × 650 window (a common laptop with browser bars). Larger screens fit automatically.
2. **Stat tile order:** build order, as above: user stories, delivery phases, tasks, checkpoints you approve, then acceptance criteria, risks, questions for you. Zero counts are skipped.
3. **Opening mode:** follow the computer's light or dark setting, as now. The switch still works and the last choice is remembered.
4. **Text-only slides** (2026-10-16, at E2): split stage for text-heavy slides, launch stage for very short ones (see "Text-only slides").

## Open Questions

None.
