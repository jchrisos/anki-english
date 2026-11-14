#!/usr/bin/env python3
"""Synthesize one mp3 per spoken part with edge-tts.

Each part gets its own clip — the target, the definition, the authored example, and one per
verb form row (`present`, `present participle`, `past`, `past participle`) — so a learner
replays only the piece they need. Every part uses the pinned female voice; nothing on the card
is a character's line.

Existing files are never rewritten. TTS is a cloud call and not guaranteed to be
byte-identical between runs, so the mp3s are **inputs** to the build, exactly like the
images: regenerate only on explicit request, with `--force`. They are gitignored — a clone
runs this step once — so "input" here means "not produced by `build_decks.py`", not "tracked".

A clip is written under a `.part` name and moved into place only once edge-tts produced it:
`Communicate.save` opens the destination before the first audio arrives, so a dropped
connection would otherwise leave an empty or half-written mp3 at the real name, which the
skip check below would report as done forever.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

import edge_tts

from deck_common import (
    GUID_PREFIX,
    RATE,
    VOICE_FEMALE,
    Layout,
    audio_file,
    audio_parts,
    layout,
    load_entries,
    media_key,
    part_text,
)

CONCURRENCY = 3

# Sidecar name for a clip that edge-tts is still writing. Same directory, so the final
# `replace` is a rename and cannot leave a half file behind.
PART_SUFFIX = ".part"


async def synthesize(entry: dict, key: str, part: str, force: bool, lay: Layout) -> str:
    path = audio_file(lay, key, part)
    # A zero-byte file is a failed run that got as far as creating the name, not a clip:
    # re-synthesize it instead of skipping it for good.
    if path.is_file() and path.stat().st_size > 0 and not force:
        return f"skip {path.name} (exists)"
    staged = path.with_name(path.name + PART_SUFFIX)
    communicate = edge_tts.Communicate(part_text(entry, part), VOICE_FEMALE, rate=RATE)
    try:
        await communicate.save(str(staged))
        if staged.stat().st_size == 0:
            raise RuntimeError("edge-tts returned no audio")
        staged.replace(path)
    except BaseException:
        # Includes the cancellation a Ctrl-C raises: never leave a `.part` behind, and never
        # leave the real name occupied by a clip that was not finished.
        staged.unlink(missing_ok=True)
        raise
    return f"wrote {path.name} ({VOICE_FEMALE})"


async def run(slugs: list[str], force: bool, test: bool) -> int:
    lay = layout(test)
    semaphore = asyncio.Semaphore(CONCURRENCY)
    jobs = []
    for slug in slugs:
        prefix = GUID_PREFIX[slug]
        for entry in load_entries(lay, slug):
            key = media_key(prefix, entry)
            jobs.extend((entry, key, part) for part in audio_parts(entry))

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
