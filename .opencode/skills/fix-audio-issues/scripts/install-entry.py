#!/usr/bin/env python3
"""Install both halves of an entry into the live collection, then verify.

A reworded sentence has two artifacts and they reach Anki by two roads: the clip is copied in
by name, the note text is written field by field. Fixing one and forgetting the other is the
defect behind #1 and #2 — the card played the new sentence while displaying the old one — so
the pair is one step here rather than two commands to remember.

Run after `build_audio.py --force --key <key>` re-renders the clips:

  - `install-anki-media.py --all <key>` copies every clip in (a no-op when the bytes match);
  - `install-anki-note.py <key>` writes the text fields (a no-op when the text did not change);
  - `check-collection.py --key <key>` proves the collection now agrees with `src/`.

Anki must be quit: each step refuses to run otherwise. Exit status is the check's, so a half
landed fix fails here.

Usage:
    ./install-entry.py col_d1e334e5
    ./install-entry.py col_d1e334e5 col_b5aa9739
    ANKI_MEDIA="/path/to/collection.media" ./install-entry.py col_d1e334e5
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
STEPS = (
    ("install-anki-media.py", "--all"),
    ("install-anki-note.py", None),
    ("check-collection.py", "--key"),
)


def main() -> int:
    summary = __doc__.splitlines()[0] if __doc__ else None
    parser = argparse.ArgumentParser(description=summary)
    parser.add_argument("keys", nargs="+", help="media keys (col_d1e334e5)")
    args = parser.parse_args()

    for key in args.keys:
        print(f"\n== {key} ==", flush=True)
        for script, flag in STEPS:
            command = [sys.executable, str(SCRIPT_DIR / script), key]
            if flag:
                command.insert(2, flag)
            print(f"  {script} {flag or ''}".rstrip(), flush=True)
            result = subprocess.run(command, check=False)
            # The check is the verdict; a failure in an installer stops the pair at once.
            if result.returncode != 0:
                print(f"  failed: {script} exited {result.returncode}", flush=True)
                return result.returncode

    print("\nclips installed, note text in place: the collection matches src/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
