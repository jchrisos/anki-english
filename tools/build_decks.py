#!/usr/bin/env python3
"""Build the anki-english deck packages.

Each package contains exactly one deck and one note type. By default it also contains **no
notes**: that is the baseline which puts the pinned deck ids, deck names and note-type ids
into the collection before any content exists, and re-importing a later build updates those
same objects instead of creating parallel ones.

Content from `src/<kind>.json` is included only with `--notes`. Content is added on demand,
so a plain build must never quietly ship entries.

Every note is validated before the package is written: all text fields present, exactly one
CEFR level, at least one known category, and both its image and its mp3 on disk. A note
missing any of them is a build failure, not a card with a blank panel.

Production output goes to `decks/` and is committed. Test output goes to `tests/decks/`,
which is gitignored together with the rest of `tests/`: test builds read `tests/src/` and
`tests/media/`, so no test artifact ever mixes with production.

Test builds are fully isolated: they use their own pinned deck ids and model ids, their own
deck/model names (suffixed `(test)`) and their own filenames (`<kind>-test.apkg`). Anki
matches decks by **name**, note types by **id** and notes by **GUID**, so all three have to
differ — a test package that reused any one of them would merge into the real deck.

Ids are pinned constants from `.okf/concepts/deck-schema.md`. Never derive them at runtime
and never let them drift: a new id means a duplicate deck or note type in Anki.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

import genanki

from deck_common import (
    ALLOWED_CATEGORIES,
    ALLOWED_POS,
    AUDIO_PARTS,
    GUID_PREFIX,
    LEVELS,
    REPO_ROOT,
    REQUIRED_TEXT_FIELDS,
    SPEAKER_GENDERS,
    TEST_GUID_PREFIX,
    Layout,
    audio_file,
    image_file,
    layout,
    load_entries,
    media_key,
)

# Fixed so repeated builds of unchanged input are equivalent (no wall-clock ids/timestamps).
#
# This is also the note type's `mod`, and Anki's apkg importer updates an existing note type
# only when the incoming mod is **newer** (`update_notetypes = if_newer`). So: raise this
# value whenever the fields, templates or CSS change, or the new template never reaches a
# collection that already has the note type — which is how a stale `<img src="{{Image}}">`
# template survived a re-import and rendered the image tag as literal text.
BUILD_MOD = 1794700000

CSS = """\
.card {
  font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
  font-size: 20px;
  text-align: center;
  color: #1a1a1a;
  background: #fdfdfd;
}
.headword { font-size: 34px; font-weight: 600; }
.pronunciation { color: #666; font-size: 18px; margin: 6px 0 2px; }
.pos { color: #777; font-size: 15px; font-style: italic; margin: 0 0 4px; }
.pos:empty { display: none; }
.meta { margin: 0 0 12px; }
.level {
  display: inline-block;
  padding: 2px 10px 3px;
  border-radius: 10px;
  background: #eef1f5;
  color: #445;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: .06em;
  text-transform: uppercase;
}
.definition { margin: 0 auto 16px; max-width: 34em; }
.image img { max-width: 100%; max-height: 320px; border-radius: 8px; }
.dialog { font-style: italic; margin-top: 16px; }
.source { color: #777; font-size: 15px; }
.audio { margin: 6px 0 12px; }
"""

FRONT_TEMPLATE = '<div class="headword">{{%(headword)s}}</div>\n'

BACK_TEMPLATE = """\
{{FrontSide}}
<hr id="answer">
<div class="pronunciation">{{Pronunciation}}</div>
<div class="pos" id="pos"></div>
<div class="meta"><span class="level" id="level"></span></div>
<div class="audio">{{Audio}}</div>
<hr>
<div class="definition">{{Definition}}</div>
<div class="audio">{{AudioExplanation}}</div>
<hr>
<div class="image">{{Image}}</div>
<div class="dialog">{{Dialog}}</div>
<div class="source">{{Source}}</div>
<div class="audio">{{AudioDialog}}</div>
<script>
// Part of speech and CEFR level are tags, not fields, so they are extracted at render time.
// Tags arrive space-separated and the vocabulary is controlled (`level::a2`, `pos::verb`),
// so no escaping is needed.
(function () {
  var tags = "{{Tags}}".split(" ");
  var level = "";
  var pos = "";
  for (var i = 0; i < tags.length; i++) {
    if (tags[i].indexOf("level::") === 0) {
      level = tags[i].slice(7);
    } else if (tags[i].indexOf("pos::") === 0) {
      pos = tags[i].slice(5);
    }
  }
  document.getElementById("level").textContent = level;
  document.getElementById("pos").textContent = pos;
})();
</script>
"""

KINDS = (
    {
        "slug": "vocabulary",
        "deck_id": 517813484872,
        "deck_name": "Vocabulary",
        "model_id": 552622157608,
        "model_name": "English Vocabulary",
        "headword": "Word",
        "test_deck_id": 804850451889,
        "test_model_id": 817309927966,
    },
    {
        "slug": "phrasal-verbs",
        "deck_id": 807523115129,
        "deck_name": "Phrasal Verbs",
        "model_id": 726156055118,
        "model_name": "English Phrasal Verb",
        "headword": "Phrase",
        "test_deck_id": 567855487385,
        "test_model_id": 618605022273,
    },
    {
        "slug": "collocations",
        "deck_id": 221110591407,
        "deck_name": "Collocations",
        "model_id": 889236578191,
        "model_name": "English Collocation",
        "headword": "Phrase",
        "test_deck_id": 242142671948,
        "test_model_id": 499896888196,
    },
)

# Appended to both the deck and the model name of a test build. Different names, not just
# different ids: Anki looks a deck up by name, so a matching name would still merge.
TEST_NAME_SUFFIX = " (test)"


def variant(kind: dict, test: bool) -> dict:
    """Resolve the deck/model identity and filename for a production or test build."""
    if not test:
        return {
            "deck_id": kind["deck_id"],
            "deck_name": kind["deck_name"],
            "model_id": kind["model_id"],
            "model_name": kind["model_name"],
            "filename": f"{kind['slug']}.apkg",
        }
    return {
        "deck_id": kind["test_deck_id"],
        "deck_name": f"{kind['deck_name']}{TEST_NAME_SUFFIX}",
        "model_id": kind["test_model_id"],
        "model_name": f"{kind['model_name']}{TEST_NAME_SUFFIX}",
        "filename": f"{kind['slug']}-test.apkg",
    }


def build_model(kind: dict, ident: dict) -> genanki.Model:
    headword = kind["headword"]
    return genanki.Model(
        ident["model_id"],
        ident["model_name"],
        fields=[
            {"name": headword},
            {"name": "Pronunciation"},
            {"name": "Definition"},
            {"name": "Image"},
            {"name": "Dialog"},
            {"name": "Source"},
            # `Audio` is the word clip: the name predates the split, and renaming a field is
            # destructive, so the two new parts were appended instead.
            {"name": "Audio"},
            {"name": "AudioExplanation"},
            {"name": "AudioDialog"},
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


class BuildError(Exception):
    """A note that must not reach a package: missing field, bad tag, missing media."""


def validate(entry: dict, key: str, seen: set[str], slug: str, lay: Layout) -> None:
    """Reject an entry instead of emitting a card with a blank panel.

    Missing media is the failure that does not announce itself: Anki imports the note and
    renders an empty image or a silent card, so both files are asserted here.
    """
    label = f"{entry.get('phrase', '?')} ({key})"
    for field in REQUIRED_TEXT_FIELDS:
        if not str(entry.get(field, "")).strip():
            raise BuildError(f"{label}: empty {field}")
    if not entry["pronunciation"].startswith("/") or not entry["pronunciation"].endswith("/"):
        raise BuildError(f"{label}: pronunciation must be IPA in slashes")
    level = entry.get("level")
    if level not in LEVELS:
        raise BuildError(f"{label}: level must be one of {', '.join(LEVELS)}, got {level!r}")
    pos = entry.get("pos")
    if pos is None:
        # Vocabulary cards are the ones where the word class is not obvious from the deck.
        if slug == "vocabulary":
            raise BuildError(f"{label}: vocabulary needs a part of speech (pos)")
    elif pos not in ALLOWED_POS:
        raise BuildError(f"{label}: unknown part of speech {pos!r}")
    gender = entry.get("speaker_gender")
    if gender not in SPEAKER_GENDERS:
        raise BuildError(
            f"{label}: speaker_gender must be one of {', '.join(SPEAKER_GENDERS)}, got {gender!r}"
        )
    categories = entry.get("categories") or []
    if not categories:
        raise BuildError(f"{label}: needs at least one category")
    unknown = [c for c in categories if c not in ALLOWED_CATEGORIES]
    if unknown:
        raise BuildError(f"{label}: unknown categories {unknown}")
    if entry["phrase"] in seen:
        raise BuildError(f"{label}: duplicate phrase within the kind")
    seen.add(entry["phrase"])
    for path in [image_file(lay, key)] + [audio_file(lay, key, p) for p in AUDIO_PARTS]:
        if not path.exists():
            raise BuildError(f"{label}: missing media file {path.name}")


def make_note(
    kind: dict, model: genanki.Model, entry: dict, test: bool, lay: Layout
) -> genanki.Note:
    prefix = GUID_PREFIX[kind["slug"]]
    key = media_key(prefix, entry)
    # Authored sense slug, never the definition text: rewording a definition must not
    # strand a card's review history on a new note.
    guid = f"{prefix}:{entry['phrase']}:{entry['sense']}"
    if test:
        guid = TEST_GUID_PREFIX + guid
    return genanki.Note(
        model=model,
        fields=[
            entry["phrase"],
            entry["pronunciation"],
            entry["definition"],
            # The field carries the whole tag, not a bare filename. Anki's importer only
            # copies media that it can see referenced in the field text (`<img src>` and
            # `[sound:]`), so a filename the template wrapped later is silently skipped.
            f'<img src="{image_file(lay, key).name}">',
            entry["dialog"],
            entry["source"],
            # Each clip lives in its own field so the template can place it directly under
            # the text it reads, instead of stacking three players at the bottom.
            f"[sound:{audio_file(lay, key, 'word').name}]",
            f"[sound:{audio_file(lay, key, 'explanation').name}]",
            f"[sound:{audio_file(lay, key, 'dialog').name}]",
        ],
        tags=[f"category::{c}" for c in entry["categories"]]
        + [f"level::{entry['level']}"]
        + ([f"pos::{entry['pos']}"] if entry.get("pos") else []),
        guid=guid,
    )


def build(kind: dict, test: bool, notes: bool) -> tuple[Path, dict, int]:
    ident = variant(kind, test)
    lay = layout(test)
    deck = genanki.Deck(ident["deck_id"], ident["deck_name"])
    model = build_model(kind, ident)
    # Attach the note type explicitly: with no notes, the model would not be written and
    # the import would create a deck without a note type.
    deck.add_model(model)

    media: list[Path] = []
    entries = load_entries(lay, kind["slug"]) if notes else []
    seen: set[str] = set()
    for entry in entries:
        key = media_key(GUID_PREFIX[kind["slug"]], entry)
        validate(entry, key, seen, kind["slug"], lay)
        deck.add_note(make_note(kind, model, entry, test, lay))
        media.extend([image_file(lay, key), *(audio_file(lay, key, p) for p in AUDIO_PARTS)])

    lay.out.mkdir(parents=True, exist_ok=True)
    path = lay.out / ident["filename"]
    genanki.Package(deck, media_files=[str(p) for p in media]).write_to_file(
        str(path), timestamp=BUILD_MOD
    )
    _make_zip_hermetic(path)
    return path, ident, len(entries)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--test",
        action="store_true",
        help="build from tests/src + tests/media into tests/decks (all gitignored)",
    )
    parser.add_argument(
        "--notes",
        action="store_true",
        help="include the entries in src/<kind>.json (content is on demand only)",
    )
    parser.add_argument(
        "--only",
        choices=[kind["slug"] for kind in KINDS],
        help="build a single kind instead of all three",
    )
    args = parser.parse_args()

    kinds = [kind for kind in KINDS if args.only in (None, kind["slug"])]

    for kind in kinds:
        try:
            path, ident, count = build(kind, args.test, args.notes)
        except (BuildError, FileNotFoundError) as exc:
            print(f"error: {kind['slug']}: {exc}", file=sys.stderr)
            return 1
        print(
            f"{path.relative_to(REPO_ROOT)}  notes={count}  deck={ident['deck_name']!r} "
            f"deck_id={ident['deck_id']} model_id={ident['model_id']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
