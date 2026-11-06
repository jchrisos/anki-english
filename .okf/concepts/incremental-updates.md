---
type: policy
title: "Incremental deck updates that keep review progress"
description: "How re-importing rebuilt .apkg files updates notes in place so scheduling and review history survive, and which changes silently destroy them."
status: active
verified:
  - by: "OpenCode session"
    at: "2026-11-05"
sources:
  - uri: "https://docs.ankiweb.net/importing/packaged-decks.html"
    credibility: high
  - uri: "https://docs.ankiweb.net/exporting.html"
    credibility: high
  - uri: "file:///Users/julio/Projects/anki-english/AGENTS.md"
    credibility: high
stale_after: "2027-05-05"
---

# Incremental deck updates that keep review progress

The deck is meant to grow: new words are added, definitions and quotes get better, and the
user keeps studying. Re-importing a rebuilt package must therefore **update the existing
notes in place**, never replace them. Anki does this — but only if identity is stable.

## What Anki actually does on import

- **Notes are matched by GUID.** The note id is not used for matching. A GUID already in
  the collection is treated as an edit of that note: its **cards and review log stay**, its
  fields are replaced.
- **The newer version wins by default.** Since 23.10 the import dialog can override this
  with *Update notes: Always / If newer / Never*, and note types can be merged.
- **Decks are matched by name.** A deck name that does not exist yet becomes a new deck.
- **Note types are matched by id.** If the field list changed, existing notes are not
  updated ("this updating process is generally not possible if the note type is changed").
- **Import only adds and updates.** A note that is absent from the package is not deleted
  from the collection.
- **A `.colpkg` replaces the entire collection**, review history included. Import `.apkg`
  only.

## Rules the generator must never break

1. **GUID = kind prefix + normalized phrase + an explicit sense key slug**
   (`voc:have:eat-or-drink`). The sense key is authored data, never derived from the
   definition text: editing a definition must not change the identity, or every reworded
   card becomes a new note with no history. Never derive a GUID from a row index, the file
   path, `hash()`, or a timestamp.
2. **Deck name, deck id, model id and the field list are frozen.** A renamed deck is a new
   deck; a changed field list means Anki stops updating the old notes.
3. **Generation is a full rebuild; the merge happens inside Anki.** Do not delete and
   re-create notes to "refresh" them, and do not try to ship deltas — a rebuilt package
   with stable GUIDs is the incremental mechanism.
4. **Media filenames derive from the same key** (`<key>.jpg`, `<key>-word.mp3`,
   `<key>-explanation.mp3`, `<key>-dialog.mp3`) and are never renamed. Renaming orphans the
   old file and, worse, is a visible symptom of identity churn.
5. **A note never changes kind in place.** Moving `give up` from phrasal verb to
   collocation is a new model and a new GUID — a new note. If that is ever needed, move the
   card between note types in Anki instead.
6. **Removing an entry from the source does not remove the card.** Import never deletes, so
   a dropped entry keeps its history and simply stops being updated. Deleting it in Anki is
   a deliberate, irreversible loss of progress; prefer leaving it.

## Import checklist (Anki 25.09 on this machine)

1. Import the `.apkg`, never a `.colpkg`.
2. Leave **"Import any learning progress"** unticked — our packages carry no scheduling, and
   ticking it only invites surprises from other packages.
3. Set **Update notes: Always** when the generator is the source of truth, or *If newer*
   if you sometimes hand-edit cards in Anki and want those edits to survive. *Never* keeps
   local edits but freezes card content forever.
4. After the first update of a real deck, open a card's **Info** and confirm the review
   count and interval are unchanged.

## What still loses progress

Deleting a deck or note, changing a note type, reclassifying an entry's kind, importing a
`.colpkg`, restoring a backup older than the reviews, or "cleaning up" duplicate notes by
deleting one of them. These are all outside the generator's control; the rules above exist
to make sure the generator never becomes one of them.

## Verification

- GUIDs are deterministic: rebuilding from unchanged source produces the same GUID set.
- GUIDs are unique within a package (duplicates in one file mean only one of them can ever
  be updated on the next import).
- When a rebuild drops a key that the previous build had, report it — that is either an
  intentional retirement or an accidental identity change, and the two need different
  answers.
