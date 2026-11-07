---
type: log
title: "Decision log"
description: "Reverse-chronological record of design decisions and trade-offs for the anki-english bundle."
status: active
---

# Decision Log

Newest entries first. ISO dates (`YYYY-MM-DD`).

## 2026-11-06 — Verb form examples under the quote; the tense table dropped

- Two requests in a row: show the past forms (`write` → `wrote`, `written`) and then the
  present third-person form (`I have` → `she has`), each with an example. The first build was
  a labelled table under the headword — present, past, past participle, each with its own
  clip — and a screenshot of it drew "this is not necessary".
- Removed: **the table**. `PresentSimple` / `PastSimple` / `PastParticiple` and their two
  `-forms` clips are gone; the card never lists the forms, and the base form is the front
  anyway.
- Kept, as asked ("the dialogs must stay… only the block below the movie quote"): **one
  example sentence per form**, rendered as three labelled rows under the quote —
  `Present` / `Past` / `Past participle` — each with its own play button. They are the only
  examples on a card that are not movie quotes, because no checkable film line uses an
  arbitrary past form (`paid attention`, `fastened your seatbelt`) and inventing a credit is
  worse than a plain sentence.
- Net schema: **six** verb fields (`PresentExample`, `PastSimpleExample`,
  `PastParticipleExample` + their three audio fields), 15 fields per model, six clips for a
  verb instead of three. `pos` stays required on all three kinds because it is what decides
  whether an entry owes the examples (`tag:pos::verb` also filters verbs across decks).
- **New model ids (v4)** rather than reusing v3: v3 was the interim 20-field table, and a
  build of it was imported while it existed. Anki will not carry a field change into an
  already-imported note type, so the rehearsal `(test)` decks must be deleted before importing
  the rebuilt packages; the unused v3 note types can be removed in Manage Note Types.
  `BUILD_MOD` raised to `1796100000`.
- Validation is unchanged in spirit: a verb without all three examples fails, a non-verb
  carrying them fails, and a missing example mp3 fails. Test content extended for the 24
  verb entries; 72 new mp3s generated.

## 2026-11-06 — Play buttons hug the text instead of the card edge

- `.row-text` had `flex: 1 1 auto`, so it ate the free space and pushed each button to the
  right margin. It is now `flex: 0 1 auto` and the row centres its two children, which puts
  the button next to the text while still letting a long definition shrink and wrap.
- CSS-only; `BUILD_MOD` raised to `1795100000`.

## 2026-11-06 — YouTube embeds tried and dropped

- User asked for the dialog clip embedded at the foot of the card; 29 of 30 were found and
  every id passed YouTube's `oembed` check (exists + embeddable).
- User then called it a distraction. The feature was removed completely: template markup,
  JS, CSS, the `video` key in `tests/src/*.json` and its validation.
- Nothing was committed while it existed, so no collection ever saw it. `BUILD_MOD` was
  raised to `1795000000` anyway, so a collection that did import the short-lived build
  returns to the plain card.
- Kept in the log only as a "do not re-propose this" marker: the blocker was not the finding
  of clips but that a video adds a player, a network dependency and a codec caveat to a card
  that already has an illustration, three audio clips and a quote.

## 2026-11-06 — Play buttons inline, at the right of each row

- Players move from under the text to the right of it: each block is a flex row with the
  text on the left and the button on the right (headword block, definition, quote+source).
- The back can no longer start with `{{FrontSide}}`, because the headword has to share a row
  with its button — so the back template is now formatted per kind with the headword field
  name, exactly like the front.
- Template and CSS only; `BUILD_MOD` raised to `1794800000`, same model ids, so a normal
  re-import applies it.

## 2026-11-06 — Section rules between the three card blocks

- The card reads as three blocks — headword (with IPA/word class/level), definition, and
  illustration + quote — and only the first had a divider. Two plain `<hr>` elements were
  added so each block is separated the same way.
