---
type: decision
title: "v1 schema: one model and one deck per kind, media-rich cards"
description: "Decided 2026-11-05, revised 2026-11-09: one note type and one deck per content kind with pinned ids; every note carries IPA, an authored example sentence with the target in bold, and female-voice TTS mp3s, plus an AI-generated image named by its own `image` field when that file exists, and every verb adds four authored example sentences (present, present participle, past, past participle). The movie/TV quote block was removed on 2026-11-08. Card templates beyond front→back remain open."
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

# v1 schema: three per-kind models, image + authored example cards

## Decision (2026-11-05, revised)

- **One note type per content kind**, i.e. three models with three pinned ids, rather
  than one shared model plus a `Kind` field.
- **Every note has one authored example sentence, plus an image when its `image` field names
  a file in `media/`.** The example shows the target
  in use, is written by us and is never attributed. It **uses the target in the entry's own
  form** — the base form on the front — so `hire` reads `We need to hire two more nurses this
  month.`, never `You're hired.`; an inflected example would put a form on the card that the
  entry is not teaching. The other tenses belong to the verb's form rows.
- **The movie/TV quote block was removed (2026-11-08).** User: "remove movie/tv show quote."
  `Dialog`, `Source` and `AudioDialog` are gone, and `speaker_gender` with them: the card is
  shown and spoken entirely in our own text. The quote's historical rationale stays in the log.
- **Images are AI-generated and committed to the repo** under `media/`. They are licensed
  for use here and regenerable, at the cost of being invented scenes rather than real
  stills.
- **Audio is synthesized speech.** Three clips per note — `word`, `explanation`, `example` —
  so each part can be replayed on its own, all on the pinned female voice because nothing on
  the card is a character's line. This gives listening practice entirely in our own material.
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
| Vocabulary | `Word`, `Pronunciation`, `Definition`, `Image`, `Audio`, `AudioExplanation`, `PresentExample`, `PastSimpleExample`, `PastParticipleExample`, `PresentParticipleExample`, `AudioPresentExample`, `AudioPastSimpleExample`, `AudioPastParticipleExample`, `AudioPresentParticipleExample`, `Example`, `AudioExample` | homographs need a sense in the GUID, not extra fields |
| Phrasal verb | `Phrase`, `Pronunciation`, `Definition`, `Image`, `Audio`, `AudioExplanation`, `PresentExample`, `PastSimpleExample`, `PastParticipleExample`, `PresentParticipleExample`, `AudioPresentExample`, `AudioPastSimpleExample`, `AudioPastParticipleExample`, `AudioPresentParticipleExample`, `Example`, `AudioExample` | phrase stored whole; particle splitting is deferred |
| Collocation | `Phrase`, `Pronunciation`, `Definition`, `Image`, `Audio`, `AudioExplanation`, `PresentExample`, `PastSimpleExample`, `PastParticipleExample`, `PresentParticipleExample`, `AudioPresentExample`, `AudioPastSimpleExample`, `AudioPastParticipleExample`, `AudioPresentParticipleExample`, `Example`, `AudioExample` | same shape as phrasal verb, separate model so ids stay independent |

The audio fields are one clip each — `Audio` is the **word** clip (the name predates the
split; renaming a field is destructive, so it stayed), `AudioExplanation` and `AudioExample`
follow. Separate fields are what let the template put each player directly under the text it
reads instead of stacking them at the bottom. The same pattern repeats for a verb: each of
the four example rows has its own text and audio field.

The eight verb fields are the **verb-only example block**; they are empty on a non-verb note,
and the template's `{{#PresentExample}}` / `{{#PastSimpleExample}}` /
`{{#PastParticipleExample}}` / `{{#PresentParticipleExample}}` sections then render nothing at
all — no empty rows, no stray dividers. `Example` and `AudioExample` come last and are required
on **every** note.

The authored examples — `Example` and the four verb rows — carry their target in `**...**`,
which the build renders as `<b>`; a split phrasal verb uses two pairs (`Never **leave** a
teammate **behind**.`). The markers are stripped before the text is spoken, and validation
rejects an example that marks nothing, leaves a stray `**`, or has an empty span.

Field **order** is part of the pinned schema too: it drives the editor layout and the
`{{Field}}` references, and reordering a field list is as destructive as renaming one.

