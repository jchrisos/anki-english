---
okf_version: "0.2"
title: "anki-english knowledge bundle"
description: "Greenfield project for generating Anki (.apkg) English flashcards. Bundle captured before any code exists."
---

# anki-english

Knowledge bundle for this repo. Read `AGENTS.md` at the repo root for the short
operational version; concepts below hold the reasoning.

## Concepts

- [architecture](concepts/architecture.md) — Implemented pipeline: `src/<kind>.json` + `media/` → three packages, with fail-loud validation.
- [deck schema](concepts/deck-schema.md) — v1 decided: one model and one deck per kind, three pinned ids each, output to `decks/<kind>.apkg`; every card carrying IPA, a part of speech, an AI image, an attributed movie/TV dialog and female-voice TTS mp3s, grouped by `category::` tags and tagged with one CEFR `level::`; verbs add three authored example sentences (present, past, past participle) under the quote.
- [incremental updates](concepts/incremental-updates.md) — re-importing a rebuilt package updates notes in place, so stable GUIDs and frozen ids are what keep review progress.
- [environment](concepts/environment.md) — Verified local Anki/Python setup and the tooling that is missing.
- [apkg safety](concepts/apkg-safety.md) — Rules that prevent duplicated decks and broken notes on re-import.

## Log

- [log.md](log.md)
