---
type: log
title: "Decision log"
description: "Reverse-chronological record of design decisions and trade-offs for the anki-english bundle."
status: active
---

# Decision Log

Newest entries first. ISO dates (`YYYY-MM-DD`).

## 2026-11-05 — Git initialized, remote on GitHub

- Repo now has git: branch `main`, remote `origin` →
  `https://github.com/jchrisos/anki-english.git`, initial commit `657df61`
  ("feat: initial commit") holding `AGENTS.md` and the `.okf/` bundle.
- No CI, pre-commit hooks or PR templates exist, so there is no automatic verification;
  checks stay manual until tooling is added.
- Added `.gitignore` for `.venv/`, `__pycache__/`, `dist/` and `*.apkg` so the future
  environment and generated decks cannot be committed by accident. This matches the
  "bundles are build artifacts" rule in `concepts/architecture.md`; revisit if the user
  decides decks should be versioned.
- Corrected `AGENTS.md`, which still described the directory as not being a git repo and
  told agents to run `git init`.

## 2026-11-05 — Schema decided: three per-kind models, text-only v1

- User chose **one note type per kind** over a shared model with a `Kind` field.
  Rationale: card shapes per kind diverge (front/back vs particle gap-fill), and three
  pinned model ids now are cheaper than a migration later.
- v1 fields are text only (headword/phrase, definition, example). No IPA, no audio, so
  the package has no media map yet.
- Refinement to the accepted option: dropped the `Kind` field, since the model already
  encodes kind; a tag can carry it if cross-deck filtering is ever needed.
- Deferred and cheap: extra card templates are additive and do not change note identity,
  so front→back ships first. Field changes are the expensive kind, not template changes.
- Still open: deck layout (one deck vs three, and therefore the pinned deck id), source
  vocabulary format, and per-kind gap-fill/cloze templates.

## 2026-11-05 — Scope confirmed: vocabulary, phrasal verbs, collocations

- User fixed the deck's content kinds. This narrows `concepts/deck-schema.md` from
  "what is this deck about" to layout questions.
- Consequences recorded there: entries are frequently multi-word; GUIDs need a kind
  prefix so the same string cannot collide across kinds; card shapes will differ per
  kind, which argues for per-kind templates while that is still free.
- Deliberately left open: one note type vs three, fields/audio, source format,
  recognition vs recall.
- No code or schema written. Importing anything before the schema is settled would
  create notes that are expensive to re-model.

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
