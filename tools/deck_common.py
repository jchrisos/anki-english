"""Shared constants and helpers for the deck tools.

Everything that decides a note's identity lives here: the kind prefixes, the media key and
the spoken script. `build_decks.py` and `build_audio.py` both import it so the image, the
mp3 and the note can never disagree about what an entry is called.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Layout:
    """Where a build reads its inputs and writes its packages.

    Production and test builds are physically separate trees: production owns `src/`,
    `media/` and `decks/` at the repo root, while every test artifact — source, media and
    packages — lives under `tests/`, which is gitignored as a whole. Test content can
    therefore never be committed or mistaken for production content.
    """

    src: Path
    media: Path
    out: Path


def layout(test: bool) -> Layout:
    if test:
        base = REPO_ROOT / "tests"
        return Layout(base / "src", base / "media", base / "decks")
    return Layout(REPO_ROOT / "src", REPO_ROOT / "media", REPO_ROOT / "decks")

# Kind prefix is the first half of the note GUID and of every media filename.
GUID_PREFIX = {
    "vocabulary": "voc",
    "phrasal-verbs": "pv",
    "collocations": "col",
}

# Order matters: the first extension found wins, so a converted .jpg beats a stale .png.
IMAGE_EXTS = (".jpg", ".png", ".webp")

LEVELS = ("a1", "a2", "b1", "b2", "c1", "c2")

# Part of speech of the sense being taught. Single-valued, so it gets its own namespace:
# `tag:pos::verb` stays exact and never mixes with themes or levels.
ALLOWED_POS = frozenset(
    """
    noun verb adjective adverb pronoun preposition conjunction interjection
    determiner numeral modal-verb auxiliary-verb
    """.split()
)

# Controlled list. Reuse a slug before inventing a near-duplicate: `car` vs `vehicle`
# would silently split one filter into two.
ALLOWED_CATEGORIES = frozenset(
    """
    color car travel kitchen food work money daily-routine emotions body home
    technology nature time relationships health education sports shopping weather
    communication transport clothes animals city music
    """.split()
)

REQUIRED_TEXT_FIELDS = ("phrase", "sense", "pronunciation", "definition", "dialog", "source")

# Prefix on the GUID of a test build. Deck/model ids and names already differ, but Anki
# also matches notes by GUID, so a rehearsal must not share one with production.
TEST_GUID_PREFIX = "test:"


def media_key(prefix: str, entry: dict) -> str:
    """Return the stable key shared by an entry's image, mp3 and filename references."""
    seed = f"{prefix}:{entry['phrase']}:{entry['sense']}"
    return f"{prefix}_{hashlib.sha1(seed.encode()).hexdigest()[:8]}"


def load_entries(layout: Layout, slug: str) -> list[dict]:
    path = layout.src / f"{slug}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def image_file(layout: Layout, key: str) -> Path:
    for ext in IMAGE_EXTS:
        path = layout.media / f"{key}{ext}"
        if path.exists():
            return path
    exts = "|".join(e.lstrip(".") for e in IMAGE_EXTS)
    raise FileNotFoundError(f"{layout.media}/{key}.{{{exts}}} is missing")


def audio_file(layout: Layout, key: str, part: str) -> Path:
    """One mp3 per spoken part: `word`, `explanation`, `dialog`."""
    return layout.media / f"{key}-{part}.mp3"


def dialog_line(entry: dict) -> str:
    """The quoted line alone, without the attribution or the quotation marks."""
    dialog = entry["dialog"]
    for sep in (" — ", " – ", " - "):
        if sep in dialog:
            dialog = dialog.rsplit(sep, 1)[0]
            break
    return dialog.strip().strip('"“”').strip()


# Spoken parts, in the order they are played. Each gets its own mp3: a learner replays the
# movie line far more often than the definition, and one long clip makes that impossible.
AUDIO_PARTS = ("word", "explanation", "dialog")

# Pinned voices. The word and the explanation are always the same woman; the dialog follows
# the character who says the line, so a male character is not read by a female voice.
VOICE_FEMALE = "en-US-AvaNeural"
VOICE_MALE = "en-US-AndrewNeural"
RATE = "-10%"

SPEAKER_GENDERS = ("female", "male")


def part_text(entry: dict, part: str) -> str:
    return {
        "word": entry["phrase"],
        "explanation": entry["definition"],
        "dialog": dialog_line(entry),
    }[part]


def part_voice(entry: dict, part: str) -> str:
    if part == "dialog":
        return VOICE_MALE if entry["speaker_gender"] == "male" else VOICE_FEMALE
    return VOICE_FEMALE
