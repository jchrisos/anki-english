# AGENTS.md

## Status: early skeleton

The repo holds documentation plus the first piece of tooling: `tools/build_decks.py`
builds the three **empty** deck packages from pinned constants. There is still no content
pipeline, no source data, and no tests or linter.

**Content only on demand.** The decks stay empty until the user explicitly asks for
flashcards. Never add notes, seed a package with a placeholder card, generate a starter
vocabulary list, or "test" the pipeline by writing real entries into `decks/`. Building the
packages is not a request for content; if an empty package turns out to be unimportable,
ask before seeding it.

```sh
python3 -m venv .venv                       # already exists locally, .venv/ is gitignored
.venv/bin/pip install -r requirements.txt   # genanki==0.13.1, edge-tts==7.3.1
.venv/bin/python tools/build_decks.py       # empty baseline: decks/*.apkg (gitignored)
.venv/bin/python tools/build_decks.py --test  # tests/src + tests/media -> tests/decks (all gitignored)
.venv/bin/python tools/build_decks.py --test --notes  # same, with the entries from tests/src/
.venv/bin/python tools/lint_content.py --test --report  # manifest + source checks (production: omit --test)
.venv/bin/python tools/build_audio.py --test  # mp3s into tests/media (production: omit --test)
.venv/bin/python tools/prepare_media.py --test  # PNG -> 900px JPEG in tests/media
```

Content lives in `src/<kind>.json` (one array per kind) and is included **only** with
`--notes`; a plain build still ships empty packages. Images under `media/` are inputs and are
committed — nothing regenerates art on a plain build. Audio is generated locally by
`tools/build_audio.py` and is **gitignored**: a clone has the images but no mp3s until that
step runs. Audio is named from the entry's key (`voc_6a648cec-word.mp3`); the illustration is
named by the entry's own `image` field (`"image": "voc_6a648cec"`).

**Packages are build artifacts.** `.gitignore` excludes every `*.apkg` (and `tests/`), so
nothing under `decks/` is committed — build locally and import the file by hand. The 71 MB
collocation package would otherwise trip GitHub's large-file warning on every push.

**The manifest comes first.** `src/index.csv` is the reviewed plan — one row per *sense*
(`kind,phrase,sense,pos,level,categories,gloss`), written and deduplicated before any card is.
Fixing a gloss is cheap; re-slugging a sense after import orphans review history. Write the
batch into the manifest, then fill `src/<kind>.json`, then run
`tools/lint_content.py` (manifest + source agreement, repetition report) and only then build.
The lint fails on unknown tags, a level outside the deck's range, duplicate
`kind + phrase + sense`, source entries missing from the manifest, and broken examples.

**The project writes image briefs; it does not render the images.** Every entry's `image_brief`
is a finished, paste-ready Midjourney prompt: a compressed scene description, then the shared
parameter block `--ar 3:2 --raw --s 50 --v 8.2 --no text, signage, watermark, logo, posed smile,
oversaturated, HDR`. V8.2 is the default model and spells raw mode `--raw`; `--style raw` belongs
to V7 only. `--s 50` and `--raw` keep the render literal and photographic instead of Midjourney's
glossy house look, and `--no` replaces the separate negative prompt. Rendering happens outside
the repo: the PNG is made in Midjourney, committed under `media/` (or `tests/media/`), and its
filename is written into that entry's `image` field so the build can find it;
`tools/prepare_media.py` derives the 900px JPEG. Nothing in `tools/` renders, upscales or
calls an image model. An `image` that names no file on disk is not an error: the card is
built without an illustration.

**Prompts are written like a documentary shot, not a stock portrait.** Each one names the camera
position (`from behind`, `from the side`, `from across the room`, `low angle`, `over the
shoulder`, `wide shot`) and keeps the subject at medium or wide distance; a prompt that reads
"a man looks at the camera" produces the plastic, front-lit look the deck must avoid. At most
**two people** in frame — one primary subject plus, when the definition needs them, a second —
with background figures indistinct or absent; group scenes are out. Add the ordinary clutter of
the place (empty desks, dishes, boxes, shadows) so the frame says where it is, and end the scene
with the mood. Never ask for a close-up, a frontal portrait or eye contact with the lens.

