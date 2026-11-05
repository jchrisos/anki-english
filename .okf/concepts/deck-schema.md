---
type: decision
title: "v1 schema: three per-kind models, image + movie/TV dialog cards"
description: "Decided 2026-11-05: one note type per content kind with pinned model ids; every note carries an AI-generated image and an attributed movie/TV dialog quote. Templates, deck layout and source format remain open."
status: active
verified:
  - by: "OpenCode session"
    at: "2026-11-05"
sources:
  - uri: "file:///Users/julio/Projects/anki-english/AGENTS.md"
    credibility: high
  - uri: "user://scope-statement"
    credibility: high
stale_after: "2027-05-05"
---

# v1 schema: three per-kind models, image + movie/TV dialog cards

## Decision (2026-11-05, revised)

- **One note type per content kind**, i.e. three models with three pinned ids, rather
  than one shared model plus a `Kind` field.
- **Every note has an image and a quoted movie/TV dialog line as its example.** The
  earlier "write your own example sentence" field is gone: the dialog quote *is* the
  example. This is a user requirement, not a suggestion — a card without either is
  incomplete and must not be emitted.
- **Images are AI-generated and committed to the repo** under `media/`. They are licensed
  for use here and regenerable, at the cost of being invented scenes rather than real
  stills.
- **Dialog is text only**: the line(s) plus attribution. No audio clip, no video, so no
  `[sound:...]` entries and no clip-cutting step in v1.
- **No `Kind` field.** The model already encodes the kind; add a tag only if cross-deck
  filtering is ever needed.
- **Front→back template only** for v1. Additional templates are additive and do not
  change note identity, so they are cheap to add later — unlike fields.

## Fields

| Model | Fields | Note |
|---|---|---|
| Vocabulary | `Word`, `Definition`, `Image`, `Dialog`, `Source`, `Audio` | homographs need a sense in the GUID, not extra fields |
| Phrasal verb | `Phrase`, `Definition`, `Image`, `Dialog`, `Source`, `Audio` | phrase stored whole; particle splitting is deferred |
| Collocation | `Phrase`, `Definition`, `Image`, `Dialog`, `Source`, `Audio` | same shape as phrasal verb, separate model so ids stay independent |

`Audio` is **reserved and always empty in v1**. It is pinned now because adding a field
later means a new model id and a migration; if audio clips are ever wanted for the same
dialog line, the slot already exists. Anything that would make it non-empty (mp3s,
timestamps) is out of scope until the user asks.

### Field contract

- `Word` / `Phrase` — the target form, no articles unless part of the phrase.
- `Definition` — one plain sentence per sense, no circular definition.
- `Image` — **bare filename only** (`voc_9f2c1ab3.jpg`), never a path and never an
  `<img>` tag; the template renders `{{Image}}` into `<img src="...">`, so the package
  media map and the field agree by construction.
- `Dialog` — the quoted line(s), attributed to a speaker inside the text (e.g.
  `"I'll be there for you." — Rachel`). One or two short lines; no scene description.
- `Source` — title plus episode (`Friends, S01E01`), and a timestamp only if it is known.
- `Audio` — empty in v1.

## Media rules

- Images live in `media/` in the repo, named from the note's stable key: kind prefix plus
  a short deterministic hash of `phrase + sense` (the same string the GUID uses), so a
  re-run maps an entry to the same file and a renamed entry never silently reuses another
  card's picture.
- One image per note, showing the sense concretely. No text, logos, or captions baked
  into the image: AI-rendered lettering is unreliable, and on the back of a word card the
  meaning is already spelled out by `Definition`.
- Images are committed, not regenerated at build time. Regenerating would break the
  "same input, same output" rule because image models are not deterministic; the media
  folder is therefore an **input** to generation, and only missing files are generated.
- The package registers every referenced image in its media map. Missing media does not
  fail the import — it silently yields an empty card — so the generator asserts that each
  referenced filename exists before writing the `.apkg`.

## Dialog rules

- The quote must be a real line from a real show or film, with a source that can be
  checked. Fabricated credits ("this is from Seinfeld") are worse than no card.
- Keep quotes short (one or two lines) and use them as **usage evidence**, not decoration:
  the line must only work with the target sense.
- The show should be recognizable to a Brazilian learner of English and the line should
  not depend on visual context to make sense.
- Short quotes with attribution are a fair-use-style compromise; do not paste long
  transcripts or scene descriptions.

## Why not a shared model

Rejected: one note type with a `Kind` field would force a single template onto three card
shapes, and the only per-kind difference would live in data rather than in the model.
Cheaper now, worse as soon as the card designs diverge.

## Still open — do not invent

1. **Deck layout**: one deck or three. This decides the pinned deck id(s).
2. **Source vocabulary format**: CSV, Markdown, JSON, or a dictionary API — now it must
   also carry the dialog quote, the attribution and the image reference.
3. **Per-kind card templates** beyond front→back (particle gap-fill, word cloze).
4. Whether images sit on the back only (assumed) or also on the front as a recall cue.
5. Whether vocabulary needs a register/CEFR tag for filtering.

## Cost of changing fields later

Anki indexes a model's fields by name and position. Editing the field list of a model
that already has notes remaps or destroys those notes and requires a new model id, a new
note type and a migration — while scheduling history stays on the old notes. A GUID only
deduplicates within one model+deck, so a late field change typically yields a parallel
duplicate deck instead of an update. This is why `Audio` is pinned even though it is
empty.

## Consequences for code

- One constants block: `VOC_MODEL_ID`, `PV_MODEL_ID`, `COL_MODEL_ID`, plus the deck id
  once layout is chosen. Never derived from time or randomness.
- GUIDs are content-derived and prefixed per kind (`voc:` / `pv:` / `col:`), and the image
  filename is derived from the same key.
- The package now always has a media map: build it from the referenced images, verify it,
  and fail generation if a note is missing an image or a dialog.
