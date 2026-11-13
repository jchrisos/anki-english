# anki-english

Anki flashcard decks (`.apkg`) for English study, built from plain JSON: **vocabulary**,
**phrasal verbs** and **collocations**.

Every card carries General American IPA, a part of speech, a CEFR level, a one-line definition,
an authored example with the target in **bold**, three audio clips (word, explanation, example)
and a set of `category::` tags. A **verb** card adds one example sentence per form — present,
present participle, past, past participle — each shown and spoken on its own row. An
illustration is included when the entry's image file exists.

The decks build locally into `decks/` and, audio included, are ready to import into Anki.
Neither the `.apkg` files nor the mp3s are committed — both are build artifacts — so a clone
rebuilds them with `tools/build_audio.py` and then `tools/build_decks.py --notes`. Images are
the one piece still missing: I'm publishing this for my own study, so illustrations are a low
priority rather than a blocker.

## Status

All three decks are complete: **vocabulary 5,500** (A1–C1), **phrasal verbs 350** (A1–B2) and
**collocations 800** (A1–B2) — 6,650 cards, each with its three clips plus four per verb form.
The cards are text and audio only until illustrations are rendered. Content is added only on
explicit request.

## Quick start

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt       # genanki 0.13.1, edge-tts 7.3.1

.venv/bin/python tools/build_audio.py           # mp3s into media/ (gitignored, skips existing)
.venv/bin/python tools/build_decks.py --notes   # decks/*.apkg
```

`--only vocabulary|phrasal-verbs|collocations` restricts any step to one deck. Add `--test` to
work in the gitignored `tests/` tree instead of production. Without `--notes` the build only
writes empty baseline packages that pin the ids.

## Importing into Anki

There is no Anki CLI and no AnkiConnect here, so import by hand:

1. **File → Import**, choose the `.apkg`.
2. **Import any learning progress**: unticked (the packages carry no scheduling).
3. **Update notes**: *Always* — the JSON is the source of truth.
4. **Update note types**: *If newer* or *Always*; *Never* silently strands a collection on an
   old template.

Re-importing updates notes **in place** by GUID, keeping their cards and review history.

## Where to look next

- `AGENTS.md` — how the build works: source schema and field mapping, the manifest-first
  content workflow, lint and validation rules, authoring conventions, Anki pitfalls.
- `.okf/` — design rationale and the decision log (start at `.okf/index.md`).
