#!/usr/bin/env python3
"""Merge one authored batch into the vocabulary manifest and source.

The batch is produced outside this script, in a staging directory, by an authoring agent
that writes two kinds of files:

- `plan.csv` — 50 rows with **no header**, one row per sense, in the manifest's column order:
  `kind,phrase,sense,pos,level,categories,gloss`;
- `entries_01.json` … `entries_05.json` — arrays of card objects, in the same order as the plan.

Nothing is written to `src/` until the whole batch passes the same checks as
`lint_content.py`: the plan and the cards must agree on `phrase`, `sense`, `pos`, `level` and
`categories`, every card must pass the source rules, and no phrase may already exist in the
deck. A failure prints `error:` lines and exits non-zero, leaving `src/` untouched.

The illustration key is not authored: it is the stable media key derived from
`phrase + sense`, exactly as `tools/build_audio.py` derives the audio filenames.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from deck_common import (
    GUID_PREFIX,
    VERB_TEXT_KEYS,
    is_verb,
    media_key,
)
from lint_content import MANIFEST_COLUMNS, Report, check_manifest, check_source

MANIFEST_PATH = Path("src/index.csv")
SOURCE_PATH = Path("src/vocabulary.json")
USED_PATH = Path("tests/batch/used.txt")

# Source key order used by every finished entry.
KEY_ORDER = ("phrase", "pos", "sense", "pronunciation", "definition", "categories", "level")
VERB_ORDER = (
    "present_example",
    "past_simple_example",
    "past_participle_example",
    "present_participle_example",
)
TAIL_ORDER = ("image", "image_brief", "example")


class BatchError(Exception):
    pass


def read_plan(path: Path) -> list[dict]:
    if not path.is_file():
        raise BatchError(f"{path}: plan.csv is missing")
    rows: list[dict] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for line, raw in enumerate(csv.reader(handle), 1):
            if not raw:
                continue
            if len(raw) != len(MANIFEST_COLUMNS):
                raise BatchError(
                    f"{path}:{line}: expected {len(MANIFEST_COLUMNS)} columns, got {len(raw)}"
                )
            row = dict(zip(MANIFEST_COLUMNS, (value.strip() for value in raw)))
            row["_line"] = line
            rows.append(row)
    return rows


def read_entries(chunk_dir: Path) -> list[dict]:
    files = sorted(chunk_dir.glob("entries_*.json"))
    if not files:
        raise BatchError(f"{chunk_dir}: no entries_*.json files")
    entries: list[dict] = []
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise BatchError(f"{path}: invalid JSON ({exc})") from exc
        if not isinstance(payload, list):
            raise BatchError(f"{path}: must contain a JSON array")
        entries.extend(payload)
    return entries


def load_manifest(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [row for row in reader]


def split_categories(value) -> list[str]:
    if isinstance(value, list):
        return [str(part).strip() for part in value if str(part).strip()]
    return [part.strip() for part in str(value).split(";") if part.strip()]


def check_batch(plan: list[dict], entries: list[dict], existing: list[dict], level: str) -> None:
    report = Report()
    check_manifest(plan, report)

    for row in plan:
        if row["kind"] != "vocabulary":
            report.error(f"{row['_line']}: kind must be vocabulary, got {row['kind']!r}")
        if row["level"] != level:
            report.error(f"{row['_line']}: level must be {level}, got {row['level']!r}")

    if len(plan) != 50:
        report.error(f"plan.csv: expected 50 rows, got {len(plan)}")
    if len(entries) != 50:
        report.error(f"source: expected 50 entries, got {len(entries)}")

    manifest = {(row["kind"], row["phrase"], row["sense"]): row for row in plan}
    seen: dict[tuple[str, str, str], str] = {}
    for entry in entries:
        check_source(entry, "vocabulary", manifest, report, seen)

    known = {row["phrase"] for row in existing}
    for row in plan:
        if row["phrase"] in known:
            report.error(f"{row['_line']}: {row['phrase']!r} is already in the manifest")
        known.add(row["phrase"])

    for error in report.errors:
        print(f"error: {error}", file=sys.stderr)
    for warning in report.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if report.errors:
        raise BatchError(f"{len(report.errors)} batch error(s); src/ was not changed")


def normalize(entry: dict) -> dict:
    keys = KEY_ORDER + (VERB_ORDER if is_verb(entry) else ()) + TAIL_ORDER
    missing = [key for key in keys if key not in entry and key != "image"]
    extra = [key for key in entry if key not in keys]
    if missing:
        raise BatchError(f"{entry.get('phrase')}: missing keys {missing}")
    if extra:
        raise BatchError(f"{entry.get('phrase')}: unexpected keys {extra}")
    entry["image"] = media_key(GUID_PREFIX["vocabulary"], entry)
    return {key: entry[key] for key in keys}


def append_manifest(rows: list[dict]) -> None:
    with MANIFEST_PATH.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        for row in rows:
            writer.writerow([row[column] for column in MANIFEST_COLUMNS])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--chunk-dir", required=True, type=Path)
    parser.add_argument("--level", required=True, help="expected CEFR level of the batch")
    args = parser.parse_args()

    try:
        plan = read_plan(args.chunk_dir / "plan.csv")
        entries = read_entries(args.chunk_dir)
        existing_rows = load_manifest(MANIFEST_PATH)
        existing_entries = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))

        check_batch(plan, entries, existing_rows, args.level)
        normalized = [normalize(entry) for entry in entries]

        append_manifest(plan)
        SOURCE_PATH.write_text(
            json.dumps(existing_entries + normalized, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        USED_PATH.parent.mkdir(parents=True, exist_ok=True)
        with USED_PATH.open("a", encoding="utf-8") as handle:
            for row in plan:
                handle.write(row["phrase"] + "\n")
    except BatchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    total = len(existing_entries) + len(normalized)
    print(f"merged {args.chunk_dir.name}: +{len(normalized)} entries, vocabulary={total}/5500")
    return 0


if __name__ == "__main__":
    sys.exit(main())
