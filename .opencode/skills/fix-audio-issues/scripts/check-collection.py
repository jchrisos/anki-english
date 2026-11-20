#!/usr/bin/env python3
"""Report notes whose text in the live Anki collection disagrees with `src/`.

A reworded sentence and its regenerated clip reach a collection by two different roads, and
they can arrive apart. The clip is copied in by name (`install-anki-media.py`); the text
changes only through a package import or `install-anki-note.py`. An import left at *Update
notes: If newer* quietly skips every note, because `BUILD_MOD` is a fixed constant, so the
incoming `mod` equals the one already stored. The card then shows the old sentence while
playing the new clip — a mismatch no build and no lint can see, because it exists only in the
collection.

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
import os
import sys
from contextlib import closing

from anki_collection import (
    GUID_PREFIX,
    anki_running,
    collection_path,
    entries,
    expected_fields,
    expected_tags,
    find_media_dir,
    open_collection,
    split_fields,
    split_tags,
)


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

    collection = collection_path(find_media_dir(os.environ.get("ANKI_MEDIA")))
    with closing(open_collection(collection)) as db:
        notes = {
            guid: (split_fields(flds), split_tags(tags))
            for guid, flds, tags in db.execute("select guid, flds, tags from notes")
        }

    checked = drifted = absent = 0
    for _kind, entry, key, guid in entries(args.kind):
        if args.key and key != args.key:
            continue
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
        missing_tags = expected_tags(entry) - tags
        if missing_tags:
            problems.append(("tags", " ".join(sorted(missing_tags)), " ".join(sorted(tags))))
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
                f"{drifted} note(s) behind src/: run "
                "./install-anki-note.py --stale to write them in."
            )
        if absent:
            print(
                f"{absent} note(s) from src/ are not in the collection at all: "
                "import the package first."
            )
        return 1

    print(f"collection matches src/: {checked} note(s) checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
