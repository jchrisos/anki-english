#!/usr/bin/env python3
"""Lint the content manifest and the source entries before cards are built.

The manifest — `src/index.csv` — is the reviewed plan, not the cards: one row per *sense*
(`kind,phrase,sense,pos,level,categories,gloss`). Fixing 900 glosses is cheap; fixing 900
finished cards is not, and re-slugging a sense after import would orphan review history. So
the manifest is written and deduplicated first, then `src/<kind>.json` fills the rows in.

This tool checks both halves:

- the manifest itself (known kind, kebab-case sense, level inside the deck's range, known
  part of speech and categories, unique `kind + phrase + sense`);
- every source entry (in the manifest, agrees with its manifest row, required text present,
  IPA in slashes, target bolded in each example, verb rows consistent, Midjourney parameters
  at the end of `image_brief`).

It reads the layout exactly like `build_decks.py`: `--test` switches to `tests/src`. It
writes nothing and exits non-zero when any `error:` is reported; `warning:` lines are advice.
`--report` adds the repetition report: example openers, image-brief openers and camera angles,
so a batch that has gone monotone shows up before it is built.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter

from deck_common import (
    ALLOWED_CATEGORIES,
    ALLOWED_POS,
    GUID_PREFIX,
    IMAGE_FIELD,
    KIND_LEVELS,
    KIND_TARGET_CARDS,
    MANIFEST_NAME,
    MARKUP,
    REMOVED_KEYS,
    REQUIRED_TEXT_FIELDS,
    VERB_TEXT_KEYS,
    Layout,
    identity_problem,
    is_verb,
    layout,
    load_entries,
    markup_spans,
)

MANIFEST_COLUMNS = ("kind", "phrase", "sense", "pos", "level", "categories", "gloss")

# Every `image_brief` ends with the shared Midjourney block; the scene text differs, the
# parameters do not. A prompt missing it is not a deck-wide style drift, it is a typo.
IMAGE_PARAMETERS = (
    "--ar 3:2 --raw --s 50 --v 8.2 --no text, signage, watermark, logo, posed smile, "
    "oversaturated, HDR"
)

# Camera positions the briefs are supposed to rotate through. `--report` counts them so one
# angle cannot quietly become the house shot.
CAMERA_POSITIONS = (
    "from behind",
    "from the side",
    "from across the room",
    "over the shoulder",
    "low angle",
    "high angle",
    "wide shot",
)


class Report:
    """Errors fail the lint; warnings are printed and ignored."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def emit(self) -> None:
        for message in self.errors:
            print(f"error: {message}", file=sys.stderr)
        for message in self.warnings:
            print(f"warning: {message}", file=sys.stderr)


