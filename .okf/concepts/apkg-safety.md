---
type: policy
title: ".apkg data-safety rules"
description: "Non-negotiable rules for generating packages so re-imports update notes instead of duplicating or breaking them."
status: active
verified:
  - by: "OpenCode session"
    at: "2026-11-05"
sources:
  - uri: "file:///Users/julio/Projects/anki-english/AGENTS.md"
    credibility: high
stale_after: "2027-11-05"
---

# .apkg data-safety rules

These apply to every generator version, including throwaway scripts. Violating them
damages a collection that may hold months of review history.

## Format

- A `.apkg` is a zip of `collection.anki2` plus a media map. Never hand-edit or patch a
  package; change the source data and regenerate.
- Keep generation deterministic so regenerating from unchanged input produces an
  equivalent package.

## Identity

- **Pin** the deck name and id, the model id, and the GUID function as constants. Random
  or timestamped ids cause every import to create another deck and another copy of every
  note.
- Derive GUIDs from stable content — kind prefix + normalized phrase + an explicit
  sense-key slug — not from the definition text, row order, file path, or `hash()` of an
  unordered structure. Python's `hash()` is salted per process and will silently rotate
  GUIDs between runs. See [incremental updates](incremental-updates.md).
- Import deduplicates by GUID only inside the same model and deck. A new model id means a
  new note type, so plan the migration rather than reusing an id with different fields.
- An existing note type is updated only when the incoming `mod` is **newer** (Anki's
  `update_notetypes` defaults to *if newer*), so raise `BUILD_MOD` in
  `tools/build_decks.py` whenever fields, templates or CSS change. Otherwise the package
  imports cleanly, the notes update, and the collection keeps rendering the old template.
- Re-importing a rebuilt package updates existing notes in place and keeps their cards and
  review history; that is the intended workflow, so never delete and re-create a note to
  refresh it.
- **Test builds need a third identity, not a copy of the production one.** Give them their
  own deck ids, model ids, deck/model names and GUID prefix (`test:voc:` …). Deck names and
  note type ids are match keys on import, so a "test" package that reuses them writes into
  the real deck no matter what its filename says.

## Media

- Register files in the package media map **and** reference them from a field with a real
  media tag — `<img src="key.jpg">` or `[sound:key.mp3]`. A bare filename is not a reference:
  Anki's importer only copies media it finds in the field text, so the file is skipped and
  the card shows a broken image while the package looked complete. Absolute or relative paths
  break the same way.
- Every note is incomplete without its image and its dialog quote, so missing media is a
  content bug, not a cosmetic one. Generate nothing silently: fail the run and report the
  entry instead of importing a blank card.
- Audio counts as required media: the `Audio` field holds three
  `[sound:<key>-<part>.mp3]` references (`word`, `explanation`, `dialog`), `AudioExample`
  adds the authored example clip, a verb adds `present-example`, `past-simple-example` and
  `past-participle-example`, and a missing file is a silent, soundless card. Check every
  reference and every file, and never point two notes at the same mp3.
- Name an image from the note's stable content key (kind prefix + deterministic hash of
  phrase + sense), keep it under `media/`, and never reuse a filename for a different
  entry — the media map has no notion of "which card this belongs to". The mp3 uses the
  same key with a different extension.
- Missing media does not fail the import; it produces silent gaps, so assert that every
  referenced filename is present before writing the package.
- Never regenerate existing images on a normal build. AI image output is not
  deterministic, so regeneration would churn committed files and break the
  same-input-same-output rule; regenerate only on explicit request.

## Verification before handing the file to the user

1. Unzip and query the bundled sqlite for note/card counts and for duplicate GUIDs — once
   per package, since there are three (`vocabulary`, `phrasal-verbs`, `collocations`).
2. Confirm each package's deck and model ids match the pinned constants from
   `concepts/deck-schema.md`, and that no package contains another kind's notes.
3. Confirm the media map entry count matches the number of distinct image filenames
   referenced by fields, and that the map's keys point at the expected files.
4. Do one manual import in Anki to check template rendering, which counts cannot catch.

Never delete or overwrite an existing deck in the user's collection to "fix" an import
mistake; report the problem and let the user decide.
