#!/usr/bin/env python3
"""
export_glossary_csv.py -- ontology -> ER/Studio Team Server glossary CSV.

Emits Export/support-ontology-glossary.csv in the format documented at
docwiki.embarcadero.com .../CSV_Format_to_Load_Glossaries_and_Terms:

    +++ Glossaries Begin +++      parent glossary + one per domain type
    +++ Terms Begin +++           concepts, attributes, reference values, synonyms
    +++ Term Relations Begin +++  Related / Attribute / Type / Synonym

How the ontology maps onto Team Server's three relationship families
-------------------------------------------------------------------
  object property  ->  Related, carrying the verb both ways and the
                       cardinality as From/To multiplicity
  datatype property ->  Attribute - Parent / Attribute - Child
  individual        ->  Type - Parent / Type - Child   (S1 is-a Severity Level)
  equivalence (EQ)  ->  Synonym                        (Case == Ticket)

Object Relations are deliberately NOT emitted: that section needs the numeric
key of an ER object in *your* repository, and inventing keys makes the import
fail. See the notes printed at the end of a run.

Usage:
    python scripts/export_glossary_csv.py
"""

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_graph import ENTITY_DIR, ROOT, parse_entity, split_sections  # noqa: E402
from export_rdf import parse_equivalences, parse_individuals  # noqa: E402

OUT = ROOT / "Export" / "support-ontology-glossary.csv"

ROOT_GLOSSARY = "Support Organization Ontology"
ATTR_GLOSSARY = "Attributes"
ENTITY_TYPE = "Business Terms"          # matches the documented working example
STATUS_CANONICAL = "Approved"
STATUS_PROPOSED = "Not Yet Approved"     # both listed as valid nomenclature in the docs
WIDTH = 15                               # every example row is padded to 15 fields

TYPE_ORDER = ["Customer", "Product", "Support", "Engineering", "Knowledge"]

MULTIPLICITY = {
    "1..1": "ONLY_ONE",
    "0..1": "ZERO_OR_ONE",
    "1..*": "ONE_OR_MANY",
    "0..*": "ZERO_ONE_OR_MANY",
}

# camelCase fragments that should not be title-cased into nonsense
ACRONYMS = {"Id": "ID", "Url": "URL", "Crm": "CRM", "Csm": "CSM", "Ai": "AI",
            "Kb": "KB", "Sku": "SKU", "Nfr": "NFR", "Eol": "EOL"}


def humanize(name):
    """accountName -> Account Name ; SupportEntitlement -> Support Entitlement."""
    if name.isupper():
        return name
    parts = re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z0-9]+", name)
    out = []
    for p in parts:
        word = p if p.isupper() else p[:1].upper() + p[1:]
        out.append(ACRONYMS.get(word, word))
    return " ".join(out)


# The markdown is full of typographic punctuation. Fold it to ASCII: this file
# exists only to be parsed by the Team Server importer, and a plain-ASCII CSV
# cannot be mangled by whatever encoding the upload path assumes.
ASCII_FOLD = {
    "—": "-", "–": "-", "−": "-",          # em/en dash, minus
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "…": "...", "≡": "is equivalent to", "→": "->",
    " ": " ", "≤": "<=", "≥": ">=",
}


def ascii_fold(text):
    for bad, good in ASCII_FOLD.items():
        text = text.replace(bad, good)
    return text.encode("ascii", "ignore").decode("ascii")


def one_line(text):
    return ascii_fold(re.sub(r"\s+", " ", (text or "")).strip())


def pad(row):
    row = list(row)
    return row + [""] * (WIDTH - len(row)) if len(row) < WIDTH else row[:WIDTH]


def marker(text):
    return pad([text])


# --------------------------------------------------------------------------

