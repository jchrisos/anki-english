---
name: fix-audio-issues
description: Fix audio problems in this Anki deck repository end to end — find the report with `gh issue list`, map the quoted words to the one card, reproduce the sound, always reword the text behind it, re-render and install the clip into the live collection. Use this whenever someone says a clip is noisy, buzzing, robotic, garbled, clipped, cut off or silent, reports a mispronounced word, says "rebuild the audio" or "the audio is still wrong", names a GitHub issue about sound, or asks for an audio fix to land in their Anki collection. Also the skill to use when triaging or closing a GitHub issue on this repo: nearly every report here is about a clip.
---

# Fix Audio Issues

Every clip is synthesized by edge-tts from one field of one entry, stored as a gitignored mp3,
and reaches Anki **by filename**. So an audio report has three possible homes — the text the
voice was given, the take the voice produced, or the file the collection actually holds — and a
fix that misses one of them leaves the reporter hearing exactly the same noise.

Most reports here are audio, and most are not what they first appear to be. A buzz that sounds
like a corrupt file is usually a deterministic artefact of the voice on those phonemes, and the
fix for it is a **rewording** — never a rebuild, a different voice or a faster rate; a clip that
"did not change" after a rebuild is usually still the old file, because Anki matches media by
name. Section 4 is the order that actually works.

The other card-level reports — a wrong definition, a missing illustration, a card that will not
import — run the same loop; section 2 places the fault.

`AGENTS.md` is the contract (manifest first, GUID identity, media rules, level ranges). The
commands below are the operational summary; when they disagree, `AGENTS.md` wins.

## 0. Preflight

```sh
gh auth status
gh repo view --json nameWithOwner,defaultBranchRef --jq '"\(.nameWithOwner) default=\(.defaultBranchRef.name)"'
git status --porcelain        # must be empty
git branch --show-current
```

Stop if the tree is dirty — committing someone else's half-finished content into a fix branch
makes the PR unreviewable. Needs `.venv` with `requirements.txt` installed:

```sh
.venv/bin/python -c "import genanki, edge_tts" || .venv/bin/pip install -r requirements.txt
```

## 1. List the issues and let the person choose

```sh
scripts/list-issues.sh                     # 50 most recently updated open issues
scripts/list-issues.sh --label bug         # any `gh issue list` filter passes through
scripts/list-issues.sh --assignee @me
```

An issue number or URL given up front skips the listing.

**Titles here are not unique** — two open issues were both "Audio with noise" and were
different defects. Read the body before choosing or dismissing anything; never triage on the
title.

## 2. Read the issue, then map it to one entry

```sh
gh issue view <n> --json number,title,body,state,labels,author,comments,createdAt
scripts/find-entry.py washes her hands          # the quoted text, not the issue number
scripts/find-entry.py --kind collocations "set the table"
```

`find-entry.py` prints the kind, phrase, sense, **media key**, and every clip with its size and
the exact text it speaks:

```
collocations: wash your hands  (sense: clean-your-hands, level: a1)
  key: col_d1e334e5
  present-example   20016 bytes  'Before dinner, she washes her hands.'
```

That is how you learn which of the 3–7 clips is at fault, and whether one is `MISSING`. Read
the comments too — reproductions and "actually intended" verdicts live there.

Then place the fault in one layer, because the fix is completely different:

| Symptom | Layer | Where it is fixed |
|---|---|---|
| awkward, wrong or unnatural wording; a definition off the sense | source | `src/<kind>.json` |
| noisy, robotic, garbled or clipped audio | source (the spoken text) | `src/<kind>.json`, then `tools/build_audio.py --key` |
| card imports but shows nothing: no sound, no tag, blank field | packaging | `tools/build_decks.py`, templates, tags |
| no illustration on the card | media input | the `image_brief`, rendered outside the repo |
| a planned sense that never became a card | manifest | `src/index.csv`, then the entry |

## 3. Reproduce

**Content** — read the entry in `src/<kind>.json` and compare it with what the issue quotes.
The source is the truth; there is nothing to run.

**Audio** — play the clip the issue is about:

```sh
afplay media/col_d1e334e5-present-example.mp3
```

**Packaging** — build and read the counts:

```sh
.venv/bin/python tools/build_decks.py --notes
```

A plain build ships **empty** packages (`--notes` is what includes `src/<kind>.json`), so a
"card is missing" report is often someone having built without it — check that before hunting
for a bug.

**Perceptual audio reports are the common case here** and cannot be reproduced by measuring.
Go to section 4 rather than guessing.

