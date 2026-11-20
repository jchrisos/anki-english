#!/usr/bin/env python3
"""Write one entry's card text into the live Anki collection, like installing a clip.

A reworded sentence has two artifacts: the clip, which `install-anki-media.py` copies in by
name, and the note text, which the package importer only applies when *Update notes* is
*Always*. Leaving the import at *If newer* applies nothing at all, because `BUILD_MOD` is a
fixed constant and the incoming `mod` equals the stored one — so a card can play the new
sentence while displaying the old one.

This is the direct route for the text half, and it is deliberately narrow:

  - it rewrites the **text fields only**; the `Image` and audio fields are left byte for byte,
    because media is matched by name and has its own installer;
  - the note `id`, `guid` and model are untouched, so review history and cards stay put;
  - `mod` moves forward (never back), `usn` becomes -1 so a synced collection uploads it, and
    the sort field plus its checksum are refreshed if field 0 changed;
  - tags are unioned, never replaced: a tag added by hand survives.

Anki must be quit: it holds the database and rewrites it on exit. A copy of the collection is
left next to it (`collection.anki2.before-note-write`) before anything is written.

Usage:
    ./install-anki-note.py col_d1e334e5 col_b5aa9739
    ./install-anki-note.py --stale            # every entry that disagrees with src/
    ./install-anki-note.py --stale --dry-run  # show the diff, write nothing
    ANKI_MEDIA="/path/to/collection.media" ./install-anki-note.py --stale
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from contextlib import closing

from anki_collection import (
    SEPARATOR,
    SORT_FIELD,
    collection_path,
    entries,
    expected_fields,
    expected_tags,
    field_checksum,
    find_media_dir,
    join_tags,
    open_collection,
    split_fields,
    split_tags,
)


def plan(entry: dict, flds: list[str], tags: set[str]) -> tuple[list[str], set[str], list]:
    """Return the rewritten fields, the merged tags, and the changes to report."""
    new = list(flds)
    changes = []
    for name, index, want in expected_fields(entry):
        have = new[index] if index < len(new) else ""
        if have != want:
            changes.append((name, have, want))
            new[index] = want
    added = expected_tags(entry) - tags
    if added:
        changes.append(("tags", " ".join(sorted(tags)), " ".join(sorted(added))))
    return new, tags | added, changes


def main() -> int:
    summary = __doc__.splitlines()[0] if __doc__ else None
    parser = argparse.ArgumentParser(description=summary)
    parser.add_argument("keys", nargs="*", help="media keys (col_d1e334e5)")
    parser.add_argument(
        "--stale",
        action="store_true",
        help="write every entry whose note disagrees with src/",
    )
    parser.add_argument("--dry-run", action="store_true", help="show the diff, write nothing")
    args = parser.parse_args()

    if not args.keys and not args.stale:
        sys.exit("name at least one media key, or pass --stale")

    wanted = set(args.keys)
    known = {key for _kind, _entry, key, _guid in entries()}
    if wanted - known:
        sys.exit(f"not in src/: {', '.join(sorted(wanted - known))}")

    collection = collection_path(find_media_dir(os.environ.get("ANKI_MEDIA")))

    with closing(open_collection(collection, write=True)) as db:
        rows = {
            guid: (nid, split_fields(flds), split_tags(tags), mod)
            for nid, guid, flds, tags, mod in db.execute(
                "select id, guid, flds, tags, mod from notes"
            )
        }

        targets = []
        for _kind, entry, key, guid in entries():
            if not args.stale and key not in wanted:
                continue
            row = rows.get(guid)
            if row is None:
                sys.exit(f"not in the collection: {guid} — import the package first")
            nid, flds, tags, mod = row
            if len(flds) != 16:
                sys.exit(f"{guid}: {len(flds)} fields, expected 16 — the model changed")
            new_flds, new_tags, changes = plan(entry, flds, tags)
            if changes:
                targets.append((guid, key, nid, flds, mod, new_flds, new_tags, changes))

        if not targets:
            print("nothing to write: the collection already matches src/.")
            return 0

        if args.dry_run:
            for guid, key, _nid, _flds, _mod, _new, _tags, changes in targets:
                print(f"\n{guid}  ({key})")
                for name, have, want in changes:
                    print(f"  {name}\n    collection: {have}\n    src:        {want}")
            print(f"\n{len(targets)} note(s) would change; nothing written (--dry-run).")
            return 0

        backup = collection.with_name(collection.name + ".before-note-write")
        shutil.copy2(collection, backup)

        now = int(time.time())
        col_mod = db.execute("select mod from col").fetchone()[0]
        for guid, key, nid, flds, mod, new_flds, new_tags, changes in targets:
            sets = ["flds = ?", "tags = ?", "mod = ?", "usn = -1"]
            values = [SEPARATOR.join(new_flds), join_tags(new_tags), max(now, mod + 1)]
            if new_flds[SORT_FIELD] != flds[SORT_FIELD]:
                sets += ["sfld = ?", "csum = ?"]
                values += [new_flds[SORT_FIELD], field_checksum(new_flds[SORT_FIELD])]
            db.execute(f"update notes set {', '.join(sets)} where id = ?", (*values, nid))
            print(f"written  {guid}  ({key})  {len(changes)} change(s)")
            for name, _have, want in changes:
                print(f"    {name}: {want}")
        # Anki stamps this in milliseconds; notes' `mod` is in seconds.
        db.execute("update col set mod = ?", (max(int(time.time() * 1000), col_mod + 1),))
        db.commit()

    print(f"\n{len(targets)} note(s) written to {collection}")
    print(f"backup: {backup.name}")
    print("Start Anki: the cards show the new text. A synced collection uploads it (usn=-1).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