Keep one shared look across a deck: the parameter block above is identical on every prompt, and
if the set drifts, add the same `--sref <code>` to all of them rather than rewriting the scene
text. The scene carries the meaning, the parameters carry the style.

`tests/` is a **separate, fully gitignored tree**: `tests/src/`, `tests/media/` and
`tests/decks/`. `--test` on any of the three tools switches the whole layout there, so test
source, images, audio and packages never mix with production and can never be committed.
Test builds are also isolated in Anki: their own pinned deck and model ids, their own names
(`Vocabulary (test)`), their own filenames (`vocabulary-test.apkg`) and a `test:` GUID
prefix. Anki matches decks by name, note types by id and notes by GUID, so reusing any one
of them would merge a rehearsal into the real deck.

The build validates every note before writing: all text fields (the authored example
included), a part of speech, exactly one `level::` tag inside the deck's range, at least one
known `category::` tag,
and every required mp3 present on disk. The image is optional: an `image` field that names
no file leaves the card without an illustration. A verb also needs one example sentence for
each form; a non-verb carrying those keys is rejected. A failure is a build error, not a card with
a blank panel. Verifying a package still means unzipping it and querying the bundled sqlite;
there is no test suite yet.

**Two rules that bite on import, both learned the hard way:**

1. Media must be referenced *in the field*, not by the template: `Image` holds
   `<img src="key.jpg">` and `Audio` holds `[sound:key.mp3]`. Anki's importer only copies
   media it can see referenced in field text, so a bare filename wrapped by the template is
   silently dropped.
2. `BUILD_MOD` in `tools/build_decks.py` is the note type's `mod`, and Anki updates an
   existing note type only when the incoming mod is **newer**. Raise it whenever fields,
   templates or CSS change, or the new template never reaches a collection that already has
   the note type. In the import dialog keep "Update note types" at *If newer* (or *Always*).

Git is set up: branch `main`, remote `origin` →
`https://github.com/jchrisos/anki-english.git`. There is **no CI, no pre-commit hooks and no
PR template**, so nothing verifies a change automatically — run whatever checks you create
yourself.

## Project intent

Design rationale and the verified environment live in the OKF bundle at `.okf/`
(start at `.okf/index.md`); keep it in sync when the schema or tooling is decided.

Generate Anki flashcard decks (`.apkg`) for English study across three confirmed content
kinds: **vocabulary** (single words), **phrasal verbs**, and **collocations**. Entry text
is often multi-word, so an entry's identity is the full phrase plus its sense — never a
single token or a row index — and GUIDs are prefixed per kind (`voc:`/`pv:`/`col:`) so
the same string cannot collide across kinds.

Decided for v1: **one note type per kind** (three pinned model ids) with fields
headword/phrase, pronunciation (General American IPA), definition, image, example and three
audio fields (word, explanation, example), plus a verb-only block:
one example sentence per form (present, present participle, past, past participle) and four matching audio
fields. **Three decks, one per kind**, each built as its own package under `decks/` —
`vocabulary.apkg`, `phrasal-verbs.apkg`, `collocations.apkg` — with pinned deck ids and flat
names (no `English::` parent; a parent would be a different id, not a rename).

**Production deck targets** — the scope each deck is generated against:

| Deck | Target level | Cards | Content focus |
|---|---|---|---|
| Vocabulary | A1–C1 | 5,500 | Basic lexicon through abstract concepts and analytical verbs (`mitigate`, `feasible`). |
| Phrasal verbs | A1–B2 | 350 | High-frequency structures for daily life and work (`figure out`, `carry out`, `bring up`). |
| Collocations | A1–B2 | 800 | Natural word pairings (`make a decision`, `meet a deadline`, `heavily reliant on`). |

The card counts are **planning targets, not build assertions** — content arrives in batches,
so a build only reports progress (`notes=120/5500`). The level ranges **are** enforced: a
source entry outside its deck's range is a build error (`KIND_LEVELS` in
`tools/deck_common.py`). Vocabulary stops at C1; the other two stop at B2, and no deck takes
C2.

