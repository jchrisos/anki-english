# AGENTS.md

## Status: greenfield

This directory is empty — no code, no manifests, not even a git repo. There are **no**
build/test/lint commands to run, and no `Makefile`, `pyproject.toml`, or `package.json`
to infer from. Run `git init` before any `git` command, and add the real commands to
this file once tooling exists instead of assuming defaults.

## Project intent

Design rationale and the verified environment live in the OKF bundle at `.okf/`
(start at `.okf/index.md`); keep it in sync when the schema or tooling is decided.

Generate Anki flashcard decks (`.apkg`) for English study. The note type, source
vocabulary format (CSV/Markdown/API), and card design are **not decided yet** — confirm
before committing to a schema, because changing a note type's fields later invalidates
every note already created with it.

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
- Media must be registered in the package's media map and referenced by bare filename
  in fields/templates. Absolute or relative paths import as broken references.
- Verify output programmatically — unzip the `.apkg` and query the bundled sqlite
  (`select count(*) from notes`) — but still do one manual import to check card
  template rendering, which the note count cannot validate.
