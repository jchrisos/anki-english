"""Shared plumbing for reading and writing the live Anki collection.

The content scripts need the same three things: which profile Anki is using, what a note
should say given its source entry, and how a note is keyed. They live here rather than in
each script because the installer writes what the checker verifies — a second copy of the
field map could write a sentence that the check then calls clean.

Anki owns `collection.anki2` while it runs and rewrites it on exit, so every writer here
refuses to start unless Anki is quit.
"""
from __future__ import annotations

import hashlib
import html
import re
import sqlite3
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from deck_common import (
    GUID_PREFIX,
    VERB_TEXT_KEYS,
    bold_markup,
    is_verb,
    layout,
    load_entries,
    media_key,
)

ANKI_ROOT = Path.home() / "Library" / "Application Support" / "Anki2"

# Anki separates a note's fields with U+001F and pads the tag list with spaces.
SEPARATOR = "\x1f"

# The note type's field order is pinned by the model id, so it is safe to index into. Text
# fields only: the audio and image fields hold media references, which reach the collection
# by name through `install-anki-media.py`, not by import. The verb block sits between the
# clips and the authored example (`Example` is the second-to-last field).
TEXT_FIELDS = (("phrase", 0), ("pronunciation", 1), ("definition", 2))
VERB_FIELD_BASE = 6
EXAMPLE_FIELD = 14
SORT_FIELD = 0

MEDIA_TAG_RE = re.compile(r"<[^>]+>|\[sound:[^\]]*\]")


def anki_running() -> bool:
    return subprocess.run(
        ["pgrep", "-x", "Anki"], check=False, capture_output=True
    ).returncode == 0


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


def collection_path(media_dir: Path) -> Path:
    collection = media_dir.with_suffix(".anki2")
    if not collection.is_file():
        sys.exit(f"no collection at {collection}")
    return collection


def open_collection(collection: Path, write: bool = False) -> sqlite3.Connection:
    """Open the collection read-only by default, or read-write after the Anki guard."""
    if write and anki_running():
        sys.exit("Anki is running — quit it first: the collection is rewritten on exit.")
    # `as_uri()` percent-encodes the space in the profile name ("User 1"); a raw path in the
    # `file:` URI makes sqlite read the name as truncated and report "unable to open".
    uri = collection.resolve().as_uri() + ("" if write else "?mode=ro")
    return sqlite3.connect(uri, uri=True)


def card_text(value: object) -> str:
    """Escape an authored field the way `build_decks.card_text` does.

    Mirrored rather than imported: `build_decks` imports genanki, which only the repo's
    `.venv` has, and these scripts run under the plain interpreter like their siblings.
    Quotes stay unescaped on purpose — the value lands in a text node, and `don&#x27;t` would
    break Anki's own search.
    """
    return html.escape(str(value), quote=False)


def expected_fields(entry: dict) -> list[tuple[str, int, str]]:
    """The rendered value of every text field this entry's note should carry."""
    fields = [(key, index, card_text(entry[key])) for key, index in TEXT_FIELDS]
    if is_verb(entry):
        fields += [
            (key, VERB_FIELD_BASE + offset, bold_markup(card_text(entry[key])))
            for offset, key in enumerate(VERB_TEXT_KEYS)
        ]
    fields.append(("example", EXAMPLE_FIELD, bold_markup(card_text(entry["example"]))))
    return fields


def expected_tags(entry: dict) -> set[str]:
    """The tags the build sets. User-added tags are extra and never removed."""
    return {f"category::{c}" for c in entry["categories"]} | {
        f"level::{entry['level']}",
        f"pos::{entry['pos']}",
    }


def entries(kinds: list[str] | None = None) -> Iterator[tuple[str, dict, str, str]]:
    """Yield `(kind, entry, media key, GUID)` for every written entry in src/."""
    lay = layout(False)
    for kind in kinds or sorted(GUID_PREFIX):
        for entry in load_entries(lay, kind):
            key = media_key(GUID_PREFIX[kind], entry)
            yield kind, entry, key, guid_for(kind, entry)


def guid_for(kind: str, entry: dict) -> str:
    return f"{GUID_PREFIX[kind]}:{entry['phrase']}:{entry['sense']}"


def split_fields(flds: str) -> list[str]:
    return flds.split(SEPARATOR)


def split_tags(tags: str) -> set[str]:
    return set(tags.split())


def join_tags(tags: set[str]) -> str:
    return f" {' '.join(sorted(tags))} " if tags else ""


def field_checksum(value: str) -> int:
    """Anki's note checksum: the first 8 hex digits of the sha1 of the sort field.

    Only needed when field 0 changes; it keys Anki's duplicate detection, so a stale value
    would make the note invisible to "duplicate" lookups.
    """
    stripped = MEDIA_TAG_RE.sub("", value)
    return int(hashlib.sha1(stripped.encode()).hexdigest()[:8], 16)