- No CSS was added for them: a bare `<hr>` picks up the same default styling as the existing
  `<hr id="answer">`, which is what makes them match. Template-only change, so a normal
  re-import applies it; `BUILD_MOD` raised to `1794700000`.

## 2026-11-06 — Headword block regrouped, level last

- The word's play button sat between the headword and its IPA/word-class/level, splitting
  one visual block. The player now comes **after** that block.
- Level badge moved to the **end** of the block (pronunciation → part of speech → level), as
  requested, so the meta line reads as one unit under the word.
- Template and CSS only: same fields, same model ids, so a normal re-import applies it.
  `BUILD_MOD` raised to `1794600000`.

## 2026-11-06 — Dialog player moved below the source line

- The quote and its attribution (`"Show me the money!" — Rod Tidwell` / `Jerry Maguire`) are
  one block; the player between them split it. `{{AudioDialog}}` now renders after
  `{{Source}}`, at the foot of the card.
- Template-only change: same field list, same model ids, so **no deck deletion is needed** —
  a normal re-import with *Update note types: If newer* applies it. `BUILD_MOD` raised to
  `1794500000`.
- Worth noting the asymmetry: a template edit is a cheap update; a field edit is not (it
  trips `equal_schema` and the notes are logged as conflicting). The cheap/expensive split
  is enforced by Anki, not just by convention.

## 2026-11-06 — Each player sits under its text: three audio fields, new model ids

- User rule: the play button belongs directly under the text it reads (word, definition,
  dialog), not stacked at the bottom, and without the `WORD`/`EXPLANATION`/`DIALOG` labels.
- That needs one field per clip, so `AudioExplanation` and `AudioDialog` were appended to
  each model. `Audio` keeps the word clip: renaming a field is destructive, so the old name
  stayed and the docs say what it now holds.
- **This forced new model ids** (`sha1("anki-english:v2:model:<kind>")`), and the reason is
  in Anki's source: `apkg/import/notes.rs` compares `equal_schema()`, and
  `maybe_update_existing_note()` logs a GUID match with a different notetype as
  **conflicting** and does not update it. A field change under the same id would have left
  every existing card untouched, with no error.
- Consequence for the user: the notes already in a collection are on the old note type, so
  the old `(test)` decks must be **deleted before importing** the rebuilt packages. The old
  note types stay behind as unused entries in Manage Note Types.
- Deck ids and names are unchanged, so the decks themselves are reused rather than
  duplicated.
- Template now renders `{{Audio}}` under the headword, `{{AudioExplanation}}` under the
  definition and `{{AudioDialog}}` under the dialog; the `.audio` block is a small centred
  margin and the label CSS is gone.

## 2026-11-06 — Audio split in three, dialog voice follows the character

- User rule: one clip per part — word, explanation, dialog — because a single combined mp3
  cannot be replayed from the line the learner actually wants to hear again.
- Word and explanation are always the pinned female voice (`en-US-AvaNeural`); the dialog
  uses a male voice (`en-US-AndrewNeural`) when the character who says it is a man, and the
  female voice when it is a woman. Rate stays `-10%`; both are conversational `en-US`.
- **`speaker_gender` is authored data**, required in `src/<kind>.json` (`female`/`male`) and
  validated. Inferring it from the speaker's name would break on exactly the entries we
  have: `Alfred`, `Lilo`, `Miracle Max`, `Brooke`.
- No schema change: `Audio` still holds `[sound:...]` references, now three of them, each on
  its own labelled line (`word`, `explanation`, `dialog`). Filenames gained a `-<part>`
  suffix: `<key>-word.mp3`, `<key>-explanation.mp3`, `<key>-dialog.mp3`.
- Cost: 3× the TTS calls and 3× the media map entries (4 files per note instead of 2). The
  three clips are shorter than the old combined one, so the package grew only slightly.
- `BUILD_MOD` raised to `1794300000` for the template/CSS change. Old `<key>.mp3` files were
  deleted, since their names are now ambiguous.

## 2026-11-06 — Test builds moved to their own `tests/` tree

