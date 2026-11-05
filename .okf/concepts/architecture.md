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
   verbs, collocations, and, per entry, the dialog quote, its attribution and the image
   reference.
2. **Normalization** — dedupe *within* a kind and derive a stable per-note key. That key
   becomes the note GUID: full phrase plus sense, prefixed with the kind
   (`voc:` / `pv:` / `col:`), never a row index or `hash()` of an unordered structure.
   The same key names the image file, so an entry always maps to one picture.
3. **Image assets** — resolve `media/<key>.jpg` for every entry and generate it only if
   missing (AI-generated, then committed). The media folder is an input, not a build
   product: image models are not deterministic, so nothing is regenerated on a plain run.
4. **Audio assets** — synthesize `media/<key>.mp3` with edge-tts when missing: pinned
   female US voice, one call reading target → definition → dialog. Also an input, for the
   same non-determinism reason; synthesis needs network access.
5. **Note construction** — map normalized entries onto that kind's pinned model. Decided:
   one model per kind, fields `Word`/`Phrase`, `Pronunciation`, `Definition`, `Image`,
   `Dialog`, `Source` and `Audio` (see `concepts/deck-schema.md`). A note lacking an image,
   a dialog quote, a pronunciation or audio is rejected, not emitted.
6. **Package assembly** — build the `.apkg` with fixed deck id, model id, and GUID
   function; register every referenced image and mp3 in the media map and verify the map
   matches the field values before writing.
7. **Verification** — inspect the generated package programmatically (prevents silent
   missing-media gaps), then do one manual import to confirm template rendering.
8. **Delivery** — a file the user imports by hand; there is no Anki CLI on this machine.

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