`Audio` is **required on every note** and holds one `[sound:<key>-word.mp3]` reference;
`AudioExplanation` and `AudioExample` hold the other two clips. It was reserved empty in the
first draft precisely so that turning audio on later would not require a new model id — that is
now what happened: the field list grew only for the explanation and example clips.

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
  template therefore renders `{{Image}}` on its own. **Optional:** the filename is authored in
  the entry's `image` field; when the file is not on disk the field is left empty and the card
  renders without an illustration.
- `Example` — **one authored sentence** using the target sense in an everyday
  situation, shown directly under the illustration: `Round up everyone who was near
  the bank.` Required on every note, at every level. It is not attributed, it never describes
  the illustration, and it uses **the entry's own form** — the base
  form on the front (`We need to hire two more nurses this month.`). A different form here
  would teach a tense the entry is not, while the form rows already cover the rest. The target
  is marked `**like this**` (two pairs when the phrase splits).
- `PresentExample` / `PastSimpleExample` / `PastParticipleExample` /
  `PresentParticipleExample` — **one short authored sentence per form**, shown as a labelled
  row under the authored example, in the order `Present` / `Present participle` / `Past` /
  `Past participle`: `She has coffee with breakfast every day.` / `She is having breakfast
  right now.` / `We had pizza at the new place downtown.` / `I have had the same breakfast all
  week.` Verbs only. The `-ing` row is labelled `Present participle` on the card, so it reads
  as a form name beside `Past participle`; its sentence is the `-ing` form in use. The target
  is bold here too.
- `Audio` — the word clip: one `[sound:<key>-word.mp3]` reference, bare filename, no path
  (Anki resolves it from the media map). Synthesized.
- `AudioExplanation` — the clip for the definition.
- `AudioExample` — the clip for the authored example; required on every note.
- `AudioPresentExample` / `AudioPastSimpleExample` / `AudioPastParticipleExample` /
  `AudioPresentParticipleExample` — the same `[sound:]` shape, one per example row; verbs only.

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
  words are A1; the chunk is what the learner is acquiring. Level describes the target, not
  the surrounding sentence.
- **Use the lowest level at which a learner is expected to need the item.** When torn
  between two adjacent bands, take the lower one and keep the reasoning out of the card.
- **Full namespace, but per-deck scope:** the CEFR scale is `a1`–`c2`, yet each production
  deck accepts only its own range — Vocabulary A1–C1, Phrasal verbs and Collocations A1–B2.
  A level outside that range is a build error, so a C2 item cannot land in any of the three
  decks as scoped today.
- **Production deck targets** (planning targets, not build assertions):

  | Deck | Target level | Cards | Content focus |
  |---|---|---|---|
  | Vocabulary | A1–C1 | 5,500 | Basic lexicon through abstract concepts and analytical verbs (`mitigate`, `feasible`). |
  | Phrasal verbs | A1–B2 | 350 | High-frequency structures for daily life and work (`figure out`, `carry out`, `bring up`). |
  | Collocations | A1–B2 | 800 | Natural word pairings (`make a decision`, `meet a deadline`, `heavily reliant on`). |

  The build reports progress as `notes=<count>/<target>`; only the level ranges are enforced.
- **Displayed as a badge on the back**, next to the pronunciation: `A1`…`C2`. The level is a
  tag, so the card template extracts it from `{{Tags}}` with a few lines of JS — no field,
  no model change. Categories stay undisplayed; only the level is worth seeing while
  reviewing.

## Part of speech (all kinds)

Every note carries **one part of speech for the sense being taught**, shown on the card
directly under the pronunciation (`noun`, `verb`, `adverb`, …).

- **A tag, not a field:** `pos::verb`. Single-valued, filterable (`tag:pos::verb`), and it
  costs no model change — the same reasoning that put level and categories in tags.
- **Own namespace.** `pos::` never mixes with `category::` (themes) or `level::`
  (difficulty), so each filter stays exact.
- **Controlled list:** `noun`, `verb`, `adjective`, `adverb`, `pronoun`, `preposition`,
  `conjunction`, `interjection`, `determiner`, `numeral`, `modal-verb`, `auxiliary-verb`.
  A typo would silently produce a card with no word class, so the build rejects unknown
  values and requires one on every entry of every kind.
- **The sense decides it, not the spelling.** `run` here is a verb because the note teaches
  "move fast on foot"; a noun sense of `run` is a different entry with a different sense
  slug and its own `pos::noun`.
