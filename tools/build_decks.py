#!/usr/bin/env python3
"""Build the anki-english deck packages.

Each package contains exactly one deck and one note type, and **no notes** — this is the
baseline that puts the pinned deck ids, deck names and note-type ids into the collection
before any content exists. Re-importing a later build updates those same objects instead
of creating parallel ones.

Production output goes to `decks/` and is committed. Test output goes to `decks/tests/`,
which is gitignored: it is for rehearsing an import (or a new batch) without committing a
package. Test packages carry the same pinned ids and names as production, so importing one
touches the real deck — use a temporary Anki profile for a dry run.

Ids are pinned constants from `.okf/concepts/deck-schema.md`. Never derive them at runtime
and never let them drift: a new id means a duplicate deck or note type in Anki.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

import genanki

# Fixed so repeated builds of unchanged input are equivalent (no wall-clock ids/timestamps).
BUILD_TIMESTAMP = 1730000000

REPO_ROOT = Path(__file__).resolve().parent.parent
DECKS_DIR = REPO_ROOT / "decks"
TEST_DIR = DECKS_DIR / "tests"

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


def _make_zip_hermetic(path: Path) -> None:
    """Rewrite the package with fixed zip metadata.

    genanki stamps zip entries with the build machine's clock, so two builds of identical
    input differ byte for byte. Pinning the entry timestamps makes the rebuild a no-op in
    git, which is what "same input, same output" has to mean for a committed artifact.
    """
    with zipfile.ZipFile(path) as src:
        entries = [(info.filename, src.read(info.filename)) for info in src.infolist()]

    tmp = path.with_suffix(".tmp")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as out:
        for name, data in entries:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            out.writestr(info, data)
    tmp.replace(path)


def build(kind: dict, out_dir: Path) -> Path:
    deck = genanki.Deck(kind["deck_id"], kind["deck_name"])
    # Attach the note type explicitly: with no notes, the model would not be written and
    # the import would create a deck without a note type.
    deck.add_model(build_model(kind))

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{kind['slug']}.apkg"
    genanki.Package(deck).write_to_file(str(path), timestamp=BUILD_TIMESTAMP)
    _make_zip_hermetic(path)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--test",
        action="store_true",
        help="write to decks/tests/ (gitignored) instead of decks/",
    )
    parser.add_argument(
        "--only",
        choices=[kind["slug"] for kind in KINDS],
        help="build a single kind instead of all three",
    )
    args = parser.parse_args()

    out_dir = TEST_DIR if args.test else DECKS_DIR
    kinds = [kind for kind in KINDS if args.only in (None, kind["slug"])]

    for kind in kinds:
        path = build(kind, out_dir)
        print(
            f"{path.relative_to(REPO_ROOT)}  deck={kind['deck_name']!r} "
            f"deck_id={kind['deck_id']} model_id={kind['model_id']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