def collect(entities):
    by_id = {e["id"]: e for e in entities}
    glossary_of = {}          # class id -> glossary name
    for e in entities:
        glossary_of[e["id"]] = e["type"] if e["type"] in TYPE_ORDER else "Support"

    # ---- concepts -------------------------------------------------------
    terms = []
    seen_terms = set()

    def add_term(name, glossary, definition, aliases="", notes="", status=STATUS_CANONICAL,
                 abbreviation=""):
        key = (name.lower(), glossary.lower())
        if key in seen_terms:
            return False
        seen_terms.add(key)
        terms.append({
            "Name": ascii_fold(name), "Status": status, "Definition": one_line(definition),
            "Abbreviations": ascii_fold(abbreviation), "Aliases": ascii_fold(aliases),
            "AdditionalNotes": one_line(notes), "ParentGlossary": glossary,
        })
        return True

    for e in entities:
        alias_terms = [one_line(a["term"]) for a in e["aliases"]
                       if one_line(a["context"]).lower() != "canonical" and one_line(a["term"])]
        flat = []
        for a in alias_terms:
            flat.extend([x.strip() for x in a.split(",") if x.strip()])
        notes = ("Ontology class sup:%s (%s). " % (e["id"], e["type"]))
        if e["identity"]:
            notes += "Identity: " + one_line(e["identity"]) + " "
        if flat:
            notes += "Known aliases: " + ", ".join(dict.fromkeys(flat)) + "."
        add_term(
            humanize(e["id"]), glossary_of[e["id"]], e["definition"],
            aliases=flat[0] if flat else "",
            notes=notes,
            status=STATUS_PROPOSED if e["status"] == "Proposed" else STATUS_CANONICAL,
        )

    # ---- attributes (deduped across classes) ----------------------------
    attr_owners = {}
    attr_note = {}
    for e in entities:
        for a in e["attributes"]:
            label = humanize(a["name"])
            attr_owners.setdefault(label, []).append(e["id"])
            if a["notes"] and label not in attr_note:
                attr_note[label] = one_line(a["notes"])
    for label in sorted(attr_owners):
        owners = attr_owners[label]
        definition = attr_note.get(label, "")
        if not definition:
            definition = "Attribute of " + ", ".join(humanize(o) for o in owners) + "."
        add_term(
            label, ATTR_GLOSSARY, definition,
            notes="Datatype property. Used by: " + ", ".join(humanize(o) for o in owners) + ".",
        )

    # ---- reference values (individuals), in their concept's glossary -----
    individuals = {}
    for path in sorted(ENTITY_DIR.glob("*.md")):
        sections = split_sections(path.read_text(encoding="utf-8"))
        cls = path.stem
        found = parse_individuals(sections.get("Subclasses and individuals", ""),
                                  known_classes=set(by_id))
        if not found:
            continue
        individuals[cls] = found
        for ind in found:
            extras = ind.get("extras") or {}
            alias_cell = ""
            desc_bits = []
            for col, val in extras.items():
                if re.search(r"alias", col, re.I):
                    alias_cell = one_line(val)
                else:
                    desc_bits.append("%s: %s" % (col, one_line(val)))
            definition = ind.get("label") or "; ".join(desc_bits)
            if not definition:
                definition = "A %s." % humanize(cls)
            add_term(
                ind["id"], glossary_of[cls], definition,
                aliases=alias_cell.split(",")[0].strip() if alias_cell else "",
                notes="Reference value of %s.%s" % (
                    humanize(cls), (" Aliases: " + alias_cell + ".") if alias_cell else ""),
            )

    # ---- synonyms from the equivalence declarations ---------------------
    synonyms = []
    for eq in parse_equivalences():
        f = eq["fields"]
        # The anchor is usually a class, but EQ-02 anchors on an *individual*
        # ("sup:SupportEntitlement -> Premium"). Premium is a term in its own
        # right, and pointing the synonym at the class instead would assert that
        # Platinum is a synonym for the whole tier concept rather than for the
        # Premium tier specifically.
        anchor = None
        for key in ("Canonical class", "Canonical individual"):
            if key not in f:
                continue
            cell = one_line(f[key])
            m = re.search(r"sup:([A-Za-z]+)", cell)
            if not (m and m.group(1) in by_id):
                break
            cls = m.group(1)
            ind = re.search(r"sup:[A-Za-z]+\s*(?:->|/)\s*([A-Za-z][\w]*)", cell)
            if ind and (ind.group(1).lower(), glossary_of[cls].lower()) in seen_terms:
                anchor = ind.group(1)          # the specific individual
            else:
                anchor = cls
            anchor_gloss = glossary_of[cls]
            break
        if not anchor:
            continue
        labels = [x.strip() for x in one_line(f.get("Equivalent labels", "")).split(",")
                  if x.strip()]
        if not labels:
            continue
        headline = labels[0]
        anchor_name = anchor if anchor in {t["Name"] for t in terms} else humanize(anchor)
        if add_term(headline, anchor_gloss,
                    "%s. Business synonym for %s; the two denote the same thing, so a "
                    "query for one must return the other."
                    % (eq["title"], anchor_name),
                    notes="Equivalence %s. Varies by %s. Canonical term is %s."
                          % (eq["id"], one_line(f.get("Varies by", "context")), anchor_name)):
            synonyms.append((anchor_name, anchor_gloss, headline, anchor_gloss))

    # ---- relationships --------------------------------------------------
    relations = []

    # Related: one row per object-property pair
    emitted = set()
    for e in entities:
        for rel in e["relations"]:
            target = by_id.get(rel["target"])
            if not target:
                continue
            pair = frozenset({"%s|%s" % (e["id"], rel["property"]),
                              "%s|%s" % (rel["target"], rel["inverse"])})
            if pair in emitted:
                continue
            emitted.add(pair)
            back = [r for r in target["relations"] if r["property"] == rel["inverse"]]
            back_card = back[0]["cardinality"] if back else "0..*"
            relations.append({
                "Name1": humanize(e["id"]), "Glossary1": glossary_of[e["id"]],
                "ForwardType": "Related", "ForwardName": rel["property"],
                # multiplicity of the FROM term is how many of it per TO term
                "FromMultiplicity": MULTIPLICITY.get(back_card, ""),
                "Name2": humanize(rel["target"]), "Glossary2": glossary_of[rel["target"]],
                "ReverseType": "Related", "ReverseName": rel["inverse"],
                "ToMultiplicity": MULTIPLICITY.get(rel["cardinality"], ""),
            })

    # Attribute - Parent / Child
    for label in sorted(attr_owners):
        for owner in attr_owners[label]:
            relations.append({
                "Name1": humanize(owner), "Glossary1": glossary_of[owner],
                "ForwardType": "Attribute - Parent", "ForwardName": "",
                "FromMultiplicity": "",
                "Name2": label, "Glossary2": ATTR_GLOSSARY,
                "ReverseType": "Attribute - Child", "ReverseName": "", "ToMultiplicity": "",
            })

    # Type - Parent / Child
    for cls, found in individuals.items():
        for ind in found:
            relations.append({
                "Name1": humanize(cls), "Glossary1": glossary_of[cls],
                "ForwardType": "Type - Parent", "ForwardName": "", "FromMultiplicity": "",
                "Name2": ind["id"], "Glossary2": glossary_of[cls],
                "ReverseType": "Type - Child", "ReverseName": "", "ToMultiplicity": "",
            })

    # Synonym
    for canonical, g1, synonym, g2 in synonyms:
        relations.append({
            "Name1": canonical, "Glossary1": g1,
            "ForwardType": "Synonym", "ForwardName": "", "FromMultiplicity": "",
            "Name2": synonym, "Glossary2": g2,
            "ReverseType": "Synonym", "ReverseName": "", "ToMultiplicity": "",
        })

    return terms, relations, glossary_of