- User rule: test source, media and packages must live in `tests/src`, `tests/media` and
  `tests/decks`, and **all** of `tests/` must be gitignored.
- Implemented as a `Layout` in `deck_common.py`: `--test` on any of the three tools switches
  `src/media/out` together, so a test build cannot read production art or write a package
  into `decks/`. One flag, one tree — the three paths can no longer drift apart.
- `.gitignore` replaced `decks/tests/` with `tests/`. Verified with `git check-ignore` on a
  package, an image and a source file: all three ignored.
- Moved the existing 30 entries, 60 media files and three packages into `tests/`. Production
  `src/` and `media/` do not exist yet — a `--notes` production build fails loudly with
  `FileNotFoundError` rather than silently shipping test content.
- Consequence worth stating: test content is now **unversioned**. The 30 cards and their art
  exist only on this machine until they are promoted to `src/` and `media/` and built
  without `--test`. That is the intended trade — test decks are rehearsal, not a library.

## 2026-11-05 — Part of speech under the IPA (vocabulary)

- User: the word class (verb, noun, adverb, …) must appear below the pronunciation.
- Implemented as a `pos::` **tag**, not a field — single-valued per sense, filterable as
  `tag:pos::verb`, and free of any model change. Same reasoning as level and categories,
  and the third namespace so each filter stays exact.
- Display: the card template extracts `pos::` from `{{Tags}}` in the same JS that already
  pulls `level::`; `.pos:empty` hides the line, so phrasal verbs and collocations — which do
  not carry the tag yet — show nothing rather than a blank row.
- `pos` is **required on vocabulary** and validated against a controlled list (a typo would
  otherwise render a card with no word class, silently). Optional on the other two kinds:
  their deck already implies the shape, and adding it later stays free.
- Source data gained a `pos` key for the 10 vocabulary entries. No GUID changed, so review
  history is untouched; `BUILD_MOD` was raised to `1794200000` because the template and CSS
  changed.

## 2026-11-05 — CEFR level shown on the card back

- User: "I don't see the english level". The level was only a `level::` tag, filterable in
  the browser but invisible while reviewing — the schema had deliberately deferred display.
- Implemented as a template change, which is the cheap kind: a `.level` badge above the
  pronunciation, filled by a few lines of JS that pull the `level::` tag out of `{{Tags}}`.
  No new field, no new model id, no change to note identity.
- `BUILD_MOD` raised to `1794000000` in the same change — the rule from the previous entry,
  exercised on its first real use. Without it the badge would never reach an existing
  collection, because note types only update `if newer`.
- Categories remain undisplayed on purpose: the level is the one tag worth seeing during
  review, and printing `category::` slugs would leak technical prefixes onto the card.

## 2026-11-05 — Stale template: the note type is only updated `if newer`

- Symptom: after the media fix, the card showed `%3Cimg%20src="%3Cimg%20src="voc_6a648cec.jpg">">`
  as literal text — the image tag nested inside the old `<img src="{{Image}}">` template.
- Cause: Anki's apkg importer takes `update_notetypes` from
  `ImportAnkiPackageOptions`, whose default is `IF_NEWER`
  (`proto/anki/import_export.proto`). genanki stamps the note type's `mod` with the
  `timestamp` passed to `write_to_file`, and ours was the fixed `1730000000` — the same
  value the first import already stored. Equal mods are not newer, so the template was never
  updated while the notes were.
- Fix: the constant is now `BUILD_MOD = 1793900000` and the docstring states the rule —
  **raise it whenever fields, templates or CSS change**. Re-imports now carry a newer mod,
  so the notetype updates and the card renders `<img src="key.jpg">` once.
- The images themselves had already imported correctly (10 JPEGs in `collection.media`), so
  the two bugs were independent: field-not-referenced, then template-not-updated.
- Rule recorded in `AGENTS.md`: keep "Update note types" at *If newer* or *Always*; leaving
  it at *Never* will strand a collection on an old template forever, with no error.

## 2026-11-05 — Broken images: media must be referenced in the field, not the template

