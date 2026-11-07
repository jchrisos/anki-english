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
    GUID_PREFIX,
    LEVELS,
    REPO_ROOT,
    REQUIRED_TEXT_FIELDS,
    SPEAKER_GENDERS,
    TEST_GUID_PREFIX,
    VERB_AUDIO_PARTS,
    VERB_TEXT_KEYS,
    Layout,
    audio_file,
    audio_parts,
    image_file,
    is_verb,
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
BUILD_MOD = 1796100000

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
.block-label {
  display: block;
  color: #777;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: .06em;
  text-transform: uppercase;
  margin: 0 0 2px;
}
.row { display: flex; align-items: center; justify-content: center; gap: 10px; margin: 0 auto 10px; max-width: 34em; }
.row-text { flex: 0 1 auto; min-width: 0; }
.row-audio { flex: 0 0 auto; }
"""

FRONT_TEMPLATE = '<div class="headword">{{%(headword)s}}</div>\n'

# One authored example per form, appended after the movie quote. The labels name the form the
# sentence demonstrates; they are the only example rows on a card that are not quotes, and the
# label keeps that visible. A non-verb note leaves the fields empty, so the `{{#...}}` sections
# render nothing at all — no empty rows, no stray dividers.
EXAMPLE_BLOCKS = """\
{{#PresentExample}}
<hr>
<div class="row">
  <div class="row-text">
    <div class="block-label">Present</div>
    <div class="dialog">{{PresentExample}}</div>
  </div>
  <div class="row-audio">{{AudioPresentExample}}</div>
</div>
{{/PresentExample}}
{{#PastSimpleExample}}
<hr>
<div class="row">
  <div class="row-text">
    <div class="block-label">Past</div>
    <div class="dialog">{{PastSimpleExample}}</div>
  </div>
  <div class="row-audio">{{AudioPastSimpleExample}}</div>
</div>
{{/PastSimpleExample}}
{{#PastParticipleExample}}
<hr>
<div class="row">
  <div class="row-text">
    <div class="block-label">Past participle</div>
    <div class="dialog">{{PastParticipleExample}}</div>
  </div>
  <div class="row-audio">{{AudioPastParticipleExample}}</div>
</div>
{{/PastParticipleExample}}
"""

BACK_TEMPLATE = """\
<div class="row">
  <div class="row-text">
    <div class="headword">{{%(headword)s}}</div>
    <div class="pronunciation">{{Pronunciation}}</div>
    <div class="pos" id="pos"></div>
    <div class="meta"><span class="level" id="level"></span></div>
  </div>
  <div class="row-audio">{{Audio}}</div>
</div>
<hr id="answer">
<div class="row">
  <div class="row-text"><div class="definition">{{Definition}}</div></div>
  <div class="row-audio">{{AudioExplanation}}</div>
</div>
<hr>
<div class="image">{{Image}}</div>
<div class="row">
  <div class="row-text">
    <div class="dialog">{{Dialog}}</div>
    <div class="source">{{Source}}</div>
  </div>
  <div class="row-audio">{{AudioDialog}}</div>
</div>
""" + EXAMPLE_BLOCKS + """\
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
        "model_id": 145594572691,
        "model_name": "English Vocabulary",
        "headword": "Word",
        "test_deck_id": 804850451889,
        "test_model_id": 508936285996,
    },
    {
        "slug": "phrasal-verbs",
        "deck_id": 807523115129,
        "deck_name": "Phrasal Verbs",
        "model_id": 143525141992,
        "model_name": "English Phrasal Verb",
        "headword": "Phrase",
        "test_deck_id": 567855487385,
        "test_model_id": 703766918383,
    },
    {
        "slug": "collocations",
        "deck_id": 221110591407,
        "deck_name": "Collocations",
        "model_id": 573397697437,
        "model_name": "English Collocation",
        "headword": "Phrase",
        "test_deck_id": 242142671948,
        "test_model_id": 534902278227,
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
            # Verb-only example block, appended so the first nine fields keep their order.
            # Empty on every other part of speech, which is what the template's `{{#...}}`
            # sections test.
            {"name": "PresentExample"},
            {"name": "PastSimpleExample"},
            {"name": "PastParticipleExample"},
            {"name": "AudioPresentExample"},
            {"name": "AudioPastSimpleExample"},
            {"name": "AudioPastParticipleExample"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": FRONT_TEMPLATE % {"headword": headword},
                "afmt": BACK_TEMPLATE % {"headword": headword},
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


def validate(entry: dict, key: str, seen: set[str], lay: Layout) -> None:
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
        # The word class is what decides whether the example rows are required, so every kind
        # carries it — a phrasal verb is a verb, and a collocation's head word may be one.
        raise BuildError(f"{label}: needs a part of speech (pos)")
    if pos not in ALLOWED_POS:
        raise BuildError(f"{label}: unknown part of speech {pos!r}")
    gender = entry.get("speaker_gender")
    if gender not in SPEAKER_GENDERS:
        raise BuildError(
            f"{label}: speaker_gender must be one of {', '.join(SPEAKER_GENDERS)}, got {gender!r}"
        )
    # A verb card teaches the verb, so its three example rows are part of the card, not an
    # optional extra: a missing one would vanish silently with the rest of its section.
    if is_verb(entry):
        for field in VERB_TEXT_KEYS:
            if not str(entry.get(field, "")).strip():
                raise BuildError(f"{label}: verb needs {field}")
    else:
        stray = [f for f in VERB_TEXT_KEYS if entry.get(f)]
        if stray:
            raise BuildError(f"{label}: {pos} must not carry verb examples {stray}")
    categories = entry.get("categories") or []
    if not categories:
        raise BuildError(f"{label}: needs at least one category")
    unknown = [c for c in categories if c not in ALLOWED_CATEGORIES]
    if unknown:
        raise BuildError(f"{label}: unknown categories {unknown}")
    if entry["phrase"] in seen:
        raise BuildError(f"{label}: duplicate phrase within the kind")
    seen.add(entry["phrase"])
    for path in [image_file(lay, key)] + [audio_file(lay, key, p) for p in audio_parts(entry)]:
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
            # Verb-only example rows; empty on other parts of speech, which is what the
            # template's `{{#...}}` sections test.
            *(
                [
                    entry["present_example"],
                    entry["past_simple_example"],
                    entry["past_participle_example"],
                    *(f"[sound:{audio_file(lay, key, p).name}]" for p in VERB_AUDIO_PARTS),
                ]
                if is_verb(entry)
                else [""] * 6
            ),
        ],
        tags=[f"category::{c}" for c in entry["categories"]]
        + [f"level::{entry['level']}", f"pos::{entry['pos']}"],
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
        validate(entry, key, seen, lay)
        deck.add_note(make_note(kind, model, entry, test, lay))
        media.extend([image_file(lay, key), *(audio_file(lay, key, p) for p in audio_parts(entry))])

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
