---
type: decision
title: "Note type and field schema is an open decision"
description: "Why the note type must be fixed before the first import, and what remains unresolved."
status: draft
verified:
  - by: "OpenCode session"
    at: "2026-11-05"
sources:
  - uri: "file:///Users/julio/Projects/anki-english/AGENTS.md"
    credibility: high
stale_after: "2027-05-05"
---

# Note type and field schema is an open decision

## Status

**Deferred.** The user has not chosen the note type, field list, card templates, or the
input vocabulary format. Confirm with the user before implementing anything that writes
notes — do not infer a schema from the project name.

## Why this cannot be defaulted

- Anki identifies a note type by a numeric model id and keys its fields by name and
  index. Editing the field list of an existing model remaps or destroys existing notes.
- Changing the model therefore requires a new model id, which means a new note type and
  a migration for anything already reviewed. Scheduling history lives on the note, so a
  careless re-model silently resets study progress.
- The GUID only deduplicates within a model and deck. A schema change made after an
  import produces a second parallel deck instead of updating the first.

Practical consequence: settle the schema *and* the GUID rule before the first import
into a deck the user cares about, not after.

## Options considered (no selection made)

- **Minimal two-field** (`Front`/`Back`) — fastest to build, but no room for IPA,
  audio, or example sentences without a later migration.
- **Word-centric multi-field** (word, definition, example, IPA, audio, tags) — matches
  typical English study decks and AwesomeTTS (an installed add-on) could supply audio,
  at the cost of denser templates and more per-note data validation.
- **Sentence/cloze-oriented** — different card generation semantics; only sensible if
  the user's study goal is production rather than recognition.

## What must be answered first

1. Recognition, recall, or both? This drives template count (forward/reverse).
2. Are audio and IPA required, and must audio ship inside the `.apkg`?
3. What is the source of truth for entries, and does it need sense disambiguation
   (same headword, multiple meanings) in the GUID?

Record the outcome here and in `log.md` when decided, then move this to `status: active`.
