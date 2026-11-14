#!/usr/bin/env python3
"""Normalize generated images into small committed JPEGs.

Image models emit 1–3 MB PNGs. Ten of those per package makes a deck the user has to
import by hand needlessly heavy, and Anki re-encodes nothing, so the cost is permanent.
This downsizes to 900 px on the long edge and re-encodes as JPEG.

Idempotent: a file that is already `.jpg` is left alone, and a source whose `.jpg` already
exists is skipped — the JPEG is the committed input, so a stray `.png` (or a second format
of the same stem) must never quietly replace it. The source is removed only once the JPEG is
complete, and the JPEG is written under a temporary name and moved into place, so neither an
interrupted run nor a failed `sips` can lose an image or leave half of one where the deck
expects a picture. `media/` is an input to the build, not a build product — this never
regenerates art.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from deck_common import layout

MAX_EDGE = 900
QUALITY = 82
SOURCE_EXTS = (".png", ".webp")


def convert(source: Path) -> int | None:
    """Write `source`'s JPEG and drop the source; `None` when there was nothing to do."""
    target = source.with_suffix(".jpg")
    if target.exists():
        print(f"skip {source.name}: {target.name} already exists (remove it to reconvert)")
        return None
    staged = target.with_name(f"{target.stem}.part.jpg")
    try:
        result = subprocess.run(
            [
                "sips",
                "-Z",
                str(MAX_EDGE),
                "-s",
                "format",
                "jpeg",
                "-s",
                "formatOptions",
                str(QUALITY),
                str(source),
                "--out",
                str(staged),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"sips exited {result.returncode}")
        if not staged.is_file() or staged.stat().st_size == 0:
            raise RuntimeError("sips wrote no image")
        staged.replace(target)
    finally:
        staged.unlink(missing_ok=True)
    source.unlink()
    return target.stat().st_size


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--test",
        action="store_true",
        help="convert tests/media instead of media/",
    )
    args = parser.parse_args()
    lay = layout(args.test)
    sources = sorted(p for ext in SOURCE_EXTS for p in lay.media.glob(f"*{ext}"))
    if not sources:
        print("nothing to convert")
        return 0
    for source in sources:
        try:
            size = convert(source)
        except RuntimeError as exc:
            print(f"error: {source.name}: {exc}", file=sys.stderr)
            return 1
        if size is not None:
            print(f"{source.name} -> {source.with_suffix('.jpg').name} ({size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
