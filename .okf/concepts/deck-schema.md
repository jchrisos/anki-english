---
type: decision
title: "v1 schema: three per-kind models, text-only fields"
description: "Decided 2026-11-05: one note type per content kind with pinned model ids and text-only fields. Templates, deck layout and source format remain open."
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

# v1 schema: three per-kind models, text-only fields

## Decision (2026-11-05)

- **One note type per content kind**, i.e. three models with three pinned ids, rather
  than one shared model plus a `Kind` field.
- **v1 is text only**: headword/phrase, definition, example. No IPA and no audio, so the
  generated package carries no media map that can be wrong.
- **No `Kind` field.** The model already encodes the kind; add a tag only if cross-deck
  filtering is ever needed. A redundant field is another thing to keep consistent.
- **Front→back template only** for v1. Additional templates are additive and do not
  change note identity, so they are cheap to add later — unlike fields.

## Fields

| Model | Fields | Note |
|---|---|---|
| Vocabulary | `Word`, `Definition`, `Example` | homographs need a sense in the GUID, not extra fields |
| Phrasal verb | `Phrase`, `Definition`, `Example` | phrase stored whole; splitting the particle is deferred |
| Collocation | `Phrase`, `Definition`, `Example` | same shape as phrasal verb, separate model so ids stay independent |

Three models share a shape today. That is fine: keeping separate model ids preserves the
freedom to diverge (particle cloze, collocation gap-fill) without a migration.

## Why not a shared model

Rejected: one note type with a `Kind` field would force a single template onto three card
shapes, and the only per-kind difference would live in data rather than in the model.
Cheaper now, worse as soon as the card designs diverge.

## Still open — do not invent

1. **Deck layout**: one deck or three. This decides the pinned deck id(s).
2. **Source vocabulary format**: CSV, Markdown, JSON, or a dictionary API.
3. **Per-kind card templates** beyond front→back (particle gap-fill, word cloze).
4. Whether vocabulary needs a register/CEFR tag for filtering.

## Cost of changing fields later

Anki indexes a model's fields by name and position. Editing the field list of a model
that already has notes remaps or destroys those notes and requires a new model id, a new
note type and a migration — while scheduling history stays on the old notes. A GUID only
deduplicates within one model+deck, so a late field change typically yields a parallel
duplicate deck instead of an update.

## Consequences for code

- One constants block: `VOC_MODEL_ID`, `PV_MODEL_ID`, `COL_MODEL_ID`, plus the deck id
  once layout is chosen. Never derived from time or randomness.
- GUIDs are content-derived and prefixed per kind (`voc:` / `pv:` / `col:`).
- The package stays media-free until audio is requested, and adding media later does not
  alter note identity.