def split_categories(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def read_manifest(lay: Layout, report: Report) -> list[dict]:
    path = lay.src / MANIFEST_NAME
    if not path.is_file():
        report.error(f"{path}: manifest is missing (expected columns: {','.join(MANIFEST_COLUMNS)})")
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        header = tuple(reader.fieldnames or ())
        if header != MANIFEST_COLUMNS:
            report.error(
                f"{path}: header must be {','.join(MANIFEST_COLUMNS)}, got {','.join(header)}"
            )
            return []
        rows = []
        for raw in reader:
            # Cells are trimmed: the manifest is hand-edited, a stray space is invisible, and
            # the build trims identically (`deck_common.manifest_identities`). Exact identity
            # is still enforced on the JSON source, where a space would really change the GUID.
            row = {name: (raw.get(name) or "").strip() for name in MANIFEST_COLUMNS}
            row["_line"] = reader.line_num
            rows.append(row)
    return rows


def check_manifest(rows: list[dict], report: Report, name: str = MANIFEST_NAME) -> None:
    """Validate plan rows. `name` is what the row errors point at: the manifest, or a batch's
    `plan.csv` before it is merged into it."""
    seen: dict[tuple[str, str, str], int] = {}
    phrases: dict[str, set[str]] = {}
    for row in rows:
        where = f"{name}:{row['_line']}"
        kind, phrase, sense = row["kind"], row["phrase"], row["sense"]
        label = f"{where} ({phrase or '?'})"

        if kind not in GUID_PREFIX:
            report.error(f"{label}: unknown kind {kind!r}")
            continue
        if not phrase:
            report.error(f"{label}: empty phrase")
        if not sense:
            report.error(f"{label}: empty sense")
        problem = identity_problem(phrase, sense)
        if problem:
            report.error(f"{label}: {problem}")
        if row["pos"] not in ALLOWED_POS:
            report.error(f"{label}: unknown part of speech {row['pos']!r}")
        if row["level"] not in KIND_LEVELS[kind]:
            report.error(
                f"{label}: level must be one of {', '.join(KIND_LEVELS[kind])} "
                f"for {kind}, got {row['level']!r}"
            )
        categories = split_categories(row["categories"])
        if not categories:
            report.error(f"{label}: needs at least one category")
        for category in categories:
            if category not in ALLOWED_CATEGORIES:
                report.error(f"{label}: unknown category {category!r}")
        if not row["gloss"]:
            report.error(f"{label}: empty gloss")

        key = (kind, phrase, sense)
        if key in seen:
            report.error(f"{label}: repeats manifest line {seen[key]}")
        else:
            seen[key] = row["_line"]
        phrases.setdefault(phrase, set()).add(kind)

    for phrase, kinds in phrases.items():
        if len(kinds) > 1:
            report.warn(f"{name}: {phrase!r} is planned in {', '.join(sorted(kinds))}")


def markup_problem(text: str) -> str | None:
    spans = markup_spans(text)
    if not spans:
        return "must bold the target with **...**"
    if any(not span.strip() for span in spans):
        return "has an empty **...** span"
    if text.count(MARKUP) != 2 * len(spans):
        return "has unbalanced ** markers"
    return None


def regular_inflection_warning(entry: dict, example: str) -> str | None:
    """Warn when a single-word verb's example bolds a regular inflected form.

    The example must use the entry's own base form; the four form rows carry the others.
    Only regular spellings are caught — an irregular (`ran`, `wrote`) is left to review
    rather than guessed at, so this never fails a build.
    """
    if entry.get("pos") != "verb" or " " in entry.get("phrase", ""):
        return None
    spans = markup_spans(example)
    if not spans:
        return None
    target = spans[0].lower()
    phrase = entry["phrase"].lower()
    if target == phrase:
        return None
    regular = {phrase + suffix for suffix in ("s", "es", "ed", "d", "ing")}
    if len(phrase) > 2:
        regular.add(phrase + phrase[-1] + "ing")
        regular.add(phrase + phrase[-1] + "ed")
    if target in regular:
        return f"example bolds the inflected form {target!r}; use the base form {phrase!r}"
    return None


def check_source(entry: dict, slug: str, manifest: dict, report: Report, seen: dict) -> None:
    path = f"{slug}.json"
    phrase, sense = str(entry.get("phrase") or ""), str(entry.get("sense") or "")
    label = f"{path}: {phrase or '?'} ({sense or '?'})"

    for field in REQUIRED_TEXT_FIELDS:
        if not str(entry.get(field, "")).strip():
            report.error(f"{label}: empty {field}")
    # The phrase and the sense become the note's GUID; check their shape here too, so a
    # malformed entry is reported as malformed instead of as "not in index.csv".
    problem = identity_problem(phrase, sense)
    if problem:
        report.error(f"{label}: {problem}")
    if not str(entry.get("image_brief", "")).strip():
        report.error(f"{label}: empty image_brief")
    elif not str(entry["image_brief"]).endswith(IMAGE_PARAMETERS):
        report.error(f"{label}: image_brief must end with {IMAGE_PARAMETERS}")

    pronunciation = str(entry.get("pronunciation", ""))
    if pronunciation and (not pronunciation.startswith("/") or not pronunciation.endswith("/")):
        report.error(f"{label}: pronunciation must be IPA in slashes")

    if entry.get("level") not in KIND_LEVELS[slug]:
        report.error(
            f"{label}: level must be one of {', '.join(KIND_LEVELS[slug])}, "
            f"got {entry.get('level')!r}"
        )
    if entry.get("pos") not in ALLOWED_POS:
        report.error(f"{label}: unknown part of speech {entry.get('pos')!r}")
    categories = entry.get("categories") or []
    if not categories:
        report.error(f"{label}: needs at least one category")
    for category in categories:
        if category not in ALLOWED_CATEGORIES:
            report.error(f"{label}: unknown category {category!r}")

    removed = [key for key in REMOVED_KEYS if key in entry]
    if removed:
        report.error(f"{label}: remove the retired movie-quote keys {removed}")

    image_name = str(entry.get(IMAGE_FIELD) or "").strip()
    if image_name and "/" in image_name:
        report.error(f"{label}: image must be a bare name, got {image_name!r}")

    markup_fields = ["example"] + (list(VERB_TEXT_KEYS) if is_verb(entry) else [])
    for field in markup_fields:
        problem = markup_problem(str(entry.get(field) or ""))
        if problem:
            report.error(f"{label}: {field} {problem}")

    if is_verb(entry):
        for field in VERB_TEXT_KEYS:
            if not str(entry.get(field, "")).strip():
                report.error(f"{label}: verb needs {field}")
    else:
        stray = [field for field in VERB_TEXT_KEYS if entry.get(field)]
        if stray:
            report.error(f"{label}: {entry.get('pos')} must not carry verb examples {stray}")

    warning = regular_inflection_warning(entry, str(entry.get("example") or ""))
    if warning:
        report.warn(f"{label}: {warning}")

    key = (slug, phrase, sense)
    if key in seen:
        report.error(f"{label}: duplicate phrase+sense within the kind")
    else:
        seen[key] = label

    if not phrase or not sense or slug not in GUID_PREFIX:
        return
    row = manifest.get((slug, phrase, sense))
    if row is None:
        report.error(f"{label}: not in {MANIFEST_NAME}")
        return
    if row["pos"] != entry.get("pos"):
        report.error(f"{label}: pos {entry.get('pos')!r} differs from manifest {row['pos']!r}")
    if row["level"] != entry.get("level"):
        report.error(
            f"{label}: level {entry.get('level')!r} differs from manifest {row['level']!r}"
        )
    if set(split_categories(row["categories"])) != set(categories):
        report.error(
            f"{label}: categories {categories} differ from manifest "
            f"{split_categories(row['categories'])}"
        )


def source_report(rows: list[dict], lay: Layout, report: Report, show_gaps: bool = True) -> None:
    manifest = {(row["kind"], row["phrase"], row["sense"]): row for row in rows}
    written: set[tuple[str, str, str]] = set()
    seen: dict[tuple[str, str, str], str] = {}

    for slug in GUID_PREFIX:
        try:
            entries = load_entries(lay, slug)
        except FileNotFoundError:
            if rows:
                report.warn(f"{lay.src / f'{slug}.json'}: no source entries yet")
            continue
        for entry in entries:
            key = (slug, str(entry.get("phrase") or ""), str(entry.get("sense") or ""))
            written.add(key)
            check_source(entry, slug, manifest, report, seen)

    missing = [key for key in manifest if key not in written]
    if show_gaps and missing:
        print(f"planned but not written yet: {len(missing)}")
    for kind in GUID_PREFIX:
        planned = sum(1 for row in rows if row["kind"] == kind)
        built = sum(1 for key in written if key[0] == kind)
        print(
            f"{kind}: {built}/{KIND_TARGET_CARDS[kind]} written, "
            f"{planned}/{KIND_TARGET_CARDS[kind]} planned"
        )


def repetition_report(entries: list[tuple[str, dict]]) -> None:
    def first_words(text: str, count: int) -> str:
        words = re.findall(r"[a-z']+", re.sub(r"<[^>]+>", " ", text).lower())
        return " ".join(words[:count])

    openers = Counter()
    briefs = Counter()
    cameras = Counter()
    for _, entry in entries:
        openers[first_words(str(entry.get("example", "")), 3)] += 1
        briefs[first_words(str(entry.get("image_brief", "")), 6)] += 1
        for camera in CAMERA_POSITIONS:
            if camera in str(entry.get("image_brief", "")):
                cameras[camera] += 1

    print("\nrepetition report")
    print("  example openers:")
    for opener, count in openers.most_common(5):
        print(f"    {count:>3}  {opener or '(empty)'}")
    print("  image-brief openers:")
    for opener, count in briefs.most_common(5):
        print(f"    {count:>3}  {opener or '(empty)'}")
    print("  camera positions:")
    for camera, count in cameras.most_common():
        print(f"    {count:>3}  {camera}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--test",
        action="store_true",
        help="lint tests/src instead of the production src/",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="add the repetition report for examples and image briefs",
    )
    parser.add_argument(
        "--quiet-gaps",
        action="store_true",
        help="do not list how many planned entries are still unwritten",
    )
    args = parser.parse_args()

    lay = layout(args.test)
    report = Report()
    rows = read_manifest(lay, report)
    check_manifest(rows, report)
    source_report(rows, lay, report, show_gaps=not args.quiet_gaps)

    if args.report:
        entries = []
        for slug in GUID_PREFIX:
            try:
                entries.extend((slug, entry) for entry in load_entries(lay, slug))
            except FileNotFoundError:
                pass
        repetition_report(entries)

    report.emit()
    if report.errors:
        print(
            f"\n{len(report.errors)} error(s), {len(report.warnings)} warning(s)",
            file=sys.stderr,
        )
        return 1
    print(f"\nclean: {len(report.warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
