#!/usr/bin/env python3
"""Build the anki-english deck packages.

Each package contains exactly one deck and one note type. By default it also contains **no
notes**: that is the baseline which puts the pinned deck ids, deck names and note-type ids
into the collection before any content exists, and re-importing a later build updates those
same objects instead of creating parallel ones.

Content from `src/<kind>.json` is included only with `--notes`. Content is added on demand,
so a plain build must never quietly ship entries.

Every note is validated before the package is written: all text fields present, exactly one
CEFR level, at least one known category, and every mp3 on disk. The illustration is optional:
an entry names its image with an `image` field, and a name that resolves to no file on disk
leaves the card without a picture rather than with a broken `<img>`. A note missing any other
required part is a build failure, not a card with a blank panel.

Production output goes to `decks/`, but every `*.apkg` there is a **build artifact**: it is
gitignored and imported by hand after the build, so nothing ships in git. Test output goes to
`tests/decks/`, which is gitignored together with the rest of `tests/`: test builds read
`tests/src/` and `tests/media/`, so no test artifact ever mixes with production.

Test builds are fully isolated: they use their own pinned deck ids and model ids, their own
deck/model names (suffixed `(test)`) and their own filenames (`<kind>-test.apkg`). Anki
matches decks by **name**, note types by **id** and notes by **GUID**, so all three have to
differ — a test package that reused any one of them would merge into the real deck.

Ids are pinned constants from `.okf/concepts/deck-schema.md`. Never derive them at runtime
and never let them drift: a new id means a duplicate deck or note type in Anki.
"""

from __future__ import annotations

import argparse
import html
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import genanki

from deck_common import (
    ALLOWED_CATEGORIES,
    ALLOWED_POS,
    GUID_PREFIX,
    KIND_LEVELS,
    KIND_TARGET_CARDS,
    MANIFEST_NAME,
    MARKUP,
    REMOVED_KEYS,
    REPO_ROOT,
    REQUIRED_TEXT_FIELDS,
    TEST_GUID_PREFIX,
    VERB_AUDIO_PARTS,
    VERB_TEXT_KEYS,
    Layout,
    audio_file,
    audio_parts,
    bold_markup,
    identity_problem,
    image_for,
    is_verb,
    layout,
    load_entries,
    manifest_identities,
    markup_spans,
    media_key,
)

# Fixed so repeated builds of unchanged input are equivalent (no wall-clock ids/timestamps).
#
# This is also the note type's `mod`, and Anki's apkg importer updates an existing note type
# only when the incoming mod is **newer** (`update_notetypes = if_newer`). So: raise this
# value whenever the fields, templates or CSS change, or the new template never reaches a
# collection that already has the note type — which is how a stale `<img src="{{Image}}">`
# template survived a re-import and rendered the image tag as literal text.
BUILD_MOD = 1796600000

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
.sentence { font-style: italic; }
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

