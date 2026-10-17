#!/usr/bin/env python3
"""
validate_ontology.py -- structural consistency checks over Ontology/

Checks that the ontology is internally coherent. It does not check that the
ontology is *true* -- only that it does not contradict itself. Truth is what the
open questions in 06-Open-Questions.md are for.

Checks performed:
  1. Every entity file has every required section heading.
  2. Status is one of Canonical / Proposed / Deprecated.
  3. Every object property target resolves to a real entity file.
  4. Every object property has a matching inverse declared on the target class.
  5. Every object property appears in the 02-Relationships.md catalog.
  6. Every C-nn / CQ-nn / OQ-nn reference resolves to a defined item.
  7. Every Proposed class has at least one open question against it.
  8. The counts stated in 05-Competency-Questions.md match the questions in it.
  9. Every Conditional question names what it is conditional on.
 10. Every competency question a class claims actually traverses that class.

Checks 8-10 exist because prose counts drift. A question added without updating
the summary table leaves two numbers in the file disagreeing, and every document
downstream -- the Navigator, the stack view, the changelog -- repeats whichever
one it copied.

Usage:
    python scripts/validate_ontology.py
Exit code 0 = clean, 1 = problems found.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_graph import (  # noqa: E402
    ENTITY_DIR,
    REL_FILE,
    ROOT,
    clean,
    parse_entity,
    parse_tables,
    split_sections,
)

REQUIRED_SECTIONS = [
    "Definition",
    "Canonical name and aliases",
    "Identity rule",
    "Datatype properties",
    "Object properties",
    "Subclasses and individuals",
    "Disjoint with",
    "Constraints",
    "Provenance",
    "Competency questions answered",
    "Open questions",
]

VALID_STATUS = {"Canonical", "Proposed", "Deprecated"}

CONSTRAINTS_FILE = ROOT / "Ontology" / "04-Constraints-and-Rules.md"
QUESTIONS_FILE = ROOT / "Ontology" / "05-Competency-Questions.md"
OPEN_FILE = ROOT / "Ontology" / "06-Open-Questions.md"

errors = []
warnings = []


def error(message):
    errors.append(message)


def warn(message):
    warnings.append(message)


def defined_ids(path, pattern):
    """IDs defined in a reference file -- i.e. appearing inside backticks."""
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8")
    return set(re.findall(r"`(%s)`" % pattern, text))


def catalog_properties():
    if not REL_FILE.exists():
        error("02-Relationships.md is missing")
        return set()
    props = set()
    for header, rows in parse_tables(REL_FILE.read_text(encoding="utf-8")):
        if "Property" in header and "Domain" in header and "Range" in header:
            for row in rows:
                props.add(clean(row["Property"]))
                props.add(clean(row["Inverse"]))
    return props


def competency_blocks():
    """Active questions as {id: (status_marker, body)}.

    An active question is one with its own '### `CQ-nn`' heading. Retired
    questions live in a table at the bottom of the file and are deliberately
    excluded -- they are kept so an old ID resolves to an explanation, not
    because they are still asked.
    """
    if not QUESTIONS_FILE.exists():
        return {}
    blocks = {}
    for chunk in re.split(r"^###\s+", QUESTIONS_FILE.read_text(encoding="utf-8"), flags=re.M)[1:]:
        match = re.match(r"`(CQ-\d+)`\s*(.*)", chunk)
        if not match:
            continue
        heading = match.group(2).splitlines()[0] if match.group(2) else ""
        marker = "answerable" if "✅" in heading else "conditional" if "⚠" in heading else ""
        blocks[match.group(1)] = (marker, chunk)
    return blocks


def check_competency_file(entities):
    blocks = competency_blocks()
    if not blocks:
        error("05-Competency-Questions.md defines no questions")
        return

    text = QUESTIONS_FILE.read_text(encoding="utf-8")
    answerable = [q for q, (m, _) in blocks.items() if m == "answerable"]
    conditional = [q for q, (m, _) in blocks.items() if m == "conditional"]

    # 8: stated counts match the questions actually in the file
    for q, (marker, _) in sorted(blocks.items()):
        if not marker:
            error("05-: %s carries neither an answerable nor a conditional marker" % q)

    stated_total = re.search(r"\*\*(\d+) active questions\.\*\*", text)
    if not stated_total:
        error("05-: the '**N active questions.**' line is missing")
    elif int(stated_total.group(1)) != len(blocks):
        error(
            "05-: header says %s active questions, the file defines %d"
            % (stated_total.group(1), len(blocks))
        )

    for label, actual in (("Answerable today", answerable), ("Conditional", conditional)):
        stated = re.search(r"\|\s*\S?\s*%s\s*\|\s*(\d+)\s*\|" % re.escape(label), text)
        if not stated:
            error("05-: the coverage summary has no '%s' row" % label)
        elif int(stated.group(1)) != len(actual):
            error(
                "05-: coverage summary says %s %s, the file marks %d"
                % (stated.group(1), label.lower(), len(actual))
            )

    # 9: a conditional question that does not say what blocks it cannot be
    # scheduled -- it looks like work with no prerequisite.
    for q in sorted(conditional):
        if not re.findall(r"`(OQ-\d+|EQ-\d+)`", blocks[q][1]):
            error("05-: %s is conditional but names no OQ or EQ that blocks it" % q)

    # 10: a class may only claim a question its traversal actually reaches --
    # directly by name, or through one of the class's own properties.
    for name, entity in sorted(entities.items()):
        handles = {name}
        handles.update(a["name"] for a in entity["attributes"])
        for rel in entity["relations"]:
            handles.update((rel["property"], rel["inverse"]))
        pattern = re.compile(r"\b(%s)\b" % "|".join(re.escape(h) for h in sorted(handles)))
        for q in sorted(entity["questions"]):
            if q not in blocks:
                error("%s.md claims %s, which is not an active question" % (name, q))
            elif not pattern.search(blocks[q][1]):
                warn(
                    "%s claims %s, but that traversal never reaches %s"
                    % (name, q, name)
                )


def main():
    paths = sorted(ENTITY_DIR.glob("*.md"))
    if not paths:
        print("[FAIL] no entity files found")
        return 1

    entities = {}
    for path in paths:
        text = path.read_text(encoding="utf-8")
        sections = split_sections(text)
        for required in REQUIRED_SECTIONS:
            if required not in sections:
                error("%s: missing required section '## %s'" % (path.name, required))
        entity = parse_entity(path)
        if entity["id"] != path.stem:
            error(
                "%s: class name '%s' does not match filename" % (path.name, entity["id"])
            )
        if entity["status"] not in VALID_STATUS:
            error("%s: invalid status '%s'" % (path.name, entity["status"]))
        entities[entity["id"]] = entity

    # 3 + 4: targets resolve, inverses are declared on the other side
    for name, entity in entities.items():
        for rel in entity["relations"]:
            target = entities.get(rel["target"])
            if target is None:
                error(
                    "%s.%s: target class '%s' has no entity file"
                    % (name, rel["property"], rel["target"])
                )
                continue
            back = [r for r in target["relations"] if r["property"] == rel["inverse"]]
            if not back:
                error(
                    "%s.%s: inverse '%s' is not declared on %s"
                    % (name, rel["property"], rel["inverse"], rel["target"])
                )
            elif back[0]["target"] != name:
                error(
                    "%s.%s: inverse '%s' on %s points at '%s', expected '%s'"
                    % (
                        name,
                        rel["property"],
                        rel["inverse"],
                        rel["target"],
                        back[0]["target"],
                        name,
                    )
                )
            elif back[0]["inverse"] != rel["property"]:
                error(
                    "%s.%s: inverse pairing is not symmetric with %s.%s"
                    % (name, rel["property"], rel["target"], rel["inverse"])
                )

    # 5: the relationship catalog covers every declared property
    catalog = catalog_properties()
    for name, entity in entities.items():
        for rel in entity["relations"]:
            if rel["property"] not in catalog:
                error(
                    "%s.%s is not listed in 02-Relationships.md"
                    % (name, rel["property"])
                )

    # 6: cross-reference IDs resolve
    known_c = defined_ids(CONSTRAINTS_FILE, r"C-\d+")
    known_cq = defined_ids(QUESTIONS_FILE, r"CQ-\d+")
    known_oq = defined_ids(OPEN_FILE, r"OQ-\d+")

    for path in paths:
        text = path.read_text(encoding="utf-8")
        for ref in sorted(set(re.findall(r"C-\d+", text))):
            if ref not in known_c:
                error("%s: references %s which is not defined in 04-" % (path.name, ref))
        for ref in sorted(set(re.findall(r"CQ-\d+", text))):
            if ref not in known_cq:
                error("%s: references %s which is not defined in 05-" % (path.name, ref))
        for ref in sorted(set(re.findall(r"OQ-\d+", text))):
            if ref not in known_oq:
                error("%s: references %s which is not defined in 06-" % (path.name, ref))

    # 8 + 9 + 10: the competency question file must agree with itself, and with
    # the classes that claim to answer its questions.
    check_competency_file(entities)

    # 7: proposed classes must be under discussion somewhere
    for name, entity in entities.items():
        if entity["status"] == "Proposed" and not entity["openQuestions"]:
            warn("%s is Proposed but raises no open question" % name)
        if not entity["definition"]:
            warn("%s has an empty Definition" % name)
        if not entity["questions"]:
            warn("%s answers no competency question -- is it needed?" % name)

    # report
    print("Validating %d entity files in %s" % (len(entities), ENTITY_DIR.relative_to(ROOT)))
    print("")

    if errors:
        print("[FAIL] %d error(s):" % len(errors))
        for item in errors:
            print("       - %s" % item)
    else:
        print("[OK] no structural errors")

    if warnings:
        print("")
        print("[WARN] %d warning(s):" % len(warnings))
        for item in warnings:
            print("       - %s" % item)

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
