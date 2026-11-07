# anki-english

Generate Anki flashcard decks (`.apkg`) for English study across three content kinds —
**vocabulary**, **phrasal verbs** and **collocations** — from plain JSON source plus
committed images and audio.

Every card carries: General American IPA, a part of speech, a CEFR level, a one-sentence
definition, an AI-generated illustration, a quoted movie/TV line with attribution, a second
authored example sentence, four separate audio clips (word, explanation, dialog, example) and
a set of `category::` tags for filtering. A **verb** card also carries one example sentence
per form — `Present`, `Past`, `Past participle` — each shown and spoken on its own row under
the authored example.

The authored example is required because many quotes are a single short line ("Round up the
usual suspects.") and show the target in only one situation; the extra sentence gives a
second, everyday use. **Both the quote and that sentence use the target in the entry's own
form** — the base form on the front — so `hire` quotes `"I want to hire you."` (not
`"You're hired."`) and its example reads `We need to hire two more nurses this month.` It is
ours, the quote never is. Verbs are the other place the text is
not a movie quote, because real lines that use a given past form of an arbitrary verb are too
rare to require. There is no conjugation table on the card — that was tried and dropped.

## Status

Early, but working. The generator builds real packages; the committed decks are deliberately
**empty baselines** that pin the deck and note-type ids. Content is added only on explicit
request, and the only real content currently lives in `tests/`, which is not versioned.

## Quick start

```sh
python3 -m venv .venv                        # already exists locally
.venv/bin/pip install -r requirements.txt    # genanki 0.13.1, edge-tts 7.3.1

# empty baseline packages that pin the ids (committed)
.venv/bin/python tools/build_decks.py

# test build: reads tests/src + tests/media, writes tests/decks (all gitignored)
.venv/bin/python tools/build_decks.py --test --notes

# one mp3 per entry (skips files that already exist)
.venv/bin/python tools/build_audio.py --test

# PNG -> 900px JPEG, keeps a package near 2 MB
.venv/bin/python tools/prepare_media.py --test
```

`--only vocabulary|phrasal-verbs|collocations` restricts any of these to one kind.
`--notes` is what makes the build include entries; without it you get the empty baseline.

## Repository layout

```
decks/            committed baseline packages (0 notes, ids only)
src/              production source, one JSON array per kind  (does not exist yet)
media/            production images and mp3s                  (does not exist yet)
tests/            the whole test tree — gitignored
  src/  media/  decks/
tools/
  build_decks.py    validate, assemble and pack the decks
  build_audio.py    edge-tts clips, three per note
  prepare_media.py  downsize generated images
  deck_common.py    identity rules shared by all of the above
.okf/             design rationale, schema, decision log (start at .okf/index.md)
AGENTS.md         operating notes for agents working in this repo
```

`--test` moves `src`, `media` and the output directory together, so a test build can never
read production art or write into `decks/`.

## How a note is built

Each entry in `src/<kind>.json` becomes one note:

| Key | Goes to |
|---|---|
| `phrase` | `Word` / `Phrase` |
| `pronunciation` | `Pronunciation` |
| `definition` | `Definition` |
| `dialog`, `source` | `Dialog`, `Source` |
| `example` | `Example` — a second authored sentence using the target, under the quote |
| `speaker_gender` | picks the dialog voice (male/female) |
| `present_example`, `past_simple_example`, `past_participle_example` | the three example rows under the quote (verbs only) |
| `categories`, `level`, `pos` | `category::*`, `level::*`, `pos::*` tags |
| `sense` | the stable half of the note GUID — never derived from the definition |
| `image_brief` | authoring metadata for regenerating the illustration |

Media filenames come from the phrase and sense, so they cannot drift:

```
media/voc_6a648cec.jpg
media/voc_6a648cec-word.mp3
media/voc_6a648cec-explanation.mp3
media/voc_6a648cec-dialog.mp3
media/voc_6a648cec-example.mp3
media/voc_6a648cec-present-example.mp3        # verbs only
media/voc_6a648cec-past-simple-example.mp3
media/voc_6a648cec-past-participle-example.mp3
```

The build **fails** rather than emitting a half-empty card: every text field must be
present, the pronunciation must be IPA in slashes, a part of speech is required on every
kind, there must be exactly one `level::` tag, at least one known `category::` tag, and the
image plus every required mp3 must exist. A missing authored example fails, a verb without
all three form examples fails, and a non-verb carrying them fails as well.

## Importing into Anki

There is no Anki CLI on this machine and no AnkiConnect, so you import the file by hand:

1. **File → Import**, choose the `.apkg`.
2. **Import any learning progress**: unticked (the packages carry no scheduling).
3. **Update notes**: *Always* — the JSON is the source of truth.
4. **Update note types**: *If newer* or *Always*. Leaving this at *Never* strands a
   collection on an old template forever, silently.

Re-importing updates notes **in place** by GUID, keeping cards and review history.

## Rules that protect your collection

These are the ones that bite; the full reasoning is in `.okf/concepts/apkg-safety.md`.

- **Identity is the GUID**, built from kind prefix + phrase + an authored sense slug.
  Rewording a definition must not change it, or that card's history starts over.
- **Deck names, deck ids, model ids and media filenames are frozen.** A rename is a new
  object in Anki, not an edit.
- **Media must be referenced inside a field** — `<img src="key.jpg">`, `[sound:key.mp3]`.
  A bare filename wrapped by the template is silently dropped on import and the card shows
  a broken image.
- **A field-list change needs a new model id.** Anki compares schemas and treats a GUID
  match with a different note type as *conflicting*, leaving the old card untouched. The
  model ids in this repo are on their **fifth** generation for exactly that reason (the
  authored example is the latest field change).
- **`BUILD_MOD` must be raised** whenever fields, templates or CSS change — note types only
  update when the incoming `mod` is newer.

## Content

Content is added **only on demand**. The committed packages stay empty; nothing seeds a deck
with a placeholder card or a starter list to prove the pipeline works.

Design decisions, the schema and the trade-offs behind them live in `.okf/` (start at
`.okf/index.md`, with the reverse-chronological log at `.okf/log.md`).
