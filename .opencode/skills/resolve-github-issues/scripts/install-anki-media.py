#!/usr/bin/env python3
"""Install rebuilt clips into the live Anki collection and keep its media index honest.

Anki resolves media by **name** against `collection.media.db2`, and its package importer
skips every name the index still knows. So re-importing a package is not how a rebuilt clip
reaches a collection. Deleting the file is worse: the next `Check Media` turns the row into a
tombstone (`csum NULL, mtime 0`), and the importer then skips it forever while the card shows
a missing file.

So this copies the file in and rewrites the index row to match:

  - `media/<name>.mp3`          ->  `<profile>/collection.media/<name>.mp3`
  - row `csum`   = sha1 of the installed file
  - row `mtime`  = the file's mtime, in seconds
  - row `dirty`  = 1, so a synced collection uploads the new bytes

Anki must be quit: it rewrites `collection.media` and the index on exit.

Usage:
    ./install-anki-media.py col_d1e334e5-present-example col_b5aa9739-explanation
    ./install-anki-media.py --all col_d1e334e5        # every clip of one entry
    ANKI_MEDIA="/path/to/collection.media" ./install-anki-media.py ...
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SOURCE_MEDIA = REPO_ROOT / "media"
ANKI_ROOT = Path.home() / "Library" / "Application Support" / "Anki2"


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


def sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    summary = __doc__.splitlines()[0] if __doc__ else None
    parser = argparse.ArgumentParser(description=summary)
    parser.add_argument("names", nargs="+", help="clip names, with or without .mp3")
    parser.add_argument(
        "--all",
        action="store_true",
        help="treat each name as an entry key and install every clip it owns",
    )
    args = parser.parse_args()

    if anki_running():
        sys.exit("Anki is running — quit it first: it rewrites the media index on exit.")

    media_dir = find_media_dir(os.environ.get("ANKI_MEDIA"))
    db_path = media_dir.with_suffix(".media.db2")
    if not db_path.is_file():
        sys.exit(f"no media index at {db_path}")

    wanted: list[str] = []
    for name in args.names:
        stem = name[: -len(".mp3")] if name.endswith(".mp3") else name
        if args.all:
            found = sorted(path.name for path in SOURCE_MEDIA.glob(f"{stem}-*.mp3"))
            if not found:
                sys.exit(f"no clips named {stem}-*.mp3 in {SOURCE_MEDIA}")
            wanted.extend(found)
        else:
            wanted.append(f"{stem}.mp3")

    missing = [name for name in wanted if not (SOURCE_MEDIA / name).is_file()]
    if missing:
        sys.exit(f"not in {SOURCE_MEDIA}: {', '.join(missing)}")

    installed = 0
    with sqlite3.connect(db_path) as db:
        for name in wanted:
            source = SOURCE_MEDIA / name
            target = media_dir / name
            before = target.stat().st_size if target.is_file() else None
            shutil.copy2(source, target)
            db.execute(
                "insert into media (fname, csum, mtime, dirty) values (?, ?, ?, 1) "
                "on conflict(fname) do update set csum=excluded.csum, "
                "mtime=excluded.mtime, dirty=1",
                (name, sha1(target), int(target.stat().st_mtime)),
            )
            size = target.stat().st_size
            was = f"{before} -> " if before is not None and before != size else ""
            print(f"installed  {name:<46} {was}{size:>7} bytes")
            installed += 1
        db.commit()

    print(f"\n{installed} clip(s) installed in {media_dir}")
    print("Start Anki and run Tools -> Check Media: it should report 0 missing, 0 unused.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
