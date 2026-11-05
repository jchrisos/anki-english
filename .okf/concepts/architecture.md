---
type: architecture
title: "Planned .apkg generation pipeline"
description: "Intended flow for turning vocabulary sources into importable Anki packages. Nothing is implemented yet."
status: draft
verified:
  - by: "OpenCode session"
    at: "2026-11-05"
sources:
  - uri: "file:///Users/julio/Projects/anki-english/AGENTS.md"
    credibility: high
  - uri: "local://machine-inspection"
    credibility: medium
stale_after: "2027-05-05"
---

# Planned .apkg generation pipeline

**This is a plan, not an implemented architecture.** At initialization the repo held no
source files, so no entrypoint, module layout, or data flow could be observed. Treat
every stage below as provisional until code exists.

## Intended stages

1. **Vocabulary source** — the input format is undecided (CSV, Markdown, JSON, or a
   dictionary API). Do not hard-code one before the user picks it.
2. **Normalization** — dedupe entries and derive stable per-note keys. The key becomes
   the note GUID, so it must depend on content (e.g. headword + sense), never on list
   position or iteration order.
3. **Note construction** — map normalized entries onto the chosen model's fields
   (see `concepts/deck-schema.md`).
4. **Package assembly** — build the `.apkg` with fixed deck id, model id, and GUID
   function; register any media in the media map.
5. **Verification** — inspect the generated package programmatically, then do one
   manual import to confirm template rendering.
6. **Delivery** — a file the user imports by hand; there is no Anki CLI on this machine.

## Structural rules that survive refactors

- Deck id, model id, and GUID derivation belong in one place guarded as constants, not
  scattered through generation code.
- Generation must be deterministic: same input, byte-identical output. This makes
  regeneration safe and diffs meaningful.
- The bundle is a build artifact. Keep it out of version control (or commit only under
  an explicit `dist/` policy the user approves) and regenerate instead of patching.

## Unknown until code lands

Entrypoints, dependency management, test strategy, and whether a CLI argument or config
file drives generation. Update this concept when the first implementation exists, and
promote it from `draft` to `active` only then.