# --------------------------------------------------------------------------

def main():
    entities = [parse_entity(p) for p in sorted(ENTITY_DIR.glob("*.md"))]
    terms, relations, glossary_of = collect(entities)

    used_types = [t for t in TYPE_ORDER if t in set(glossary_of.values())]
    glossaries = [(ROOT_GLOSSARY,
                   "The semantic base for our AI projects: the concepts, relationships and "
                   "vocabulary agents may use when reasoning about accounts, tickets, "
                   "documentation and escalations.", "")]
    for t in used_types:
        glossaries.append((t, "%s concepts in the support organization ontology." % t,
                           ROOT_GLOSSARY))
    glossaries.append((ATTR_GLOSSARY,
                       "Attributes carried by the concepts in this ontology. Shared where "
                       "more than one concept uses the same attribute.", ROOT_GLOSSARY))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    # No BOM: the importer matches the "+++ ... Begin +++" marker literally, and a
    # byte-order mark sitting in front of it stops that first row being recognised.
    with OUT.open("w", newline="", encoding="ascii") as fh:
        w = csv.writer(fh, lineterminator="\r\n")

        w.writerow(marker("+++ Glossaries Begin +++"))
        w.writerow(pad(["Key", "Name", "Status", "Definition", "Abbreviations", "Aliases",
                        "AdditionalNotes", "Stewards", "ParentGlossary"]))
        for name, definition, parent in glossaries:
            w.writerow(pad(["", name, STATUS_CANONICAL, definition, "", "", "", "", parent]))
        w.writerow(marker("+++ Glossaries End +++"))

        w.writerow(marker("+++ Terms Begin +++"))
        w.writerow(pad(["Key", "Name", "Status", "Definition", "Abbreviations", "Aliases",
                        "AdditionalNotes", "Stewards", "RelatedGlossaries", "TermEntityType",
                        "ParentGlossary"]))
        for t in terms:
            w.writerow(pad(["", t["Name"], t["Status"], t["Definition"], t["Abbreviations"],
                            t["Aliases"], t["AdditionalNotes"], "", "", ENTITY_TYPE,
                            t["ParentGlossary"]]))
        w.writerow(marker("+++ Terms End +++"))

        w.writerow(marker("+++ Term Relations Begin +++"))
        w.writerow(pad(["RelationKey", "TermKey1", "Name1", "TermEntityType1", "ParentGlossary1",
                        "ForwardRelationType", "ForwardRelationName", "FromMultiplicity",
                        "TermKey2", "Name2", "TermEntityType2", "ParentGlossary2",
                        "ReverseRelationType", "ReverseRelationName", "ToMultiplicity"]))
        for r in relations:
            w.writerow(pad(["", "", r["Name1"], ENTITY_TYPE, r["Glossary1"],
                            r["ForwardType"], r["ForwardName"], r["FromMultiplicity"],
                            "", r["Name2"], ENTITY_TYPE, r["Glossary2"],
                            r["ReverseType"], r["ReverseName"], r["ToMultiplicity"]]))
        w.writerow(marker("+++ Term Relations End +++"))

    # ---- self-check -----------------------------------------------------
    problems = []
    known = {(t["Name"].lower(), t["ParentGlossary"].lower()) for t in terms}
    gloss_names = {g[0] for g in glossaries}
    valid_types = {"Attribute - Parent", "Attribute - Child", "Related",
                   "Type - Parent", "Type - Child", "Synonym"}
    opposite = {"Attribute - Parent": "Attribute - Child",
                "Attribute - Child": "Attribute - Parent",
                "Type - Parent": "Type - Child", "Type - Child": "Type - Parent",
                "Related": "Related", "Synonym": "Synonym"}

    for t in terms:
        if not t["Name"]:
            problems.append("a term has no name")
        if t["ParentGlossary"] not in gloss_names:
            problems.append("term %s points at undeclared glossary %s"
                            % (t["Name"], t["ParentGlossary"]))
    for r in relations:
        for side, name, gloss in (("1", r["Name1"], r["Glossary1"]),
                                  ("2", r["Name2"], r["Glossary2"])):
            if (name.lower(), gloss.lower()) not in known:
                problems.append("relation references unknown term %s in %s" % (name, gloss))
        if r["ForwardType"] not in valid_types or r["ReverseType"] not in valid_types:
            problems.append("invalid relation type on %s -> %s" % (r["Name1"], r["Name2"]))
        elif opposite[r["ForwardType"]] != r["ReverseType"]:
            problems.append("forward/reverse types are not opposites on %s -> %s"
                            % (r["Name1"], r["Name2"]))
        if r["ForwardType"] != "Related" and (r["ForwardName"] or r["FromMultiplicity"]
                                              or r["ToMultiplicity"]):
            problems.append("name/multiplicity set on a non-Related relation (%s)"
                            % r["ForwardType"])
        if r["ForwardType"] == "Related" and not r["ForwardName"]:
            problems.append("Related relation with no name on %s -> %s"
                            % (r["Name1"], r["Name2"]))

    raw = OUT.read_bytes()
    if raw[:3] == b"\xef\xbb\xbf":
        problems.append("file starts with a BOM, which hides the first section marker")
    try:
        raw.decode("ascii")
    except UnicodeDecodeError as exc:
        problems.append("non-ASCII byte in output: %s" % exc)
    with OUT.open(encoding="ascii") as fh:
        rows = list(csv.reader(fh))
    widths = {len(row) for row in rows}
    if widths != {WIDTH}:
        problems.append("rows are not all %d columns wide: %s" % (WIDTH, sorted(widths)))
    # every section must open and close
    flat = [r[0] for r in rows]
    for section in ("Glossaries", "Terms", "Term Relations"):
        if flat.count("+++ %s Begin +++" % section) != 1 or \
           flat.count("+++ %s End +++" % section) != 1:
            problems.append("section markers for %s are not balanced" % section)

    counts = {}
    for r in relations:
        counts[r["ForwardType"]] = counts.get(r["ForwardType"], 0) + 1

    print("[OK] %s" % OUT.relative_to(ROOT))
    print("       %-24s %d" % ("glossaries", len(glossaries)))
    print("       %-24s %d" % ("terms", len(terms)))
    print("       %-24s %d" % ("term relations", len(relations)))
    for k in sorted(counts):
        print("         %-22s %d" % (k, counts[k]))
    print("       %-24s %d" % ("columns per row", WIDTH))

    if problems:
        print("")
        print("[FAIL] %d problem(s):" % len(problems))
        for p in sorted(set(problems))[:20]:
            print("       - %s" % p)
        return 1
    print("")
    print("[OK] self-check clean")
    print("")
    print("Before importing:")
    print("  - Stewards are left blank; add Team Server usernames if you want owners set.")
    print("  - Status uses Approved / Not Yet Approved. Change if your Team Server")
    print("    uses a different nomenclature.")
    print("  - Object Relations are not emitted: that section needs ER object keys from")
    print("    your own repository, and invented keys fail the import.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
