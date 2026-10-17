"""Build deny-lists from the structured columns of a ticket export.

Deny-lists are the highest-precision signal the masker has, and an export
already contains them: the same people named in the free text appear as clean,
structured values in the author and assignee columns. Harvesting those beats
asking NER to find them in prose.

Each output file maps to one ontology class, because the ontology declares them
disjoint. Nothing here guesses: a value is only written to the list its column
already means.

Usage:
    python scripts/extract_deny_lists.py "Ticket examples/export.json" --out data/in
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# Export column -> deny-list file. One column, one ontology class.
COLUMN_MAP = {
    "created_by": "customers.txt",       # sup:Contact
    "responsible": "agents.txt",         # sup:SupportAgent
    "completed_by": "agents.txt",        # sup:SupportAgent
    "user_team": "accounts.txt",         # sup:Account
}

# Placeholders and generic bucket values that are not anybody's name.
JUNK = {"-", "", "n/a", "none", "null", "users", "unassigned", "unknown", "public"}


def rows_from(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    arrays = [value for value in payload.values() if isinstance(value, list)]
    if len(arrays) != 1:
        raise SystemExit(f"Cannot find the ticket array. Top-level keys: {sorted(payload)}")
    return arrays[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("export", help="path to the ticket export (.json)")
    parser.add_argument("--out", default="data/in", help="directory to write deny-lists into")
    args = parser.parse_args()

    rows = rows_from(Path(args.export))
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    collected: dict[str, set[str]] = {}
    for row in rows:
        for column, filename in COLUMN_MAP.items():
            value = str(row.get(column) or "").strip()
            if value.lower() in JUNK:
                continue
            collected.setdefault(filename, set()).add(value)

    for filename, values in sorted(collected.items()):
        path = out_dir / filename
        existing = set()
        if path.exists():
            existing = {
                line.strip() for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.startswith("#")
            }
        merged = sorted(existing | values, key=str.lower)
        path.write_text("\n".join(merged) + "\n", encoding="utf-8")
        print(f"{path}: {len(merged)} terms ({len(values - existing)} new)")

    print(f"\n{len(rows)} tickets scanned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