**Every card has one authored example sentence, and an illustration when its `image` field
names a file in `media/`.** The example is ours —
the only usage evidence on the card — and it exists because the definition names the sense
rather than showing it in use. **It must show the target in the entry's own form** — the base
form on the front: `hire` says `We need to hire two more nurses this month.`, never
`You're hired.` The other tenses are what the verb's form rows are for.

**The target is bold in every authored example.** The author wraps it in `**...**` (one pair,
or two when a phrasal verb splits: `Never **leave** a teammate **behind**.`), and the build
turns that into `<b>` for the card and strips the markers before TTS reads the sentence. The
span is authored, not derived: the sentence inflects (`runs`, `ran`, `running`) and sometimes
separates the particles, so the build cannot find the target on its own. A missing or
unbalanced marker pair is a build error.

**The illustration is built from the `definition` — never the authored example.** The phrase
fixes what object must be visible and the sense slug fixes which meaning of it, but the
definition is the only scene source: it says what that meaning is, so the picture and the
back of the card agree. The example is one sentence about the item, not a definition of it,
and it drifts away from the sense (`hire` drawn from a ward corridor says "understaffed", not
"give someone a job"), so it is never allowed to steer the art.

Draw the sense, and make the target the subject of the frame:

- **concrete noun** (`money`, `boat`, `road`) — the thing is in the frame, in focus, at a usable
  size, ideally in use: `money` shows bills and coins being handed over, not a man who happens
  to be short of cash.
- **verb** (`wear`, `hire`, `run`) — the action is caught in progress and readable from the
  silhouette: clothes already on the body, a pen and contract crossing a desk, a stride with
  both feet off the ground.
- **abstract noun or adverb** (`truth`, `back`) — show the one situation the definition describes
  and nothing else (the plain telling of what happened; the return to the place you came from).

The `image_brief` is rewritten when the definition or the sense changes, never because an
example was swapped.

Images are committed under `media/` and are **inputs** — the project writes the prompt, never the
picture. **Audio is synthesized with edge-tts** in three
separate clips per note — `-word`, `-explanation`, `-example` — so each part can be
replayed on its own. Every clip uses the pinned female voice (`en-US-AvaNeural`); nothing on
the card is a character's line. Rate is `-10%` throughout.

**A note whose part of speech is `verb` also gets a block of example sentences under the
authored example** — `Present`, `Present participle`, `Past`, `Past participle`, each one
labelled, spoken and shown on its own row, and each one bolding the target the same way. This
is **all** the card shows about conjugation: there is deliberately no
`wrote / written` table under the headword, which was tried and judged to read like a
dictionary entry. The sentences are **authored**: a real line that happens
to use `paid attention` or `fastened your seatbelt` in the past barely exists, and inventing
a credit is worse than not having one. `pos` is therefore required on **all three kinds**
(`tag:pos::verb` also gives a cross-deck verb filter), and a verb entry without the four
example keys fails the build.

**Every note — vocabulary, phrasal verb or collocation — carries one or more categories**
(`color`, `car`, `travel`, `kitchen`, …) stored as `category::<slug>` **tags, never a
field** — an entry can belong to several groups. **Every note in all three kinds also
carries exactly one CEFR level tag** (`level::a1` … `level::c2`), assigned to the sense
being taught rather than to its individual words.

Still open: source vocabulary format (CSV/Markdown/API) and card templates beyond
front→back. Adding a template later is cheap; changing a model's field list is not, since
it invalidates existing notes.

## Repo-local agent

`.opencode/agents/american-english-teacher.md` is a `subagent` for the **content** of the
decks (definitions, General American pronunciation, register, pt-BR interference, authored
example sentences, image briefs). It has no shell access and asks before editing,
and it does not touch schema, model/deck ids, GUIDs or `.apkg` packaging — launch it for
wording, not for build work. It writes the **Midjourney prompts**, never the images: rendering
happens outside the repo.

## One model only

