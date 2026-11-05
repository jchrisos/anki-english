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
- Re-importing a rebuilt package updates existing notes in place and keeps their cards and
  review history; that is the intended workflow, so never delete and re-create a note to
  refresh it.

## Media

- Register files in the package media map and reference them by bare filename in fields
  and templates. Absolute or relative paths import as broken references.
- Every note is incomplete without its image and its dialog quote, so missing media is a
  content bug, not a cosmetic one. Generate nothing silently: fail the run and report the
  entry instead of importing a blank card.
- Audio counts as required media: the `Audio` field holds `[sound:<key>.mp3]`, and an
  empty field or a missing file is a silent, soundless card. Check both the reference and
  the file, and never point two notes at the same mp3.
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
