"""Build the plain sample export from the annotated sample tickets.

samples/tickets.annotated.jsonl is the source of truth: synthetic tickets with
[[TYPE|value]] ground-truth markers. This strips the markers and writes the
export a helpdesk would actually hand over, in the two formats `ticketmask
mask` reads:

    samples/tickets.csv
    samples/tickets.json

Usage:
    python scripts/build_samples.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ticketmask.corpus import MARKER_RE  # noqa: E402

SAMPLES = ROOT / "samples"
COLUMNS = ["ticket_id", "created_at", "status", "product", "severity", "region",
           "subject", "description", "comments"]


def strip(value: str) -> str:
    return MARKER_RE.sub(lambda m: m.group(2), value)


def main() -> int:
    rows = []
    source = SAMPLES / "tickets.annotated.jsonl"
    for line in source.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        record = json.loads(line)
        rows.append({column: strip(str(record.get(column, ""))) for column in COLUMNS})

    with (SAMPLES / "tickets.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    (SAMPLES / "tickets.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"{len(rows)} tickets -> samples/tickets.csv, samples/tickets.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
