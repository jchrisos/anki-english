#!/usr/bin/env python3
"""Build the three anki-english deck packages.

Each package contains exactly one deck and one note type, and **no notes** — this is the
baseline that puts the pinned deck ids, deck names and note-type ids into the collection
before any content exists. Re-importing a later build updates those same objects instead
of creating parallel ones.

Ids are pinned constants from `.okf/concepts/deck-schema.md`. Never derive them at runtime
and never let them drift: a new id means a duplicate deck or note type in Anki.
"""

from __future__ import annotations

import sys
from pathlib import Path

import genanki

# Fixed so repeated builds of unchanged input are equivalent (no wall-clock ids/timestamps).
BUILD_TIMESTAMP = 1730000000

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "decks"

CSS = """\
.card {
  font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
  font-size: 20px;
  text-align: center;
  color: #1a1a1a;
  background: #fdfdfd;
}
.headword { font-size: 34px; font-weight: 600; }
.pronunciation { color: #666; font-size: 18px; margin: 6px 0 14px; }
.definition { margin: 0 auto 16px; max-width: 34em; }
.image img { max-width: 100%; max-height: 320px; border-radius: 8px; }
.dialog { font-style: italic; margin-top: 16px; }
.source { color: #777; font-size: 15px; }
.audio { margin-top: 10px; }
"""

FRONT_TEMPLATE = '<div class="headword">{{%(headword)s}}</div>\n'

BACK_TEMPLATE = """\
{{FrontSide}}
<hr id="answer">
<div class="pronunciation">{{Pronunciation}}</div>
<div class="definition">{{Definition}}</div>
<div class="image"><img src="{{Image}}"></div>
<div class="dialog">{{Dialog}}</div>
<div class="source">{{Source}}</div>
<div class="audio">{{Audio}}</div>
"""

KINDS = (
    {
        "slug": "vocabulary",
        "deck_id": 517813484872,
        "deck_name": "Vocabulary",
        "model_id": 104320564501,
        "model_name": "English Vocabulary",
        "headword": "Word",
    },
    {
        "slug": "phrasal-verbs",
        "deck_id": 807523115129,
        "deck_name": "Phrasal Verbs",
        "model_id": 1030950240795,
        "model_name": "English Phrasal Verb",
        "headword": "Phrase",
    },
    {
        "slug": "collocations",
        "deck_id": 221110591407,
        "deck_name": "Collocations",
        "model_id": 834857214829,
        "model_name": "English Collocation",
        "headword": "Phrase",
    },
)


def build_model(kind: dict) -> genanki.Model:
    headword = kind["headword"]
    return genanki.Model(
        kind["model_id"],
        kind["model_name"],
        fields=[
            {"name": headword},
            {"name": "Pronunciation"},
            {"name": "Definition"},
            {"name": "Image"},
            {"name": "Dialog"},
            {"name": "Source"},
            {"name": "Audio"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": FRONT_TEMPLATE % {"headword": headword},
                "afmt": BACK_TEMPLATE,
            }
        ],
        css=CSS,
    )


def build(kind: dict) -> Path:
    deck = genanki.Deck(kind["deck_id"], kind["deck_name"])
    # Attach the note type explicitly: with no notes, the model would not be written and
    # the import would create a deck without a note type.
    deck.add_model(build_model(kind))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{kind['slug']}.apkg"
    genanki.Package(deck).write_to_file(str(path), timestamp=BUILD_TIMESTAMP)
    return path


def main() -> int:
    for kind in KINDS:
        path = build(kind)
        print(f"{path.relative_to(path.parent.parent)}  deck={kind['deck_name']!r} "
              f"deck_id={kind['deck_id']} model_id={kind['model_id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
