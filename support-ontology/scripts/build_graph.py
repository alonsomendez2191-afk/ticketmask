#!/usr/bin/env python3
"""
build_graph.py -- compile the markdown ontology into Navigator/graph-data.js

The .md files in Ontology/ are the source of truth. This script parses them and
emits a single JS file that Navigator/index.html loads. graph-data.js is
generated: never edit it by hand.

Emitted as a .js assignment rather than .json so the Navigator works when opened
directly from disk -- file:// blocks fetch(), but a <script> tag is fine.

Usage:
    python scripts/build_graph.py
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTITY_DIR = ROOT / "Ontology" / "Entities"
REL_FILE = ROOT / "Ontology" / "02-Relationships.md"
OUT_FILE = ROOT / "Navigator" / "graph-data.js"

TYPE_ORDER = [
    "Customer",
    "Product",
    "Support",
    "Engineering",
    "Knowledge",
]


# --------------------------------------------------------------------------
# markdown helpers
# --------------------------------------------------------------------------

def split_sections(text):
    """Split a markdown document into {heading: body} on '## ' headings."""
    sections = {}
    current = "_preamble"
    buf = []
    for line in text.splitlines():
        if line.startswith("## "):
            sections[current] = "\n".join(buf).strip()
            current = line[3:].strip()
            buf = []
        else:
            buf.append(line)
    sections[current] = "\n".join(buf).strip()
    return sections


def is_separator_row(cells):
    return all(re.fullmatch(r":?-{2,}:?", c.strip() or "-") for c in cells)


def parse_tables(text):
    """Return every markdown table in `text` as a list of row-dict lists."""
    tables = []
    rows = None
    header = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped[1:-1].split("|")]
            if header is None:
                header = cells
                rows = []
                continue
            if is_separator_row(cells):
                continue
            if len(cells) != len(header):
                continue
            rows.append(dict(zip(header, cells)))
        else:
            if header is not None:
                tables.append((header, rows))
                header, rows = None, None
    if header is not None:
        tables.append((header, rows))
    return tables


def clean(value):
    """Strip markdown emphasis, backticks and the sup: namespace prefix."""
    value = value.replace("`", "").replace("**", "").strip()
    if value.startswith("sup:"):
        value = value[4:]
    return value


def field(text, label):
    """Pull a '**Label:** value' line out of a document preamble."""
    match = re.search(r"\*\*%s:\*\*\s*(.+)" % re.escape(label), text)
    return clean(match.group(1)) if match else ""


def first_paragraph(text):
    """First non-blockquote paragraph of a section."""
    parts = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block or block.startswith(">"):
            continue
        parts.append(" ".join(block.splitlines()))
        break
    return re.sub(r"\*\*(.+?)\*\*", r"\1", " ".join(parts)).strip()


def bullet_list(text):
    items = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("- "):
            items.append(re.sub(r"\*\*(.+?)\*\*", r"\1", line[2:]).replace("`", "").strip())
    return items


# --------------------------------------------------------------------------
# parsers
# --------------------------------------------------------------------------

def parse_entity(path):
    text = path.read_text(encoding="utf-8")
    sections = split_sections(text)
    pre = sections.get("_preamble", "")

    name_match = re.search(r"^#\s+(.+)$", pre, re.MULTILINE)
    name = name_match.group(1).strip() if name_match else path.stem

    entity = {
        "id": name,
        "file": path.relative_to(ROOT).as_posix(),
        "type": field(pre, "Type") or "Support",
        "status": field(pre, "Status") or "Proposed",
        "definition": first_paragraph(sections.get("Definition", "")),
        "aliases": [],
        "identity": first_paragraph(sections.get("Identity rule", "")),
        "attributes": [],
        "relations": [],
        "individuals": first_paragraph(sections.get("Subclasses and individuals", "")),
        "disjoint": first_paragraph(sections.get("Disjoint with", "")),
        "constraints": bullet_list(sections.get("Constraints", "")),
        "provenance": [],
        "questions": re.findall(r"CQ-\d+", sections.get("Competency questions answered", "")),
        "openQuestions": re.findall(r"OQ-\d+", sections.get("Open questions", "")),
    }

    # Free-text search index. Deliberately wider than the alias table: a term
    # like "Platinum" may live in the individuals table or a definition note,
    # and someone searching for it should still land on the right class.
    haystack = " ".join(
        [
            name,
            sections.get("Definition", ""),
            sections.get("Canonical name and aliases", ""),
            sections.get("Subclasses and individuals", ""),
        ]
    )
    entity["search"] = re.sub(r"[|`*#>]+", " ", haystack).lower()

    for header, rows in parse_tables(sections.get("Canonical name and aliases", "")):
        if "Context" in header:
            for row in rows:
                entity["aliases"].append(
                    {"context": clean(row["Context"]), "term": clean(row["Term used"])}
                )

    for header, rows in parse_tables(sections.get("Datatype properties", "")):
        if "Property" in header and "Type" in header:
            for row in rows:
                entity["attributes"].append(
                    {
                        "name": clean(row["Property"]),
                        "type": clean(row["Type"]),
                        "required": clean(row.get("Required", "")),
                        "notes": clean(row.get("Notes", "")),
                    }
                )

    for header, rows in parse_tables(sections.get("Object properties", "")):
        if "Property" in header and "Target" in header:
            for row in rows:
                entity["relations"].append(
                    {
                        "property": clean(row["Property"]),
                        "target": clean(row["Target"]),
                        "cardinality": clean(row["Cardinality"]),
                        "inverse": clean(row["Inverse"]),
                    }
                )

    for header, rows in parse_tables(sections.get("Provenance", "")):
        if "Source system" in header:
            for row in rows:
                entity["provenance"].append(
                    {
                        "system": clean(row["Source system"]),
                        "supplies": clean(row["What it supplies"]),
                        "authoritative": clean(row["Authoritative for"]),
                    }
                )

    return entity


def parse_relationship_notes():
    """Map property name -> notes text from 02-Relationships.md."""
    notes = {}
    if not REL_FILE.exists():
        return notes
    for header, rows in parse_tables(REL_FILE.read_text(encoding="utf-8")):
        if "Property" in header and "Domain" in header and "Range" in header:
            for row in rows:
                notes[clean(row["Property"])] = row.get("Notes", "").strip()
    return notes


# --------------------------------------------------------------------------
# graph assembly
# --------------------------------------------------------------------------

def build_edges(entities, notes):
    by_id = {e["id"]: e for e in entities}
    edges = []
    seen = set()
    problems = []

    for entity in entities:
        for rel in entity["relations"]:
            target = rel["target"]
            if target not in by_id:
                problems.append(
                    "%s.%s points at unknown class '%s'" % (entity["id"], rel["property"], target)
                )
                continue

            key = frozenset(
                {
                    "%s|%s" % (entity["id"], rel["property"]),
                    "%s|%s" % (target, rel["inverse"]),
                }
            )
            if key in seen:
                continue
            seen.add(key)

            note = notes.get(rel["property"], "")
            edges.append(
                {
                    "source": entity["id"],
                    "target": target,
                    "property": rel["property"],
                    "inverse": rel["inverse"],
                    "cardinality": rel["cardinality"],
                    "type": entity["type"],
                    "transitive": "Transitive" in note,
                    "note": re.sub(r"\*\*(.+?)\*\*", r"\1", note).replace("`", ""),
                }
            )

    return edges, problems


def main():
    if not ENTITY_DIR.exists():
        print("[FAIL] entity directory not found: %s" % ENTITY_DIR)
        return 1

    paths = sorted(ENTITY_DIR.glob("*.md"))
    if not paths:
        print("[FAIL] no entity files found in %s" % ENTITY_DIR)
        return 1

    entities = [parse_entity(p) for p in paths]
    notes = parse_relationship_notes()
    edges, problems = build_edges(entities, notes)

    entities.sort(
        key=lambda e: (
            TYPE_ORDER.index(e["type"]) if e["type"] in TYPE_ORDER else 99,
            e["id"],
        )
    )

    payload = {
        "generated": date.today().isoformat(),
        "typeOrder": TYPE_ORDER,
        "nodes": entities,
        "edges": edges,
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(
        "// GENERATED FILE -- do not edit.\n"
        "// Source: Ontology/*.md   Regenerate: python scripts/build_graph.py\n"
        "window.ONTOLOGY = %s;\n" % json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("[OK] %d classes, %d relationships -> %s" % (len(entities), len(edges), OUT_FILE.relative_to(ROOT)))
    for t in TYPE_ORDER:
        count = sum(1 for e in entities if e["type"] == t)
        if count:
            print("       %-14s %d" % (t, count))

    if problems:
        print("\n[WARN] %d unresolved relationship target(s):" % len(problems))
        for problem in problems:
            print("       - %s" % problem)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
