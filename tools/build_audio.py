#!/usr/bin/env python3
"""Synthesize one mp3 per entry with edge-tts.

Fixed script order: the target, then the definition, then the dialog line. The speaker
attribution and the quotation marks are stripped (see `deck_common.spoken_script`), because
the voice should not read them aloud.

Existing files are never rewritten. TTS is a cloud call and not guaranteed to be
byte-identical between runs, so the mp3s are committed **inputs** to the build, exactly
like the images: regenerate only on explicit request, with `--force`.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

import edge_tts

from deck_common import (
    AUDIO_PARTS,
    GUID_PREFIX,
    RATE,
    Layout,
    audio_file,
    layout,
    load_entries,
    media_key,
    part_text,
    part_voice,
)

CONCURRENCY = 3


async def synthesize(entry: dict, key: str, part: str, force: bool, lay: Layout) -> str:
    path = audio_file(lay, key, part)
    if path.exists() and not force:
        return f"skip {path.name} (exists)"
    communicate = edge_tts.Communicate(part_text(entry, part), part_voice(entry, part), rate=RATE)
    await communicate.save(str(path))
    return f"wrote {path.name} ({part_voice(entry, part)})"


async def run(slugs: list[str], force: bool, test: bool) -> int:
    lay = layout(test)
    semaphore = asyncio.Semaphore(CONCURRENCY)
    jobs = []
    for slug in slugs:
        prefix = GUID_PREFIX[slug]
        for entry in load_entries(lay, slug):
            key = media_key(prefix, entry)
            jobs.extend((entry, key, part) for part in AUDIO_PARTS)

    async def guarded(entry: dict, key: str, part: str) -> str:
        async with semaphore:
            return await synthesize(entry, key, part, force, lay)

    results = await asyncio.gather(*(guarded(e, k, p) for e, k, p in jobs), return_exceptions=True)
    failures = 0
    for result in results:
        if isinstance(result, Exception):
            failures += 1
            print(f"FAILED: {result}", file=sys.stderr)
        else:
            print(result)
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--only",
        choices=sorted(GUID_PREFIX),
        action="append",
        help="restrict to one kind (repeatable)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-synthesize mp3s that already exist",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="read tests/src and write tests/media (gitignored)",
    )
    args = parser.parse_args()
    return asyncio.run(run(args.only or sorted(GUID_PREFIX), args.force, args.test))


if __name__ == "__main__":
    sys.exit(main())