## 4. Audio reports: measure, then reword — never re-tune the voice

A "noise" in a clip is a property of the **string**, not of the take or the file. Every
perceptual report so far (#1, #2, #12–#14) has been one performance the voice produces
identically on every rebuild: two fresh takes of the same text differ in roughly half their
bytes but keep the **same duration and the same speech onset**. Re-rendering the same sentence
therefore brings the artefact straight back.

So the fix for a noisy, buzzing, robotic or garbled clip is **always a rewording**. Never change
`VOICE_FEMALE` or `RATE`, and never offer a different voice, a faster rate or another encoder as
the repair — those change every clip in the project to patch one, and they are a separate
decision, not a fix.

The single exception is a clip that is **missing, zero-byte or truncated**: that is a failed
write, not a performance, and it is regenerated with `build_audio.py --force --key` (the tool
already distrusts a file too short to have spoken its text). It is not a "noise" report.

**1. Measure against controls.** The suspect is probably not corrupt, and saying so with numbers
is useful:

```sh
ffmpeg -hide_banner -nostats -i media/<key>-<part>.mp3 \
  -af astats=metadata=1:reset=0 -f null - 2>&1 | grep -E "Peak level|RMS level|DC offset"
```

Peak, RMS, DC offset, 10 ms spikes and dropouts, and lead-in noise floor, compared with a few
clips nobody complained about. "Inside the control range" rules out corruption and clipping.
It does **not** mean nothing is wrong, and it does not mean "bad take, rebuild it".

**2. Show the reporter why a rebuild would not help** (optional, only when asked). Synthesize the
same text twice into a scratch directory and compare **duration and speech onset, not bytes**:

```sh
mkdir -p /tmp/det
.venv/bin/python - <<'PY'
import asyncio, edge_tts
text = "She washes her hands before dinner."
async def main():
    for n in (1, 2):
        await edge_tts.Communicate(text, "en-US-AvaNeural", rate="-10%").save(f"/tmp/det/take{n}.mp3")
asyncio.run(main())
PY
ffprobe -v error -show_entries format=duration -of csv=p=0 /tmp/det/take1.mp3
```

Identical duration and onset are the **same performance with different dither**. Never write this
test over `media/`: the shipped clip is not the problem, and a forced re-render only replaces a
reported take with an identical one.

**3. Write a reword set and let the reporter choose.** Same voice, same rate, same pitch — the only
variable is the text. Keep the failing clip as the reference and offer two or three rewordings:

```sh
mkdir -p /tmp/v
cp media/<key>-<part>.mp3 /tmp/v/A-as-shipped.mp3
.venv/bin/python - <<'PY'
import asyncio, edge_tts
variants = {
    "B-reorder": "Before dinner, she washes her hands.",
    "C-swap":    "She washes her hands before supper.",
}
async def main():
    for name, text in variants.items():
        await edge_tts.Communicate(text, "en-US-AvaNeural", rate="-10%").save(f"/tmp/v/{name}.mp3")
asyncio.run(main())
PY
```

Aim at the defect: a buzz between two words points at that junction, so reordering or inserting a
word there (`"to drivers"` → `"to every driver"`) is the targeted move. Prefer the smallest edit
that keeps the meaning and the target intact — a reorder before a rewrite, a single word before a
new sentence. Every candidate keeps the target **in the entry's own form** and keeps the
collocation's particle, since that is what the card teaches.

One round trip with a labelled set beats five rounds of "still noisy", and the verdict is the
reporter's: never claim an audio fix verified on your own authority.

**4. Fix the source, not the artifact.** Once a clean rewording exists, put it in `src/<kind>.json`
and re-render the entry's clips. Never hand-edit an mp3; a post-processed file is not reproducible
from the repo.

```sh
.venv/bin/python tools/build_audio.py --force --key col_d1e334e5     # 7 clips
```

Without `--key` this re-synthesizes the **whole kind** — 4,464 collocation clips to repair one.

**Then write both halves into the live Anki collection.** This is part of the fix, not a
follow-up, and neither half is done by re-importing the package:

```sh
scripts/install-entry.py col_d1e334e5     # clips + note text + drift check; Anki must be quit
```

It installs every clip of the entry, writes the note's text fields, then runs the drift check,
so a half-landed fix fails there instead of reaching the reporter. It is idempotent by design:
a take-only fix leaves the text write with nothing to do, and a wording-only fix copies clips
whose bytes already match. The pieces, when one half is all you need:

```sh
scripts/install-anki-media.py --all col_d1e334e5             # every clip of the entry
scripts/install-anki-media.py col_d1e334e5-present-example   # one clip
scripts/install-anki-note.py col_d1e334e5                    # text fields only
scripts/check-collection.py --key col_d1e334e5               # read-only drift check
```

Why the import does not work for the **clips**, learned the hard way:

- Anki resolves media by **name** against `collection.media.db2`, and the package importer
  skips every name that index still knows. `media/` being right and the package carrying the
  new bytes is not enough.
- Deleting the file is worse. The name stays in the index; the next `Check Media` marks the row
  a tombstone (`csum NULL, mtime 0`) and the importer skips it forever, while the card reports
  a missing file. That is a dead end, not a step.
- So the clip is **copied straight in** and the index row rewritten to match (sha1, mtime,
  `dirty=1`). No import is involved, and a synced collection uploads the new bytes.

The script refuses to run while Anki is open (Anki rewrites the folder and the index on exit),
finds the profile, and is safe to re-run.

**The text is the second half, and it has the same kind of trap.** A package import also writes
it, but only at *Update notes: Always*: at *If newer* it applies nothing, because `BUILD_MOD` is
a fixed constant and the incoming `mod` equals the one already stored, so Anki skips every note
in silence. That is exactly how #1 and #2 ended up playing the new sentence while displaying
the old one. So the text is written directly — text fields only, media fields, note id and
review history untouched — and an import at *If newer* is never a way to land a reword.

`check-collection.py` compares the live note text and tags with `src/` by GUID and exits 1 on
drift. It cannot write, so a red result is either an unfinished fix or the hand-back: name the
script, or the package and the two dialog settings, and the one card to read.

A rewording is the only lever a clip fix has. `VOICE_FEMALE` and `RATE` are project-wide:
changing one of them to patch a single clip re-renders every card in all three decks, so it is
never the fix — it is its own decision, made deliberately and never in response to one noisy
clip.

## 5. Checkpoint the plan

For anything beyond a one-word reword, state it before editing:

> #1: Ava buzzes on "She washes her hands before dinner." — a vocoder artefact, not the take or
> the codec; three rewordings read clean. Plan: use "Before dinner, she **washes her hands**.",
> re-render `--key col_d1e334e5`, lint, build.

## 6. Branch

```sh
gh issue develop <n> --checkout        # linked branch, so the issue timeline shows the work
```

Fallback: `git switch -c fix/<n>-<slug> origin/main`. Never commit onto `main`.

## 7. Implement

The rules that decide whether a change is acceptable:

- **Manifest first.** `src/index.csv` is the reviewed plan, one row per sense. A new card needs
  its row before the entry; an existing card's wording fix does not.
- **Identity is sacred.** A note's GUID is kind prefix + `phrase` + `sense`, and the media key
  is a hash of the same two. Changing **`phrase` or `sense`** creates a new note and orphans
  review history and every clip. Changing a definition or an example does not — so prefer
  rewording those over renaming the thing.
- **Every authored example bolds the target** with one `**…**` pair (two when a phrasal verb
  splits), and shows the target **in the entry's own form** — the base form on the front.
- **A verb needs four form examples**, and a non-verb must not carry those keys.
- **An audio defect is fixed in the text.** Reword the field the clip speaks (`definition` or the
  offending example) and re-render that entry; never change `VOICE_FEMALE`, `RATE` or the encoder
  to get around one bad clip.
- **`image_brief` derives from the definition, never the example.** Swapping an example never
  justifies editing a brief; changing the definition or the sense does.
- **Levels are enforced**: A1–C1 for vocabulary, A1–B2 for phrasal verbs and collocations. No
  C2 anywhere. Exactly one `level::` tag, at least one known `category::` tag.
- **Content only on demand.** Never seed a placeholder card, a starter list, or a "test" entry
  to exercise the pipeline.
- **Never hand-edit an `.apkg`** and never change a model id to make fields fit; field-list
  changes need a new model generation and are a schema decision, not a fix.
- Content wording is authored inline. The rules for US English, GA IPA, register and pt-BR
  interference are in `.opencode/agents/american-english-teacher.md`; do not delegate to
  another model.

## 8. Verify

```sh
.venv/bin/python tools/lint_content.py --report      # manifest + source agreement, repetition
.venv/bin/python tools/build_decks.py --notes        # 5,500 / 350 / 800 notes
```

Expect `clean: 0 warning(s)` and those three counts. The lint catches a bad kind, part of
speech, category, level, sense slug, duplicate `kind + phrase + sense`, a source entry missing
from the manifest, unbolded targets, verb rows on a non-verb, bad IPA, and a missing Midjourney
parameter block — so a green lint is a real signal, not a formality (there is no CI or
pre-commit hook to catch what you skip).

`--report` prints the most repeated example openers, image-brief openers and camera angles;
read it when the issue is "every card sounds the same".

**Audio is not validated by the lint.** After any `build_audio.py` run, check the clip exists
and plays, that `find-entry.py` no longer reports `MISSING`, and that `install-entry.py` put
both halves in (section 4).

**Neither the build nor the lint sees the collection.** `check-collection.py` is the only check
that compares the live note text and tags with `src/`, and `install-entry.py` ends with it;
expect `collection matches src/`.

## 8b. When the fix produces no committable diff

`media/` mp3s are **gitignored**, and `decks/*.apkg` is build output. So a perfectly real fix —
a regenerated clip, a rebuilt package — leaves `git status` empty. Check before committing:

```sh
git status --short
```

If nothing is staged-able, do not invent a change to justify a PR and do not open an empty one.
Report the local action instead: what you regenerated, how you verified it, and that a rebuild
from source reproduces it. If the *tool* could not do what the issue needed, that tool change
**is** the committable fix.

## 9. Commit

Conventional commits, matching the log (`git log --oneline -15`): `fix(content):`,
`feat(tools):`, `chore(tools):`, `docs:` … Stage specific files, never `git add -A`.

```sh
git commit -F - <<'EOF'
fix(content): reword the present example for "wash your hands"

Ava renders a buzz on "She washes her hands before dinner." … three rewordings
read clean; chose the reordering because it keeps every word and the target form.

Closes #1
EOF
```

## 10. Open the pull request

```sh
git push -u origin HEAD
gh pr create --base main --title "…" --body-file - <<'EOF'
## Summary
## Changes
## Testing
EOF
```

- **`Closes #n`** when the PR resolves the issue on merge.
- **`Refs #n`** when the PR is necessary but not sufficient — a tool that makes the repair
  possible, or a fix the reporter still has to confirm by ear. Auto-closing then hides an open
  problem behind a merged PR.
- Say in the body that audio is **not** in the diff when it is not, and that `build_audio.py`
  regenerates it from source.

Never force-push a shared branch, and never close or relabel the issue by hand.

## 11. Report

Give the issue number, the one-sentence cause, the layer that was at fault, the files changed,
the exact commands run and their results, and the PR URL. Say what is still the reporter's to
confirm — usually a listen — and how to hear it.

## Guardrails

- **Audio is fixed by rewording, always.** A buzz, a robotic stretch or a swallowed word is the
  voice reading that exact string, and the same performance comes back on every rebuild. Reword
  the sentence, re-render `--key`, install both halves. Never change the voice or the rate, never
  hand back "try a different voice", and never close a report on a rebuild alone.
- **A rebuilt clip is not fixed until it is installed in the collection.** Anki resolves media
  by name through `collection.media.db2`, so re-importing a package never replaces a clip, and
  deleting the file turns its index row into a tombstone the importer then skips forever. Every
  regenerated clip is installed in the same run, with Anki quit — `install-entry.py <key>` does
  the clips and the text together. Never hand this back as advice without doing it, and never
  claim a clip is fixed when only `media/` changed.
- **A reword moves two artifacts, and both are installed in one step.** `install-entry.py <key>`
  copies the clips and writes the note text, then verifies the collection. Installing one half
  is exactly the bug in #1 and #2: the card played the new sentence while showing the old one.
  Never close a fix with `check-collection.py` red.
- **`media/` is one gitignored tree shared by every branch.** Switch branches and the mp3s on
  disk no longer match the source; `find-entry.py` will show a clip whose text disagrees with the
  entry. Re-run `build_audio.py --key …` after checking out the branch that holds the text.
- **Audio is not optional, illustrations are.** A missing mp3 imports silently as a silent card;
  the build asserts every clip. A missing image is a warning and a card without a picture.
- **Model ids are on their seventh generation.** Dropping or adding a field means a new id, new
  notes, and lost history — escalate instead of "just adding a field".
- **Targets are planning numbers, not assertions.** A build reports progress (`notes=120/5500`);
  never pad a deck to hit one.
- **One model only.** No `model` override on subagents, and do not call `claude-headless`,
  `claude-plan-creator`, `claude-plan-validator`, `java-legacy-architect` or browser/computer-use
  tools.