Every turn in this repo runs on **`DeepSeek V4.1 Flash`** (`opencode/deepseek-v4.1-flash`).
Never pass a `model` override to a subagent, and do not call the agents that exist only to
forward work to something else — `claude-headless`, `claude-plan-creator`,
`claude-plan-validator`, `java-legacy-architect` and any `mcp__claude-in-chrome__*`,
`computer-use` or `built-in-browser` tool. With no `model` key anywhere (the repo-local
agent's frontmatter has none, and the global config pins none), subagents inherit the session
model, so "only this model" holds by leaving the override alone. Content work — definitions,
IPA, examples and image briefs — is done inline here, not delegated.

## Verified local environment (macOS, this machine)

- Anki desktop **25.09** at `/Applications/Anki.app`, profile `User 1`
  (`~/Library/Application Support/Anki2/`). There is no `anki` binary on `PATH`, so the
  workflow is "write a file, import it by hand", not CLI automation.
- Installed add-ons: AwesomeTTS, Review Heatmap. **No AnkiConnect** — do not plan on
  writing to the live collection over `127.0.0.1:8765` unless the user installs it.
- `python3` is 3.10.16 (pyenv default; 3.11.5 also installed). No `uv`, no `pipx`, and
  `genanki` is **not** installed. Create a repo-local `.venv` and pin deps; never
  install packages into the pyenv global interpreter.
- **`edge-tts` 7.3.1** is installed and working (`en-US` female neural voices,
  `--list-voices` to enumerate). The user installed it into the pyenv global interpreter,
  which bends the rule above — pin `edge-tts==7.3.1` in the repo `.venv` when one exists.
  Synthesis needs network access; it fails offline.
- `ffmpeg`, `lame` and `afinfo` are present but **not** used: one edge-tts call per spoken
  part produces each clip, so no concat/mux step is needed.

## Anki-specific pitfalls (these corrupt or duplicate data)

- The deck is **incremental by design**: re-importing a rebuilt package updates notes in
  place by GUID and keeps their cards, intervals and review history. Identity is therefore
  sacred — see `.okf/concepts/incremental-updates.md`.
- A note's GUID is `voc:`/`pv:`/`col:` + phrase + an **authored sense slug**, never derived
  from the definition text, a row number or a timestamp. Rewording a definition must not
  change the GUID; if it does, that card starts over as a new note.
- Anki matches **decks by name** and **note types by id**. Renaming the deck or changing a
  model's field list stops updates on the existing notes. Import `.apkg` files only —
  a `.colpkg` replaces the whole collection, review history included.
- Normal import: leave "Import any learning progress" **unticked** (our packages carry no
  scheduling) and set "Update notes" to *Always*, since the source data is the truth.
- `.apkg` is just a zip containing `collection.anki2` plus a `media` map. Never
  hand-edit one; always regenerate from source.
- Pin `deck_id`, the model id, and the note `guid` function as **constants**. Random
  ids/GUIDs mean every re-import creates a duplicate deck and duplicate notes instead
  of updating the existing ones — the single most common mistake here.
- Import matches notes by GUID only within the same model and deck ids. Changing a
  model's field list requires a new model id; reusing it remaps or breaks old notes.
- Categories are **tags** (`category::kitchen`), not fields. Multi-value by design, and
  tag edits never touch note identity — so adding a category later is free, while a
  `Category` field would have been a permanent schema decision.
- CEFR level is a **separate tag namespace** (`level::b1`), never `category::b1`, so
  `tag:category::*` stays a clean list of themes and level filters stay exact.
- Media must be registered in the package's media map and referenced by bare filename
  in fields/templates. Absolute or relative paths import as broken references.
- The illustration is optional. The entry names its file in an `image` field; if that file is
  absent, the card is built without a picture and the build prints a warning. Audio is not
  optional: a missing mp3 imports silently as a silent card, so every one of them is asserted.
- Image names are authored (`"image": "voc_6a648cec"`, no extension), never derived. Keep them in
  `media/`, and reference them by bare filename — a path in the field imports as broken.
- Audio is a `[sound:<key>-<part>.mp3]` reference per part — `word`, `explanation`,
  `example` in their own fields, plus one per verb form row — and plays on the
  **back only**; on the front it would read the answer aloud. A missing mp3 imports
  silently, exactly like a missing image, so every one of them is asserted.
- Verify output programmatically — unzip the `.apkg` and query the bundled sqlite
  (`select count(*) from notes`) — but still do one manual import to check card
  template rendering, which the note count cannot validate.
