---
okf_version: "0.2"
title: "anki-english knowledge bundle"
description: "Greenfield project for generating Anki (.apkg) English flashcards. Bundle captured before any code exists."
---

# anki-english

Knowledge bundle for this repo. Read `AGENTS.md` at the repo root for the short
operational version; concepts below hold the reasoning.

## Concepts

- [architecture](concepts/architecture.md) — Planned `.apkg` generation pipeline. No code exists yet.
- [deck schema](concepts/deck-schema.md) — v1 decided: one model and one deck per kind, three pinned ids each, output to `decks/<kind>.apkg`; every card carrying IPA, an AI image, an attributed movie/TV dialog and a female-voice TTS mp3, grouped by `category::` tags and tagged with one CEFR `level::`.
- [environment](concepts/environment.md) — Verified local Anki/Python setup and the tooling that is missing.
- [apkg safety](concepts/apkg-safety.md) — Rules that prevent duplicated decks and broken notes on re-import.

## Log

- [log.md](log.md)
