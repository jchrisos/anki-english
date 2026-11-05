---
type: log
title: "Decision log"
description: "Reverse-chronological record of design decisions and trade-offs for the anki-english bundle."
status: active
---

# Decision Log

Newest entries first. ISO dates (`YYYY-MM-DD`).

## 2026-11-05 — Bundle initialized on an empty repository

- Repo contained no code, no manifests, and no git history at initialization time.
  `okf-init` therefore had no build config, folder layout, or commits to analyze; all
  structure here is either verified machine state or explicitly marked `draft`.
- Created the scope: a generator producing `.apkg` decks for English study.
- Recorded the verified local environment (Anki 25.09, Python 3.10.16, no `genanki`,
  no AnkiConnect) so later sessions do not assume tooling that is not installed.
- Kept the note-type/field design as an open decision rather than inventing a schema,
  because changing it after notes exist is destructive (see `concepts/deck-schema.md`).
- Trade-off: a sparse bundle now beats speculative architecture docs that would be
  mistaken for implemented behavior later.

## 2026-11-05 — `AGENTS.md` written

- Chose to document only verified environment facts plus Anki data-safety pitfalls, and
  to state that no build/test commands exist, rather than guessing a Python toolchain.
- Rejected adding `uv`/`pytest` conventions: none are installed and none were requested.
