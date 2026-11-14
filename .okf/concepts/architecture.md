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
| `tools/lint_content.py` | check `src/index.csv` against `src/<kind>.json` before a build |
| `tools/deck_common.py` | kind prefixes, media key, spoken script, allowed tags |
| `tools/build_audio.py` | one edge-tts mp3 per entry, skipping files that exist |
| `tools/prepare_media.py` | PNG → 900 px JPEG, so a package stays ~2 MB |

## Stages

0. **Manifest** — `src/index.csv`, one row per planned sense
   (`kind,phrase,sense,pos,level,categories,gloss`), reviewed and deduplicated before any
   card is written. It is deliberately cheap to review and freeze the sense slugs, because
   the slug is the note's identity and re-slugging after import orphans review history.
   `lint_content.py` checks it against the written entries and reports progress and
   repetition (`--report`). The build reads the same file and refuses an entry that has no
   row (`not in index.csv`), so `--notes` can never ship a sense that was never planned. It
   does not re-check the row's pos, level or categories: that comparison stays lint's job.
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
   part uses the pinned female voice; nothing on the card is a character's line. Also an input;
   `build_audio.py` skips a clip only when it exists **and is non-empty** (`--force` rewrites
   it), and writes through a `.part` sidecar that is renamed into place on success:
   `Communicate.save` opens the destination before any audio arrives, so a dropped connection
   would otherwise leave a 0-byte mp3 that every later run skipped as already done.
5. **Validation** — every note is rejected unless all text fields are non-empty, the
   pronunciation is IPA in slashes, a `pos::` tag is present, there is exactly one
   `level::` tag, at least one `category::` tag from the controlled list, the phrase is
   unique within its kind, the phrase/sense pair keeps its GUID shape (lowercase,
   colon-free phrase, kebab-case sense), no two entries share a media key (a 32-bit digest,
   so a collision is possible and would make one card play another's audio), and every
   required **mp3** exists **and is non-empty**. The authored example is
   required on every note and must bold its target with `**...**`; a verb must also carry the
   four form examples, and a non-verb
   carrying them is rejected. A missing image is not fatal — the field is left empty — because
   the file is authored by hand; a missing or empty mp3 is the failure that does not announce
   itself. Authored text is HTML-escaped (`&`, `<`, `>`) before `**…**` becomes `<b>`, so a
   definition containing a comparison sign cannot eat the rest of the card.
6. **Package assembly** — one deck and one note type per package, with the pinned deck id,
   model id and name; media registered in the package map by bare filename. With no notes
   the model is attached explicitly, otherwise Anki would create a deck with no note type.
7. **Package assembly + hermetic zip** — `_write_package()` writes the package through two
   sidecars (`<kind>.apkg.build`, then `<kind>.apkg.tmp` with entry timestamps pinned) and
   moves the finished archive into place with one `replace`. The destination therefore only
   ever holds a complete package — genanki's own `write_to_file` truncates what was there
   first — and unchanged input still reproduces a byte-identical `.apkg`. Entries are streamed
   rather than read whole. genanki's throwaway sqlite is created inside a `TemporaryDirectory`.
8. **Verification** — unzip and query the bundled sqlite: note and card counts, GUID
   uniqueness, media-map entries present in the zip and byte-identical to `media/`, and
   fields referencing exactly the registered filenames. Then one manual import, because
   counts cannot validate template rendering.

## Structural rules that survive refactors

- Deck ids, model ids, deck names and the GUID/media-key derivation live in one place as
  pinned constants (`build_decks.py` + `deck_common.py`), never inline at a call site.
- Generation is deterministic: same input, byte-identical output.
- Every file a tool replaces is written beside its target and moved into place with
  `Path.replace`: `.apkg` packages, `src/index.csv` and `src/<kind>.json` (which `merge_batch.py`
  writes source-first, so an interruption leaves rows awaiting cards, not cards without a plan
  row). `merge_batch.py` resolves its paths from `REPO_ROOT` — never the working directory — and
  takes `--test` like the other tools.
- `decks/` and generated `*.mp3` are build output, `tests/` is a fully gitignored tree;
  committed `media/` images and `src/` are the real inputs. `--test` on any tool switches the whole layout to
  `tests/src` + `tests/media` + `tests/decks`, so test content is never versioned.
- Content is opt-in (`--notes`). A plain build emits the empty baseline, so "add
  flashcards" can never happen by accident.

## Not automated, on purpose

- **Image generation.** Not deterministic, not free, and outside this repo's scope, so it
  happens by hand before a build and writes into `media/`. It is never a build step.
- **Importing into Anki.** There is no `anki` binary on `PATH` and no AnkiConnect; the
  user imports the `.apkg` by hand.
- **Delta builds.** Every build is a full rebuild; Anki merges by GUID on import.
