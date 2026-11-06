# AGENTS.md

## Status: early skeleton

The repo holds documentation plus the first piece of tooling: `tools/build_decks.py`
builds the three **empty** deck packages from pinned constants. There is still no content
pipeline, no source data, and no tests or linter.

**Content only on demand.** The decks stay empty until the user explicitly asks for
flashcards. Never add notes, seed a package with a placeholder card, generate a starter
vocabulary list, or "test" the pipeline by writing real entries into `decks/`. Building the
packages is not a request for content; if an empty package turns out to be unimportable,
ask before seeding it.

```sh
python3 -m venv .venv                       # already exists locally, .venv/ is gitignored
.venv/bin/pip install -r requirements.txt   # genanki==0.13.1, edge-tts==7.3.1
.venv/bin/python tools/build_decks.py       # empty baseline: decks/{vocabulary,phrasal-verbs,collocations}.apkg
.venv/bin/python tools/build_decks.py --test  # tests/src + tests/media -> tests/decks (all gitignored)
.venv/bin/python tools/build_decks.py --test --notes  # same, with the entries from tests/src/
.venv/bin/python tools/build_audio.py --test  # mp3s into tests/media (production: omit --test)
.venv/bin/python tools/prepare_media.py --test  # PNG -> 900px JPEG in tests/media
```

Content lives in `src/<kind>.json` (one array per kind) and is included **only** with
`--notes`; a plain build still ships empty packages. Media lives in `media/`, named from the
entry's key (`voc_6a648cec.jpg`), and is an input: nothing regenerates art on a plain build.

`tests/` is a **separate, fully gitignored tree**: `tests/src/`, `tests/media/` and
`tests/decks/`. `--test` on any of the three tools switches the whole layout there, so test
source, images, audio and packages never mix with production and can never be committed.
Test builds are also isolated in Anki: their own pinned deck and model ids, their own names
(`Vocabulary (test)`), their own filenames (`vocabulary-test.apkg`) and a `test:` GUID
prefix. Anki matches decks by name, note types by id and notes by GUID, so reusing any one
of them would merge a rehearsal into the real deck.

The build validates every note before writing: all text fields, exactly one `level::` tag,
at least one known `category::` tag, and both the image and the mp3 present on disk. A
failure is a build error, not a card with a blank panel. Verifying a package still means
unzipping it and querying the bundled sqlite; there is no test suite yet.

**Two rules that bite on import, both learned the hard way:**

1. Media must be referenced *in the field*, not by the template: `Image` holds
   `<img src="key.jpg">` and `Audio` holds `[sound:key.mp3]`. Anki's importer only copies
   media it can see referenced in field text, so a bare filename wrapped by the template is
   silently dropped.
2. `BUILD_MOD` in `tools/build_decks.py` is the note type's `mod`, and Anki updates an
   existing note type only when the incoming mod is **newer**. Raise it whenever fields,
   templates or CSS change, or the new template never reaches a collection that already has
   the note type. In the import dialog keep "Update note types" at *If newer* (or *Always*).

Git is set up: branch `main`, remote `origin` →
`https://github.com/jchrisos/anki-english.git`. There is **no CI, no pre-commit hooks and no
PR template**, so nothing verifies a change automatically — run whatever checks you create
yourself.

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
source. **Three decks, one per kind**, each built as its own package under `decks/` —
`vocabulary.apkg`, `phrasal-verbs.apkg`, `collocations.apkg` — with pinned deck ids and
flat names (no `English::` parent; a parent would be a different id, not a rename).

**Every card has an illustration and a quoted movie/TV line** as its example — there is no
"make up a sentence" example field. Images are AI-generated and committed under `media/`;
**audio is synthesized with edge-tts** (pinned female US voice, `en-US-AvaNeural`,
`--rate=-10%`), one mp3 per note reading target → definition → dialog. It is never the
film's audio.

**Every note — vocabulary, phrasal verb or collocation — carries one or more categories**
(`color`, `car`, `travel`, `kitchen`, …) stored as `category::<slug>` **tags, never a
field** — an entry can belong to several groups. **Every note in all three kinds also
carries exactly one CEFR level tag** (`level::a1` … `level::c2`), assigned to the sense
being taught rather than to its individual words.

Still open: source vocabulary format (CSV/Markdown/API) and card templates beyond
front→back. Adding a template later is cheap; changing a model's field list is not, since
it invalidates existing notes.

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
- **`edge-tts` 7.3.1** is installed and working (`en-US` female neural voices,
  `--list-voices` to enumerate). The user installed it into the pyenv global interpreter,
  which bends the rule above — pin `edge-tts==7.3.1` in the repo `.venv` when one exists.
  Synthesis needs network access; it fails offline.
- `ffmpeg`, `lame` and `afinfo` are present but **not** used: one edge-tts call per card
  produces the whole three-part script, so no concat/mux step is needed.

## Anki-specific pitfalls (these corrupt or duplicate data)

- The deck is **incremental by design**: re-importing a rebuilt package updates notes in
  place by GUID and keeps their cards, intervals and review history. Identity is therefore
  sacred — see `.okf/concepts/incremental-updates.md`.
- A note's GUID is `voc:`/`pv:`/`col:` + phrase + an **authored sense slug**, never derived
  from the definition text, a row number or a timestamp. Rewording a definition must not
  change the GUID; if it does, that card starts over as a new note.
- Anki matches **decks by name** and **note types by id**. Renaming the deck or changing a
  model's field list stops updates on the existing notes. Import `.apkg` files only —
  a `.colpkg` replaces the whole collection, review history included.
- Normal import: leave "Import any learning progress" **unticked** (our packages carry no
  scheduling) and set "Update notes" to *Always*, since the source data is the truth.
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
- Audio is `[sound:<key>.mp3]` in the `Audio` field, same key as the image, and plays on
  the **back only** — on the front it would read the answer aloud. A missing mp3 imports
  silently, exactly like a missing image.
- Verify output programmatically — unzip the `.apkg` and query the bundled sqlite
  (`select count(*) from notes`) — but still do one manual import to check card
  template rendering, which the note count cannot validate.
