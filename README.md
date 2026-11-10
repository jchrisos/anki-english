# anki-english

Generate Anki flashcard decks (`.apkg`) for English study across three content kinds —
**vocabulary**, **phrasal verbs** and **collocations** — from plain JSON source plus
committed images and locally generated audio.

Every card carries: General American IPA, a part of speech, a CEFR level, a one-sentence
definition, an illustration (when the entry's image file exists), an authored example sentence,
three separate audio clips (word, explanation, example) and a set of `category::` tags for
filtering. A **verb** card also
carries one example sentence per form — `Present`, `Present participle`, `Past`, `Past
participle` — each shown and spoken on its own row under the authored example. The target is
**bold** in every authored example: the source wraps it in `**...**` and the build renders
`<b>` (and strips the markers from the spoken text).

The authored example is required because a definition names the sense but never shows it in
use; one everyday sentence does. **It uses the target in the entry's own form** — the base form
on the front — so `hire` reads `We need to hire two more nurses this month.`, never
`You're hired.` The verb form rows show the other tenses. There is no conjugation table on the
card — that was tried and dropped.

## Status

Early, but working. The generator builds real packages. The generated **vocabulary** deck is
still an empty baseline that pins the deck and note-type ids; the **phrasal verbs** deck is
complete at its **350-card target** (A1–B2) and the **collocations** deck at its
**800-card target** (A1–B2). Content is added only on explicit request. Illustrations for both
finished batches are still pending: every entry has a paste-ready Midjourney brief, but no
image files are committed yet, so those cards are text and audio only until the renders land
in `media/`.

## Quick start

```sh
python3 -m venv .venv                        # already exists locally
.venv/bin/pip install -r requirements.txt    # genanki 0.13.1, edge-tts 7.3.1

# empty baseline packages that pin the ids (written to decks/, not committed)
.venv/bin/python tools/build_decks.py

# test build: reads tests/src + tests/media, writes tests/decks (all gitignored)
.venv/bin/python tools/build_decks.py --test --notes

# check the manifest and the source entries before building
.venv/bin/python tools/lint_content.py --test --report

# one mp3 per entry (skips files that already exist)
.venv/bin/python tools/build_audio.py --test

# production collocations batch (lint first, then audio, then the package)
.venv/bin/python tools/lint_content.py --report
.venv/bin/python tools/build_audio.py --only collocations
.venv/bin/python tools/build_decks.py --notes --only collocations

# PNG -> 900px JPEG, keeps a package near 2 MB
.venv/bin/python tools/prepare_media.py --test
```

`--only vocabulary|phrasal-verbs|collocations` restricts any of these to one kind.
`--notes` is what makes the build include entries; without it you get the empty baseline.

Packages are build artifacts: the build writes them under `decks/`, and `.gitignore` keeps
them out of git. Build locally before importing; nothing in the repository ships a package.

## Content workflow: manifest first

`src/index.csv` is the reviewed plan and comes before any card:

```
kind,phrase,sense,pos,level,categories,gloss
vocabulary,run,move-fast-on-foot,verb,a1,sports,to move quickly on your feet
vocabulary,run,manage-an-operation,verb,b1,work,to control or manage something
```

One row per **sense**, not per word: `sense` is the stable identity half of the GUID, so it is
frozen before a note exists. `categories` is semicolon-separated. Glosses are one line; the
full definition is written later in `src/<kind>.json`.

The intended loop is **plan → write → lint → build**:

1. Add the batch to `src/index.csv` and review the glosses and level bands.
2. Write the matching entries in `src/<kind>.json`.
3. `tools/lint_content.py` checks both halves and reports progress and repetition.
4. `tools/build_decks.py --notes` only after the lint is clean.

`lint_content.py` fails on an unknown kind/part of speech/category, a level outside the deck's
range, a bad sense slug, a duplicate `kind + phrase + sense`, a source entry missing from the
manifest, a manifest/source disagreement, missing text, bad IPA slashes, unbolded targets, verb
rows on a non-verb, and a missing Midjourney parameter block. `--report` prints the most
repeated example openers, image-brief openers and camera angles, which is how a batch that has
gone monotone is caught early.

## Repository layout

```
decks/            build output (.apkg, gitignored; .gitkeep keeps the folder)
src/              production source
  index.csv         the reviewed manifest: one row per planned sense
  <kind>.json       the written entries, included only with --notes
media/            committed images + generated mp3s (mp3s gitignored)
tests/            the whole test tree — gitignored
  src/  media/  decks/
tools/
  build_decks.py    validate, assemble and pack the decks
  lint_content.py   manifest + source checks and the repetition report
  build_audio.py    edge-tts clips, one per spoken part
  prepare_media.py  normalize committed images to 900px JPEG
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
| `image` | `Image` — name of the illustration in `media/` without an extension (e.g. `voc_6a648cec`, resolved to `.jpg`/`.png`/`.gif`/…); if no file is found the card is built without a picture |
| `example` | `Example` — an authored sentence using the target; the target is wrapped in `**...**` |
| `present_example`, `present_participle_example`, `past_simple_example`, `past_participle_example` | the four example rows under the authored example, in card order (verbs only) |
| `categories`, `level`, `pos` | `category::*`, `level::*`, `pos::*` tags |
| `sense` | the stable half of the note GUID — never derived from the definition |
| `image_brief` | the Midjourney prompt for the illustration, derived from `definition` (never `example`) and rendered outside the repo, never written to the note |

The illustration comes from the entry's `image` field, which names the image rather than its
format — a stem without an extension is tried against `.jpg`, `.jpeg`, `.png`, `.gif` and
`.webp`. Audio filenames come from the phrase and sense, so they cannot drift:

```
media/voc_6a648cec.jpg                          # "image": "voc_6a648cec"
media/voc_6a648cec-word.mp3
media/voc_6a648cec-explanation.mp3
media/voc_6a648cec-example.mp3
media/voc_6a648cec-present-example.mp3        # verbs only
media/voc_6a648cec-present-participle-example.mp3
media/voc_6a648cec-past-simple-example.mp3
media/voc_6a648cec-past-participle-example.mp3
```

The build **fails** rather than emitting a half-empty card: every text field must be
present, the pronunciation must be IPA in slashes, a part of speech is required on every
kind, there must be exactly one `level::` tag, at least one known `category::` tag, and
every required mp3 must exist. The image is the exception: an `image` that names no file on
disk leaves the card without an illustration (with a warning) instead of failing the build.
Every authored example must bold its target with
`**...**` (split phrasal verbs use two pairs), every verb needs all four form examples, and a
non-verb carrying them fails as well.

## Production targets

| Deck | Target level | Cards | Content focus |
|---|---|---|---|
| Vocabulary | A1–C1 | 5,500 | Basic lexicon through abstract concepts and analytical verbs (`mitigate`, `feasible`). |
| Phrasal verbs | A1–B2 | 350 | High-frequency structures for daily life and work (`figure out`, `carry out`, `bring up`). |
| Collocations | A1–B2 | 800 | Natural word pairings (`make a decision`, `meet a deadline`, `heavily reliant on`). |

Card counts are planning targets; the build prints progress as `notes=<count>/<target>`.
Level ranges are enforced — an entry outside its deck's range fails the build.

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
  model ids in this repo are on their **seventh** generation for exactly that reason (removing
  the movie-quote block is the latest field change).
- **`BUILD_MOD` must be raised** whenever fields, templates or CSS change — note types only
  update when the incoming `mod` is newer.

## Content

Content is added **only on demand**. Nothing seeds a deck with a placeholder card or a starter
list to prove the pipeline works. The collocations deck is complete: 800 A1–B2 entries in
`src/index.csv` and `src/collocations.json`, authored in sixteen 50-card chunks. The phrasal
verbs deck is complete at 350 A1–B2 entries, authored in seven 50-card chunks. The vocabulary
deck remains empty until its own batch is requested. Every entry's `image_brief` is ready to
paste into Midjourney, and the `image` field stays empty until the rendered file is committed
under `media/`. Audio is synthesized locally with `tools/build_audio.py`; its mp3s are
gitignored, so run that step after cloning before building.

Design decisions, the schema and the trade-offs behind them live in `.okf/` (start at
`.okf/index.md`, with the reverse-chronological log at `.okf/log.md`).