# One authored example per form, appended after the authored example row. The labels name the form
# the sentence demonstrates. Rows run simple present, `-ing`, simple past, past participle:
# tense pairs first, perfect last. The `-ing` row is labelled "Present participle" so it reads
# as a form name beside "Past participle" and is not mistaken for the simple present. A non-verb
# note leaves the fields empty, so the `{{#...}}` sections render nothing at all — no empty rows,
# no stray dividers.
EXAMPLE_BLOCKS = """\
{{#PresentExample}}
<hr>
<div class="row">
  <div class="row-text">
    <div class="block-label">Present</div>
    <div class="sentence">{{PresentExample}}</div>
  </div>
  <div class="row-audio">{{AudioPresentExample}}</div>
</div>
{{/PresentExample}}
{{#PresentParticipleExample}}
<hr>
<div class="row">
  <div class="row-text">
    <div class="block-label">Present participle</div>
    <div class="sentence">{{PresentParticipleExample}}</div>
  </div>
  <div class="row-audio">{{AudioPresentParticipleExample}}</div>
</div>
{{/PresentParticipleExample}}
{{#PastSimpleExample}}
<hr>
<div class="row">
  <div class="row-text">
    <div class="block-label">Past</div>
    <div class="sentence">{{PastSimpleExample}}</div>
  </div>
  <div class="row-audio">{{AudioPastSimpleExample}}</div>
</div>
{{/PastSimpleExample}}
{{#PastParticipleExample}}
<hr>
<div class="row">
  <div class="row-text">
    <div class="block-label">Past participle</div>
    <div class="sentence">{{PastParticipleExample}}</div>
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
    <div class="block-label">Example</div>
    <div class="example">{{Example}}</div>
  </div>
  <div class="row-audio">{{AudioExample}}</div>
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
        "model_id": 691519255953,
        "model_name": "English Vocabulary",
        "headword": "Word",
        "test_deck_id": 804850451889,
        "test_model_id": 220571904367,
    },
    {
        "slug": "phrasal-verbs",
        "deck_id": 807523115129,
        "deck_name": "Phrasal Verbs",
        "model_id": 350528611282,
        "model_name": "English Phrasal Verb",
        "headword": "Phrase",
        "test_deck_id": 567855487385,
        "test_model_id": 355844549585,
    },
    {
        "slug": "collocations",
        "deck_id": 221110591407,
        "deck_name": "Collocations",
        "model_id": 377855104706,
        "model_name": "English Collocation",
        "headword": "Phrase",
        "test_deck_id": 242142671948,
        "test_model_id": 202971465130,
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
            # `Audio` is the word clip: the name predates the split, and renaming a field is
            # destructive, so the explanation clip was appended instead.
            {"name": "Audio"},
            {"name": "AudioExplanation"},
            # Verb-only example block. Empty on every other part of speech, which is what the
            # template's `{{#...}}` sections test.
            {"name": "PresentExample"},
            {"name": "PastSimpleExample"},
            {"name": "PastParticipleExample"},
            {"name": "PresentParticipleExample"},
            {"name": "AudioPresentExample"},
            {"name": "AudioPastSimpleExample"},
            {"name": "AudioPastParticipleExample"},
            {"name": "AudioPresentParticipleExample"},
            # The authored example under the definition. Required on every note, so it is
            # appended after the verb block to keep both earlier groups in order.
            {"name": "Example"},
            {"name": "AudioExample"},
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


def _write_package(deck: genanki.Deck, media: list[Path], out: Path) -> None:
    """Write the package to `out` without ever truncating the previous one.

    Two things have to hold that genanki does not give us:

    - the destination must only ever hold a **complete** archive. `write_to_file` opens it
      with `"w"` and then streams every mp3 and image into it, so an exception or a Ctrl-C
      mid-write leaves a truncated zip exactly where the last good package was;
    - the zip metadata must be fixed. genanki stamps entries with the build machine's clock,
      so two builds of identical input would differ byte for byte and the "same input, same
      output" promise would not mean anything.

    So the package is written to a sidecar, copied streaming into a second sidecar with
    pinned timestamps, and moved into place with a single `replace`. Each entry is streamed
    rather than read whole, so a deck of 27k media files does not have to fit in memory
    twice.
    """
    raw = out.with_name(out.name + ".build")
    staged = out.with_name(out.name + ".tmp")
    try:
        with tempfile.TemporaryDirectory(prefix="anki-english-") as scratch:
            # genanki creates its throwaway sqlite with `tempfile.mkstemp()` and never
            # removes it, so every run used to leave a database in $TMPDIR. Pointing
            # `tempfile` at a directory we own makes it disappear with the package.
            previous = tempfile.tempdir
            tempfile.tempdir = scratch
            try:
                genanki.Package(deck, media_files=[str(p) for p in media]).write_to_file(
                    str(raw), timestamp=BUILD_MOD
                )
            finally:
                tempfile.tempdir = previous

        with (
            zipfile.ZipFile(raw) as src,
            zipfile.ZipFile(staged, "w", compression=zipfile.ZIP_DEFLATED) as dst,
        ):
            for info in src.infolist():
                pinned = zipfile.ZipInfo(info.filename, date_time=(1980, 1, 1, 0, 0, 0))
                pinned.compress_type = zipfile.ZIP_DEFLATED
                pinned.external_attr = 0o644 << 16
                with src.open(info) as reader, dst.open(pinned, "w") as writer:
                    shutil.copyfileobj(reader, writer, 1024 * 1024)
        staged.replace(out)
    finally:
        raw.unlink(missing_ok=True)
        staged.unlink(missing_ok=True)


class BuildError(Exception):
    """A note that must not reach a package: missing field, bad tag, missing media."""


def check_markup(entry: dict, field: str, label: str) -> None:
    """An authored example must bold its target and leave no stray `**` behind.

    The span is authored rather than derived: the sentence uses an inflected form and a phrasal
    verb may be split (`pick yourself up`), so the build cannot find the target on its own.
    """
    text = str(entry.get(field) or "")
    spans = markup_spans(text)
    if not spans:
        raise BuildError(f"{label}: {field} must bold the target with **...**")
    if any(not span.strip() for span in spans):
        raise BuildError(f"{label}: {field} has an empty **...** span")
    if text.count(MARKUP) != 2 * len(spans):
        raise BuildError(f"{label}: {field} has unbalanced ** markers")


def validate(
    entry: dict,
    key: str,
    seen: set[tuple[str, str]],
    keys: dict[str, str],
    lay: Layout,
    levels: tuple[str, ...],
) -> None:
    """Reject an entry instead of emitting a card with a blank panel.

    Missing media is the failure that does not announce itself: Anki imports the note and
    renders an empty image or a silent card, so both files are asserted here. Empty is the
    same failure with a file attached — a clip that edge-tts opened and never finished — so
    the size is asserted too.
    """
    label = f"{entry.get('phrase', '?')} ({key})"
    for field in REQUIRED_TEXT_FIELDS:
        if not str(entry.get(field, "")).strip():
            raise BuildError(f"{label}: empty {field}")
    # The phrase and the sense are the GUID, so the build does not wait for the lint to
    # reject a shape that would fork the note's review history on the next import.
    problem = identity_problem(str(entry["phrase"]), str(entry["sense"]))
    if problem:
        raise BuildError(f"{label}: {problem}")
    if not entry["pronunciation"].startswith("/") or not entry["pronunciation"].endswith("/"):
        raise BuildError(f"{label}: pronunciation must be IPA in slashes")
    level = entry.get("level")
    if level not in levels:
        raise BuildError(
            f"{label}: level must be one of {', '.join(levels)} for this deck, got {level!r}"
        )
    pos = entry.get("pos")
    if pos is None:
        # The word class is what decides whether the example rows are required, so every kind
        # carries it — a phrasal verb is a verb, and a collocation's head word may be one.
        raise BuildError(f"{label}: needs a part of speech (pos)")
    if pos not in ALLOWED_POS:
        raise BuildError(f"{label}: unknown part of speech {pos!r}")
    # The movie-quote block was removed on 2026-11-08. A source entry still carrying its keys
    # would import a card with the quote silently dropped, so the build stops instead.
    removed = [stale_key for stale_key in REMOVED_KEYS if stale_key in entry]
    if removed:
        raise BuildError(f"{label}: remove the retired movie-quote keys {removed}")
    # A verb card teaches the verb, so its four example rows are part of the card, not an
    # optional extra: a missing one would vanish silently with the rest of its section.
    if is_verb(entry):
        for field in VERB_TEXT_KEYS:
            if not str(entry.get(field, "")).strip():
                raise BuildError(f"{label}: verb needs {field}")
            check_markup(entry, field, label)
    else:
        stray = [f for f in VERB_TEXT_KEYS if entry.get(f)]
        if stray:
            raise BuildError(f"{label}: {pos} must not carry verb examples {stray}")
    check_markup(entry, "example", label)
    categories = entry.get("categories") or []
    if not categories:
        raise BuildError(f"{label}: needs at least one category")
    unknown = [c for c in categories if c not in ALLOWED_CATEGORIES]
    if unknown:
        raise BuildError(f"{label}: unknown categories {unknown}")
    identity = (entry["phrase"], entry["sense"])
    if identity in seen:
        raise BuildError(f"{label}: duplicate phrase+sense within the kind")
    seen.add(identity)
    # The key is the shared name of the image and of every mp3, and it is a 32-bit digest,
    # so two entries *can* land on one. Sharing it would make one card play the other's
    # audio while `build_audio` skipped the clip as already written, so a collision is a
    # build failure rather than a quiet mix-up.
    if key in keys:
        raise BuildError(f"{label}: media key {key} is already used by {keys[key]}")
    keys[key] = label
    # The illustration is optional: an entry whose `image` names no file on disk is built
    # without one, instead of importing a card with a broken `<img>`. A path in the field
    # would be baked into the note and break on import, so only a bare filename is allowed.
    image_name = str(entry.get("image") or "").strip()
    if image_name and Path(image_name).name != image_name:
        raise BuildError(f"{label}: image must be a bare filename, got {image_name!r}")
    # Audio is still mandatory: a missing mp3 renders a silent card with no visible clue,
    # and so does an empty one left behind by a failed synthesis.
    for path in [audio_file(lay, key, p) for p in audio_parts(entry)]:
        if not path.is_file() or path.stat().st_size == 0:
            raise BuildError(f"{label}: missing or empty media file {path.name}")


def card_text(value: str) -> str:
    """Escape an authored field for the card's HTML.

    The fields are HTML — `bold_markup` emits `<b>` and the image field carries an `<img>`
    tag — so a definition containing `<`, `>` or `&` would otherwise be parsed as markup
    and vanish or break the layout. The authored `**` markers contain none of those
    characters, so escaping first and bolding second leaves the generated `<b>` intact.

    Quotes are deliberately left alone (`quote=False`): these values only ever land in text
    nodes, never in an attribute, and escaping them would store `don&#x27;t` in the note,
    where Anki's own search for `don't` would no longer find it.
    """
    return html.escape(str(value), quote=False)


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
    image = image_for(lay, entry)
    return genanki.Note(
        model=model,
        fields=[
            card_text(entry["phrase"]),
            card_text(entry["pronunciation"]),
            card_text(entry["definition"]),
            # The field carries the whole tag, not a bare filename. Anki's importer only
            # copies media that it can see referenced in the field text (`<img src>` and
            # `[sound:]`), so a filename the template wrapped later is silently skipped.
            # No resolvable image means an empty field: the card simply has no illustration.
            f'<img src="{image.name}">' if image else "",
            # Each clip lives in its own field so the template can place it directly under
            # the text it reads, instead of stacking players at the bottom.
            f"[sound:{audio_file(lay, key, 'word').name}]",
            f"[sound:{audio_file(lay, key, 'explanation').name}]",
            # Verb-only example rows; empty on other parts of speech, which is what the
            # template's `{{#...}}` sections test.
            *(
                [
                    *(bold_markup(card_text(entry[field])) for field in VERB_TEXT_KEYS),
                    *(f"[sound:{audio_file(lay, key, p).name}]" for p in VERB_AUDIO_PARTS),
                ]
                if is_verb(entry)
                else [""] * 8
            ),
            # The authored example, required on every note.
            bold_markup(card_text(entry["example"])),
            f"[sound:{audio_file(lay, key, 'example').name}]",
        ],
        tags=[f"category::{c}" for c in entry["categories"]]
        + [f"level::{entry['level']}", f"pos::{entry['pos']}"],
        guid=guid,
    )