- Symptom: the test decks imported with 20 notes and all 30 mp3s, but **not one image**;
  `collection.media` held every `*.mp3` and zero `*.jpg`.
- Cause, confirmed in Anki's source (`rslib/src/import_export/package/apkg/import/media.rs`
  → `notes.rs::munge_media` → `rslib/src/text.rs::replace_media_refs`): the importer builds a
  media-use map and copies **only** entries it marks used, and a filename is marked used only
  when it appears in a field inside `HTML_MEDIA_TAGS` (`<img|audio|video|object|source src=…`)
  or `AV_TAGS` (`[sound:…]`). Our `Image` field held a bare filename and the *template*
  wrapped it in `<img src>`, so the JPEG was never referenced and was skipped. Audio survived
  because `[sound:…]` is a real reference.
- Fix: the `Image` field now carries the whole tag (`<img src="voc_6a648cec.jpg">`) and the
  back template renders `{{Image}}` bare. `deck-schema.md` previously *required* the bare
  filename, so that rule was wrong and is reversed there and in `apkg-safety.md`.
- This also explains why "the media map is correct" is not a sufficient check: the package
  can be internally consistent and still import with no images. Verification now mirrors
  Anki's own regexes and asserts every registered file is referenced by a field.
- User-facing consequence: re-importing is enough. GUIDs did not change, so the existing
  notes update in place and only the missing media is copied.

## 2026-11-05 — First content: 30 notes, three test packages

- User asked for three **test** decks of 10 entries each, at full card contract, so all 30
  notes carry IPA, definition, a real attributed movie/TV line, category and level tags, an
  AI image and an edge-tts mp3.
- Source format decided: `src/<kind>.json`, one array per kind. JSON over CSV/Markdown
  because an entry holds a nested category list, a quoted dialog and an authored sense slug.
  `image_brief` is authoring metadata and is not written to the note.
- Content is opt-in via a new `--notes` flag. A plain build still emits the empty baseline,
  which keeps "content only on demand" enforceable in code rather than in prose.
- New `tools/deck_common.py` holds the identity rules (kind prefix, media key, spoken
  script) so `build_decks.py` and `build_audio.py` cannot disagree about an entry's name.
  The media key is `prefix_sha1(prefix:phrase:sense)[:8]`; the test GUID prefix `test:` is
  now implemented, closing the gap left open when test ids were introduced.
- Validation is fail-loud before packaging: text fields, IPA in slashes, exactly one
  `level::`, ≥1 known `category::`, unique phrase per kind, and **both media files on disk**.
  Missing media is the failure that imports silently, so it is a build error.
- Two content fixes before the data was written: vocabulary `offer` was dropped because it
  duplicated the collocation `make an offer` (same sense, same Godfather line) — replaced by
  `hire`; and several multi-word IPA strings had primary stress on the function word
  (`/ˈdu ˈriˌsɝtʃ/`), normalized to `/du ˈriˌsɝtʃ/`.
- Images arrive at 1–3 MB PNG. Added `tools/prepare_media.py` (sips, 900 px, JPEG q82):
  a package is now ~2 MB instead of ~25 MB. `media/` stays an input, never regenerated.
- `edge-tts==7.3.1` is now pinned in `requirements.txt` and installed in the repo `.venv`,
  ending the deviation where it lived only in the pyenv global interpreter.
- Operational note: 10 of 30 image generations failed with "Insufficient account funds"
  after the first 20, and one tripped moderation ("teenage boys creep along a corridor").
  Both cleared on retry — the moderation one only after softening the prompt. Budget for
  image generation is a real constraint on content batches.
- Verified per package: 10 notes / 10 cards, unique GUIDs, one `(test)` deck and model, 20
  media-map entries present in the zip and byte-identical to `media/`, fields referencing
  exactly those filenames. Production packages were not rebuilt and still hold 0 notes.
- Still unverified: the quotes themselves are the one thing a script cannot check. They are
  well-known lines with checkable sources, but a manual pass is worth doing before this
  content is promoted out of the test decks.

## 2026-11-05 — Test builds get their own ids, names and filenames