- **It now rules the schema, not just the display.** `pos::verb` is what requires the example
  block: a phrasal verb is a verb by nature, and a collocation's head word may be one
  (`make a mistake` → verb, `heavy rain` → noun). This is why `pos` moved from
  vocabulary-only to every kind.
- **Display:** the card template extracts `pos::` from `{{Tags}}` with JS, exactly like the
  level badge; the line hides itself when the tag is absent.

## Form examples (verbs)

A note with `pos::verb` carries **four extra example sentences**, one per grammatical form, in
this order: `Present` (`She runs every morning before work.`), `Present participle` (`She is
running late again.`), `Past` (`She ran to catch the bus.`) and `Past participle` (`He has run
this route many times.`). They render as four labelled rows **under the authored example**, each
with its own play button.

- **Why the `-ing` row was added (2026-11-08).** User request: "when the word is a verb add ing
  example." The continuous form is the third shape a learner needs in production, and it was
  the one form the card left out; the past participle alone does not cover `is running` /
  `being into`. For stative `be` expressions (`be up to`, `be into`, `be good at`) the row
  shows the gerund (`Being into someone you work with makes the week complicated.`), because
  `is being into` does not exist. The row is labelled `Present participle`, matching the
  `Past participle` label; the sentence shows the `-ing` form itself.
- **Under the authored example, not under the headword.** A `wrote / written` table under the
  word was built first and dropped: it read like a dictionary entry on the back of a
  flashcard. The example rows are the part that earned its space, so they are the whole
  feature.
- **Authored sentences.** A real line that uses `paid attention`, `fastened your seatbelt` or
  `had a problem` in the past barely exists, and an invented one would be worse than a plain
  sentence. The label says which form the sentence demonstrates.
- **The forms themselves are not shown.** The learner infers them from the sentences; the
  base form is the front of the card. Adding the tense table back would mean new fields and
  a new model id.
- **Required, not optional.** A verb entry without any of the four keys fails the build, and
  a non-verb carrying them fails too — the second rule catches a copy-pasted block that
  would otherwise print `Present` on a noun.
- **Row order is `Present`, `Present participle`, `Past`, `Past participle`** (set
  2026-11-08): the two present forms side by side, then the two past forms, which reads as a
  tense pairing rather than a grammar-table colon. The perfect stays last.
- **Four more clips**: `-present-example`, `-present-participle-example`,
  `-past-simple-example`, `-past-participle-example`, all on the pinned female voice because no
  character says them.

**Card order on the back:** flex rows, each with its text and its play button side by side,
the pair centred — headword (with pronunciation, word class and level, level last) + ▶ word,
definition + ▶ explanation, the illustration, then the labelled **Example** row —
and, for a verb, the four labelled example rows in the order `Present`, `Present participle`,
`Past`, `Past participle`, each with its own play button. The button hugs the text rather than
sitting at the card edge, and the text is allowed to shrink so a long definition still
wraps. Everything is separated by the same plain `<hr>` — no custom CSS, so the dividers
match the `#answer` rule by construction. The back renders the headword itself instead of
`{{FrontSide}}`, because the button has to sit beside it in the same row.

## Audio rules

Audio is generated with **edge-tts** (installed 7.3.1, `en-US` neural voices) at `--rate=-10%`.

- **Three clips per note, never one** — seven for a verb. `word`, `explanation`, `example`
  plus `present-example`, `present-participle-example`, `past-simple-example`,
  `past-participle-example`. A learner replays the example far more often than the
  definition, and one long clip makes that impossible. Each lives in its own field (`Audio`,
  `AudioExplanation`, `AudioExample`, `AudioPresentExample`, `AudioPastSimpleExample`,
  `AudioPastParticipleExample`, `AudioPresentParticipleExample`) and renders as a bare play
  button under its text — no labels, no stack of players at the bottom.
- **One pinned voice:** `en-US-AvaNeural` (female, US, conversational) reads every part.
  There is no character's line on the card any more, so nothing needs a second voice. Never
  `en-US-AnaNeural` — child voice.
- **One file per part**, named from the same content key as the image
  (`<key>-word.mp3`, `<key>-explanation.mp3`, `<key>-example.mp3`, and for verbs
  `<key>-present-example.mp3`, `<key>-present-participle-example.mp3`,
  `<key>-past-simple-example.mp3`, `<key>-past-participle-example.mp3`), so a note's media
  artifacts share one stem.
- **Strip what must not be spoken:** the `**` bold markers around the target and any
  `[sound:]`/HTML markup. A card whose definition contains symbols, parentheses or slashes
  needs the spoken version written out; if the definition cannot be read aloud cleanly, fix
  the definition.
