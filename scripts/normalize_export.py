"""Normalize any ticket export into the one shape the masking pipeline expects.

Every helpdesk exports a different schema. Rather than making each new client a
code change or a new set of CLI flags, this collapses an arbitrary export into:

    [{"ticket_id": "...", "text": "..."}, ...]

so the rest of the pipeline runs with fixed arguments every time.

Detection is reported, never silent. The point is that someone can read the
output, disagree, and override with --id-field / --text-fields — not that the
guess is always right.

Usage:
    python scripts/normalize_export.py "Ticket examples/export.json"
    python scripts/normalize_export.py export.csv --text-fields subject,body -o data/in/norm.json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from pathlib import Path

#: Checked in order; the first one that is present and near-unique wins.
ID_CANDIDATES = (
    "ticket_id", "case_number", "casenumber", "incident_id", "issue_key",
    "ticket", "case", "number", "key", "id", "reference", "ref",
)

#: Field names that are never article prose, whatever their length.
NOT_PROSE = re.compile(
    r"url|link|href|filename|file_name|path|digest|hash|guid|uuid"
    r"|^id$|_id$|size|depth|count|votes|score"
    r"|date|time|created|updated|modified|age|activity"
    r"|status|state|category|tags?$|type|visibility|source|forum|team"
    r"|email|phone|owner|assignee|responsible|author",
    re.IGNORECASE,
)

URL_RE = re.compile(r"https?://|www\.")

#: Subject lines are short by nature and would never clear the length bar, but
#: they carry the problem statement and belong at the top of the text.
TITLE_HINTS = ("subject", "title", "headline", "short_description", "summary_line")

#: A field has to average at least this many characters to count as prose.
MIN_MEAN_LENGTH = 40


def load_records(path: Path) -> list[dict]:
    """Pull the record array out of a .json / .jsonl / .csv export."""
    suffix = path.suffix.lower()

    if suffix in {".jsonl", ".ndjson"}:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    if suffix == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    if suffix != ".json":
        raise SystemExit(f"Unsupported export format: {path.suffix}. Use .csv, .json or .jsonl")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload

    # Wrapped in a named key, and the name varies by vendor: "tickets",
    # "Public tickets", "results", "issues".
    arrays = [value for value in payload.values() if isinstance(value, list)]
    if len(arrays) == 1:
        return arrays[0]
    if not arrays:
        raise SystemExit(f"No array of records found. Top-level keys: {sorted(payload)}")
    raise SystemExit(
        f"Ambiguous export: {len(arrays)} top-level arrays. "
        f"Keys: {sorted(payload)}. Extract the right one first."
    )


def detect_id_field(records: list[dict]) -> str | None:
    """First candidate field whose values are present and effectively unique."""
    present = {key for record in records for key in record}
    for candidate in ID_CANDIDATES:
        match = next((key for key in present if key.lower() == candidate), None)
        if not match:
            continue
        values = [str(record.get(match) or "").strip() for record in records]
        filled = [v for v in values if v]
        if len(filled) == len(records) and len(set(filled)) >= len(records) * 0.95:
            return match
    return None


def _populated(records: list[dict], key: str) -> list[str]:
    values = [record.get(key) for record in records]
    return [v for v in values if isinstance(v, str) and v.strip()]


def detect_text_fields(records: list[dict]) -> list[str]:
    """Subject-style fields first, then any field long enough to be prose."""
    present = sorted({key for record in records for key in record})
    chosen = []

    # Titles lead, so the problem statement is the first thing the model reads.
    for key in present:
        if key.lower() in TITLE_HINTS and len(_populated(records, key)) >= len(records) * 0.5:
            chosen.append(key)

    for key in present:
        if key in chosen or NOT_PROSE.search(key):
            continue
        values = [record.get(key) for record in records]
        strings = [v for v in values if isinstance(v, str) and v.strip()]
        if len(strings) < len(records) * 0.5:
            continue
        if statistics.mean(len(v) for v in strings) < MIN_MEAN_LENGTH:
            continue
        if sum(1 for v in strings if URL_RE.search(v)) > len(strings) * 0.5:
            continue
        chosen.append(key)
    return chosen


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize a ticket export for the masking pipeline.")
    parser.add_argument("export", help="path to the raw export (.json / .jsonl / .csv)")
    parser.add_argument("-o", "--out", default="data/in/normalized.json")
    parser.add_argument("--id-field", help="override the detected id field")
    parser.add_argument("--text-fields", help="override detected text fields (comma-separated)")
    parser.add_argument("--min-chars", type=int, default=30,
                        help="drop records whose combined text is shorter than this")
    args = parser.parse_args()

    source = Path(args.export)
    if not source.exists():
        raise SystemExit(f"No such file: {source}")

    records = load_records(source)
    if not records:
        raise SystemExit(f"{source} contains no records")

    available = sorted({key for record in records for key in record})
    print(f"{source.name}: {len(records)} records")
    print(f"fields: {', '.join(available)}\n")

    id_field = args.id_field or detect_id_field(records)
    if args.id_field and args.id_field not in available:
        raise SystemExit(f"--id-field {args.id_field!r} not in export. Available: {available}")

    if args.text_fields:
        text_fields = [f.strip() for f in args.text_fields.split(",")]
        missing = [f for f in text_fields if f not in available]
        if missing:
            raise SystemExit(f"--text-fields not in export: {missing}. Available: {available}")
    else:
        text_fields = detect_text_fields(records)

    print(f"id field    : {id_field or 'NONE — falling back to row number'}")
    print(f"text fields : {', '.join(text_fields) if text_fields else 'NONE'}")
    if not text_fields:
        raise SystemExit(
            "\nNo prose fields detected. Name them explicitly:\n"
            f"  --text-fields <one of: {', '.join(available)}>"
        )

    rows, skipped = [], 0
    for index, record in enumerate(records, start=1):
        ticket_id = str(record.get(id_field) or "").strip() if id_field else ""
        if not ticket_id:
            ticket_id = f"row-{index}"
        text = "\n\n".join(
            str(record.get(field) or "").strip()
            for field in text_fields
            if str(record.get(field) or "").strip()
        )
        if len(text) < args.min_chars:
            skipped += 1
            continue
        rows.append({"ticket_id": ticket_id, "text": text})

    if not rows:
        raise SystemExit("Every record was empty or below --min-chars")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    mean_length = statistics.mean(len(r["text"]) for r in rows)
    print(f"\nkept {len(rows)} records ({skipped} below --min-chars), mean {mean_length:.0f} chars")
    print(f"written to {out_path}")
    print(f"\nnext:\n  ticketmask mask {out_path} --id-field ticket_id --text-fields text --out data/out")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
