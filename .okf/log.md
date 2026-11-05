---
type: log
title: "Decision log"
description: "Reverse-chronological record of design decisions and trade-offs for the anki-english bundle."
status: active
---

# Decision Log

Newest entries first. ISO dates (`YYYY-MM-DD`).

## 2026-11-05 — Categories apply to all three kinds

- User asked whether phrasal verbs and collocations can have category groups like
  vocabulary. Yes — and it costs nothing, because categories are **tags**, not a field.
- Decision: categories are now **required on every note**, one to three slugs from the
  same controlled list, shared across kinds (`get up` → `daily-routine`, `make an offer`
  → `money`).
- Cross-kind filtering is accepted and expected: `tag:category::kitchen` returns
  vocabulary, phrasal verbs and collocations together; narrow with `note:PhrasalVerb`.
- This is the payoff of the earlier tag-not-field choice: if categories had been a field
  on the vocabulary model, extending them to two more models would now mean two new model
  ids, a re-import and a parallel duplicate deck.
- Levels stay in `level::`, unchanged; categories and levels remain orthogonal, so an A2
  kitchen phrasal verb filters cleanly on both.
- Consequence for code: build-time validation of ≥1 category moves from the vocabulary
  model to all three.

## 2026-11-05 — CEFR level tag on every note

- User asked for English level (A1…B2…) as another grouping, for **all three kinds** —
  unlike categories, which stay vocabulary-only.
- Implemented as `level::a1` … `level::c2` **tags**, not a field and not under
  `category::`. Reasons: single value per note, applies to every note type, and mixing it
  into the category namespace would turn a difficulty filter into a theme filter.
- Exactly one level per note. Zero or two both break a level filter silently, so the build
  rejects them — the same fail-loudly rule used for missing media.
- Assignment rule: the level of **the sense being taught, not of its words**. `give up` is
  A2/B1 with A1 words; `make a decision` is B1 with A1 words. The chunk is the unit of
  learning. When torn between adjacent bands, take the lower one.
- Cost: zero. No field, no model change, no note identity impact — this is precisely the
  kind of change tags exist for.
- Register (formal/informal) deliberately left open as a third namespace; adding a tag
  later is free, so nothing needs deciding now.

## 2026-11-05 — Pronunciation field pinned (General American IPA)

- Prompted by an example card: the teacher agent was writing IPA (`/ˈhæv/`) but the schema
  had no field to hold it, so that work was silently discarded. Added `Pronunciation`
  right after `Word`/`Phrase` in all three models.
- Free to do now and expensive later: no notes exist, so this is a field-list edit with no
  migration. It is the same reasoning that pinned the reserved `Audio` slot.
- Format: phonemic General American IPA in slashes with `ˈ`/`ˌ`, `ɚ`/`ɝ` for r-colored
  vowels, flapped `t` (`/ˈwɔt̬ɚ/`); no British variants, no respelling sentences. A fixed
  reduction may appear as a short trailing parenthetical, not prose.
- Field **order** is now explicitly part of the pinned schema (editor layout and
  `{{Field}}` references), so it is documented rather than left to the generator.
- Required on every note; the build rejects an empty pronunciation instead of rendering a
  blank line.
- Still not a field: register/CEFR level and pt-BR warnings. They remain teacher notes
  until the user asks, because each is another permanent column.

## 2026-11-05 — Vocabulary categories as multi-valued tags

- User requirement: every vocabulary word belongs to a group (`color`, `car`, `travel`,
  `kitchen`, …) and **a word can have more than one**.
- Implemented as `category::<slug>` **Anki tags**, not a field. Multi-value is native to
  tags, they filter/browse directly (`tag:category::kitchen`, filtered decks), and editing
  them never touches note identity — so categories stay free forever. A `Category` field
  would need a delimiter, search badly, break on values containing it, and be permanent.
- Enforcement: vocabulary notes require at least one category; allowed slugs are a
  controlled list seeded with `color`, `car`, `travel`, `kitchen`; reuse before inventing
  a near-duplicate, because `car` vs `vehicle` silently splits a filter in two.
- Not applied to phrasal verbs or collocations in v1 — if it comes, same namespace.
- **No field-list change**, so the pinned models and ids are untouched and this cannot
  invalidate notes: it is exactly the cheap kind of change.
- Display deferred: printing the category on the card back is a template tweak, not a
  data change, so nothing depends on it now.
- Consequence for code: build-time validation that every vocabulary note has ≥1
  `category::` tag and that each slug is in the allowed list — a typo otherwise yields an
  empty filtered deck instead of an error.

## 2026-11-05 — Cards now require an image and a movie/TV dialog

- User changed the card contract: **every note has an illustration and a quoted movie or
  TV line as its example**. The hand-written example sentence field is removed from the
  schema; the quote is the example.
- Added fields `Image`, `Dialog`, `Source`, and pinned a reserved, always-empty `Audio`.
  `Audio` costs nothing today and avoids a new model id if clips are requested later —
  field lists are the expensive change, so it is cheaper to reserve the slot now.
- Resolved the two follow-ups with the user: dialog is **text + attribution only** (no
  mp3/video), and images are **AI-generated and committed** under `media/`, named from
  the note's content key.
- Consequences: the package now always has a media map; a missing image no longer
  degrades gracefully but yields a blank card, so generation must fail loudly and the
  verification step now compares media-map size against referenced filenames.
- Images are treated as an input to the build, not a build product: AI output is not
  deterministic, so a plain regeneration must never rewrite committed images.
- Risk recorded: dialog attribution is the easiest thing to fabricate. The rule is a real
  line with a checkable source, or no card — not an invented "from Friends" credit.
- Unchanged: three per-kind models, content-derived kind-prefixed GUIDs, front→back
  template first, deck layout and source format still open.
- Why now rather than later: no notes and no code exist, so this field change is free;
  after the first import it would mean a new model id and a migration.

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
