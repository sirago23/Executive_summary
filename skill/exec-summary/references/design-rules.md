# Deck design rules

The look of the deck is fixed in `templates/deck.css` and `scripts/render.py`. You do not style anything. This file says what the standard is, so you write content that fits it and never work around it. The rules come from the owner's own review of the sample decks.

## Content comes first

- The owner reads the content. Anything that only says where it came from (the Source column, "Source: ..." lines) is **smaller, narrower and lighter**: 12 px text (11 px on a phone), about 14% of the table width, in the muted colour. Never make source text bigger or bolder, and never put it in the main columns.
- Keep `src` values short and exact (`SPEC.md > Objective`); long source text wraps in a narrow column.

## Tables

- A value that repeats in neighbouring rows is shown once, spanning those rows: the story in the criteria table, the phase in the success table. Give every row its real value; the renderer groups them. Keep rows with the same value next to each other.
- At most about 8 rows per slide; longer tables continue on a "(continued)" slide, and a group split across slides repeats its label at the top of the next one.
- Status words (High / Med / Low, phase) are text plus colour, never colour alone.

## Size and layout

- The deck is at most 1280 px wide.
- Text sizes: body at most 22 px, small text at most 18 px, slide titles at most 44 px. At most three text sizes on one slide.
- One topic per slide. Large titles, short text.

## Style

- Calm, document-like slides: neutral background, dark text, one accent colour, one sans-serif family.
- Zebra rows and clear table headers.
- No gradients, glow, emoji or stock illustrations.
- Wireframes are grayscale boxes with labels, clearly different from a real design, and always labelled "Example layout, not the final design".
- Light and dark mode, readable at 360 px wide, arrow-key navigation, and a print layout of one slide per page (printing is always light).

## What this means for you

- Write short cells. A long sentence in a narrow column makes a tall row.
- Do not add a column, field or format the schema does not have.
- If a rule here looks wrong for a real deck, tell the owner. Do not change the template while running the skill.

The rules above are checked by tests in the skill's source repository, so a later change cannot quietly undo them.
