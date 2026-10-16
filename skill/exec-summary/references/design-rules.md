# Deck design rules

The look of the deck is fixed in `templates/deck.css` and `scripts/render.py`. You do not style anything. This file says what the standard is, so you write content that fits it and never work around it. The rules come from the owner's own review of the sample decks (the "Keynote" look, see `SPEC-redesign.md` in the skill's source repository).

## Content comes first

- The owner reads the content. Anything that only says where it came from (the Source column, "Source: ..." lines) is **smaller, narrower and lighter**: 12 px text (11 px on a phone), about 14% of the table width, in the muted colour. Never make source text bigger or bolder, and never put it in the main columns.
- Keep `src` values short and exact (`SPEC.md > Objective`); long source text wraps in a narrow column. The last part after " > " also becomes the small label above the title of a text slide.

## One slide, one screen

- One slide on screen at a time. On a laptop window of 1280 x 650 px every slide fits with no scrolling. The renderer makes this true by **splitting**: a section that is too long continues on a "(continued)" slide. Text is never shrunk to make it fit.
- Limits per slide: 6 table rows, 6 user stories, 6 phase steps, 4 risks, 3 checkpoints, 5 tick boxes, 2 example screens side by side, 9 rule bullets (a rule group is never split), 4 tasks of one phase and a budget of 5 rows. A step-by-step flow with more than 4 boxes is drawn left to right.
- A very long text in a real project may still scroll inside its slide, and so may the example-screens slides on a small window (about 1280 x 650); on a larger window they fit. The top bar stays in place.

## Tables

- A value that repeats in neighbouring rows is shown once, spanning those rows: the story in the criteria table, the phase in the success table. Give every row its real value; the renderer groups them. Keep rows with the same value next to each other.
- Hairline rows, small uppercase headers, no zebra stripes. A group split across slides repeats its label at the top of the next one.
- Status words (High / Med / Low, phase) are text plus colour, never colour alone.

## Size and layout

- The deck is at most 1280 px wide.
- Text sizes: body at most 22 px, small text at most 18 px, slide titles at most 44 px. Two exceptions: the project name on the title slide (at most 84 px) and the title of a short text slide (at most 64 px). Key numbers on the title slide are at most 44 px. At most three text sizes on one slide.
- Stories, tasks, risks, phases, checkpoints and tick boxes are cards on the card colour with 12 px corners; the slide frame has 14 px corners and one soft shadow.

## Text-only slides

The Goal slide and notes slides have only a title, paragraphs and a source. The renderer picks the style from the text, so keep paragraphs short and each first sentence meaningful on its own:

- **Short text** (all paragraphs together 280 characters or fewer): a centred launch stage in the deck's own colours, with a big title and a soft glow like the title slide's.
- **Longer text:** a split stage with an accent panel (label, title, source) and one row per paragraph. The first sentence of each paragraph is bold, so the bold lines alone give the gist.

## Style

- Keynote look: one system sans-serif family, one accent colour, tight bold titles, cards and pills.
- Glow only on the title slide and on a launch-stage slide (both soft and in the theme colours). No other gradients, glow, emoji or stock illustrations.
- Wireframes are grayscale boxes with labels in a card, clearly different from a real design, and always labelled "Example layout, not the final design".
- Diagrams take their colours from the same colour tokens, in light and dark; print uses the light copy.
- Light and dark mode (WCAG AA contrast), readable at 360 px wide, full keyboard use with a visible focus ring, and a print layout of one slide per page (printing is always light).

## What this means for you

- Write short cells and short paragraphs. A long sentence in a narrow column makes a tall row.
- Do not add a column, field or format the schema does not have.
- If a rule here looks wrong for a real deck, tell the owner. Do not change the template while running the skill.

The rules above are checked by tests in the skill's source repository, so a later change cannot quietly undo them.
