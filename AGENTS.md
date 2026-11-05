# AGENTS.md

## Status: greenfield

The repo holds only documentation — no code, no manifests, no tooling. There are **no**
build/test/lint commands to run, and no `Makefile`, `pyproject.toml`, or `package.json`
to infer from. Add the real commands to this file once tooling exists instead of
assuming defaults.

Git is set up: branch `main`, remote `origin` →
`https://github.com/jchrisos/anki-english.git`, one commit so far. There is **no CI, no
pre-commit hooks and no PR template**, so nothing verifies a change automatically —
run whatever checks you create yourself.

## Project intent

Design rationale and the verified environment live in the OKF bundle at `.okf/`
(start at `.okf/index.md`); keep it in sync when the schema or tooling is decided.

Generate Anki flashcard decks (`.apkg`) for English study across three confirmed content
kinds: **vocabulary** (single words), **phrasal verbs**, and **collocations**. Entry text
is often multi-word, so an entry's identity is the full phrase plus its sense — never a
single token or a row index — and GUIDs are prefixed per kind (`voc:`/`pv:`/`col:`) so
the same string cannot collide across kinds.

Decided for v1: **one note type per kind** (three pinned model ids) with fields
headword/phrase, pronunciation (General American IPA), definition, image, dialog and
source. **Every card has an illustration
and a quoted movie/TV line** as its example — there is no "make up a sentence" example
field. Images are AI-generated and committed under `media/`; dialog quotes are text only
(no audio clip). **Vocabulary words also carry one or more categories** (`color`, `car`,
`travel`, `kitchen`, …) stored as `category::<slug>` **tags, never a field** — a word can
belong to several groups. **Every note in all three kinds also carries exactly one CEFR
level tag** (`level::a1` … `level::c2`), assigned to the sense being taught rather than to
its individual words. Still open: source vocabulary format (CSV/Markdown/API), deck
layout, and card templates beyond front→back. Adding a template later is cheap; changing a
model's field list is not, since it invalidates existing notes.

## Repo-local agent

`.opencode/agents/american-english-teacher.md` is a `subagent` for the **content** of the
decks (definitions, General American pronunciation, register, pt-BR interference, dialog
quotes with attribution, image briefs). It has no shell access and asks before editing,
and it does not touch schema, model/deck ids, GUIDs or `.apkg` packaging — launch it for
wording, not for build work.

## Verified local environment (macOS, this machine)

- Anki desktop **25.09** at `/Applications/Anki.app`, profile `User 1`
  (`~/Library/Application Support/Anki2/`). There is no `anki` binary on `PATH`, so the
  workflow is "write a file, import it by hand", not CLI automation.
- Installed add-ons: AwesomeTTS, Review Heatmap. **No AnkiConnect** — do not plan on
  writing to the live collection over `127.0.0.1:8765` unless the user installs it.
- `python3` is 3.10.16 (pyenv default; 3.11.5 also installed). No `uv`, no `pipx`, and
  `genanki` is **not** installed. Create a repo-local `.venv` and pin deps; never
  install packages into the pyenv global interpreter.

## Anki-specific pitfalls (these corrupt or duplicate data)

- `.apkg` is just a zip containing `collection.anki2` plus a `media` map. Never
  hand-edit one; always regenerate from source.
- Pin `deck_id`, the model id, and the note `guid` function as **constants**. Random
  ids/GUIDs mean every re-import creates a duplicate deck and duplicate notes instead
  of updating the existing ones — the single most common mistake here.
- Import matches notes by GUID only within the same model and deck ids. Changing a
  model's field list requires a new model id; reusing it remaps or breaks old notes.
- Categories are **tags** (`category::kitchen`), not fields. Multi-value by design, and
  tag edits never touch note identity — so adding a category later is free, while a
  `Category` field would have been a permanent schema decision.
- CEFR level is a **separate tag namespace** (`level::b1`), never `category::b1`, so
  `tag:category::*` stays a clean list of themes and level filters stay exact.
- Media must be registered in the package's media map and referenced by bare filename
  in fields/templates. Absolute or relative paths import as broken references.
- Every note now needs an image, so a silently missing file is a blank card, not a
  cosmetic bug. Name image files from the note's content hash (the GUID), keep them in
  `media/`, and assert every referenced file exists before writing the package.
- Verify output programmatically — unzip the `.apkg` and query the bundled sqlite
  (`select count(*) from notes`) — but still do one manual import to check card
  template rendering, which the note count cannot validate.
