---
type: decision
title: "v1 schema: one model and one deck per kind, media-rich cards"
description: "Decided 2026-11-05: one note type and one deck per content kind with pinned ids; every note carries IPA, an AI-generated image, an attributed movie/TV dialog and a female-voice TTS mp3. Card templates and source format remain open."
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

# v1 schema: three per-kind models, image + movie/TV dialog cards

## Decision (2026-11-05, revised)

- **One note type per content kind**, i.e. three models with three pinned ids, rather
  than one shared model plus a `Kind` field.
- **Every note has an image and a quoted movie/TV dialog line as its example.** The
  earlier "write your own example sentence" field is gone: the dialog quote *is* the
  example. This is a user requirement, not a suggestion — a card without either is
  incomplete and must not be emitted.
- **Images are AI-generated and committed to the repo** under `media/`. They are licensed
  for use here and regenerable, at the cost of being invented scenes rather than real
  stills.
- **Audio is synthesized speech, not the movie clip.** Three clips per note — `word`,
  `explanation`, `dialog` — so the line can be replayed on its own. Word and explanation
  always use the pinned female voice; the dialog follows the character who says it (male
  character → male voice, female → female). This gives listening practice without sourcing
  or licensing audio from the film.
- **Three decks, one per kind**, each exported as its own `.apkg` under `decks/`:
  `decks/vocabulary.apkg`, `decks/phrasal-verbs.apkg`, `decks/collocations.apkg`. Deck
  layout was open; it is now decided — see [Decks and output](#decks-and-output).
- **No `Kind` field.** The model already encodes the kind; add a tag only if cross-deck
  filtering is ever needed.
- **Every note carries one or more semantic categories as Anki tags** (`category::color`,
  `category::kitchen`, …) across all three kinds, not as a field. Categories are
  multi-valued and likely to change, which is exactly what tags are for; see
  [Categories](#categories-all-kinds).
- **Pronunciation is a field** (`Pronunciation`), General American IPA with stress marks.
  It is pinned now, alongside the other fields, so adding it later never forces a new
  model id; the teacher agent was already writing IPA that had nowhere to go.
- **Every note carries exactly one CEFR level tag** (`level::b1`) on all three kinds, in
  its own namespace rather than under `category::`; see [Levels](#levels-all-kinds).
- **Front→back template only** for v1. Additional templates are additive and do not
  change note identity, so they are cheap to add later — unlike fields.

## Fields

| Model | Fields | Note |
|---|---|---|
| Vocabulary | `Word`, `Pronunciation`, `Definition`, `Image`, `Dialog`, `Source`, `Audio`, `AudioExplanation`, `AudioDialog` | homographs need a sense in the GUID, not extra fields |
| Phrasal verb | `Phrase`, `Pronunciation`, `Definition`, `Image`, `Dialog`, `Source`, `Audio`, `AudioExplanation`, `AudioDialog` | phrase stored whole; particle splitting is deferred |
| Collocation | `Phrase`, `Pronunciation`, `Definition`, `Image`, `Dialog`, `Source`, `Audio`, `AudioExplanation`, `AudioDialog` | same shape as phrasal verb, separate model so ids stay independent |

The three audio fields are one clip each — `Audio` is the **word** clip (the name predates
the split; renaming a field is destructive, so it stayed), `AudioExplanation` and
`AudioDialog` follow. Separate fields are what let the template put each player directly
under the text it reads instead of stacking all three at the bottom.

Field **order** is part of the pinned schema too: it drives the editor layout and the
`{{Field}}` references, and reordering a field list is as destructive as renaming one.

`Audio` is **required on every note** and holds three `[sound:<key>-<part>.mp3]` references —
`word`, `explanation`, `dialog`. It was reserved empty in the first draft precisely so that
turning audio on later would not require a new model id — that is now what happened: the
field list is unchanged, and splitting the clip into three parts cost nothing either.

### Field contract

- `Word` / `Phrase` — the target form, no articles unless part of the phrase.
- `Pronunciation` — **General American IPA in slashes**, primary stress `ˈ`, secondary
  `ˌ` (`/ˈrɛstərɑnt/`, `/ˈlɝn/`), with `ɚ`/`ɝ` for r-colored vowels and a flap for
  intervocalic `t` (`water` → `/ˈwɔt̬ɚ/`). Phonemic, not narrow: no syllable dots, no
  "sounds like" respelling, no British variants on the card. One line; if a fixed
  reduction is worth teaching, keep it to a short trailing parenthetical
  (`/ˈhæv/ (have to → /ˈhæftə/)`), never a sentence.
- `Definition` — one plain sentence per sense, no circular definition.
- `Image` — the **whole tag**: `<img src="voc_9f2c1ab3.jpg">`, bare filename, no path. It must
  *not* be a bare filename that the template wraps later: Anki's importer copies only the
  media it can see referenced in the field text (`<img src>` and `[sound:]`), so a filename
  wrapped by the template is silently dropped and the card imports with a broken image. The
  template therefore renders `{{Image}}` on its own.
- `Dialog` — the quoted line(s), attributed to a speaker inside the text (e.g.
  `"I'll be there for you." — Rachel`). One or two short lines; no scene description.
- `Source` — title plus episode (`Friends, S01E01`), and a timestamp only if it is known.
- `Audio` — three `[sound:<key>-<part>.mp3]` references, one per line and each labelled on
  the card: `word`, `explanation`, `dialog`. Bare filenames, no paths (Anki resolves them
  from the media map). Synthesized, never the film's audio.

## Categories (all kinds)

Every entry belongs to **one or more semantic groups** — `color`, `car`, `travel`,
`kitchen`, and so on — so the deck can be studied or filtered by theme, whichever kind the
entry is. A phrasal verb like `get up` fits `daily-routine`, a collocation like
`make an offer` fits `money`, and a vocabulary item like `have` fits `kitchen`.

**Categories are tags, not a field.** The requirement is multi-valued (`car` *and*
`travel` for `rent`), and tags are Anki's native multi-value mechanism: space-separated,
hierarchical with `::`, queryable (`tag:category::kitchen`), usable in filtered decks,
and — unlike fields — free to change forever. A field would have to encode several values
with a delimiter, which searches badly, breaks on values containing the delimiter, and
would mean a new model id if the requirement changed again.

Extending categories to phrasal verbs and collocations cost **nothing**: no field, no
model id, no migration, because the value lives in tags rather than in the note type. That
is the whole reason categories were not a field.

- **Tag shape:** `category::<slug>`, lowercase, singular, hyphenated (`category::car-rental`).
  The `category::` namespace keeps categories from colliding with other tags (level,
  register, source deck).
- **Cardinality (all kinds):** at least one category per note; typically one to three.
  More than three usually means the entry is too broad and should be split by sense.
- **Allowed values:** one controlled list shared by all three kinds, seeded with `color`,
  `car`, `travel`, `kitchen` and extended deliberately. Reuse an existing category before
  inventing a near-duplicate (`car` and `vehicle` would split a filter in two); when a new
  one is justified, add it to this list in the same change.
- **Cross-kind filtering is expected.** `tag:category::kitchen` returns vocabulary,
  phrasal verbs and collocations together; narrow it with the note type
  (`tag:category::kitchen note:PhrasalVerb`) when only one kind is wanted.
- **Not a substitute for `Definition`.** The category orients study; it never explains the
  sense, and `rent` under `car` must still say which sense of `rent` is meant.
- **Display is a template concern.** v1 shows no category on the card; printing them is a
  cheap later template change (with a small CSS/JS filter so `{{Tags}}` does not leak
  technical prefixes). Because they are tags, none of this touches note identity.

## Levels (all kinds)

Every note — vocabulary, phrasal verb and collocation — carries **exactly one CEFR level**
so the deck can be studied by difficulty: `level::a1`, `level::a2`, `level::b1`,
`level::b2`, `level::c1`, `level::c2`.

- **Its own namespace, not a category.** A level is single-valued, applies to all three
  kinds, and is not a semantic group; putting it under `category::` would mix difficulty
  into `tag:category::*` filters and let a level masquerade as a theme. Separate
  namespaces keep both filters clean.
- **Cardinality:** exactly one per note. Zero levels means the note is unreachable in a
  `level::` filter; two levels means the filter double-counts, so the build rejects both.
- **Assign the level of the sense being taught, not of its words.** `give up` is roughly
  A2/B1 even though `give` is A1, and `make a decision` sits around B1 even though both
  words are A1; the chunk is what the learner is acquiring. The dialog quote may be harder
  than the target — level describes the target.
- **Use the lowest level at which a learner is expected to need the item.** When torn
  between two adjacent bands, take the lower one and keep the reasoning out of the card.
- **Full scale allowed, realistic deck:** A1–C2 are all legal, but a study deck that is
  mostly C1/C2 is a bad use of review time; levels should skew toward the learner's
  working range and mixed-frequency decks should be split by filter.
- **Displayed as a badge on the back**, next to the pronunciation: `A1`…`C2`. The level is a
  tag, so the card template extracts it from `{{Tags}}` with a few lines of JS — no field,
  no model change. Categories stay undisplayed; only the level is worth seeing while
  reviewing.

## Part of speech (vocabulary)

Every vocabulary note carries **one part of speech for the sense being taught**, shown on
the card directly under the pronunciation (`noun`, `verb`, `adverb`, …).

- **A tag, not a field:** `pos::verb`. Single-valued, filterable (`tag:pos::verb`), and it
  costs no model change — the same reasoning that put level and categories in tags.
- **Own namespace.** `pos::` never mixes with `category::` (themes) or `level::`
  (difficulty), so each filter stays exact.
- **Controlled list:** `noun`, `verb`, `adjective`, `adverb`, `pronoun`, `preposition`,
  `conjunction`, `interjection`, `determiner`, `numeral`, `modal-verb`, `auxiliary-verb`.
  A typo would silently produce a card with no word class, so the build rejects unknown
  values and requires one on every vocabulary entry.
- **The sense decides it, not the spelling.** `run` here is a verb because the note teaches
  "move fast on foot"; a noun sense of `run` is a different entry with a different sense
  slug and its own `pos::noun`.
- Phrasal verbs and collocations do not carry it yet: their kind already implies the shape.
  Adding it later is a tag, so it stays free.
- **Display:** the card template extracts `pos::` from `{{Tags}}` with JS, exactly like the
  level badge; the line hides itself when the tag is absent.

**Card order on the back:** headword → pronunciation → part of speech → level badge →
▶ word → **rule** → definition → ▶ explanation → **rule** → image → quote → source →
▶ dialog. The word, its IPA, its word class and its level form one block; the level is
deliberately the **last** line of that block, and the word's player comes after it so the
block is never split. The three sections (headword block, definition, illustration + quote)
are separated by the same plain `<hr>` — no custom CSS, so they match the `#answer` rule by
construction.

## Audio rules

Audio is generated with **edge-tts** (installed 7.3.1, `en-US` neural voices) at `--rate=-10%`.

- **Three clips per note, never one.** `word`, `explanation`, `dialog` — a learner replays
  the movie line far more often than the definition, and a single combined clip makes that
  impossible. Each lives in its own field (`Audio`, `AudioExplanation`, `AudioDialog`) and
  renders as a bare play button under its text — no labels, no stack of players at the
  bottom. The dialog player is the exception: it sits **after** the source line, at the foot
  of the card, so the quote and its attribution stay together.
- **Voices are pinned constants, and gender-aware:** `en-US-AvaNeural` (female, US,
  conversational) reads the word and the explanation **always**; `en-US-AndrewNeural` (male,
  US, conversational) reads the dialog **only when the character who says the line is a
  man**. A female character keeps the female voice. Never `en-US-AnaNeural` — child voice.
- **`speaker_gender` is authored data**, not inferred from the speaker's name: it is a
  required field in `src/<kind>.json` (`female` / `male`) and the build rejects anything
  else. Guessing from names breaks on `Alfred`, `Lilo`, `Miracle Max`.
- **One file per part**, named from the same content key as the image
  (`<key>-word.mp3`, `<key>-explanation.mp3`, `<key>-dialog.mp3`), so a note's four media
  artifacts share one stem.
- **Strip what must not be spoken:** the speaker attribution after the last `—` (or ` - `)
  in `Dialog`, the surrounding quotation marks, and any `[sound:]`/HTML markup. A card
  whose definition contains symbols, parentheses or slashes needs the spoken version
  written out; if the definition cannot be read aloud cleanly, fix the definition.
- **Audio plays on the back only.** On the front it would read the answer out loud.
- Regenerate on explicit request, never on a plain build: edge-tts is a cloud service, so
  byte-identical output is not guaranteed. Like images, committed audio is an **input**.
- Guard against the failure that does not error: a note whose `Audio` is empty or points at
  a missing mp3 renders silent. Assert both the field and the file, same as images.

## Media rules

- Images live in `media/` in the repo, named from the note's stable key: kind prefix plus
  a short deterministic hash of `phrase + sense` (the same string the GUID uses), so a
  re-run maps an entry to the same file and a renamed entry never silently reuses another
  card's picture.
- One image per note, showing the sense concretely. No text, logos, or captions baked
  into the image: AI-rendered lettering is unreliable, and on the back of a word card the
  meaning is already spelled out by `Definition`.
- Images are committed, not regenerated at build time. Regenerating would break the
  "same input, same output" rule because image models are not deterministic; the media
  folder is therefore an **input** to generation, and only missing files are generated.
- The package registers every referenced image in its media map. Missing media does not
  fail the import — it silently yields an empty card — so the generator asserts that each
  referenced filename exists before writing the `.apkg`.

## Dialog rules

- The quote must be a real line from a real show or film, with a source that can be
  checked. Fabricated credits ("this is from Seinfeld") are worse than no card.
- Keep quotes short (one or two lines) and use them as **usage evidence**, not decoration:
  the line must only work with the target sense.
- The show should be recognizable to a Brazilian learner of English and the line should
  not depend on visual context to make sense.
- Short quotes with attribution are a fair-use-style compromise; do not paste long
  transcripts or scene descriptions.

## Decks and output

Three decks, one per kind, each in its own package:

| Kind | Deck name | Deck id | Model id | Output file |
|---|---|---|---|---|
| Vocabulary | `Vocabulary` | `517813484872` | `552622157608` | `decks/vocabulary.apkg` |
| Phrasal verb | `Phrasal Verbs` | `807523115129` | `726156055118` | `decks/phrasal-verbs.apkg` |
| Collocation | `Collocations` | `221110591407` | `889236578191` | `decks/collocations.apkg` |

Test builds (`--test`) get a **second, fully separate identity** so a rehearsal can never
touch the real deck — different ids *and* different names, because Anki matches decks by
name and note types by id:

| Kind | Test deck name | Test deck id | Test model id | Output file |
|---|---|---|---|---|
| Vocabulary | `Vocabulary (test)` | `804850451889` | `817309927966` | `tests/decks/vocabulary-test.apkg` |
| Phrasal verb | `Phrasal Verbs (test)` | `567855487385` | `618605022273` | `tests/decks/phrasal-verbs-test.apkg` |
| Collocation | `Collocations (test)` | `242142671948` | `499896888196` | `tests/decks/collocations-test.apkg` |

Test ids were derived once from `sha1("anki-english:test:deck:<slug>")` /
`sha1("anki-english:test:model:<slug>")` and pinned like the production ones. The `(test)`
suffix on both names is the load-bearing part: ids alone would not stop the merge.

- **Why three packages and not one:** each kind is studied separately, so a phrasal-verb
  session should not draw collocations; each package carries only its own kind's images and
  mp3s, so they stay small; and re-importing one kind cannot disturb the other two.
- **Ids are pinned literals.** They were derived once from
  `sha1("anki-english:deck:<name>")` / `sha1("anki-english:model:<name>")` and are now
  recorded here. Never recompute them at runtime and never derive them from time or
  randomness — that is what produces a duplicate deck on every import.
- **The model ids are on their second generation** (`sha1("anki-english:v2:model:<kind>")`)
  because adding the two extra audio fields changed the field list. That is not a cosmetic
  bump: Anki's importer compares schemas and treats a GUID match with a different schema as
  a **conflict**, leaving the existing note untouched. A new id is the only way to carry a
  field change into a collection that already has the old note type.
- **Flat names, no `English::` parent deck.** Anki matches an incoming deck by **name**, so
  a new name creates a parallel deck rather than grouping the existing one; the pinned id
  is what a fresh collection receives. Decide the hierarchy now, while no notes exist.
- **The names are part of the contract.** Renaming a deck inside Anki keeps its id, but
  changing the name the generator emits means Anki sees a new deck, not the old one.
- **`decks/` holds build output.** The three empty baseline packages are committed on
  purpose (`.gitignore` re-includes `decks/*.apkg`) so the deck and note-type ids exist in
  Anki before any content is imported; every later rebuild overwrites them from source.
  `tests/` is the throwaway tree (`--test`) and is **gitignored** as a whole — `tests/src/`,
  `tests/media/` and `tests/decks/`: test source, art and packages never mix with production
  and can never be committed. They carry their own ids, names and filenames (see the test
  table above) so an import lands in a `(test)` deck instead of the real one. Never hand-edit
  a package.
- **Rebuilds are incremental.** Importing a rebuilt package updates existing notes in place
  and keeps their scheduling, provided the GUIDs, deck names and model ids stay put; see
  [incremental updates](incremental-updates.md).
- **Content is added only on demand.** The committed packages are deliberately empty and
  stay that way until the user asks for flashcards. Nothing seeds a deck to make it
  "testable": no placeholder note, no starter list, no sample entry. The baseline exists to
  pin ids, not to hold content.
- **GUID scope:** import deduplicates within one model *and* one deck, so with one model
  per deck the per-kind GUID prefix (`voc:` / `pv:` / `col:`) is what prevents cross-kind
  collisions.

## Why not a shared model

Rejected: one note type with a `Kind` field would force a single template onto three card
shapes, and the only per-kind difference would live in data rather than in the model.
Cheaper now, worse as soon as the card designs diverge.

## Source format

**Decided 2026-11-05: one JSON array per kind under `src/`** — `src/vocabulary.json`,
`src/phrasal-verbs.json`, `src/collocations.json`. Chosen over CSV and Markdown because an
entry carries a nested list (categories), a quoted multi-line dialog and an authored sense
slug; JSON holds all three without inventing a delimiter or an escape rule.

| Key | Written to the note | Notes |
|---|---|---|
| `phrase` | `Word` / `Phrase` | the target form, lowercase |
| `sense` | — | kebab-case slug, becomes the GUID's identity half; reword freely, rename never |
| `pronunciation` | `Pronunciation` | GenAm IPA in slashes |
| `definition` | `Definition` | one sentence |
| `dialog` | `Dialog` | quoted line plus `— Speaker` attribution |
| `source` | `Source` | title, plus episode when known |
| `categories` | `category::*` tags | 1–3 slugs from the controlled list |
| `level` | `level::*` tag | exactly one |
| `image_brief` | — | authoring metadata for regenerating the illustration |

`src/` is an **input** and is committed; it is not a cache of the packages. The image and
mp3 filenames are not in the source at all — they are derived from `phrase` + `sense`, so a
typo in a filename is impossible and renaming a file by hand is never necessary.

Content is included only with `--notes`; a plain build still emits the empty baseline.

## Still open — do not invent

1. **Per-kind card templates** beyond front→back (particle gap-fill, word cloze).
2. Whether images sit on the back only (assumed) or also on the front as a recall cue.
3. Whether to add a register tag (`register::informal`) for filtering. CEFR level is
   decided ([Levels](#levels-all-kinds)); register stays open and, if added, gets its own
   namespace so it never mixes with categories or levels.
4. Whether production content ships at all, or the decks stay empty and only test builds
   carry entries.

## Cost of changing fields later

Anki indexes a model's fields by name and position. Editing the field list of a model
that already has notes remaps or destroys those notes and requires a new model id, a new
note type and a migration — while scheduling history stays on the old notes. A GUID only
deduplicates within one model+deck, so a late field change typically yields a parallel
duplicate deck instead of an update. This is why `Audio` was pinned before it was used:
when audio was requested, the schema did not move.

## Consequences for code

- One constants block: `VOC_MODEL_ID`, `PV_MODEL_ID`, `COL_MODEL_ID`, `VOC_DECK_ID`,
  `PV_DECK_ID`, `COL_DECK_ID`, and the three output paths — literals from the table above,
  never derived at runtime.
- TTS constants live there too: `EDGE_VOICE = "en-US-AvaNeural"`, `EDGE_RATE = "-10%"`, and
  the segment order (target → definition → dialog). Changing the voice is a one-line edit
  and a regeneration of media, not a schema change.
- GUIDs are `voc:` / `pv:` / `col:` + normalized phrase + an **explicit sense-key slug**
  (`voc:have:eat-or-drink`), and all media filenames (`<key>.jpg`, `<key>-word.mp3`,
  `<key>-explanation.mp3`, `<key>-dialog.mp3`) derive from the same key. The slug is
  authored, never derived from `Definition` — see
  [incremental updates](incremental-updates.md) for why that rule is load-bearing.
- The package now always has a media map: build it from the referenced images and mp3s,
  verify it, and fail generation if a note is missing either, or if `Audio` is empty.
- Every note must carry at least one `category::<slug>` tag, and every slug must be in
  the allowed list. Enforce this at build time; a category typo silently empties a
  filtered deck rather than failing.
- Every note needs the full field set, `Pronunciation` included: reject a note with an
  empty pronunciation rather than letting the card render with a blank line.
- Every note needs exactly one `level::a1`…`level::c2` tag; reject zero levels and reject
  two, because either silently corrupts a level filter.
