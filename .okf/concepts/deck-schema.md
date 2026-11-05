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
- **Audio is synthesized speech, not the movie clip.** One mp3 per note, read by a pinned
  female US voice (edge-tts), containing the target, then the definition, then the dialog
  line. This gives listening practice without sourcing or licensing audio from the film.
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
| Vocabulary | `Word`, `Pronunciation`, `Definition`, `Image`, `Dialog`, `Source`, `Audio` | homographs need a sense in the GUID, not extra fields |
| Phrasal verb | `Phrase`, `Pronunciation`, `Definition`, `Image`, `Dialog`, `Source`, `Audio` | phrase stored whole; particle splitting is deferred |
| Collocation | `Phrase`, `Pronunciation`, `Definition`, `Image`, `Dialog`, `Source`, `Audio` | same shape as phrasal verb, separate model so ids stay independent |

Field **order** is part of the pinned schema too: it drives the editor layout and the
`{{Field}}` references, and reordering a field list is as destructive as renaming one.

`Audio` is **required on every note** and holds `[sound:<key>.mp3]`. It was reserved empty
in the first draft precisely so that turning audio on later would not require a new model
id — that is now what happened: the field list is unchanged.

### Field contract

- `Word` / `Phrase` — the target form, no articles unless part of the phrase.
- `Pronunciation` — **General American IPA in slashes**, primary stress `ˈ`, secondary
  `ˌ` (`/ˈrɛstərɑnt/`, `/ˈlɝn/`), with `ɚ`/`ɝ` for r-colored vowels and a flap for
  intervocalic `t` (`water` → `/ˈwɔt̬ɚ/`). Phonemic, not narrow: no syllable dots, no
  "sounds like" respelling, no British variants on the card. One line; if a fixed
  reduction is worth teaching, keep it to a short trailing parenthetical
  (`/ˈhæv/ (have to → /ˈhæftə/)`), never a sentence.
- `Definition` — one plain sentence per sense, no circular definition.
- `Image` — **bare filename only** (`voc_9f2c1ab3.jpg`), never a path and never an
  `<img>` tag; the template renders `{{Image}}` into `<img src="...">`, so the package
  media map and the field agree by construction.
- `Dialog` — the quoted line(s), attributed to a speaker inside the text (e.g.
  `"I'll be there for you." — Rachel`). One or two short lines; no scene description.
- `Source` — title plus episode (`Friends, S01E01`), and a timestamp only if it is known.
- `Audio` — `[sound:<key>.mp3]` with the bare filename and no path (Anki resolves it from
  the media map). The clip reads, in this fixed order: the target, the definition, the
  dialog line — synthesized, never the film's audio.

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
- **Display is a template concern,** same as categories: nothing is printed in v1.

## Audio rules

Audio is generated with **edge-tts** (installed 7.3.1, `en-US` neural voices) using a
pinned female voice and rate, so every card sounds the same person.

- **Voice is a constant, not a per-card choice:** `en-US-AvaNeural` (female, US,
  conversational), `--rate=-10%`. Alternatives on this machine if that one disappoints:
  `en-US-AriaNeural`, `en-US-JennyNeural`, `en-US-EmmaNeural`. Never `en-US-AnaNeural` —
  it is a child voice, not a woman.
- **One file per note**, named from the same content key as the image
  (`<key>.mp3`), so a note's three media artifacts share one stem.
- **Script, fixed order:** target → definition → dialog. Assemble it as
  `<target>. <definition>. <dialog>` in a single call; punctuation supplies the pauses,
  which avoids an ffmpeg concat step and keeps the pipeline to one dependency.
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
| Vocabulary | `Vocabulary` | `517813484872` | `104320564501` | `decks/vocabulary.apkg` |
| Phrasal verb | `Phrasal Verbs` | `807523115129` | `1030950240795` | `decks/phrasal-verbs.apkg` |
| Collocation | `Collocations` | `221110591407` | `834857214829` | `decks/collocations.apkg` |

- **Why three packages and not one:** each kind is studied separately, so a phrasal-verb
  session should not draw collocations; each package carries only its own kind's images and
  mp3s, so they stay small; and re-importing one kind cannot disturb the other two.
- **Ids are pinned literals.** They were derived once from
  `sha1("anki-english:deck:<name>")` / `sha1("anki-english:model:<name>")` and are now
  recorded here. Never recompute them at runtime and never derive them from time or
  randomness — that is what produces a duplicate deck on every import.
- **Flat names, no `English::` parent deck.** Anki matches an incoming deck by **name**, so
  a new name creates a parallel deck rather than grouping the existing one; the pinned id
  is what a fresh collection receives. Decide the hierarchy now, while no notes exist.
- **The names are part of the contract.** Renaming a deck inside Anki keeps its id, but
  changing the name the generator emits means Anki sees a new deck, not the old one.
- **`decks/` is build output.** It is created on demand, `*.apkg` is already gitignored,
  and nothing under it is committed — regenerate instead of editing a package.
- **Rebuilds are incremental.** Importing a rebuilt package updates existing notes in place
  and keeps their scheduling, provided the GUIDs, deck names and model ids stay put; see
  [incremental updates](incremental-updates.md).
- **GUID scope:** import deduplicates within one model *and* one deck, so with one model
  per deck the per-kind GUID prefix (`voc:` / `pv:` / `col:`) is what prevents cross-kind
  collisions.

## Why not a shared model

Rejected: one note type with a `Kind` field would force a single template onto three card
shapes, and the only per-kind difference would live in data rather than in the model.
Cheaper now, worse as soon as the card designs diverge.

## Still open — do not invent

1. **Source vocabulary format**: CSV, Markdown, JSON, or a dictionary API — it must carry
   the dialog quote, the attribution, the image reference, the category slugs, and the
   stable sense-key slug that the GUID is built from.
2. **Per-kind card templates** beyond front→back (particle gap-fill, word cloze).
3. Whether images sit on the back only (assumed) or also on the front as a recall cue.
4. Whether to add a register tag (`register::informal`) for filtering. CEFR level is
   decided ([Levels](#levels-all-kinds)); register stays open and, if added, gets its own
   namespace so it never mixes with categories or levels.

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
  (`voc:have:eat-or-drink`), and both media filenames (`<key>.jpg`, `<key>.mp3`) derive
  from the same key. The slug is authored, never derived from `Definition` — see
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
