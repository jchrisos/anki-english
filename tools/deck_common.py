"""Shared constants and helpers for the deck tools.

Everything that decides a note's identity lives here: the kind prefixes, the media key and
the spoken script. `build_decks.py` and `build_audio.py` both import it so the image, the
mp3 and the note can never disagree about what an entry is called.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# The reviewed plan, one row per sense, in the same `src/` or `tests/src/` tree as the cards.
MANIFEST_NAME = "index.csv"

# Sense slugs are stable identity — half of a note's GUID — so the shape is part of the
# contract and lives here rather than in one of the tools that has to enforce it.
SENSE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


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
# The source field may name the file with or without an extension; these are the extensions
# that are looked up for a bare stem.
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp")

# The source key that names the illustration. Midjourney renders happen outside the repo and
# are pasted into `media/` by hand, so the filename is authored in the entry instead of being
# derived from the phrase: `"image": "voc_6a648cec.jpg"`.
IMAGE_FIELD = "image"

LEVELS = ("a1", "a2", "b1", "b2", "c1", "c2")

# Production scope per deck. A grade outside the deck's range is a source error, not a card
# with a level the deck is not meant to teach (C1 is the top of Vocabulary; the other two stop
# at B2). `LEVELS` stays the full CEFR vocabulary so the tags and templates do not depend on
# this table.
KIND_LEVELS = {
    "vocabulary": ("a1", "a2", "b1", "b2", "c1"),
    "phrasal-verbs": ("a1", "a2", "b1", "b2"),
    "collocations": ("a1", "a2", "b1", "b2"),
}

# Card-count targets for the production decks. Planning targets, not build assertions: content
# arrives in batches, so a build only reports how far along it is. The same numbers live in
# AGENTS.md and `.okf/concepts/deck-schema.md`.
KIND_TARGET_CARDS = {
    "vocabulary": 5500,
    "phrasal-verbs": 350,
    "collocations": 800,
}

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

# Keys that belonged to the retired movie/TV quote block. They are not silently ignored: a
# source entry still carrying one is a build error, so stale content is cleaned up rather than
# imported with part of its data missing.
REMOVED_KEYS = ("dialog", "source", "speaker_gender")

REQUIRED_TEXT_FIELDS = (
    "phrase",
    "sense",
    "pronunciation",
    "definition",
    "example",
)

# Extra text a **verb** carries: one short example sentence per form, shown as the block under
# the authored example. The sentences are authored: a real line that happens to
# use `paid attention` or `fastened your seatbelt` in the past barely exists, and inventing a
# credit is worse than not having one. Absent on every other part of speech, and required on
# `pos::verb`, so a verb card cannot render an empty example row — the same fail-loud rule as
# a missing image. The last key is the `-ing` form (present participle); it is its own row
# because continuous forms are the third shape a learner uses far more often than the perfect.
VERB_TEXT_KEYS = (
    "present_example",
    "past_simple_example",
    "past_participle_example",
    "present_participle_example",
)

# The target is shown in **bold** inside every authored example, because an example is read as a
# sentence first and the learner has to see which words are the item being taught. The author
# marks those words with `**...**`: a phrase inflects and sometimes splits (`pick yourself up`,
# `made that mistake`), so the span cannot be recomputed from `phrase` at build time. Markup is
# stripped before the text is spoken — the voice must not read the asterisks.
MARKUP = "**"
MARKUP_RE = re.compile(r"\*\*(.+?)\*\*")


def markup_spans(text: str) -> list[str]:
    return MARKUP_RE.findall(text)


def strip_markup(text: str) -> str:
    return text.replace(MARKUP, "")


def bold_markup(text: str) -> str:
    """Turn the author's `**target**` into the `<b>` the card renders."""
    return MARKUP_RE.sub(r"<b>\1</b>", text)


def identity_problem(phrase: str, sense: str) -> str | None:
    """Why `phrase` + `sense` cannot be a note GUID, or `None` when they can.

    The GUID is `prefix:phrase:sense` and Anki matches notes by it, so both halves are
    identity: a trailing space, a capital or a colon changes the GUID without changing the
    card, which starts its review history over on the next import. Empty values are left to
    the caller's required-field check. The build and the lint both call this, so the two can
    never disagree about what a valid identity looks like.
    """
    if not phrase or not sense:
        return None
    if phrase != phrase.strip():
        return "phrase has leading or trailing whitespace"
    if phrase != phrase.lower():
        return "phrase must be lowercase"
    if ":" in phrase:
        return "phrase must not contain ':' (it separates the GUID)"
    if not SENSE_RE.match(sense):
        return f"sense must be a kebab-case slug, got {sense!r}"
    return None


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