def load_manifest(lay: Layout) -> set[tuple[str, str, str]]:
    """Return the reviewed `kind + phrase + sense` identities from the plan.

    Only identity is read here: the row's pos, level, categories and gloss belong to
    `lint_content.py`. Cells are trimmed by `manifest_identities()`, so a hand-edited plan
    cannot disagree with the lint about the same entry. A missing manifest is a build error
    rather than "no plan", because `--notes` against a tree without its reviewed plan is
    exactly the state the manifest exists to prevent.
    """
    path = lay.src / MANIFEST_NAME
    try:
        return manifest_identities(path)
    except FileNotFoundError:
        raise BuildError(f"{path}: manifest is missing; --notes needs {MANIFEST_NAME}") from None


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
    plan = load_manifest(lay) if entries else set()
    seen: set[tuple[str, str]] = set()
    keys: dict[str, str] = {}
    for entry in entries:
        # The key is derived from the phrase and the sense, so a malformed entry has to be
        # rejected before `media_key` can raise a bare KeyError past `main()`'s handler.
        if not str(entry.get("phrase") or "").strip() or not str(entry.get("sense") or "").strip():
            raise BuildError(
                f"{kind['slug']}: entry without a phrase or a sense: {sorted(entry)}"
            )
        key = media_key(GUID_PREFIX[kind["slug"]], entry)
        # The manifest is the reviewed plan, one row per sense; a card that is not in it was
        # never deduplicated and never agreed on. Lint compares the row's pos, level and
        # categories; the build only insists that the row exists at all.
        if (kind["slug"], entry["phrase"], entry["sense"]) not in plan:
            raise BuildError(
                f"{entry['phrase']} ({key}): not in {MANIFEST_NAME}; write the plan row first"
            )
        validate(entry, key, seen, keys, lay, KIND_LEVELS[kind["slug"]])
        deck.add_note(make_note(kind, model, entry, test, lay))
        image = image_for(lay, entry)
        if image is None:
            print(
                f"warning: {entry['phrase']} ({key}): no image file named "
                f"{entry.get('image') or '(none)'}; card built without an illustration",
                file=sys.stderr,
            )
        else:
            media.append(image)
        media.extend(audio_file(lay, key, p) for p in audio_parts(entry))

    lay.out.mkdir(parents=True, exist_ok=True)
    path = lay.out / ident["filename"]
    _write_package(deck, media, path)
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
            f"{path.relative_to(REPO_ROOT)}  notes={count}/{KIND_TARGET_CARDS[kind['slug']]}  "
            f"deck={ident['deck_name']!r} deck_id={ident['deck_id']} model_id={ident['model_id']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
