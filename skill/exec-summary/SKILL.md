---
name: exec-summary
description: Turn planning files (spec, plan, todo) into an executive summary presentation for a non-programmer, published as a private Claude Artifact. Use when the user types /exec-summary followed by file names, or asks for an "executive summary of <files>" or a presentation of a spec, plan or task list for the project owner to review.
argument-hint: <file> [<file> ...]
---

# exec-summary

Make a slide-style presentation that lets a project owner (who knows what they want, not how code works) check that a planned system is what they want, before any code is written. The owner names the files. The deck shows only what those files say, in plain English, with a source on every item.

You do the judgment (plain wording, diagram nodes, screen layouts). The scripts do everything else (checking, counting, drawing, HTML). Never write HTML or Mermaid yourself.

`<skill-dir>` below is this skill's base directory, shown when the skill loads. Run every script from the **project root** (the folder the owner's files are relative to), as `python "<skill-dir>/scripts/<name>.py" ...`.

Read these before writing `summary.json`:
- `<skill-dir>/references/writing-guide.md` - plain-language rules and a jargon glossary
- `<skill-dir>/references/summary-format.md` - every field, with a short example
- `<skill-dir>/references/design-rules.md` - the deck standard (so you know what the deck will look like and never fight it)

## Rules

**Always**
- Use only the files the owner named. Every fact comes from them and carries a `src` of the form `<path> > <heading>`.
- Label anything you infer (wireframes, simplified diagrams) as an example (`"example": true` on screens).
- Run `validate.py` and `check_coverage.py` before rendering. Render only when both pass.
- Publish as a **private** Artifact and reuse the saved link on re-runs.

**Ask the owner first**
- Before using design images (see step 5).
- Before publishing, and before sharing the link.
- Before changing the `summary.json` format or adding anything outside the standard library to the scripts.

**Never**
- Edit any input file.
- Read or summarize a file the owner did not name, or guess which files to use.
- Put secrets, `.env` values, real names, account numbers or personal data in the deck, even if a source file contains them. Leave such text out and say so.
- Write raw Mermaid or raw HTML into `summary.json`.

## Steps

1. **Check the inputs.** Paths come after the command, relative to the project or absolute, in any order. Only `.md` and `.txt` files are accepted. A path that does not exist or has another type stops the run: tell the owner which one.
   - **No paths given:** list likely planning files (Markdown files whose name or first heading mentions spec, plan, todo or tasks) and ask which to use. Never pick for them.
2. **Outline the files.**
   `python "<skill-dir>/scripts/outline.py" <file> [<file> ...]`
   It prints each file's headings, list items, checkboxes, `Task N` headings, checkpoint headings and stories as JSON. It reports structure only; you decide what each section means, whatever the file is called.
3. **Read the files and write `.tmp/exec-summary/summary.json`** in the project (a scratch file, not committed). Build a section only when the files contain that content: a spec alone gives a deck with no phase or task slides, and a todo alone gives phases, tasks and checkpoints. Do not mention files that were not given. List what you found in each `sources[].found`.
   - A section that fits no slide goes in `notes` (shown as "Other notes") unless you list it in `skipped` with a reason, for example "code example, not useful to the owner".
   - Every heading below level 1 in every file must end up either as the source of a deck item or in `skipped`.
4. **Check the shape.**
   `python "<skill-dir>/scripts/validate.py" .tmp/exec-summary/summary.json`
5. **Check nothing was dropped.**
   `python "<skill-dir>/scripts/check_coverage.py" .tmp/exec-summary/summary.json <file> [<file> ...]`
   Give exactly the files listed in `sources`.
6. **Design images (optional).** If the project has design images (for example in `design/`, `docs/design/` or `mockups/`), ask the owner whether to use them. If yes, pass the folder with `--design-dir <folder>` in step 7. Only folders the owner names are read; never search for them. Tell the owner that embedded images are **not checked for personal data**. Without images, the deck draws 2-4 grayscale wireframes from `screens`, labelled as examples.
7. **Render.**
   `python "<skill-dir>/scripts/render.py" .tmp/exec-summary/summary.json [--out <path.html>] [--design-dir <folder>]`
   The deck is written to `docs/exec-summary/<name>.html` and the path is printed. The name follows the inputs: one file gives `SPEC.html`, several give `SPEC+plan+todo.html` in the order given. If another deck made from different inputs already has that name, the folders are added (`other-SPEC.html`); the first deck keeps its simple name. `--out` must end in `.html` and can never be the summary or an input file. The render also records the deck's inputs in `docs/exec-summary/links.json`.
8. **Publish (after the owner agrees).** Show the owner the deck path, then publish the finished HTML file as a private Artifact with the Artifact tool. Do not edit or rewrite the HTML.
   - Look up a saved link: `python "<skill-dir>/scripts/paths.py" url <deck path>`. If it prints a link, publish to that same link (pass it as `url`) so the owner's link shows the new version.
   - After a first publish, save the link: `python "<skill-dir>/scripts/paths.py" set-url <deck path> <link>`. Only `https://claude.ai/` links are accepted.
   - Each deck has its own link, so a spec-only deck and a full deck never overwrite each other.
9. **Report** the link, the files covered, what you skipped and why, and anything you left out for privacy. Keep it short.

## When a script fails

Errors look like `path.to.field: message`, one per line, exit code 1. Fix `summary.json` and run the scripts again, **at most 3 times**. Then stop and show the owner the remaining errors. Never edit a script, a schema or an input file to make a check pass, and never skip a check.

## What the checks cover, and what they do not

- Tasks and checkpoints cannot be skipped. A task is counted from a `Task N` heading; **tasks written only as checkboxes are not counted**, so put them in the deck yourself and check by eye.
- Stories are counted from a "User stories" heading (numbered or `As ...` items) or `Story N` headings.
- Two files that repeat the same checkpoints show them once.
- Two headings with identical text: write `Heading#2` in the `src` of the second one.
- **Path spelling:** use the same spelling of each file in `sources`, in every `src` and on the command line. Slashes and a leading `./` are treated as the same. Paths must be relative to the project, with no `..`.
- The checks prove nothing was dropped and every `src` is real. They cannot prove your wording is faithful or plain. Read each item against its source before you render.

## Notes

- The Mermaid library loads from one pinned address. If it cannot load, each diagram shows a table of its parts instead, so the deck still reads.
- Re-running on the same files after they change updates the same deck and the same link.
- Do not run `install.py` or write to `~/.claude/skills` from this skill; the owner does that.