- **Audio plays on the back only.** On the front it would read the answer out loud.
- Regenerate on explicit request, never on a plain build: edge-tts is a cloud service, so
  byte-identical output is not guaranteed. Like images, committed audio is an **input**.
- Guard against the failure that does not error: a note whose `Audio` is empty or points at
  a missing mp3 renders silent. Assert both the field and the file, same as images.

## Media rules

- Images live in `media/` in the repo. The filename is **authored**, not derived: an entry's
  `image` field names the file without an extension (`"image": "voc_6a648cec"`), because the picture is pasted
  in by hand from Midjourney. The field names the image, not its format: the stem is tried
  against `.jpg`, `.jpeg`, `.png`, `.gif` and `.webp`, and a written extension that does not
  match the file falls back to the same stem.
- An `image` that names no file on disk is **not an error**: the note is built with an empty
  `Image` field and a warning, so the card has no illustration rather than a broken `<img>`.
  Audio keeps the fail-loud rule below.
- One image per note, showing the sense concretely. No text, logos, or captions baked
  into the image: AI-rendered lettering is unreliable, and on the back of a word card the
  meaning is already spelled out by `Definition`.
- The `image_brief` is derived from the **`Definition`** (the phrase fixes what must be
  visible; the sense slug picks the meaning) and never from the authored `Example`, which
  drifts into a different situation. It is authoring metadata for a re-render, not a card
  field.
- Images are committed, not regenerated at build time. Regenerating would break the
  "same input, same output" rule because image models are not deterministic; the media
  folder is therefore an **input** to generation, and only missing files are generated.
- The package registers every referenced image in its media map. Missing media does not
  fail the import — it silently yields an empty panel — so the generator asserts that each
  referenced **mp3** exists before writing the `.apkg`, while an absent image simply leaves
  the `Image` field empty.

## Decks and output

Three decks, one per kind, each in its own package:

| Kind | Deck name | Deck id | Model id | Output file |
|---|---|---|---|---|
| Vocabulary | `Vocabulary` | `517813484872` | `691519255953` | `decks/vocabulary.apkg` |
| Phrasal verb | `Phrasal Verbs` | `807523115129` | `350528611282` | `decks/phrasal-verbs.apkg` |
| Collocation | `Collocations` | `221110591407` | `377855104706` | `decks/collocations.apkg` |

Test builds (`--test`) get a **second, fully separate identity** so a rehearsal can never
touch the real deck — different ids *and* different names, because Anki matches decks by
name and note types by id:

| Kind | Test deck name | Test deck id | Test model id | Output file |
|---|---|---|---|---|
| Vocabulary | `Vocabulary (test)` | `804850451889` | `220571904367` | `tests/decks/vocabulary-test.apkg` |
| Phrasal verb | `Phrasal Verbs (test)` | `567855487385` | `355844549585` | `tests/decks/phrasal-verbs-test.apkg` |
| Collocation | `Collocations (test)` | `242142671948` | `202971465130` | `tests/decks/collocations-test.apkg` |

Test ids were derived once from `sha1("anki-english:test:deck:<slug>")` /
`sha1("anki-english:test:v7:model:<slug>")` and pinned like the production ones. The `(test)`
suffix on both names is the load-bearing part: ids alone would not stop the merge.

- **Why three packages and not one:** each kind is studied separately, so a phrasal-verb
  session should not draw collocations; each package carries only its own kind's images and
  mp3s, so they stay small; and re-importing one kind cannot disturb the other two.
- **Ids are pinned literals.** They were derived once from
  `sha1("anki-english:deck:<name>")` / `sha1("anki-english:model:<name>")` and are now
  recorded here. Never recompute them at runtime and never derive them from time or
  randomness — that is what produces a duplicate deck on every import.
- **The model ids are on their seventh generation** (`sha1("anki-english:v7:model:<kind>")`)
  because removing the movie/TV quote block changed the field list — v2 came with the two
  extra audio fields, v3 was an interim conjugation table that shipped no further, v4 added
  the verb examples, v5 added the authored example, and v6 added the present-participle row.
  That is not a cosmetic bump: Anki's importer compares schemas and treats a GUID match with
  a different schema as a **conflict**, leaving the existing note untouched. A new id is the
  only way to carry a field change into a collection that already has the old note type.
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
entry carries a nested list (categories), an authored sense slug and multi-line example
sentences; JSON holds all three without inventing a delimiter or an escape rule.

