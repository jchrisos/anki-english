#!/usr/bin/env python3
"""Normalize generated images into small committed JPEGs.

Image models emit 1–3 MB PNGs. Ten of those per package makes a deck the user has to
import by hand needlessly heavy, and Anki re-encodes nothing, so the cost is permanent.
This downsizes to 900 px on the long edge and re-encodes as JPEG.

Idempotent: a file that is already `.jpg` is left alone. The original `.png`/`.webp` is
removed only after the JPEG is written, so an interrupted run cannot lose an image.
`media/` is an input to the build, not a build product — this never regenerates art.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

from deck_common import layout

MAX_EDGE = 900
QUALITY = 82
SOURCE_EXTS = (".png", ".webp")


def convert(source) -> int:
    target = source.with_suffix(".jpg")
    subprocess.run(
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
            str(target),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
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
        size = convert(source)
        print(f"{source.name} -> {source.with_suffix('.jpg').name} ({size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
