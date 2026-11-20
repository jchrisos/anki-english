#!/usr/bin/env python3
"""Locate the source entry behind a phrase or sentence quoted in an issue.

An issue quotes card text ("she washes her hand before dinner"), never a filename, so every
content or audio report starts with the same lookup: which entry is this, what is its media
key, which of its clips exist, and what does each clip say? That is exactly what
`build_audio.py --key` and any edit to `src/<kind>.json` need, so the lookup lives here
instead of being retyped per issue.

Usage:
    scripts/find-entry.py washes her hands
    scripts/find-entry.py --kind collocations "set the table"
    scripts/find-entry.py --test "washes"          # search tests/src instead of src
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from deck_common import (  # noqa: E402  (path set up above)
    GUID_PREFIX,
    audio_file,
    audio_parts,
    layout,
    load_entries,
    media_key,
    part_text,
)


def main() -> int:
    summary = __doc__.splitlines()[0] if __doc__ else None
    parser = argparse.ArgumentParser(description=summary)
    parser.add_argument(
        "text",
        nargs="+",
        help="every word must appear somewhere in the entry: a phrase, a definition fragment, a sentence",
    )
    parser.add_argument(
        "--kind",
        action="append",
        choices=sorted(GUID_PREFIX),
        help="restrict to one kind (repeatable)",
    )
    parser.add_argument("--test", action="store_true", help="search tests/src instead of src")
    args = parser.parse_args()

    lay = layout(args.test)
    wanted = [token.lower() for token in args.text]
    hits = 0

    for kind in args.kind or sorted(GUID_PREFIX):
        prefix = GUID_PREFIX[kind]
        for entry in load_entries(lay, kind):
            # Every value, so a match on the definition or an example row counts too: an issue
            # quoting the definition names the entry without ever naming its phrase.
            blob = " ".join(str(value) for value in entry.values()).lower()
            if not all(token in blob for token in wanted):
                continue
            hits += 1
            key = media_key(prefix, entry)
            print(f"{kind}: {entry['phrase']}  (sense: {entry['sense']}, level: {entry.get('level', '?')})")
            print(f"  key: {key}")
            for part in audio_parts(entry):
                path = audio_file(lay, key, part)
                size = f"{path.stat().st_size:>7} bytes" if path.is_file() else "  MISSING"
                print(f"  {part:<26} {size}  {part_text(entry, part)!r}")
            print()

    if not hits:
        print(f"no entry contains all of: {' '.join(args.text)!r}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