**The manifest comes first (2026-11-09).** `src/index.csv` is the reviewed plan, one row per
sense: `kind,phrase,sense,pos,level,categories,gloss` (categories semicolon-separated). It is
written and deduplicated before any card, because a wrong gloss is cheap to fix and a
re-slugged sense orphans review history. `tools/lint_content.py` checks the manifest against
the JSON and reports progress and repetition; only a clean lint should reach a build.

| Key | Written to the note | Notes |
|---|---|---|
| `phrase` | `Word` / `Phrase` | the target form, lowercase |
| `sense` | — | kebab-case slug, becomes the GUID's identity half; reword freely, rename never |
| `pronunciation` | `Pronunciation` | GenAm IPA in slashes |
| `definition` | `Definition` | one sentence |
| `image` | `Image` | name of the illustration in `media/` without an extension, e.g. `voc_6a648cec` (the file may be `.jpg`, `.png`, `.gif`, …); optional — no matching file leaves the card without a picture |
| `example` | `Example` | an authored sentence using the target, required on every entry; the target is wrapped in `**...**` |
| `pos` | `pos::*` tag | part of speech, required on all three kinds |
| `present_example`, `present_participle_example`, `past_simple_example`, `past_participle_example` | `PresentExample`, `PresentParticipleExample`, `PastSimpleExample`, `PastParticipleExample` | verbs only; one authored sentence per form, target marked `**...**`, shown in this order |
| `categories` | `category::*` tags | 1–3 slugs from the controlled list |
| `level` | `level::*` tag | exactly one |
| `image_brief` | — | authoring metadata for regenerating the illustration |

`src/` is an **input** and is committed; it is not a cache of the packages. The image
filename is authored in the entry's `image` field, and the mp3 filenames are derived from
`phrase` + `sense`, so a typo in an audio filename is impossible. A hand-named image that
does not exist is tolerated — the card is built without it.

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
  the segment order (target → definition → example, then the verb's four form examples).
  Changing the voice is a one-line edit and a regeneration of media, not a schema change.
- GUIDs are `voc:` / `pv:` / `col:` + normalized phrase + an **explicit sense-key slug**
  (`voc:have:eat-or-drink`), and the mp3 filenames (`<key>-word.mp3`,
  `<key>-explanation.mp3`, `<key>-example.mp3`, plus the verb parts
  `<key>-present-example.mp3`, `<key>-present-participle-example.mp3`,
  `<key>-past-simple-example.mp3`, `<key>-past-participle-example.mp3`) derive from the same
  key. The `image` filename is authored on the entry instead. The slug is authored, never
  derived from `Definition` — see [incremental updates](incremental-updates.md) for why that
  rule is load-bearing.
- Uniqueness is `(phrase, sense)` within a kind, not the phrase alone: two senses of `run`
  are two notes with different GUIDs and different media keys, and a repeated sense is the
  collision that must fail.
- `src/index.csv` is checked by `tools/lint_content.py` before a build: manifest shape,
  source/manifest agreement, duplicate `kind + phrase + sense`, level range, tags, and the
  `**...**`/image-brief rules.
- The package now always has a media map: build it from the referenced images and mp3s,
  verify it, and fail generation if a note is missing an mp3 or if `Audio` is empty. A missing
  image is skipped, not fatal.
- Every note must carry at least one `category::<slug>` tag, and every slug must be in the
  allowed list. Enforce this at build time; a category typo silently empties a filtered deck
  rather than failing. Exactly one `level::` tag is required, and its value must be inside
  `KIND_LEVELS[slug]`. Production card counts live in `KIND_TARGET_CARDS` and are reported as
  progress, never asserted.
- Every note needs a `pos::` tag from the controlled list — the build rejects a missing or
  unknown word class, because it decides whether the example block is required.
- Every `pos::verb` note needs all four example sentences; a non-verb carrying them is
  rejected, so a copy-pasted block cannot print `Present` on a noun.
- Every authored example must bold its target with `**...**` and leave no stray marker; the
  markers are removed before TTS, so the spoken text stays plain.
- Every note needs the full field set, `Pronunciation` and `Example` included: reject a
  note with an empty pronunciation or example rather than letting the card render with a
  blank line.
- Every note needs exactly one `level::a1`…`level::c2` tag; reject zero levels and reject
  two, because either silently corrupts a level filter.
