---
type: architecture
title: "Implemented .apkg generation pipeline"
description: "How src/<kind>.json plus media/ become three importable packages: key derivation, validation, packaging, and what is deliberately not automated."
status: active
verified:
  - by: "OpenCode session"
    at: "2026-11-05"
sources:
  - uri: "file:///Users/julio/Projects/anki-english/tools/build_decks.py"
    credibility: high
  - uri: "file:///Users/julio/Projects/anki-english/tools/deck_common.py"
    credibility: high
  - uri: "file:///Users/julio/Projects/anki-english/tools/build_audio.py"
    credibility: high
stale_after: "2027-05-05"
---

# Implemented .apkg generation pipeline

Four scripts, no framework. `tools/deck_common.py` owns the identity rules so the builder
and the audio tool cannot disagree about what an entry is called.

| Script | Job |
|---|---|
| `tools/build_decks.py` | validate the layout's `src/` and `media/`, assemble the three packages |
| `tools/deck_common.py` | kind prefixes, media key, spoken script, allowed tags |
| `tools/build_audio.py` | one edge-tts mp3 per entry, skipping files that exist |
| `tools/prepare_media.py` | PNG → 900 px JPEG, so a package stays ~2 MB |

## Stages

1. **Source** — `src/<kind>.json`, one array per kind, one object per entry: `phrase`,
   `sense`, `pronunciation`, `definition`, `image` (the illustration name, no extension), `example`,
   `categories`, `level`, and `image_brief` (a paste-ready Midjourney prompt, never written to
   the note). JSON because it is the
   one format that holds nested category lists and multi-line sentences without a delimiter
   argument.
2. **Identity** — `media_key()` = `f"{prefix}_{sha1(prefix:phrase:sense)[:8]}"`, with
   prefix `voc` / `pv` / `col`. The GUID is `prefix:phrase:sense`, prefixed `test:` for a
   test build. Both derive from the *authored sense slug*, never from the definition text,
   a row number or a timestamp, so rewording a definition cannot strand review history.
3. **Images** — the entry's `image` field names a file in `media/` without an extension
   (e.g. `voc_6a648cec`, resolved to `.jpg`/`.jpeg`/`.png`/`.gif`/`.webp`), rendered in
   Midjourney outside the repo and committed as an **input**:
   the project writes the prompt but never the picture, and nothing is regenerated on a build.
   A name that resolves to no file leaves the `Image` field empty, so the card is built without
   an illustration instead of a broken `<img>`. `prepare_media.py` only re-encodes what already
   exists.
4. **Audio** — three files per entry, seven for a verb:
   `media/<key>-{word,explanation,example}.mp3` and, for verbs,
   `media/<key>-present-example.mp3`, `-present-participle-example.mp3`,
   `-past-simple-example.mp3`, `-past-participle-example.mp3`. One edge-tts call each. Every
   part uses the pinned female voice; nothing on the card is a character's line. Also an input; `build_audio.py` skips
   existing files unless `--force`.
5. **Validation** — every note is rejected unless all text fields are non-empty, the
   pronunciation is IPA in slashes, a `pos::` tag is present, there is exactly one
   `level::` tag, at least one `category::` tag from the controlled list, the phrase is
   unique within its kind, and every required **mp3** exists. The authored example is
   required on every note and must bold its target with `**...**`; a verb must also carry the
   four form examples, and a non-verb
   carrying them is rejected. A missing image is not fatal — the field is left empty — because
   the file is authored by hand; a missing mp3 is the failure that does not announce itself.
6. **Package assembly** — one deck and one note type per package, with the pinned deck id,
   model id and name; media registered in the package map by bare filename. With no notes
   the model is attached explicitly, otherwise Anki would create a deck with no note type.
7. **Hermetic zip** — `_make_zip_hermetic()` pins entry timestamps, so rebuilding unchanged
   input leaves the committed `.apkg` byte-identical instead of dirtying git.
8. **Verification** — unzip and query the bundled sqlite: note and card counts, GUID
   uniqueness, media-map entries present in the zip and byte-identical to `media/`, and
   fields referencing exactly the registered filenames. Then one manual import, because
   counts cannot validate template rendering.

## Structural rules that survive refactors

- Deck ids, model ids, deck names and the GUID/media-key derivation live in one place as
  pinned constants (`build_decks.py` + `deck_common.py`), never inline at a call site.
- Generation is deterministic: same input, byte-identical output.
- `decks/` is build output and `tests/` is a fully gitignored tree; `media/` and `src/` are
  inputs and are committed. `--test` on any tool switches the whole layout to
  `tests/src` + `tests/media` + `tests/decks`, so test content is never versioned.
- Content is opt-in (`--notes`). A plain build emits the empty baseline, so "add
  flashcards" can never happen by accident.

## Not automated, on purpose

- **Image generation.** Not deterministic, not free, and outside this repo's scope, so it
  happens by hand before a build and writes into `media/`. It is never a build step.
- **Importing into Anki.** There is no `anki` binary on `PATH` and no AnkiConnect; the
  user imports the `.apkg` by hand.
- **Delta builds.** Every build is a full rebuild; Anki merges by GUID on import.
