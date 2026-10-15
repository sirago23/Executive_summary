# summary.json format

The file is checked by `validate.py` against `schema/summary.schema.json`, which is the full reference for every limit. This guide explains the fields. Unknown fields are errors.

Only `project`, `sources` and `skipped` are required. Leave out any other section whose content is not in the files; its slide is dropped without a warning.

Every `src` has the form `<path> > <heading>`, with the path spelled exactly as in `sources` and on the command line, and the heading exactly as in the file. `Heading#2` picks the second of two identical headings.

## Fields

| Field | What it holds |
|---|---|
| `project` | `name` (required), `tagline`, `status`, `date` |
| `sources` | One per input file: `path`, `modified` (date), `found` (kinds of content, free words such as `stories`, `stack`) |
| `skipped` | `{src, reason}` for a heading you leave out on purpose. The reason is never empty |
| `goal` | `text` (1-6 short paragraphs) and `src` |
| `stories` | `id`, `as`, `want`, optional `so`, `criteria` (a list), optional `criteria_src`, `src` |
| `screens` | `title`, `example` (true when you drew it), `blocks` (`type` and `label`), `src` |
| `diagrams` | `id`, `kind` (`architecture` or `flow`), `title`, `nodes` (`id`, `label`, optional `group`), `edges` (`from`, `to`, optional `label`), `src` |
| `data` | `name`, `plain`, optional `fields`, `src` |
| `stack` | `part`, `choice`, `plain` (what it is, in plain words), `src` |
| `phases` | `id`, `title`, optional `goal`, `tasks` (`id`, `title`, `you_will_see`, `src`), `src` |
| `checkpoints` | `title`, optional `phase`, `items`, `src` |
| `risks` | `risk`, `impact` (`High`, `Med` or `Low`), `handling`, `src` |
| `rules` | `always`, `ask_first`, `never` (lists), `src` |
| `decisions`, `out_of_scope` | `text`, `src` |
| `success` | `text`, optional `phase`, `src` |
| `notes` | `title`, `text` (1-8 paragraphs), `src` - sections that fit nowhere else |
| `open_questions` | Plain questions the owner still has to answer |

Block types for screens: `header`, `nav`, `stats`, `chart`, `list`, `form`, `button`, `text`, `image`.

## Limits worth remembering

- At most 12 nodes per diagram; every edge points to a node that exists; node ids use letters, digits and underscore only.
- Text cannot be empty or only spaces. Ids must be unique within their list.
- At most 40 stories, 12 phases, 6 screens, 6 diagrams.
- Files are read up to 2 MB.

## Short example

```json
{
  "project": { "name": "Billing Record", "tagline": "Record spending from a photo of a bill." },
  "sources": [
    { "path": "SPEC.md", "modified": "2026-10-14", "found": ["goal", "stories", "stack"] }
  ],
  "skipped": [
    { "src": "SPEC.md > Commands", "reason": "Developer commands, not useful to the owner." }
  ],
  "goal": {
    "text": ["A personal web app that keeps track of money in and out from photos of bills."],
    "src": "SPEC.md > Objective"
  },
  "stories": [
    {
      "id": "S1",
      "as": "the user",
      "want": "to photograph a bill and save a record",
      "criteria": ["A record is saved in under 30 seconds."],
      "src": "SPEC.md > User stories"
    }
  ],
  "stack": [
    {
      "part": "Database",
      "choice": "SQLite",
      "plain": "A database stored in one file on your computer.",
      "src": "SPEC.md > Tech Stack"
    }
  ],
  "open_questions": ["Which currency should totals use?"]
}
```

A complete, checked example for a real spec and for spec + plan + todo is in the source repository under `tests/fixtures/billing/`.

## Format changes

The format is frozen from Checkpoint C. Do not add or rename fields while running the skill; ask the owner.
