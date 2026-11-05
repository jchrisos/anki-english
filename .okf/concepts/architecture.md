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
every stage below as provisional until code exists. The three content kinds
(vocabulary, phrasal verbs, collocations) are confirmed; the layout serving them is not.

## Intended stages

1. **Vocabulary source** — format is undecided (CSV, Markdown, JSON, or a dictionary
   API). Whatever is chosen must carry all three content kinds: vocabulary, phrasal
   verbs, collocations.
2. **Normalization** — dedupe *within* a kind and derive a stable per-note key. That key
   becomes the note GUID: full phrase plus sense, prefixed with the kind
   (`voc:` / `pv:` / `col:`), never a row index or `hash()` of an unordered structure.
3. **Note construction** — map normalized entries onto that kind's pinned model. Decided:
   one model per kind, text-only fields (see `concepts/deck-schema.md`).
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
file drives generation. Also unresolved: whether the three kinds land in one deck or
several. Update this concept when the first implementation exists, and promote it from
`draft` to `active` only then.
