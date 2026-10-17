#!/usr/bin/env python3
"""
export_rdf.py -- compile the markdown ontology into RDF / OWL.

Reads ONLY the .md files under Ontology/. The Navigator, its generated
graph-data.js and the scripts themselves are not part of the export.

Builds one in-memory triple model and serialises it four ways, so the
serialisations cannot drift from each other:

    Export/support-ontology.ttl     Turtle      -- human-readable, the primary
    Export/support-ontology.nt      N-Triples   -- canonical, line-per-triple
    Export/support-ontology.rdf     RDF/XML     -- for tools that want it
    Export/support-ontology.jsonld  JSON-LD     -- for agent/document tooling

No third-party dependencies.

Usage:
    python scripts/export_rdf.py
    python scripts/export_rdf.py --base https://ontology.acme.com/support#
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_graph import (  # noqa: E402
    ENTITY_DIR,
    ROOT,
    clean,
    parse_entity,
    parse_tables,
    split_sections,
)

ONT_DIR = ROOT / "Ontology"
OUT_DIR = ROOT / "Export"

# Placeholder. Replace with an HTTP IRI on a domain the organization controls
# before this is published anywhere -- see Export/README.md.
DEFAULT_BASE = "https://ontology.local/support#"

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
OWL = "http://www.w3.org/2002/07/owl#"
XSD = "http://www.w3.org/2001/XMLSchema#"
SKOS = "http://www.w3.org/2004/02/skos/core#"
DCT = "http://purl.org/dc/terms/"

TYPE_MAP = {
    "string": XSD + "string",
    "text": XSD + "string",
    "uuid": XSD + "string",
    "boolean": XSD + "boolean",
    "integer": XSD + "integer",
    "date": XSD + "date",
    "datetime": XSD + "dateTime",
}


# --------------------------------------------------------------------------
# term model
# --------------------------------------------------------------------------

class IRI:
    __slots__ = ("v",)

    def __init__(self, v):
        self.v = v

    def __eq__(self, o):
        return isinstance(o, IRI) and o.v == self.v

    def __hash__(self):
        return hash(("iri", self.v))


class BNode:
    __slots__ = ("v",)

    def __init__(self, v):
        self.v = v

    def __eq__(self, o):
        return isinstance(o, BNode) and o.v == self.v

    def __hash__(self):
        return hash(("bnode", self.v))


class Lit:
    __slots__ = ("v", "dt")

    def __init__(self, v, dt=None):
        self.v = str(v)
        self.dt = dt

    def __eq__(self, o):
        return isinstance(o, Lit) and o.v == self.v and o.dt == self.dt

    def __hash__(self):
        return hash(("lit", self.v, self.dt))


class Graph:
    def __init__(self):
        self.triples = []
        self._seen = set()
        self._bn = 0

    def add(self, s, p, o):
        if o is None:
            return
        key = (
            (type(s).__name__, s.v),
            p.v,
            (type(o).__name__, o.v, getattr(o, "dt", None)),
        )
        if key in self._seen:
            return
        self._seen.add(key)
        self.triples.append((s, p, o))

    def bnode(self):
        self._bn += 1
        return BNode("b%d" % self._bn)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def strip_md(text):
    """Markdown -> plain text, for literal values."""
    if text is None:
        return ""
    t = str(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"\*(.+?)\*", r"\1", t)
    t = t.replace("`", "")
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def local_name(text):
    """Make a Turtle-safe local name."""
    t = re.sub(r"[^A-Za-z0-9_\-]", "_", str(text))
    t = re.sub(r"_+", "_", t).strip("_")
    return t or "unnamed"


def camel(text):
    parts = re.split(r"[^A-Za-z0-9]+", strip_md(text))
    parts = [p for p in parts if p]
    if not parts:
        return "value"
    return parts[0][0].lower() + parts[0][1:] + "".join(p[:1].upper() + p[1:] for p in parts[1:])


def split_list(text):
    """Split a comma-separated alias cell, respecting quoted phrases."""
    t = strip_md(text)
    out = []
    for part in re.split(r",|;", t):
        part = part.strip().strip('"').strip()
        part = re.sub(r"\s*\(.*?\)\s*$", "", part).strip()
        if part and part.lower() not in ("none", "n/a", "-"):
            out.append(part)
    return out


def parse_cardinality(card):
    """'1..1' -> (min, max) with None meaning unbounded."""
    m = re.match(r"^(\d+)\.\.(\d+|\*)$", (card or "").strip())
    if not m:
        return None, None
    lo = int(m.group(1))
    hi = None if m.group(2) == "*" else int(m.group(2))
    return lo, hi


# --------------------------------------------------------------------------
# reference-document parsers
# --------------------------------------------------------------------------

def parse_constraints():
    """C-nn -> {level, text, status} from 04-Constraints-and-Rules.md."""
    path = ONT_DIR / "04-Constraints-and-Rules.md"
    out = {}
    if not path.exists():
        return out
    text = path.read_text(encoding="utf-8")
    for header, rows in parse_tables(text):
        h = [c.strip() for c in header]
        if "ID" not in h:
            continue
        for row in rows:
            cid = clean(row.get("ID", ""))
            if not re.fullmatch(r"C-\d+", cid):
                continue
            if "Retired because" in h:
                out[cid] = {
                    "level": "Retired",
                    "text": strip_md(row.get("Was", "")),
                    "status": "Retired",
                    "reason": strip_md(row.get("Retired because", "")),
                }
            else:
                body = strip_md(row.get("Constraint", ""))
                catches = strip_md(row.get("What it catches", ""))
                out[cid] = {
                    "level": strip_md(row.get("Level", "")),
                    "text": body,
                    "status": "Active",
                    "reason": catches,
                }
    return out


def parse_competency_questions():
    """CQ-nn -> {text, status} from 05-Competency-Questions.md."""
    path = ONT_DIR / "05-Competency-Questions.md"
    out = {}
    if not path.exists():
        return out
    text = path.read_text(encoding="utf-8")
    for m in re.finditer(r"^###\s+`(CQ-\d+)`\s*[—-]\s*(.+?)\s*$", text, re.MULTILINE):
        body = m.group(2)
        status = "Answerable" if "✅" in body else ("Conditional" if "⚠" in body else "Unknown")
        out[m.group(1)] = {"text": strip_md(body.replace("✅", "").replace("⚠", "")),
                           "status": status}
    for header, rows in parse_tables(text):
        if "ID" in header and "Retired because" in header:
            for row in rows:
                qid = clean(row.get("ID", ""))
                if re.fullmatch(r"CQ-\d+", qid):
                    out[qid] = {"text": strip_md(row.get("Was", "")), "status": "Retired",
                                "reason": strip_md(row.get("Retired because", ""))}
    return out


def parse_open_questions():
    """OQ-nn -> {text, status} from 06-Open-Questions.md."""
    path = ONT_DIR / "06-Open-Questions.md"
    out = {}
    if not path.exists():
        return out
    text = path.read_text(encoding="utf-8")
    marks = [("🔴", "Blocking"), ("🟡", "Open"), ("🟢", "Resolved"), ("⚫", "Retired")]
    for m in re.finditer(r"^###\s+`(OQ-\d+)`\s*(.+?)\s*$", text, re.MULTILINE):
        body = m.group(2)
        status = "Unknown"
        for glyph, name in marks:
            if glyph in body:
                status = name
                body = body.replace(glyph, "")
                break
        out[m.group(1)] = {"text": strip_md(body), "status": status}
    for header, rows in parse_tables(text):
        if "ID" in header and "Retired because" in header:
            for row in rows:
                qid = clean(row.get("ID", ""))
                if re.fullmatch(r"OQ-\d+", qid):
                    out[qid] = {"text": strip_md(row.get("Was", "")), "status": "Retired",
                                "reason": strip_md(row.get("Retired because", ""))}
    return out


def parse_equivalences():
    """EQ-nn declarations from 03-Vocabulary-and-Equivalence.md."""
    path = ONT_DIR / "03-Vocabulary-and-Equivalence.md"
    out = []
    if not path.exists():
        return out
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"^###\s+", text, flags=re.MULTILINE)[1:]
    for block in blocks:
        m = re.match(r"`(EQ-\d+)`\s*[—-]\s*(.+)", block)
        if not m:
            continue
        rec = {"id": m.group(1), "title": strip_md(m.group(2).splitlines()[0]), "fields": {}}
        for line in block.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.strip().startswith("|") else []
            if len(cells) == 2 and cells[0].startswith("**"):
                rec["fields"][strip_md(cells[0])] = strip_md(cells[1])
        out.append(rec)
    return out


def parse_individuals(section_text, known_classes=()):
    """
    Best-effort extraction of named individuals from a
    '## Subclasses and individuals' section. Handles the three shapes the
    ontology actually uses: a table with the id in column one, a bullet list
    of `CODE` — label, and an inline run of backticked names.

    A section that opens with "None" has no individuals, full stop. Those
    sections still carry explanatory prose with backticked property names in
    it, and reading those as individuals invents things the ontology never
    declared -- `Ticket_Escalation`, `Account_isStrategic` and friends.
    """
    if not section_text:
        return []
    if re.match(r"^\s*None\b", section_text):
        return []
    out = []

    tables = parse_tables(section_text)
    for header, rows in tables:
        first = header[0]
        for row in rows:
            raw = row.get(first, "")
            ident = strip_md(raw)
            if not ident or " " in ident:
                continue
            extras = {}
            for col in header[1:]:
                val = strip_md(row.get(col, ""))
                if val and val not in ("-", "—"):
                    extras[col] = val
            out.append({"id": ident, "label": None, "extras": extras})
    if out:
        return out

    for line in section_text.splitlines():
        m = re.match(r"^-\s+`([^`]+)`\s*[—-]?\s*(.*)$", line.strip())
        if m:
            out.append({"id": strip_md(m.group(1)), "label": strip_md(m.group(2)) or None,
                        "extras": {}})
    if out:
        return out

    # Inline backticked run, e.g. the product list. Only trust this shape when
    # it really is a list: a handful of backticked names in a row, none of them
    # a class name or a camelCase property reference.
    body = re.sub(r"```.*?```", "", section_text, flags=re.S)
    codes, seen = [], set()
    for c in re.findall(r"`([A-Za-z][A-Za-z0-9_]*)`", body):
        if c in seen or c in known_classes:
            continue
        if re.match(r"^[a-z]", c):          # camelCase -> a property, not an individual
            continue
        seen.add(c)
        codes.append(c)
    if len(codes) < 4:
        return []
    return [{"id": c, "label": None, "extras": {}} for c in codes]


# --------------------------------------------------------------------------
# graph construction
# --------------------------------------------------------------------------

def build(base):
    def S(name):
        return IRI(base + name)

    a = IRI(RDF + "type")
    g = Graph()

    entities = [parse_entity(p) for p in sorted(ENTITY_DIR.glob("*.md"))]
    by_id = {e["id"]: e for e in entities}
    constraints = parse_constraints()
    cqs = parse_competency_questions()
    oqs = parse_open_questions()
    eqs = parse_equivalences()

    # ---- ontology header ----
    onto = IRI(base.rstrip("#/"))
    g.add(onto, a, IRI(OWL + "Ontology"))
    g.add(onto, IRI(OWL + "versionInfo"), Lit("0.2.0"))
    g.add(onto, IRI(DCT + "title"), Lit("Support Organization Ontology"))
    g.add(onto, IRI(DCT + "modified"), Lit(date.today().isoformat(), XSD + "date"))
    g.add(onto, IRI(RDFS + "comment"), Lit(
        "Machine-readable model of the support organization: the concepts, "
        "relationships, rules and vocabulary AI agents may use when reasoning "
        "about accounts, tickets, documentation and escalations. Generated from "
        "the markdown source of truth in Ontology/."))

    # ---- annotation + meta vocabulary this export defines ----
    meta_classes = ["Alias", "ProvenanceEntry", "Constraint", "CompetencyQuestion",
                    "OpenQuestion", "EquivalenceDeclaration"]
    for c in meta_classes:
        g.add(S(c), a, IRI(OWL + "Class"))
        g.add(S(c), IRI(RDFS + "label"), Lit(c))
        g.add(S(c), IRI(RDFS + "comment"),
              Lit("Metamodel class introduced by the RDF export to carry information "
                  "the markdown source records in prose or tables."))

    ann_props = [
        ("domainType", "Navigation grouping: Customer, Product, Support, Engineering, Knowledge."),
        ("status", "Canonical, Proposed or Deprecated."),
        ("identityRule", "How two records are decided to be the same instance."),
        ("sourceFile", "Markdown file this term was generated from."),
        ("cardinalityNotation", "The min..max notation as written in the source."),
        ("isRequired", "Whether the datatype property is mandatory."),
        ("permittedValue", "One allowed value of an enumerated datatype property."),
        ("aliasTerm", "A term used for this concept in some system or context."),
        ("aliasContext", "The system, product or setting in which the alias is used."),
        ("hasAlias", "Links a class to an attributed Alias node."),
        ("sourceSystem", "System of record named in a provenance entry."),
        ("supplies", "What the source system supplies."),
        ("authoritativeFor", "What the source system is authoritative for."),
        ("hasProvenance", "Links a class to a ProvenanceEntry node."),
        ("constraintId", "Stable identifier, e.g. C-01."),
        ("enforcementLevel", "Hard, Soft, Advisory or Retired."),
        ("constraintText", "The constraint as written."),
        ("constraintNote", "What the constraint catches, or why it was retired."),
        ("governedBy", "Links a class to a Constraint."),
        ("questionId", "Stable identifier, e.g. CQ-01 or OQ-01."),
        ("questionText", "The question as written."),
        ("questionStatus", "Answerable, Conditional, Retired, Blocking, Open or Resolved."),
        ("questionNote", "Why a question was retired."),
        ("answersQuestion", "Links a class to a CompetencyQuestion it participates in."),
        ("raisesQuestion", "Links a class to an unresolved OpenQuestion."),
        ("equivalenceId", "Stable identifier, e.g. EQ-01."),
        ("equivalenceStatus", "Confirmation state of the equivalence declaration."),
        ("variesBy", "What the naming varies by: CRM, Product, or speaker."),
        ("anchorProperty", "The property that records which term is used where."),
        ("equivalentLabel", "A label asserted to denote the same thing as the canonical term."),
        ("declaresEquivalence", "Links a class to an EquivalenceDeclaration about it."),
    ]
    for name, comment in ann_props:
        g.add(S(name), a, IRI(OWL + "AnnotationProperty"))
        g.add(S(name), IRI(RDFS + "label"), Lit(name))
        g.add(S(name), IRI(RDFS + "comment"), Lit(comment))

    # ---- classes ----
    for e in entities:
        c = S(e["id"])
        g.add(c, a, IRI(OWL + "Class"))
        g.add(c, IRI(RDFS + "label"), Lit(e["id"]))
        g.add(c, IRI(SKOS + "prefLabel"), Lit(e["id"]))
        if e["definition"]:
            g.add(c, IRI(SKOS + "definition"), Lit(e["definition"]))
            g.add(c, IRI(RDFS + "comment"), Lit(e["definition"]))
        g.add(c, S("domainType"), Lit(e["type"]))
        g.add(c, S("status"), Lit(e["status"]))
        if e["identity"]:
            g.add(c, S("identityRule"), Lit(e["identity"]))
        g.add(c, S("sourceFile"), Lit(e["file"]))

        # aliases -- attributed, plus plain skos:altLabel for interoperability
        for al in e["aliases"]:
            term = strip_md(al["term"])
            ctx = strip_md(al["context"])
            if not term or ctx.lower() == "canonical":
                continue
            for one in split_list(term):
                g.add(c, IRI(SKOS + "altLabel"), Lit(one))
            node = g.bnode()
            g.add(node, a, S("Alias"))
            g.add(node, S("aliasTerm"), Lit(term))
            g.add(node, S("aliasContext"), Lit(ctx))
            g.add(c, S("hasAlias"), node)

        # provenance
        for pv in e["provenance"]:
            node = g.bnode()
            g.add(node, a, S("ProvenanceEntry"))
            g.add(node, S("sourceSystem"), Lit(strip_md(pv["system"])))
            g.add(node, S("supplies"), Lit(strip_md(pv["supplies"])))
            g.add(node, S("authoritativeFor"), Lit(strip_md(pv["authoritative"])))
            g.add(c, S("hasProvenance"), node)

        # cross references
        for cid in sorted(set(re.findall(r"C-\d+", " ".join(e["constraints"])))):
            g.add(c, S("governedBy"), S(cid))
        for qid in e["questions"]:
            g.add(c, S("answersQuestion"), S(qid))
        for qid in e["openQuestions"]:
            g.add(c, S("raisesQuestion"), S(qid))

    # ---- disjointness (only explicitly written sup: references) ----
    for path in sorted(ENTITY_DIR.glob("*.md")):
        sections = split_sections(path.read_text(encoding="utf-8"))
        me = path.stem
        for other in re.findall(r"`sup:([A-Za-z]+)`", sections.get("Disjoint with", "")):
            if other in by_id and other != me:
                g.add(S(me), IRI(OWL + "disjointWith"), S(other))

    # ---- object properties + cardinality restrictions ----
    declared = {}
    for e in entities:
        for rel in e["relations"]:
            if rel["target"] not in by_id:
                continue
            declared.setdefault(rel["property"], (e["id"], rel))

    for prop, (domain, rel) in sorted(declared.items()):
        p = S(prop)
        g.add(p, a, IRI(OWL + "ObjectProperty"))
        g.add(p, IRI(RDFS + "label"), Lit(prop))
        g.add(p, IRI(RDFS + "domain"), S(domain))
        g.add(p, IRI(RDFS + "range"), S(rel["target"]))
        if rel["inverse"] in declared:
            g.add(p, IRI(OWL + "inverseOf"), S(rel["inverse"]))

        lo, hi = parse_cardinality(rel["cardinality"])
        if lo is None:
            continue
        node = None
        if lo == hi and lo is not None:
            node = g.bnode()
            g.add(node, IRI(OWL + "qualifiedCardinality"), Lit(lo, XSD + "nonNegativeInteger"))
        elif hi is not None and lo == 0:
            node = g.bnode()
            g.add(node, IRI(OWL + "maxQualifiedCardinality"), Lit(hi, XSD + "nonNegativeInteger"))
        elif hi is None and lo > 0:
            node = g.bnode()
            g.add(node, IRI(OWL + "minQualifiedCardinality"), Lit(lo, XSD + "nonNegativeInteger"))
        if node is not None:
            g.add(node, a, IRI(OWL + "Restriction"))
            g.add(node, IRI(OWL + "onProperty"), p)
            g.add(node, IRI(OWL + "onClass"), S(rel["target"]))
            g.add(node, S("cardinalityNotation"), Lit(rel["cardinality"]))
            g.add(S(domain), IRI(RDFS + "subClassOf"), node)

    # ---- datatype properties ----
    seen_dt = {}
    for e in entities:
        for attr in e["attributes"]:
            name = attr["name"]
            p = S(name)
            if name not in seen_dt:
                seen_dt[name] = True
                g.add(p, a, IRI(OWL + "DatatypeProperty"))
                g.add(p, IRI(RDFS + "label"), Lit(name))
            g.add(p, IRI(RDFS + "domain"), S(e["id"]))

            raw = (attr["type"] or "").strip()
            enum = re.match(r"^enum\((.+)\)$", raw, re.I)
            if enum:
                g.add(p, IRI(RDFS + "range"), IRI(XSD + "string"))
                for val in split_list(enum.group(1)):
                    g.add(p, S("permittedValue"), Lit(val))
            else:
                g.add(p, IRI(RDFS + "range"), IRI(TYPE_MAP.get(raw.lower(), XSD + "string")))

            if attr["notes"]:
                g.add(p, IRI(RDFS + "comment"), Lit(strip_md(attr["notes"])))
            if (attr["required"] or "").strip().lower() == "yes":
                g.add(p, S("isRequired"), Lit("true", XSD + "boolean"))
                node = g.bnode()
                g.add(node, a, IRI(OWL + "Restriction"))
                g.add(node, IRI(OWL + "onProperty"), p)
                g.add(node, IRI(OWL + "minCardinality"), Lit(1, XSD + "nonNegativeInteger"))
                g.add(S(e["id"]), IRI(RDFS + "subClassOf"), node)

    # ---- named individuals ----
    for path in sorted(ENTITY_DIR.glob("*.md")):
        sections = split_sections(path.read_text(encoding="utf-8"))
        cls = path.stem
        section = sections.get("Subclasses and individuals", "")
        for ind in parse_individuals(section, known_classes=set(by_id)):
            iri = S("%s_%s" % (cls, local_name(ind["id"])))
            g.add(iri, a, IRI(OWL + "NamedIndividual"))
            g.add(iri, a, S(cls))
            g.add(iri, IRI(RDFS + "label"), Lit(ind["label"] or ind["id"]))
            g.add(iri, IRI(SKOS + "notation"), Lit(ind["id"]))
            for col, val in ind["extras"].items():
                if re.search(r"alias", col, re.I):
                    for one in split_list(val):
                        g.add(iri, IRI(SKOS + "altLabel"), Lit(one))
                else:
                    g.add(iri, S(camel(col)), Lit(val))

    # ---- constraints ----
    for cid, rec in sorted(constraints.items()):
        n = S(cid)
        g.add(n, a, IRI(OWL + "NamedIndividual"))
        g.add(n, a, S("Constraint"))
        g.add(n, S("constraintId"), Lit(cid))
        g.add(n, IRI(RDFS + "label"), Lit(cid))
        g.add(n, S("enforcementLevel"), Lit(rec["level"] or "Unspecified"))
        g.add(n, S("constraintText"), Lit(rec["text"]))
        g.add(n, S("status"), Lit(rec["status"]))
        if rec.get("reason"):
            g.add(n, S("constraintNote"), Lit(rec["reason"]))

    # ---- competency + open questions ----
    for qid, rec in sorted(cqs.items()):
        n = S(qid)
        g.add(n, a, IRI(OWL + "NamedIndividual"))
        g.add(n, a, S("CompetencyQuestion"))
        g.add(n, S("questionId"), Lit(qid))
        g.add(n, IRI(RDFS + "label"), Lit(qid))
        g.add(n, S("questionText"), Lit(rec["text"]))
        g.add(n, S("questionStatus"), Lit(rec["status"]))
        if rec.get("reason"):
            g.add(n, S("questionNote"), Lit(rec["reason"]))

    for qid, rec in sorted(oqs.items()):
        n = S(qid)
        g.add(n, a, IRI(OWL + "NamedIndividual"))
        g.add(n, a, S("OpenQuestion"))
        g.add(n, S("questionId"), Lit(qid))
        g.add(n, IRI(RDFS + "label"), Lit(qid))
        g.add(n, S("questionText"), Lit(rec["text"]))
        g.add(n, S("questionStatus"), Lit(rec["status"]))
        if rec.get("reason"):
            g.add(n, S("questionNote"), Lit(rec["reason"]))

    # ---- equivalence declarations: the point of the whole exercise ----
    for rec in eqs:
        n = S(rec["id"])
        g.add(n, a, IRI(OWL + "NamedIndividual"))
        g.add(n, a, S("EquivalenceDeclaration"))
        g.add(n, S("equivalenceId"), Lit(rec["id"]))
        g.add(n, IRI(RDFS + "label"), Lit("%s: %s" % (rec["id"], rec["title"])))
        f = rec["fields"]

        target = None
        for key in ("Canonical class", "Canonical individual", "Classes involved"):
            if key in f:
                names = re.findall(r"sup:([A-Za-z]+)", f[key])
                if names and names[0] in by_id:
                    target = S(names[0])
                    g.add(n, S("canonicalTerm"), target)
                    g.add(target, S("declaresEquivalence"), n)
                for extra in names[1:]:
                    if extra in by_id:
                        g.add(n, S("canonicalTerm"), S(extra))
                        g.add(S(extra), S("declaresEquivalence"), n)
                break

        for label in split_list(f.get("Equivalent labels", "")):
            g.add(n, S("equivalentLabel"), Lit(label))
            if target is not None:
                g.add(target, IRI(SKOS + "altLabel"), Lit(label))
        if f.get("Varies by"):
            g.add(n, S("variesBy"), Lit(f["Varies by"]))
        if f.get("Anchor property"):
            g.add(n, S("anchorProperty"), Lit(f["Anchor property"]))
        if f.get("Status"):
            g.add(n, S("equivalenceStatus"), Lit(f["Status"]))
        if f.get("Declared"):
            g.add(n, S("equivalenceStatus"), Lit(f["Declared"]))

    g.add(S("canonicalTerm"), a, IRI(OWL + "AnnotationProperty"))
    g.add(S("canonicalTerm"), IRI(RDFS + "label"), Lit("canonicalTerm"))

    return g, entities, declared, constraints, cqs, oqs, eqs


# --------------------------------------------------------------------------
# serialisers
# --------------------------------------------------------------------------

PREFIXES = [("sup", None), ("rdf", RDF), ("rdfs", RDFS), ("owl", OWL),
            ("xsd", XSD), ("skos", SKOS), ("dcterms", DCT)]

TTL_ESCAPES = [("\\", "\\\\"), ('"', '\\"'), ("\n", "\\n"), ("\r", "\\r"), ("\t", "\\t")]
PN_LOCAL = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_\-]*$")


def ttl_literal(lit):
    v = lit.v
    for a, b in TTL_ESCAPES:
        v = v.replace(a, b)
    out = '"%s"' % v
    if lit.dt:
        out += "^^" + ttl_iri(IRI(lit.dt))
    return out


def ttl_iri(iri, base=None):
    for pfx, ns in PREFIXES:
        namespace = base if ns is None else ns
        if namespace and iri.v.startswith(namespace):
            local = iri.v[len(namespace):]
            if PN_LOCAL.match(local):
                return "%s:%s" % (pfx, local)
    return "<%s>" % iri.v


def term_ttl(t, base):
    if isinstance(t, IRI):
        return ttl_iri(t, base)
    if isinstance(t, BNode):
        return "_:" + t.v
    return ttl_literal(t)


def serialize_turtle(g, base):
    by_subject = {}
    order = []
    for s, p, o in g.triples:
        key = (type(s).__name__, s.v)
        if key not in by_subject:
            by_subject[key] = []
            order.append((key, s))
        by_subject[key].append((p, o))

    # inline a blank node when it is the object of exactly one triple
    obj_count = {}
    for _, _, o in g.triples:
        if isinstance(o, BNode):
            obj_count[o.v] = obj_count.get(o.v, 0) + 1
    inlinable = {k for k, v in obj_count.items() if v == 1}

    def render_po(pairs, indent):
        lines = []
        for p, o in pairs:
            if isinstance(o, BNode) and o.v in inlinable:
                inner = by_subject.get(("BNode", o.v), [])
                body = render_po(inner, indent + "        ")
                lines.append("%s%s [\n%s\n%s]" % (indent, term_ttl(p, base), body, indent))
            else:
                lines.append("%s%s %s" % (indent, term_ttl(p, base), term_ttl(o, base)))
        return " ;\n".join(lines)

    out = []
    out.append("# Support Organization Ontology -- RDF/OWL export")
    out.append("# GENERATED from Ontology/*.md by Plugins/scripts/export_rdf.py")
    out.append("# Do not edit. Regenerate instead.")
    out.append("")
    out.append("@prefix sup: <%s> ." % base)
    for pfx, ns in PREFIXES[1:]:
        out.append("@prefix %s: <%s> ." % (pfx, ns))
    out.append("")

    for key, s in order:
        if key[0] == "BNode" and key[1] in inlinable:
            continue
        pairs = by_subject[key]
        out.append("%s\n%s .\n" % (term_ttl(s, base), render_po(pairs, "        ")))
    return "\n".join(out) + "\n"


NT_ESCAPES = TTL_ESCAPES


def term_nt(t):
    if isinstance(t, IRI):
        return "<%s>" % t.v
    if isinstance(t, BNode):
        return "_:" + t.v
    v = t.v
    for a, b in NT_ESCAPES:
        v = v.replace(a, b)
    return '"%s"%s' % (v, ("^^<%s>" % t.dt) if t.dt else "")


def serialize_ntriples(g):
    return "".join(
        "%s %s %s .\n" % (term_nt(s), term_nt(p), term_nt(o)) for s, p, o in g.triples
    )


def xml_escape(text, attr=False):
    t = (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    if attr:
        t = t.replace('"', "&quot;")
    return t


def serialize_rdfxml(g, base):
    by_subject = {}
    order = []
    for s, p, o in g.triples:
        key = (type(s).__name__, s.v)
        if key not in by_subject:
            by_subject[key] = []
            order.append((key, s))
        by_subject[key].append((p, o))

    def qname(iri):
        for pfx, ns in PREFIXES:
            namespace = base if ns is None else ns
            if namespace and iri.v.startswith(namespace):
                local = iri.v[len(namespace):]
                if re.match(r"^[A-Za-z_][A-Za-z0-9_\-.]*$", local):
                    return "%s:%s" % (pfx, local)
        return None

    out = ['<?xml version="1.0" encoding="utf-8"?>']
    out.append("<!-- GENERATED from Ontology/*.md by Plugins/scripts/export_rdf.py -->")
    attrs = ['xmlns:sup="%s"' % xml_escape(base, True)]
    for pfx, ns in PREFIXES[1:]:
        attrs.append('xmlns:%s="%s"' % (pfx, ns))
    out.append("<rdf:RDF %s>" % "\n         ".join(attrs))

    for key, s in order:
        if isinstance(s, BNode):
            head = '  <rdf:Description rdf:nodeID="%s">' % s.v
        else:
            head = '  <rdf:Description rdf:about="%s">' % xml_escape(s.v, True)
        out.append(head)
        for p, o in by_subject[key]:
            tag = qname(p) or None
            if tag is None:
                # fall back to an explicit element with the full predicate IRI
                ns, local = re.match(r"^(.*[#/])([^#/]+)$", p.v).groups()
                tag = "ns:%s" % local
                extra = ' xmlns:ns="%s"' % xml_escape(ns, True)
            else:
                extra = ""
            if isinstance(o, IRI):
                out.append('    <%s%s rdf:resource="%s"/>' % (tag, extra, xml_escape(o.v, True)))
            elif isinstance(o, BNode):
                out.append('    <%s%s rdf:nodeID="%s"/>' % (tag, extra, o.v))
            else:
                dt = ' rdf:datatype="%s"' % xml_escape(o.dt, True) if o.dt else ""
                out.append("    <%s%s%s>%s</%s>" % (tag, extra, dt, xml_escape(o.v), tag.split()[0]))
        out.append("  </rdf:Description>")
    out.append("</rdf:RDF>")
    return "\n".join(out) + "\n"


def serialize_jsonld(g, base):
    context = {"sup": base}
    for pfx, ns in PREFIXES[1:]:
        context[pfx] = ns

    def compact(iri):
        for pfx, ns in PREFIXES:
            namespace = base if ns is None else ns
            if namespace and iri.v.startswith(namespace):
                local = iri.v[len(namespace):]
                if PN_LOCAL.match(local):
                    return "%s:%s" % (pfx, local)
        return iri.v

    nodes, order = {}, []
    for s, p, o in g.triples:
        sid = ("_:" + s.v) if isinstance(s, BNode) else s.v
        if sid not in nodes:
            nodes[sid] = {"@id": ("_:" + s.v) if isinstance(s, BNode) else compact(s)}
            order.append(sid)
        node = nodes[sid]
        key = "@type" if p.v == RDF + "type" else compact(p)
        if isinstance(o, IRI):
            val = compact(o) if key == "@type" else {"@id": compact(o)}
        elif isinstance(o, BNode):
            val = {"@id": "_:" + o.v}
        else:
            val = {"@value": o.v}
            if o.dt:
                val["@type"] = compact(IRI(o.dt))
            if not o.dt:
                val = o.v
        node.setdefault(key, [])
        node[key].append(val)

    for node in nodes.values():
        for k, v in list(node.items()):
            if k != "@id" and isinstance(v, list) and len(v) == 1:
                node[k] = v[0]

    return json.dumps({"@context": context, "@graph": [nodes[i] for i in order]},
                      indent=2, ensure_ascii=False) + "\n"


# --------------------------------------------------------------------------
# self-check
# --------------------------------------------------------------------------

def self_check(g, base, entities, declared):
    problems = []
    S = lambda n: IRI(base + n)  # noqa: E731

    subjects = set()
    for s, p, o in g.triples:
        if isinstance(s, Lit):
            problems.append("literal used as subject")
        if not isinstance(p, IRI):
            problems.append("non-IRI predicate")
        subjects.add((type(s).__name__, s.v))

    # every class and property made it in
    for e in entities:
        if ("IRI", base + e["id"]) not in subjects:
            problems.append("class missing from graph: %s" % e["id"])
    for prop in declared:
        if ("IRI", base + prop) not in subjects:
            problems.append("object property missing: %s" % prop)

    # every blank node is used and defined
    bn_sub = {s.v for s, _, _ in g.triples if isinstance(s, BNode)}
    bn_obj = {o.v for _, _, o in g.triples if isinstance(o, BNode)}
    for orphan in bn_sub - bn_obj:
        problems.append("blank node %s is never referenced" % orphan)
    for dangling in bn_obj - bn_sub:
        problems.append("blank node %s referenced but never described" % dangling)

    # inverse pairs must be symmetric
    inv = {}
    for s, p, o in g.triples:
        if p.v == OWL + "inverseOf":
            inv[s.v] = o.v
    for x, y in inv.items():
        if inv.get(y) != x:
            problems.append("owl:inverseOf not symmetric: %s -> %s" % (x, y))

    # IRIs must not contain spaces
    for s, p, o in g.triples:
        for t in (s, p, o):
            if isinstance(t, IRI) and (" " in t.v or '"' in t.v):
                problems.append("malformed IRI: %r" % t.v)

    # the alias map must have survived -- this is the export's whole point
    checks = [
        (S("Ticket"), IRI(SKOS + "altLabel"), Lit("Case")),
        (S("SeverityLevel"), IRI(SKOS + "altLabel"), Lit("Priority")),
    ]
    triple_set = {(type(s).__name__ + s.v, p.v, type(o).__name__ + o.v + str(getattr(o, "dt", "")))
                  for s, p, o in g.triples}
    for s, p, o in checks:
        key = (type(s).__name__ + s.v, p.v, type(o).__name__ + o.v + str(o.dt))
        if key not in triple_set:
            problems.append("expected alias triple missing: %s altLabel %s" % (s.v, o.v))

    platinum = any(
        p.v == SKOS + "altLabel" and isinstance(o, Lit) and "Platinum" in o.v
        for _, p, o in g.triples
    )
    if not platinum:
        problems.append("no Platinum altLabel anywhere in the graph")

    return problems


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Export the markdown ontology to RDF/OWL.")
    ap.add_argument("--base", default=DEFAULT_BASE, help="Base IRI (must end in # or /)")
    args = ap.parse_args()
    base = args.base
    if not base.endswith(("#", "/")):
        base += "#"

    g, entities, declared, cons, cqs, oqs, eqs = build(base)
    problems = self_check(g, base, entities, declared)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    files = {
        "support-ontology.ttl": serialize_turtle(g, base),
        "support-ontology.nt": serialize_ntriples(g),
        "support-ontology.rdf": serialize_rdfxml(g, base),
        "support-ontology.jsonld": serialize_jsonld(g, base),
    }
    for name, body in files.items():
        (OUT_DIR / name).write_text(body, encoding="utf-8")

    classes = len(entities)
    inds = sum(1 for s, p, o in g.triples
               if p.v == RDF + "type" and isinstance(o, IRI) and o.v == OWL + "NamedIndividual")
    dtp = sum(1 for s, p, o in g.triples
              if p.v == RDF + "type" and isinstance(o, IRI) and o.v == OWL + "DatatypeProperty")

    print("[OK] %d triples -> %s" % (len(g.triples), OUT_DIR.relative_to(ROOT)))
    print("       %-22s %d" % ("owl:Class", classes))
    print("       %-22s %d" % ("owl:ObjectProperty", len(declared)))
    print("       %-22s %d" % ("owl:DatatypeProperty", dtp))
    print("       %-22s %d" % ("owl:NamedIndividual", inds))
    print("       %-22s %d" % ("constraints", len(cons)))
    print("       %-22s %d" % ("competency questions", len(cqs)))
    print("       %-22s %d" % ("open questions", len(oqs)))
    print("       %-22s %d" % ("equivalences", len(eqs)))
    print("")
    for name in files:
        size = (OUT_DIR / name).stat().st_size
        print("       %-28s %6.1f KB" % (name, size / 1024.0))

    if problems:
        print("")
        print("[FAIL] %d self-check problem(s):" % len(problems))
        for item in sorted(set(problems)):
            print("       - %s" % item)
        return 1
    print("")
    print("[OK] self-check clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
