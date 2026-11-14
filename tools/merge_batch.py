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

Both output files are replaced in one step each, source first: if the run dies between them,
the source holds cards whose plan row is missing, which the lint reports as an error. The
other order would leave rows with no cards — the state the workflow already treats as normal
progress ("planned but not written yet") — so a half-merged batch would look healthy. The
guard in `check_batch` then refuses the rerun: a phrase already in the manifest, or a
phrase+sense pair already in the source, is an error, so a partial merge is repaired by hand
instead of appended twice. Paths are resolved from the repo root rather than the working
directory, so the script cannot write to a second `src/` by being run from the wrong place,
and `--test` rehearses the merge against `tests/src/`.

The illustration key is not authored: it is the stable media key derived from
`phrase + sense`, exactly as `tools/build_audio.py` derives the audio filenames.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

from deck_common import (
    GUID_PREFIX,
    KIND_TARGET_CARDS,
    MANIFEST_NAME,
    REPO_ROOT,
    VERB_TEXT_KEYS,
    is_verb,
    layout,
    media_key,
)
from lint_content import MANIFEST_COLUMNS, Report, check_manifest, check_source

# Record of which phrases a previous batch already claimed. Always the test tree: it is
# gitignored scratch, never production input.
USED_PATH = REPO_ROOT / "tests" / "batch" / "used.txt"

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


def check_batch(
    plan: list[dict],
    entries: list[dict],
    existing_rows: list[dict],
    existing_entries: list[dict],
    level: str,
) -> None:
    """Refuse a batch that disagrees with itself, with its plan, or with what is merged.

    The source is checked as well as the manifest: a run that was interrupted between the two
    writes already has the cards in `vocabulary.json`, and appending them a second time would
    duplicate every note without any check noticing.
    """
    report = Report()
    check_manifest(plan, report, name="plan.csv")

    for row in plan:
        if row["kind"] != "vocabulary":
            report.error(f"plan.csv:{row['_line']}: kind must be vocabulary, got {row['kind']!r}")
        if row["level"] != level:
            report.error(
                f"plan.csv:{row['_line']}: level must be {level}, got {row['level']!r}"
            )

    if len(plan) != 50:
        report.error(f"plan.csv: expected 50 rows, got {len(plan)}")
    if len(entries) != 50:
        report.error(f"source: expected 50 entries, got {len(entries)}")

    manifest = {(row["kind"], row["phrase"], row["sense"]): row for row in plan}
    seen: dict[tuple[str, str, str], str] = {}
    for entry in entries:
        check_source(entry, "vocabulary", manifest, report, seen)

    known = {row["phrase"] for row in existing_rows}
    for row in plan:
        if row["phrase"] in known:
            report.error(f"plan.csv:{row['_line']}: {row['phrase']!r} is already in the manifest")
        known.add(row["phrase"])

    merged = {
        (str(entry.get("phrase") or ""), str(entry.get("sense") or ""))
        for entry in existing_entries
    }
    for row in plan:
        if (row["phrase"], row["sense"]) in merged:
            report.error(
                f"plan.csv:{row['_line']}: {row['phrase']!r} ({row['sense']}) "
                "is already in the source"
            )

    for error in report.errors:
        print(f"error: {error}", file=sys.stderr)
    for warning in report.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if report.errors:
        raise BatchError(f"{len(report.errors)} batch error(s); nothing was written")


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


def render_manifest_rows(rows: list[dict], terminator: str) -> bytes:
    """Render plan rows exactly like the manifest's own writer, so the append is byte-clean.

    The terminator is taken from the file being appended to: the production manifest is
    `\r\n` and the test one is `\n`, and rewriting the whole file just to normalize it would
    turn a 50-row append into a 6,650-line diff.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator=terminator)
    for row in rows:
        writer.writerow([row[column] for column in MANIFEST_COLUMNS])
    return buffer.getvalue().encode("utf-8")


def replace_atomically(path: Path, data: bytes) -> None:
    """Replace `path` in one step, so an interrupted run cannot leave it truncated."""
    staged = path.with_name(path.name + ".tmp")
    try:
        staged.write_bytes(data)
        staged.replace(path)
    finally:
        staged.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--chunk-dir", required=True, type=Path)
    parser.add_argument("--level", required=True, help="expected CEFR level of the batch")
    parser.add_argument(
        "--test",
        action="store_true",
        help="merge into tests/src (gitignored) instead of src/",
    )
    args = parser.parse_args()

    lay = layout(args.test)
    manifest_path = lay.src / MANIFEST_NAME
    source_path = lay.src / "vocabulary.json"

    try:
        if not manifest_path.is_file():
            raise BatchError(f"{manifest_path}: manifest is missing; nothing to merge into")
        if not source_path.is_file():
            raise BatchError(f"{source_path}: source is missing; nothing to merge into")

        plan = read_plan(args.chunk_dir / "plan.csv")
        entries = read_entries(args.chunk_dir)
        existing_rows = load_manifest(manifest_path)
        try:
            existing_entries = json.loads(source_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise BatchError(f"{source_path}: invalid JSON ({exc})") from exc

        check_batch(plan, entries, existing_rows, existing_entries, args.level)
        normalized = [normalize(entry) for entry in entries]

        source_text = json.dumps(
            existing_entries + normalized, indent=2, ensure_ascii=False
        ) + "\n"
        manifest_bytes = manifest_path.read_bytes()
        terminator = "\r\n" if manifest_bytes.endswith(b"\r\n") else "\n"
        if not manifest_bytes.endswith(b"\n"):
            manifest_bytes += terminator.encode()
        manifest_bytes += render_manifest_rows(plan, terminator)

        # Source first, then the manifest: see the module docstring. Each replace is atomic,
        # so an interruption leaves cards whose plan row is missing — a state the lint
        # reports — and the source guard in `check_batch` refuses to append them twice.
        replace_atomically(source_path, source_text.encode("utf-8"))
        replace_atomically(manifest_path, manifest_bytes)

        USED_PATH.parent.mkdir(parents=True, exist_ok=True)
        with USED_PATH.open("a", encoding="utf-8") as handle:
            for row in plan:
                handle.write(row["phrase"] + "\n")
    except (BatchError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    total = len(existing_entries) + len(normalized)
    print(
        f"merged {args.chunk_dir.name}: +{len(normalized)} entries, "
        f"vocabulary={total}/{KIND_TARGET_CARDS['vocabulary']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
