# Writing guide

The reader is the project owner. They know what they want the system to do, but not how code works. Every word on an owner slide must make sense to them without help.

## Plain language

- Use everyday words and short sentences. Say what the system does for the owner, not how it is built.
- A technical term appears only with a short plain explanation the first time, in the same cell, for example "SQLite (a database stored in one file on your computer)". After that, use the term alone.
- No code, file paths or commands on owner slides. Say "the settings file" or "the login page", not a path or a route.
- Keep each item to one idea. Prefer "You can ..." and "The app ..." over passive wording.
- Do not add opinions, praise or advice. Report what the files say.

## No invention

- The deck contains only facts from the files the owner named. If the files do not say it, leave it out or put it in `open_questions`.
- Every item has a `src`. Check each item against its source before you render.
- Anything you infer is labelled. Screens are `"example": true`, and a simplified diagram says so in its title (for example "How the parts connect (simplified)").
- Do not round, guess or fill in numbers, dates or names the files do not give.

## No personal data

- Leave out secrets, `.env` values, API keys, passwords, account numbers, real people's names, email addresses and phone numbers, even when a source file contains them.
- Say what you left out in your final report ("one account number was left out"), without repeating it.
- Embedded design images are not checked for personal data. Tell the owner (see SKILL.md, step 6).

## Choosing sections

Decide what a file contains from its content, never from its name. Typical content and the section it fills:

| The files contain | Section |
|---|---|
| objective, overview, purpose | `goal` |
| user stories or a feature list | `stories` (with `criteria` for how each is checked) |
| screens, UI or design notes | `screens` |
| system parts, architecture, tech stack | `diagrams` (kind `architecture`), `stack` |
| a described user journey or process | `diagrams` (kind `flow`) |
| a data model | `data` (names and plain meaning; no column types) |
| phases, milestones | `phases` |
| a task list | tasks inside each phase |
| approval steps | `checkpoints` |
| risks | `risks` |
| boundaries or rules | `rules` |
| decisions, out-of-scope lists | `decisions`, `out_of_scope` |
| success criteria | `success` |
| anything else worth reading | `notes` |
| code, commands, folder layout, style rules | `skipped`, with a reason |

## Diagrams

- Write nodes and edges as data. Never write Mermaid.
- At most 12 nodes. Labels are short and plain ("The web app", "Your records"), not product names alone.
- Node ids are letters, digits and underscore only.
- An architecture diagram shows parts and connections. A flow diagram shows the main journey step by step.

## Screens

- 2 to 4 screens for the main things the owner does. Use the fixed block types (`header`, `nav`, `stats`, `chart`, `list`, `form`, `button`, `text`, `image`) with short labels that come from the files.

## Glossary

Use these plain explanations. Add new ones in the same style when a file uses another term.

| Term | Plain explanation |
|---|---|
| API | A way for one program to ask another program for something. |
| Database | A place where the app keeps its records so they are still there tomorrow. |
| SQLite | A database stored in one file on your computer. |
| Framework | A ready-made toolkit for building a certain kind of app. |
| TypeScript | A stricter form of JavaScript that catches mistakes early. |
| Runtime | The program that runs the app on a computer. |
| Deploy | Put the app on the internet so it can be used from anywhere. |
| Hosting service | A company that runs your app on its computers so it stays online. |
| Login / authentication | Proving who you are before you can use the app. |
| Environment variable, secret | A private setting, such as a key, kept out of the code. |
| CSV | A simple table file that opens in Excel. |
| Test (automatic check) | A small program that uses the app and checks it still works. |
| Build | Turning the written code into the finished app. |
| Repository (repo) | The folder where all the project's files and their history are kept. |
| Commit | A saved step in the project's history. |
| Mockup / wireframe | A rough picture of a screen, before it is built. |
| AI model | A program that can read text or pictures and answer. |
| Checkpoint | A point where you review the work and decide whether to go on. |