- User rule: `--test` output must not collide with production, and its files must be named
  `<kind>-test.apkg` (e.g. `decks/tests/vocabulary-test.apkg`).
- Ids alone would not have been enough. Anki resolves an incoming deck **by name** and a
  note type **by id**, so a test package reusing either key still merges into the real
  deck. Fixed on all three: pinned `test_deck_id` / `test_model_id` per kind (derived once
  from `sha1("anki-english:test:deck:<slug>")`), names suffixed `(test)`
  (`Vocabulary (test)`, `English Vocabulary (test)`), filenames suffixed `-test`.
- Same `--test` directory and the same gitignore rule as before, so nothing new is
  committed; production packages stayed **byte-identical** after the change, confirming the
  refactor touched only the test path.
- Consequence recorded in `AGENTS.md` and `concepts/apkg-safety.md`: when notes arrive,
  test GUIDs must carry a `test:` prefix on top of the kind prefix. Nothing to code yet —
  there is still no note input — but the rule belongs with the ids, since all three keys
  are what import matches on.

## 2026-11-05 — Test packages go to gitignored `decks/tests/`

- User rule: when a deck is being tested, build it into `decks/tests/`, and that folder must
  be gitignored.
- Implemented as `tools/build_decks.py --test`, which writes the same three packages under
  `decks/tests/` instead of `decks/`; `.gitignore` now excludes `decks/tests/` while still
  re-including `decks/*.apkg` for the committed baseline.
- Test packages keep the **same pinned ids and names** as production so they exercise the
  real templates and fields. The flip side is that importing one does touch the real deck,
  so a dry run belongs in a temporary Anki profile — documented in `AGENTS.md`.
- Added `--only <slug>` while the flag parser was open; it saves rebuilding all three while
  iterating on one card.
- Why this is safe: production output stayed byte-identical after the change (the zip is
  hermetic), so the refactor did not dirty the committed packages.

## 2026-11-05 — Content is added only on explicit demand

- User rule: flashcards go into the decks **only when they ask**. The committed packages
  stay empty; building, rebuilding or "testing" the pipeline is not a request for content.
- Consequences recorded in `AGENTS.md` and the schema: no placeholder note, no seed card,
  no starter vocabulary list, no sample entry written into `decks/` to prove something
  works. If an empty package turns out to be unimportable, ask before seeding.
- This also bounds the teacher subagent: it produces entries only when the parent asks, and
  never "helpfully" fills a deck.
- No code change was needed — `tools/build_decks.py` has no note input at all, which is the
  structural version of this rule.

## 2026-11-05 — First code: `tools/build_decks.py` emits three empty packages

- User asked for the three decks to exist now, empty, committed — a baseline before any
  content.
- Added `tools/build_decks.py` (genanki 0.13.1 in the repo `.venv`, pinned in
  `requirements.txt`) with the deck ids, deck names, model ids and field lists as literals.
  First code in the repo; `AGENTS.md` moved from "greenfield" to "early skeleton" with the
  real commands.
- Each package carries one deck and one note type and **zero notes** (verified: `notes`
  and `cards` both 0, correct deck/model ids and field order). With no notes genanki would
  omit the model, so the script attaches it explicitly — otherwise the import would create
  a deck with no note type.
- `.gitignore` still ignores `*.apkg` but re-includes `decks/*.apkg`, so the baseline is
  committed while future builds stay regenerable. This is a deliberate exception to the
  "build output is not committed" rule, recorded here and in the schema.
- Risk to verify on the first manual import: Anki may decline a package with no notes. If
  it does, the baseline has to be a seeded package (one real card) instead; the ids and
  names would not change, so nothing else in the plan moves.

## 2026-11-05 — Incremental rebuilds: review progress must survive

- User requirement: the deck grows over time and re-importing it must not reset study
  progress in Anki.
- Mechanism confirmed from the Anki manual: notes are matched by **GUID**, and a matched
  note is updated in place, keeping its cards and review log; decks are matched by **name**,
  note types by **id**; the newer version wins unless the import dialog overrides it; import
  never deletes notes absent from the package.