def manifest_identities(path: Path) -> set[tuple[str, str, str]]:
    """The plan's `kind + phrase + sense` triples, trimmed exactly as the lint reads them.

    A hand-edited CSV cell can carry a stray space no reviewer can see. Trimming on both
    sides keeps the lint and the build agreeing about the same row, instead of the lint
    accepting `run ` and the build then failing with "not in index.csv".
    """
    with path.open(newline="", encoding="utf-8") as handle:
        return {
            (
                (row.get("kind") or "").strip(),
                (row.get("phrase") or "").strip(),
                (row.get("sense") or "").strip(),
            )
            for row in csv.DictReader(handle)
        }


def image_for(layout: Layout, entry: dict) -> Path | None:
    """Return the image the entry names, or `None` when it has none.

    The image is named in the entry's `image` field, never from the media key: the picture is
    rendered by hand outside the repo. The field holds the **name without an extension**
    (`"image": "voc_6a648cec"`); the file's format is whatever exists on disk — `.jpg`,
    `.jpeg`, `.png`, `.gif` or `.webp`. A written extension is stripped and retried against
    the same stem, so a renamed field cannot strand an image, and `IMAGE_EXTS` order stays
    the only tie-breaker: a converted `.jpg` always beats a stale `.png` left in `media/`,
    however the entry spells the name.
    A missing file is not an error — the card is built without the illustration rather than
    with a broken `<img>`.
    """
    name = str(entry.get(IMAGE_FIELD) or "").strip()
    if not name:
        return None
    path = layout.media / name
    stem = path.with_suffix("") if path.suffix.lower() in IMAGE_EXTS else path
    candidates = [stem.with_name(stem.name + ext) for ext in IMAGE_EXTS]
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def audio_file(layout: Layout, key: str, part: str) -> Path:
    """One mp3 per spoken part: `word`, `explanation`, `example`, and the verb rows."""
    return layout.media / f"{key}-{part}.mp3"


# Spoken parts, in the order they are played. Each gets its own mp3: a learner replays the
# example far more often than the definition, and one long clip makes that impossible.
# `example` is the authored sentence under the definition: a second usage of the target.
AUDIO_PARTS = ("word", "explanation", "example")

# Verb-only clips: one per example row under the authored example. Ordered after the base
# three so a non-verb note keeps exactly the three files it always had.
VERB_AUDIO_PARTS = (
    "present-example",
    "past-simple-example",
    "past-participle-example",
    "present-participle-example",
)


def audio_parts(entry: dict) -> tuple[str, ...]:
    """Every clip this entry needs: three, or seven when it is a verb."""
    return AUDIO_PARTS + VERB_AUDIO_PARTS if is_verb(entry) else AUDIO_PARTS


def is_verb(entry: dict) -> bool:
    """The tag decides, not the spelling: a noun sense of `run` is not a verb card."""
    return entry.get("pos") == "verb"


# Pinned voice. Every part is read by the same woman: nothing on the card is a character's
# line any more, so there is no gender to match.
VOICE_FEMALE = "en-US-AvaNeural"
RATE = "-10%"


# Parts whose text is the authored field of the same name (plus the four verb examples).
PLAIN_PART_KEYS = {
    "example": "example",
    "present-example": "present_example",
    "past-simple-example": "past_simple_example",
    "past-participle-example": "past_participle_example",
    "present-participle-example": "present_participle_example",
}


def part_text(entry: dict, part: str) -> str:
    # Not a dict literal over every part: a non-verb has no example keys, and building the
    # whole mapping would raise KeyError on the parts it will never be asked for.
    if part == "word":
        return entry["phrase"]
    if part == "explanation":
        return entry["definition"]
    # Authored examples carry `**` around the target for the card; the voice reads plain text.
    return strip_markup(entry[PLAIN_PART_KEYS[part]])
