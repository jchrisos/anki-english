#!/usr/bin/env python3
"""Report notes whose text in the live Anki collection disagrees with `src/`.

A reworded sentence and its regenerated clip reach a collection by two different roads, and
they can arrive apart. The clip is copied in by name (`install-anki-media.py`); the text only
lands when the rebuilt package is imported. And an import left at *Update notes: If newer*
quietly skips every note, because `BUILD_MOD` is a fixed constant, so the incoming `mod`
equals the one already stored. The card then shows the old sentence while playing the new
clip — a mismatch no build and no lint can see, because it exists only in the collection.

Read-only: opens `collection.anki2` next to `collection.media` and compares the fields the
build renders, plus the tags it sets. Anki must be quit, since it owns the database and
rewrites it on exit.

Usage:
    ./check-collection.py                       # every entry in src/
    ./check-collection.py --key col_d1e334e5    # one entry, by media key
    ./check-collection.py --kind collocations
    ANKI_MEDIA="/path/to/collection.media" ./check-collection.py
"""
from __future__ import annotations

import argparse
import html
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from deck_common import (  # noqa: E402
    GUID_PREFIX,
    VERB_TEXT_KEYS,
    bold_markup,
    is_verb,
    layout,
    load_entries,
    media_key,
)

ANKI_ROOT = Path.home() / "Library" / "Application Support" / "Anki2"
SEPARATOR = "\x1f"

# The note type's field order is pinned by the model id, so it is safe to index into. Text
# only: the audio and image fields hold bare references, and a stale clip is what
# `find-entry.py` and the media index are for. The verb block sits between the clips and the
# authored example (`Example` is the second-to-last field).
TEXT_FIELDS = (("phrase", 0), ("pronunciation", 1), ("definition", 2))
VERB_FIELD_BASE = 6
EXAMPLE_FIELD = 14


def anki_running() -> bool:
    return subprocess.run(["pgrep", "-x", "Anki"], capture_output=True).returncode == 0


def find_media_dir(override: str | None) -> Path:
    if override:
        return Path(override).expanduser()
    candidates = sorted(ANKI_ROOT.glob("*/collection.media"))
    if not candidates:
        sys.exit(f"no collection.media under {ANKI_ROOT}")
    if len(candidates) > 1:
        listing = "\n  ".join(str(c) for c in candidates)
        sys.exit(f"several profiles found; pick one with ANKI_MEDIA:\n  {listing}")
    return candidates[0]


def card_text(value: object) -> str:
    """Escape an authored field the way `build_decks.card_text` does.

    Mirrored rather than imported: `build_decks` imports genanki, which only the repo's
    `.venv` has, and this script has to run under the plain interpreter like its siblings.
    Quotes stay unescaped on purpose — the value lands in a text node, and `don&#x27;t` would
    break Anki's own search.
    """
    return html.escape(str(value), quote=False)


def expected_fields(entry: dict) -> list[tuple[str, int, str]]:
    """The rendered value of every field this entry's note should carry."""
    fields = [
        (key, index, card_text(str(entry[key])))
        for key, index in TEXT_FIELDS
    ]
    if is_verb(entry):
        fields += [
            (key, VERB_FIELD_BASE + offset, bold_markup(card_text(entry[key])))
            for offset, key in enumerate(VERB_TEXT_KEYS)
        ]
    fields.append(("example", EXAMPLE_FIELD, bold_markup(card_text(entry["example"]))))
    return fields


def expected_tags(entry: dict) -> set[str]:
    return {f"category::{c}" for c in entry["categories"]} | {
        f"level::{entry['level']}",
        f"pos::{entry['pos']}",
    }


def main() -> int:
    summary = __doc__.splitlines()[0] if __doc__ else None
    parser = argparse.ArgumentParser(description=summary)
    parser.add_argument("--key", help="check one entry's media key (col_d1e334e5)")
    parser.add_argument(
        "--kind",
        action="append",
        choices=sorted(GUID_PREFIX),
        help="restrict to one kind (repeatable)",
    )
    args = parser.parse_args()

    if anki_running():
        sys.exit("Anki is running — quit it first: the collection is rewritten on exit.")

    media_dir = find_media_dir(os.environ.get("ANKI_MEDIA"))
    collection = media_dir.with_suffix(".anki2")
    if not collection.is_file():
        sys.exit(f"no collection at {collection}")

    # `as_uri()` percent-encodes the space in the profile name ("User 1"); a raw path in the
    # `file:` URI makes sqlite read the name as truncated and report "unable to open".
    db = sqlite3.connect(collection.resolve().as_uri() + "?mode=ro", uri=True)
    notes = {
        guid: (flds.split(SEPARATOR), tags.strip())
        for guid, flds, tags in db.execute("select guid, flds, tags from notes")
    }

    lay = layout(False)
    checked = drifted = absent = 0
    for kind in args.kind or sorted(GUID_PREFIX):
        for entry in load_entries(lay, kind):
            key = media_key(GUID_PREFIX[kind], entry)
            if args.key and key != args.key:
                continue
            guid = f"{GUID_PREFIX[kind]}:{entry['phrase']}:{entry['sense']}"
            stored = notes.get(guid)
            if stored is None:
                absent += 1
                print(f"not in collection  {guid}  ({key})")
                continue
            checked += 1
            flds, tags = stored
            problems = []
            for name, index, want in expected_fields(entry):
                have = flds[index] if index < len(flds) else ""
                if have != want:
                    problems.append((name, want, have))
            missing_tags = expected_tags(entry) - set(tags.split())
            if missing_tags:
                problems.append(("tags", " ".join(sorted(missing_tags)), tags))
            if not problems:
                continue
            drifted += 1
            print(f"\n{guid}  ({key})")
            for name, want, have in problems:
                print(f"  {name}")
                print(f"    src:        {want}")
                print(f"    collection: {have}")

    if drifted or absent:
        print()
        if drifted:
            print(
                f'{drifted} note(s) behind src/: re-import the package with '
                '"Update notes: Always".'
            )
        if absent:
            print(f"{absent} note(s) from src/ are not in the collection at all: import the package.")
        return 1

    print(f"collection matches src/: {checked} note(s) checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