- New load-bearing rule: the GUID's sense component is an **authored slug**
  (`voc:have:eat-or-drink`), never derived from `Definition`. Otherwise every reworded
  definition would become a new note and the card's history would be stranded on the old
  one.
- Frozen forever: deck names, deck ids, model ids, field lists, media filenames. A renamed
  deck or a changed field list stops updates on existing notes.
- Generation stays a **full rebuild**; Anki does the merge. No delta format, no
  delete-and-re-add, and no "refresh" by recreating notes.
- Known limits recorded: reclassifying a kind, deleting a deck/note, changing a note type
  and importing a `.colpkg` all lose history — the generator must never do any of them.
- Documented the import checklist for Anki 25.09: `.apkg` only, "Import any learning
  progress" unticked, "Update notes: Always".
- New concept `.okf/concepts/incremental-updates.md`, cross-linked from the schema and the
  safety rules; verification now includes deterministic GUIDs, per-package uniqueness, and
  reporting keys that disappear between builds.

## 2026-11-05 — Three decks, output to `decks/<kind>.apkg`

- User fixed the last open layout question: decks are split by kind and written to
  `decks/` — `vocabulary.apkg`, `phrasal-verbs.apkg`, `collocations.apkg`.
- Three decks rather than one: each kind is studied on its own, each package carries only
  its own kind's images and mp3s (so they stay small), and re-importing one kind cannot
  disturb the other two.
- Deck **ids are now pinned literals** (`517813484872`, `807523115129`, `221110591407`),
  derived once from `sha1("anki-english:deck:<name>")` and recorded in the schema table
  together with the three model ids. Deriving ids at runtime is what duplicates decks.
- **Flat deck names, no `English::` parent.** A parent deck is a new deck id, not a
  rename, so adding the hierarchy later would create parallel decks instead of grouping
  the existing ones. Decided now while the cost is zero.
- `decks/` is build output: created on demand, `*.apkg` already gitignored, and the
  directory is kept in git with a `.gitkeep` so the path exists before the first build.
- Consequence: the verification step now runs per package (counts, GUID duplicates, deck
  and model ids) and must confirm no package leaks another kind's notes.

## 2026-11-05 — Audio via edge-tts, female voice, three-part script

- User installed `edge-tts` and asked for audio on the cards, in a **woman's voice**.
  Confirmed scope: one clip per card reading **target → definition → dialog**.
- Not the film's audio: a real clip means sourcing, cutting, licensing and file size, and
  it would not cover the definition. Synthesized speech covers all three parts and stays
  small (~53 KB / 8.9 s for one card).
- **No schema change.** `Audio` was pinned empty in the first draft exactly for this; it
  is now simply populated with `[sound:<key>.mp3]`. A field change here would have cost a
  new model id and a parallel duplicate deck.
- Voice pinned as a constant: `en-US-AvaNeural`, `--rate=-10%`. Female `en-US` alternatives
  on this machine: Aria, Jenny, Emma, Michelle. `AnaNeural` is a child voice and is
  excluded. Changing the voice later is a one-line edit plus media regeneration.
- Assembly: one edge-tts call with `<target>. <definition>. <dialog>`; punctuation supplies
  the pauses, so no ffmpeg concat step and no second dependency. The speaker attribution
  after the last em dash and the surrounding quotes are stripped before speaking.
- Audio plays on the **back only**; on the front it reads the answer out loud.
- Determinism: TTS is a cloud call, so mp3s are committed **inputs**, regenerated only on
  explicit request — the same rule as AI images.
- Failure mode to guard: a missing or empty mp3 imports silently and the card just has no
  sound, so the build must assert the field and the file.
- Environment note: `edge-tts` 7.3.1 lives in the pyenv global 3.10.16 interpreter (the
  user installed it there), which deviates from the repo rule; pin it in the `.venv` when
  one exists. `ffmpeg`/`lame` exist but are deliberately unused.

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
