#!/usr/bin/env python3
"""Export the support ontology, and the masking policy bound to it, as SQL.

The ontology's markdown is the source of truth (support-ontology/Ontology/).
This script parses it and writes one SQL script in four parts:

  1. ER model. One table per class, one column per datatype property, and a
     foreign key or junction table per relationship. CHECK constraints cover
     the rules a single row can enforce.
  2. Ontology catalog. Classes, attributes, relationships, constraints,
     disjointness, individuals, aliases and equivalences, stored as rows.
  3. Masking layer. The three actions, every entity type the masker emits,
     and the proposed action for every ontology attribute.
  4. Views. One per cross-row constraint listing the records that break it,
     plus the masking lookups.

The output is generated. Never hand-edit sql/support_ontology_er.sql: change
the ontology or policy.py and re-run this script.

The SQL is a subset of PostgreSQL that SQLite also accepts. --check loads it
into SQLite and exercises every part. It has not been run against PostgreSQL.

Usage:
    python scripts/export_ontology_sql.py
    python scripts/export_ontology_sql.py --check
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
import textwrap
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ticketmask.arbitrate import _ATOMIC_TYPES, ENTITY_PRECEDENCE  # noqa: E402
from ticketmask.cli import DENY_LIST_FLAGS  # noqa: E402
from ticketmask.ontology import (  # noqa: E402
    ENTITLEMENT_TERMS,
    ENTITY_BINDINGS,
    PRESIDIO_RENAMES,
    PROTECTED_VOCABULARY,
    REGION_VALUES,
    SEVERITY_TERMS,
    ontology_dir,
)
from ticketmask.policy import ATTRIBUTE_POLICY, DEFAULT_POLICY, Action, Handling  # noqa: E402
from ticketmask.recognizers import DEFAULT_PRODUCTS, DENY_LIST_ENTITY_TYPES  # noqa: E402

DEFAULT_OUT = ROOT / "sql" / "support_ontology_er.sql"
DOMAIN_TYPE_ORDER = ["Customer", "Product", "Support", "Engineering", "Knowledge"]
MAX_IDENTIFIER = 63  # PostgreSQL truncates longer names silently


class OntologyError(Exception):
    """The ontology no longer has the shape this exporter was written against."""


# =============================================================================
# Physical design decisions. Everything the markdown cannot tell us is here,
# stated once, so the reasoning is reviewable in one place.
# =============================================================================

#: Each class's identity rule, translated into primary key parts. A part is a
#: datatype property, a relationship name (its foreign key columns join the
#: key), or an identity reference listed in IDENTITY_REFERENCES.
IDENTITY_KEYS: dict[str, list[str]] = {
    "Account": ["accountId"],
    "CRM": ["systemCode"],
    "Contact": ["contactId"],
    "CustomerSuccessManager": ["csmId"],
    "Documentation": ["articleUrl"],
    "Escalation": ["escalationId"],
    "JiraIssue": ["issueKey"],
    # "Composite: accountId + productId + startDate"
    "License": ["isHeldBy", "grantsAccessTo", "startDate"],
    "Partner": ["partnerId"],
    "Product": ["productId"],
    "Region": ["regionCode"],
    # "A composite of severityLevel + entitlementTier"
    "SLA": ["severityLevel", "entitlementTier"],
    "SalesRepresentative": ["repId"],
    "SeverityLevel": ["levelCode"],
    "SupportAgent": ["agentId"],
    "SupportEntitlement": ["tierCode"],
    # "a fully qualified ticket identity is systemCode + ticketNumber"
    "Ticket": ["recordedIn", "ticketNumber"],
}

#: References the identity rule names but 02-Relationships.md does not declare
#: as relationships. They become foreign keys and are not catalogued as
#: relationships, because the ontology does not list them as relationships.
IDENTITY_REFERENCES: dict[str, dict[str, str]] = {
    "SLA": {"severityLevel": "SeverityLevel", "entitlementTier": "SupportEntitlement"},
}

#: Cardinalities whose constraint is Soft. On a Soft violation the ontology
#: says "Alert. Do not block", so the foreign key stays nullable and a view
#: reports the gap.
SOFT_CARDINALITY = {"describes": "C-55"}

#: Required properties left nullable because the ontology's own individuals
#: are unconfirmed. Inventing a value would break its rule that "an alias map
#: populated from assumption is worse than one that is visibly incomplete".
#: v_seed_gaps lists every NULL they hold.
UNCONFIRMED_SEED_COLUMNS: dict[tuple[str, str], tuple[str | None, str]] = {
    ("CRM", "ticketTermUsed"): ("OQ-50", "Confirmed for Salesforce only."),
    ("CRM", "isAuthoritative"): ("OQ-50", "Unconfirmed for Zendesk."),
    ("SupportEntitlement", "grantsEscalationRight"): (
        None,
        "Not stated for PREMIUM. C-12 settles STANDARD (false) only.",
    ),
}

#: tierRank from SupportEntitlement's notes ("Standard 1, Premium 2").
#: Asserted against the text so a change there fails this script.
ENTITLEMENT_RANKS = {"STANDARD": 1, "PREMIUM": 2}

#: Row-level rules, enforced as CHECK constraints.
TABLE_CHECKS: dict[str, tuple[str, str]] = {
    "C-12": ("SupportEntitlement", "grants_escalation_right = FALSE OR tier_code = 'PREMIUM'"),
    "C-13": ("License", "end_date IS NULL OR end_date > start_date"),
    "C-22": ("Product", "lifecycle_status <> 'EndOfLife' OR end_of_life_date IS NOT NULL"),
    "C-24": (
        "Ticket",
        "(status NOT IN ('Resolved', 'Closed') OR resolved_at IS NOT NULL) "
        "AND (resolved_at IS NULL OR resolved_at >= opened_at)",
    ),
}

TICKET_KEY = "t.system_code || ':' || t.ticket_number"

#: Cross-row rules, enforced as views. Each lists the records that break it as
#: (table_name, record_key, detail). A view reports; it never blocks a write,
#: which is the right behaviour for Soft and Advisory rules. For the Hard ones
#: it is the only portable option.
VIOLATION_VIEWS: dict[str, str] = {
    "C-06": f"""
SELECT 'ticket' AS table_name, {TICKET_KEY} AS record_key,
       'status is Escalated but no Escalation exists' AS detail
FROM ticket t
WHERE t.status = 'Escalated'
  AND NOT EXISTS (SELECT 1 FROM escalation e
                  WHERE e.system_code = t.system_code AND e.ticket_number = t.ticket_number)""",
    "C-08": """
SELECT 'account' AS table_name, a.account_id AS record_key,
       'has a CSM but isStrategic is not true' AS detail
FROM account a
WHERE a.csm_id IS NOT NULL AND (a.is_strategic IS NULL OR a.is_strategic = FALSE)""",
    "C-09": """
SELECT 'account' AS table_name, a.account_id AS record_key,
       'Active account holds no active License' AS detail
FROM account a
WHERE a.account_status = 'Active'
  AND NOT EXISTS (SELECT 1 FROM license l WHERE l.account_id = a.account_id AND l.is_active = TRUE)""",
    "C-10": """
SELECT 'region' AS table_name, r.region_code AS record_key,
       'no SalesRepresentative covers this Region' AS detail
FROM region r
WHERE NOT EXISTS (SELECT 1 FROM region_is_covered_by_sales_representative c
                  WHERE c.region_code = r.region_code)""",
    # endDate is compared to the opening timestamp, so a licence ending on the
    # day a ticket opens counts as expired. The ontology does not say.
    "C-14": f"""
SELECT 'ticket' AS table_name, {TICKET_KEY} AS record_key,
       'no active License covered the product when the ticket opened' AS detail
FROM ticket t
WHERE NOT EXISTS (SELECT 1 FROM license l
                  WHERE l.account_id = t.account_id AND l.product_id = t.product_id
                    AND l.start_date <= t.opened_at
                    AND (l.end_date IS NULL OR l.end_date >= t.opened_at))""",
    "C-16": f"""
SELECT 'ticket' AS table_name, {TICKET_KEY} AS record_key,
       'submitting Contact works for a different Account' AS detail
FROM ticket t
JOIN contact c ON c.contact_id = t.contact_id
WHERE c.account_id <> t.account_id""",
    "C-17": f"""
SELECT 'ticket' AS table_name, {TICKET_KEY} AS record_key,
       'submitted by a Contact who is not support-authorised' AS detail
FROM ticket t
JOIN contact c ON c.contact_id = t.contact_id
WHERE c.is_support_authorised = FALSE""",
    "C-23": """
SELECT 'documentation' AS table_name, d.article_url AS record_key,
       'describes an EndOfLife product: retirement candidate' AS detail
FROM documentation d
JOIN product p ON p.product_id = d.product_id
WHERE p.lifecycle_status = 'EndOfLife'""",
    "C-28": """
SELECT 'escalation' AS table_name, e.escalation_id AS record_key,
       'Bug escalation without reproductionSteps' AS detail
FROM escalation e
WHERE e.escalation_type = 'Bug'
  AND (e.reproduction_steps IS NULL OR TRIM(e.reproduction_steps) = '')""",
    "C-32": f"""
SELECT 'ticket' AS table_name, {TICKET_KEY} AS record_key,
       'open ticket assigned to an inactive SupportAgent' AS detail
FROM ticket t
JOIN support_agent s ON s.agent_id = t.agent_id
WHERE s.is_active = FALSE AND t.status NOT IN ('Resolved', 'Closed')""",
    "C-33": """
SELECT 'jira_issue' AS table_name, j.issue_key AS record_key,
       'no Escalation traces to this issue' AS detail
FROM jira_issue j
WHERE NOT EXISTS (SELECT 1 FROM escalation e WHERE e.issue_key = j.issue_key)""",
    "C-35": """
SELECT 'jira_issue' AS table_name, j.issue_key AS record_key,
       'resolved, but originating ticket ' || t.system_code || ':' || t.ticket_number
       || ' is still open' AS detail
FROM jira_issue j
JOIN escalation e ON e.issue_key = j.issue_key
JOIN ticket t ON t.system_code = e.system_code AND t.ticket_number = e.ticket_number
WHERE j.is_resolved = TRUE AND t.status NOT IN ('Resolved', 'Closed')""",
    "C-46": """
SELECT 'account' AS table_name, a.account_id AS record_key,
       'SalesRepresentative does not cover the Account''s Region' AS detail
FROM account a
WHERE NOT EXISTS (SELECT 1 FROM region_is_covered_by_sales_representative c
                  WHERE c.region_code = a.region_code AND c.rep_id = a.rep_id)""",
    "C-50": """
SELECT 'crm' AS table_name, c.system_code AS record_key,
       'ticketTermUsed is not declared' AS detail
FROM crm c
WHERE c.ticket_term_used IS NULL""",
    # All three roles are keyed on the CRM user ID, so one ID in two role
    # tables is one person in two disjoint roles. This only holds within one
    # CRM: across CRMs the ontology matches people on corporate email instead.
    "C-52": """
SELECT 'support_agent' AS table_name, s.agent_id AS record_key,
       'also a SalesRepresentative' AS detail
FROM support_agent s JOIN sales_representative r ON r.rep_id = s.agent_id
UNION ALL
SELECT 'support_agent', s.agent_id, 'also a CustomerSuccessManager'
FROM support_agent s JOIN customer_success_manager m ON m.csm_id = s.agent_id
UNION ALL
SELECT 'sales_representative', r.rep_id, 'also a CustomerSuccessManager'
FROM sales_representative r JOIN customer_success_manager m ON m.csm_id = r.rep_id""",
    "C-54": """
SELECT 'license' AS table_name,
       l.account_id || ':' || l.product_id || ':' || CAST(l.start_date AS VARCHAR(10)) AS record_key,
       'License tier differs from its Account''s tier' AS detail
FROM license l
JOIN account a ON a.account_id = l.account_id
WHERE l.tier_code <> a.tier_code""",
    "C-55": """
SELECT 'documentation' AS table_name, d.article_url AS record_key,
       'describes no Product' AS detail
FROM documentation d
WHERE d.product_id IS NULL""",
    # The severity half of C-56 is the ticket's own level_code. The
    # entitlement half has to come from the account.
    "C-56": f"""
SELECT 'ticket' AS table_name, {TICKET_KEY} AS record_key,
       'SLA does not match the ticket severity and account entitlement' AS detail
FROM ticket t
JOIN account a ON a.account_id = t.account_id
WHERE t.sla_level_code <> t.level_code OR t.sla_tier_code <> a.tier_code""",
    "C-57": f"""
SELECT 'ticket' AS table_name, {TICKET_KEY} AS record_key,
       'raised by a Partner that does not represent the Account' AS detail
FROM ticket t
WHERE t.partner_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM partner_represents_account p
                  WHERE p.partner_id = t.partner_id AND p.account_id = t.account_id)""",
}

#: How each active constraint is enforced when it is not a CHECK or a view.
#: STRUCTURAL means the table shape makes a violation impossible to store.
OTHER_ENFORCEMENT: dict[str, tuple[str, str]] = {
    "C-01": ("STRUCTURAL", "account.region_code is a NOT NULL foreign key."),
    "C-02": ("STRUCTURAL", "account.tier_code is a NOT NULL foreign key. Only the "
                           "current tier is stored; effective dates on the link are not modelled."),
    "C-04": ("STRUCTURAL", "ticket.account_id, level_code and product_id are NOT NULL foreign keys."),
    "C-05": ("STRUCTURAL", "ticket has no Jira column. The only path is escalation.issue_key."),
    "C-07": ("STRUCTURAL", "account.rep_id is a NOT NULL foreign key."),
    "C-11": ("DECLARATIVE", "CHECK on support_entitlement.tier_code, seeded with both tiers."),
    "C-15": ("STRUCTURAL", "contact.account_id is a NOT NULL foreign key."),
    "C-25": ("DECLARATIVE", "CHECK on severity_level.level_code, seeded with S1-S4."),
    "C-26": ("NOT_ENFORCED", "Query rule: compare severity_level.level_rank, never labels."),
    "C-27": ("STRUCTURAL", "escalation.issue_key is a NOT NULL foreign key."),
    "C-29": ("STRUCTURAL", "escalation.agent_id references support_agent only."),
    "C-31": ("STRUCTURAL", "ticket.agent_id is one column; assignment history is not modelled."),
    "C-34": ("NOT_ENFORCED", "isResolved is derived upstream from a per-project status mapping."),
    "C-40": ("NOT_ENFORCED", "Needs date arithmetic, which is not portable. PostgreSQL: "
                             "WHERE last_reviewed_at < CURRENT_DATE - INTERVAL '24 months'."),
    "C-47": ("STRUCTURAL", "account.csm_id is a single column."),
    "C-48": ("STRUCTURAL", "ticket.system_code is NOT NULL and part of the primary key."),
    "C-49": ("NOT_ENFORCED", "Needs fact-level provenance, which this schema does not store."),
    "C-51": ("DECLARATIVE", "product.uses_platinum_naming and severity_term_used are NOT NULL."),
    "C-53": ("STRUCTURAL", "license.tier_code is a NOT NULL foreign key."),
}

#: Class B phrases in the disjointness table that are not a single class.
DISJOINT_PHRASES = {
    "the internal role classes": ["SupportAgent", "SalesRepresentative", "CustomerSuccessManager"],
}

ACTION_ROWS: dict[Action, tuple[str, str, bool, str]] = {
    Action.PSEUDONYMIZE: (
        "Pseudonymize",
        "Typed surrogate such as <CONTACT_1>, stable within one ticket",
        True,
        "Replace with a surrogate and store the original in the encrypted per-ticket "
        "vault. Reversible on the audit path only; published articles stay masked.",
    ),
    Action.KEEP: (
        "Keep",
        "The original value",
        False,
        "Leave in place: provenance identifiers and the ontology's controlled "
        "vocabulary, which is meaning, not data.",
    ),
    Action.REDACT: (
        "Reject",
        "Type marker such as <LICENSE_KEY>",
        False,
        "Remove irreversibly and store nothing. Called REDACT in the code.",
    ),
}


# =============================================================================
# Markdown parsing
# =============================================================================

def strip_md(value: str) -> str:
    value = value.replace("**", "").replace("`", "")
    value = re.sub(r"\*(\w[^*]*?)\*", r"\1", value)  # *italic*, but not 0..*
    return " ".join(value.split())


def split_sections(text: str, marker: str = "## ") -> dict[str, str]:
    found: dict[str, str] = {}
    current, buffer = "_preamble", []
    for line in text.splitlines():
        if line.startswith(marker):
            found[current] = "\n".join(buffer).strip()
            current, buffer = line[len(marker):].strip(), []
        else:
            buffer.append(line)
    found[current] = "\n".join(buffer).strip()
    return found


def tables_in(text: str) -> list[list[list[str]]]:
    """Every markdown table as a list of rows. Row 0 is the header."""
    tables: list[list[list[str]]] = []
    current: list[list[str]] | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            current = None
            continue
        cells = [c.strip() for c in stripped[1:-1].split("|")]
        if any(cells) and all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        if current is None:
            current = []
            tables.append(current)
        current.append(cells)
    return tables


def table_with_header(text: str, first: str, where: str) -> list[list[str]]:
    for table in tables_in(text):
        if strip_md(table[0][0]) == first:
            return table
    raise OntologyError(f"{where}: no table whose first column is {first!r}")


def snake(name: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name).lower()


def split_terms(cell: str) -> list[tuple[str, str | None]]:
    """'Case owner, Owner, TAM (may be distinct)' -> [(term, note), ...]."""
    text, parts, depth, buffer = strip_md(cell), [], 0, ""
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if char == "," and depth == 0:
            parts.append(buffer)
            buffer = ""
        else:
            buffer += char
    parts.append(buffer)

    terms = []
    for part in (p.strip() for p in parts):
        if not part:
            continue
        match = re.fullmatch(r"(.*?)\s*\((.*)\)", part)
        term, note = (match.group(1), match.group(2)) if match else (part, None)
        term = term.strip().strip('"')
        if term:
            terms.append((term, note))
    return terms


@dataclass
class Attribute:
    name: str
    datatype: str
    required: bool
    notes: str


@dataclass
class ObjectProperty:
    name: str
    target: str
    cardinality: str
    inverse: str


@dataclass
class OntClass:
    name: str
    class_id: str
    domain_type: str
    status: str
    version: str
    definition: str
    identity_rule: str
    attributes: list[Attribute]
    object_properties: list[ObjectProperty]
    aliases: list[tuple[str, str, str | None]]
    individuals_text: str
    source: str


@dataclass
class Relationship:
    name: str
    domain: str
    range: str
    cardinality: str
    inverse: str
    inverse_cardinality: str
    notes: str
    group: str
    implemented_as: str = ""
    physical_table: str = ""
    physical_columns: str = ""
    constraint_name: str = ""


@dataclass
class Constraint:
    constraint_id: str
    status: str
    level: str | None
    category: str
    statement: str
    catches: str | None = None
    retired_reason: str | None = None


@dataclass
class Individual:
    class_name: str
    code: str
    label: str | None
    rank: int | None
    notes: str | None
    aliases: list[str] = field(default_factory=list)


@dataclass
class Equivalence:
    eq_id: str
    title: str
    kind: str
    canonical_ref: str | None
    equivalent_labels: str | None
    varies_by: str | None
    anchor_property: str | None
    status_note: str | None


REQUIRED_HEADINGS = [
    "Definition", "Canonical name and aliases", "Identity rule", "Datatype properties",
    "Object properties", "Subclasses and individuals", "Disjoint with", "Constraints",
    "Provenance", "Competency questions answered", "Open questions",
]


def parse_entity(path: Path) -> OntClass:
    text = path.read_text(encoding="utf-8")
    sections = split_sections(text)
    where = f"Entities/{path.name}"
    missing = [h for h in REQUIRED_HEADINGS if h not in sections]
    if missing:
        raise OntologyError(f"{where}: missing template headings {missing}")

    preamble = sections["_preamble"]

    def preamble_field(label: str) -> str:
        match = re.search(rf"\*\*{re.escape(label)}:\*\*\s*(.+)", preamble)
        if not match:
            raise OntologyError(f"{where}: no **{label}:** line")
        return strip_md(match.group(1))

    name = re.search(r"^# (\w+)", preamble, re.M).group(1)
    definition = next(
        " ".join(block.split())
        for block in sections["Definition"].split("\n\n")
        if block.strip() and not block.strip().startswith(">")
    )

    attributes = []
    for row in table_with_header(sections["Datatype properties"], "Property", where)[1:]:
        required = strip_md(row[2])
        if required not in ("Yes", "No"):
            raise OntologyError(f"{where}: Required must be Yes or No, got {required!r}")
        attributes.append(Attribute(strip_md(row[0]), strip_md(row[1]), required == "Yes", strip_md(row[3])))

    object_properties = [
        ObjectProperty(strip_md(r[0]), strip_md(r[1]).removeprefix("sup:"), strip_md(r[2]), strip_md(r[3]))
        for r in table_with_header(sections["Object properties"], "Property", where)[1:]
    ]

    aliases = []
    for row in table_with_header(sections["Canonical name and aliases"], "Context", where)[1:]:
        context = strip_md(row[0])
        if context == "Canonical":
            continue
        aliases.extend((context, term, note) for term, note in split_terms(row[1]))

    return OntClass(
        name=name,
        class_id=preamble_field("Class ID"),
        domain_type=preamble_field("Type"),
        status=preamble_field("Status"),
        version=preamble_field("Version"),
        definition=strip_md(definition),
        identity_rule=strip_md(sections["Identity rule"]),
        attributes=attributes,
        object_properties=object_properties,
        aliases=aliases,
        individuals_text=sections["Subclasses and individuals"],
        source=text,
    )


class Ontology:
    def __init__(self, root: Path):
        self.root = root
        entity_dir = root / "Ontology" / "Entities"
        if not entity_dir.is_dir():
            raise OntologyError(f"ontology not found at {root} (set TICKETMASK_ONTOLOGY_DIR)")

        parsed = [parse_entity(p) for p in sorted(entity_dir.glob("*.md"))]
        self.classes = {c.name: c for c in parsed}
        self.relationships = self._relationships()
        self.constraints, self.disjointness = self._constraints()
        self.individuals = self._individuals()
        self.equivalences = self._equivalences()
        self.changelog_head = self._changelog_head()

    def ordered_classes(self) -> list[OntClass]:
        return sorted(self.classes.values(),
                      key=lambda c: (DOMAIN_TYPE_ORDER.index(c.domain_type), c.name))

    def _relationships(self) -> list[Relationship]:
        text = (self.root / "Ontology" / "02-Relationships.md").read_text(encoding="utf-8")
        relationships = []
        for group, section in split_sections(text).items():
            catalog = [t for t in tables_in(section)
                       if [strip_md(c) for c in t[0][:3]] == ["Property", "Domain", "Range"]]
            for row in (row for table in catalog for row in table[1:]):
                name, domain, range_, card, inverse, notes = (strip_md(c) for c in row)
                for cls in (domain, range_):
                    if cls not in self.classes:
                        raise OntologyError(f"relationship {name}: unknown class {cls}")

                forward = [p for p in self.classes[domain].object_properties if p.name == name]
                backward = [p for p in self.classes[range_].object_properties
                            if p.name == inverse and p.target == domain]
                if not forward or forward[0].cardinality != card:
                    raise OntologyError(f"{name}: catalog says {card}, {domain}.md disagrees")
                if not backward:
                    raise OntologyError(f"{name}: inverse {inverse} not declared in {range_}.md")

                relationships.append(Relationship(
                    name, domain, range_, card, inverse, backward[0].cardinality, notes, group))

        declared = re.search(r"(\d+) relationships across (\d+) classes", text)
        if not declared or int(declared.group(1)) != len(relationships):
            raise OntologyError(f"02-Relationships.md declares {declared and declared.group(1)} "
                                f"relationships; parsed {len(relationships)}")
        if int(declared.group(2)) != len(self.classes):
            raise OntologyError(f"02-Relationships.md declares {declared.group(2)} classes; "
                                f"found {len(self.classes)} entity files")
        return relationships

    def _constraints(self) -> tuple[list[Constraint], list[tuple[str, str, str]]]:
        text = (self.root / "Ontology" / "04-Constraints-and-Rules.md").read_text(encoding="utf-8")
        constraints, disjoint = [], []
        for heading, body in split_sections(text).items():
            for table in tables_in(body):
                header = [strip_md(c) for c in table[0]]
                rows = [[strip_md(c) for c in row] for row in table[1:]]
                if header[:2] == ["ID", "Level"]:
                    for row in rows:
                        constraints.append(Constraint(
                            row[0], "Active", row[1], heading, row[2],
                            catches=row[3] if len(row) > 3 else None))
                elif header[:2] == ["ID", "Was"]:
                    for row in rows:
                        constraints.append(Constraint(
                            row[0], "Retired", None, heading, row[1], retired_reason=row[2]))
                elif header[:2] == ["Class A", "Class B"]:
                    for row in rows:
                        disjoint.extend((a, b, row[2])
                                        for a in self._class_list(row[0])
                                        for b in self._class_list(row[1]))
        return constraints, disjoint

    def _class_list(self, cell: str) -> list[str]:
        if cell in DISJOINT_PHRASES:
            return DISJOINT_PHRASES[cell]
        if cell == "every domain class":
            return [n for n in sorted(self.classes) if n != "CRM"]
        names = [n.strip() for n in cell.split("/")]
        unknown = [n for n in names if n not in self.classes]
        if unknown:
            raise OntologyError(f"disjointness: cannot resolve {cell!r} to classes")
        return names

    def _individuals(self) -> list[Individual]:
        out: list[Individual] = []

        region = self.classes["Region"].individuals_text
        for code, label in re.findall(r"^- `(\w+)` — (.+)$", region, re.M):
            out.append(Individual("Region", code, label.strip(), None, None))

        severity = self.classes["SeverityLevel"]
        definitions = {
            code: strip_md(body)
            for code, _name, body in re.findall(
                r"\*\*(S[1-4]) — ([^*]+?)\.\*\*\s*(.+?)(?:\n\n|\Z)", severity.source, re.S)
        }
        for row in table_with_header(severity.individuals_text, "Canonical", "SeverityLevel.md")[1:]:
            code = strip_md(row[0])
            if code not in definitions:
                raise OntologyError(f"SeverityLevel.md: no definition paragraph for {code}")
            out.append(Individual("SeverityLevel", code, strip_md(row[2]), int(strip_md(row[1])),
                                  definitions[code], [t for t, _ in split_terms(row[3])]))

        entitlement = self.classes["SupportEntitlement"]
        rank_note = next(a.notes for a in entitlement.attributes if a.name == "tierRank")
        if "Standard 1, Premium 2" not in rank_note:
            raise OntologyError("SupportEntitlement.tierRank notes changed; update ENTITLEMENT_RANKS")
        for row in table_with_header(entitlement.individuals_text, "Canonical individual",
                                     "SupportEntitlement.md")[1:]:
            code = strip_md(row[1])
            out.append(Individual("SupportEntitlement", code, strip_md(row[0]), ENTITLEMENT_RANKS[code],
                                  strip_md(row[2]), re.findall(r'"([^"]+)"', row[2])))

        for row in table_with_header(self.classes["CRM"].individuals_text, "systemCode", "CRM.md")[1:]:
            out.append(Individual("CRM", strip_md(row[0]), strip_md(row[1]), None, strip_md(row[4])))

        product_blocks = [
            b for b in self.classes["Product"].individuals_text.split("\n\n")
            if len(re.findall(r"`[^`]+`", b)) >= 3
        ]
        if len(product_blocks) != 1:
            raise OntologyError("Product.md: cannot find the working set of products")
        for code in re.findall(r"`([^`]+)`", product_blocks[0]):
            out.append(Individual("Product", code, code, None, "Working set: family-level name (OQ-14)"))
        return out

    def _equivalences(self) -> list[Equivalence]:
        text = (self.root / "Ontology" / "03-Vocabulary-and-Equivalence.md").read_text(encoding="utf-8")
        out = []
        for heading, body in split_sections(text, "### ").items():
            match = re.fullmatch(r"(EQ-\d+) — (.+)", strip_md(heading))
            if not match:
                continue
            table = tables_in(body)[0]
            rows = {strip_md(r[0]): strip_md(r[1]) for r in table[1:]}
            collision = any(k.startswith("Not an equivalence") for k in rows)
            out.append(Equivalence(
                eq_id=match.group(1),
                title=match.group(2),
                kind="COLLISION" if collision else "EQUIVALENCE",
                canonical_ref=rows.get("Canonical class") or rows.get("Canonical individual")
                or rows.get("Classes involved"),
                equivalent_labels=rows.get("Equivalent labels"),
                varies_by=rows.get("Varies by"),
                anchor_property=rows.get("Anchor property"),
                status_note=rows.get("Status") or rows.get("Declared"),
            ))
        return out

    def _changelog_head(self) -> str:
        text = (self.root / "CHANGELOG.md").read_text(encoding="utf-8")
        match = re.search(r"^## (\d{4}-\d{2}-\d{2}.*)$", text, re.M)
        return strip_md(match.group(1)) if match else "unknown"


# =============================================================================
# Physical model
# =============================================================================

TYPE_SQL = {
    "string": "VARCHAR(255)", "text": "TEXT", "integer": "INTEGER", "boolean": "BOOLEAN",
    "date": "DATE", "datetime": "TIMESTAMP", "uuid": "VARCHAR(36)",
}


@dataclass
class Column:
    name: str
    sql_type: str
    nullable: bool
    comment: str


@dataclass
class ForeignKey:
    name: str
    columns: list[str]
    ref_table: str
    ref_columns: list[str]


@dataclass
class Table:
    name: str
    kind: str                       # "entity" or "junction"
    header: list[str]
    class_name: str | None = None
    attr_columns: list[Column] = field(default_factory=list)
    fk_columns: list[Column] = field(default_factory=list)
    pk: list[str] = field(default_factory=list)
    fks: list[ForeignKey] = field(default_factory=list)
    checks: list[tuple[str, str]] = field(default_factory=list)
    attr_by_property: dict[str, Column] = field(default_factory=dict)

    def column(self, name: str) -> Column | None:
        return next((c for c in self.attr_columns + self.fk_columns if c.name == name), None)

    def ordered_columns(self) -> list[Column]:
        all_columns = self.attr_columns + self.fk_columns
        key = [self.column(n) for n in self.pk]
        return key + [c for c in all_columns if c.name not in self.pk]


def attribute_sql_type(attr: Attribute) -> tuple[str, list[str] | None]:
    enum = re.fullmatch(r"enum\((.+)\)", attr.datatype)
    if enum:
        values = [v.strip() for v in enum.group(1).split(",")]
        if max(map(len, values)) > 32:
            raise OntologyError(f"{attr.name}: enum value longer than 32 characters")
        return "VARCHAR(32)", values
    if attr.datatype not in TYPE_SQL:
        raise OntologyError(f"{attr.name}: no SQL type for datatype {attr.datatype!r}")
    if attr.datatype == "string" and attr.name.endswith("Url"):
        return "VARCHAR(2048)", None
    return TYPE_SQL[attr.datatype], None


class Model:
    def __init__(self, ontology: Ontology):
        self.ont = ontology
        self.tables: dict[str, Table] = {}
        self.junctions: list[Table] = []
        self._pk: dict[str, list[Column]] = {}
        self._done: set[str] = set()
        self.by_name = {}
        for rel in ontology.relationships:
            self.by_name[rel.name] = rel
            self.by_name[rel.inverse] = rel

        for cls in ontology.ordered_classes():
            self.tables[cls.name] = self._entity_table(cls)
        for cls in ontology.ordered_classes():
            self.tables[cls.name].pk = [c.name for c in self.pk_columns(cls.name)]
        for rel in ontology.relationships:
            self.ensure_relationship(rel)
        for constraint_id, (class_name, expr) in TABLE_CHECKS.items():
            table = self.tables[class_name]
            table.checks.append((f"ck_{table.name}_{constraint_id.replace('-', '').lower()}", expr))
        self._check_identifiers()

    def _entity_table(self, cls: OntClass) -> Table:
        wrapped = textwrap.wrap(cls.definition, 74)
        table = Table(
            name=snake(cls.name),
            kind="entity",
            class_name=cls.name,
            header=[f"{cls.class_id}  ({cls.domain_type}, {cls.status})", *wrapped,
                    *textwrap.wrap(f"Identity: {cls.identity_rule}", 74)],
        )
        for attr in cls.attributes:
            sql_type, enum_values = attribute_sql_type(attr)
            nullable = not attr.required
            comment = f"{attr.name} ({attr.datatype}{', required' if attr.required else ''})"
            if attr.notes:
                comment += f": {attr.notes}"
            gap = UNCONFIRMED_SEED_COLUMNS.get((cls.name, attr.name))
            if gap:
                nullable = True
                comment += f" | NULL allowed while unconfirmed{' (' + gap[0] + ')' if gap[0] else ''}"
            column = Column(snake(attr.name), sql_type, nullable, comment)
            table.attr_columns.append(column)
            table.attr_by_property[attr.name] = column
            if enum_values:
                listed = ", ".join(f"'{v}'" for v in enum_values)
                table.checks.append((f"ck_{table.name}_{column.name}", f"{column.name} IN ({listed})"))
        return table

    def pk_columns(self, class_name: str) -> list[Column]:
        if class_name in self._pk:
            return self._pk[class_name]
        table = self.tables[class_name]
        columns: list[Column] = []
        for part in IDENTITY_KEYS[class_name]:
            if part in table.attr_by_property:
                columns.append(table.attr_by_property[part])
            elif part in self.by_name:
                columns.extend(self.ensure_relationship(self.by_name[part], owner=class_name))
            elif part in IDENTITY_REFERENCES.get(class_name, {}):
                target = IDENTITY_REFERENCES[class_name][part]
                columns.extend(self.add_fk(class_name, target, f"identity_{snake(target)}",
                                           nullable=False,
                                           comment=f"identity: {part} -> {target}"))
            else:
                raise OntologyError(f"{class_name}: identity part {part!r} is not a property")
        if any(c.nullable for c in columns):
            raise OntologyError(f"{class_name}: identity column is nullable")
        self._pk[class_name] = columns
        return columns

    def ensure_relationship(self, rel: Relationship, owner: str | None = None) -> list[Column]:
        forward_max = rel.cardinality.split("..")[1]
        inverse_max = rel.inverse_cardinality.split("..")[1]
        if forward_max == "1" and inverse_max == "*":
            side = (rel.domain, rel.range, rel.name, rel.cardinality)
        elif inverse_max == "1" and forward_max == "*":
            side = (rel.range, rel.domain, rel.inverse, rel.inverse_cardinality)
        elif forward_max == "*" and inverse_max == "*":
            if rel.name not in self._done:
                self._done.add(rel.name)
                self.add_junction(rel)
            return []
        else:
            raise OntologyError(f"{rel.name}: one-to-one relationships are not handled")

        fk_owner, target, prop, card = side
        if owner and owner != fk_owner:
            raise OntologyError(f"{owner}: identity uses {prop}, whose key lives on {fk_owner}")
        table = self.tables[fk_owner]
        if rel.name in self._done:
            fk = next(f for f in table.fks if f.name == rel.constraint_name)
            return [table.column(n) for n in fk.columns]

        self._done.add(rel.name)
        soft = SOFT_CARDINALITY.get(rel.name)
        nullable = card.startswith("0") or soft is not None
        comment = f"{prop} -> {target} ({card})"
        if soft:
            comment += f"; nullable because {soft} is Soft"
        columns = self.add_fk(fk_owner, target, prop, nullable, comment)
        rel.implemented_as = "FOREIGN_KEY"
        rel.physical_table = table.name
        rel.physical_columns = ", ".join(c.name for c in columns)
        rel.constraint_name = table.fks[-1].name
        return columns

    def add_fk(self, owner: str, target: str, prop: str, nullable: bool, comment: str) -> list[Column]:
        table = self.tables[owner]
        target_table = self.tables[target]
        target_pk = self.pk_columns(target)
        names = [c.name for c in target_pk]
        if any(table.column(n) for n in names):
            names = [f"{target_table.name}_{n}" for n in names]
        if any(table.column(n) for n in names):
            raise OntologyError(f"{table.name}: cannot name foreign key columns for {prop}")
        columns = [Column(n, c.sql_type, nullable, comment) for n, c in zip(names, target_pk)]
        table.fk_columns.extend(columns)
        table.fks.append(ForeignKey(f"fk_{table.name}_{snake(prop)}", names,
                                    target_table.name, [c.name for c in target_pk]))
        return columns

    def add_junction(self, rel: Relationship) -> None:
        domain, range_ = self.tables[rel.domain], self.tables[rel.range]
        name = f"{domain.name}_{snake(rel.name)}_{range_.name}"
        domain_pk, range_pk = self.pk_columns(rel.domain), self.pk_columns(rel.range)
        domain_names = [c.name for c in domain_pk]
        range_names = [c.name for c in range_pk]
        if set(domain_names) & set(range_names):
            domain_names = [f"{domain.name}_{n}" for n in domain_names]
            range_names = [f"{range_.name}_{n}" for n in range_names]

        junction = Table(
            name=name,
            kind="junction",
            header=[f"{rel.domain} {rel.name} {rel.range}  ({rel.cardinality}); "
                    f"inverse {rel.inverse} ({rel.inverse_cardinality})",
                    "Many-to-many, so it needs its own table."]
            + ([f"Note: {rel.notes}"] if rel.notes else []),
        )
        for names, source, target in ((domain_names, domain_pk, domain.name),
                                      (range_names, range_pk, range_.name)):
            junction.fk_columns.extend(
                Column(n, c.sql_type, False, f"-> {target}.{c.name}") for n, c in zip(names, source))
        junction.pk = domain_names + range_names
        junction.fks = [
            ForeignKey(f"fk_{name}_from", domain_names, domain.name, [c.name for c in domain_pk]),
            ForeignKey(f"fk_{name}_to", range_names, range_.name, [c.name for c in range_pk]),
        ]
        self.junctions.append(junction)
        rel.implemented_as = "JUNCTION_TABLE"
        rel.physical_table = name
        rel.physical_columns = ", ".join(junction.pk)
        rel.constraint_name = f"pk_{name}"

    def all_tables(self) -> list[Table]:
        """Entity tables in dependency order, then junctions."""
        pending = [self.tables[c.name] for c in self.ont.ordered_classes()]
        ordered: list[Table] = []
        while pending:
            ready = next((t for t in pending
                          if all(fk.ref_table in {o.name for o in ordered} | {t.name} for fk in t.fks)),
                         None)
            if ready is None:
                raise OntologyError("foreign keys form a cycle: " + ", ".join(t.name for t in pending))
            ordered.append(ready)
            pending.remove(ready)
        return ordered + self.junctions

    def _check_identifiers(self) -> None:
        names = []
        for table in self.all_tables():
            names += [table.name, f"pk_{table.name}"]
            names += [c.name for c in table.ordered_columns()]
            names += [fk.name for fk in table.fks] + [name for name, _ in table.checks]
        too_long = [n for n in names if len(n) > MAX_IDENTIFIER]
        if too_long:
            raise OntologyError(f"identifiers longer than {MAX_IDENTIFIER}: {too_long}")


# =============================================================================
# SQL emission
# =============================================================================

def lit(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def inserts(table: str, columns: list[str], rows: list[tuple]) -> str:
    if not rows:
        return f"-- ({table}: no rows)\n"
    body = ",\n".join("    (" + ", ".join(lit(v) for v in row) + ")" for row in rows)
    return f"INSERT INTO {table} ({', '.join(columns)}) VALUES\n{body};\n"


def banner(title: str, *lines: str) -> str:
    rule = "-- " + "=" * 76
    text = [rule, f"-- {title}"] + [f"-- {line}" if line else "--" for line in lines] + [rule]
    return "\n".join(text) + "\n"


def create_table(table: Table) -> str:
    rule = "-- " + "-" * 76
    out = [rule, *(f"-- {line}" for line in table.header), rule, f"CREATE TABLE {table.name} ("]
    entries = []
    for column in table.ordered_columns():
        null = "" if column.nullable else " NOT NULL"
        entries.append((f"    {column.name} {column.sql_type}{null}", column.comment))
    entries.append((f"    CONSTRAINT pk_{table.name} PRIMARY KEY ({', '.join(table.pk)})", None))
    for fk in table.fks:
        entries.append((f"    CONSTRAINT {fk.name} FOREIGN KEY ({', '.join(fk.columns)}) "
                        f"REFERENCES {fk.ref_table} ({', '.join(fk.ref_columns)})", None))
    for name, expr in table.checks:
        entries.append((f"    CONSTRAINT {name} CHECK ({expr})", None))

    for index, (code, comment) in enumerate(entries):
        comma = "," if index < len(entries) - 1 else ""
        out.append(f"{code}{comma}" + (f"  -- {comment}" if comment else ""))
    out.append(");\n")
    return "\n".join(out)


PART_1_SEED_NOTE = (
    "Only the closed controlled vocabularies are seeded here. Products are listed "
    "in ont_individual instead: their required lifecycle and vocabulary columns "
    "are unknown, and filling them would mean inventing values."
)


def part_1(model: Model) -> str:
    ont = model.ont
    out = [banner(
        "PART 1: ER MODEL",
        "Tables are classes, columns are datatype properties. Relationships whose",
        "range side allows at most one become foreign keys; many-to-many ones",
        "become junction tables named after the verb. Row-level rules are CHECKs.",
        "Rules spanning rows are views in Part 4.",
    )]
    out += [create_table(t) for t in model.all_tables()]

    out.append(banner("PART 1b: CONTROLLED VOCABULARY", *textwrap.wrap(PART_1_SEED_NOTE, 76)))
    by_class: dict[str, list[Individual]] = {}
    for ind in ont.individuals:
        by_class.setdefault(ind.class_name, []).append(ind)

    out.append(inserts("region", ["region_code", "region_name", "time_zone_range"],
                       [(i.code, i.label, None) for i in by_class["Region"]]))
    out.append(inserts("severity_level", ["level_code", "level_rank", "level_name", "definition"],
                       [(i.code, i.rank, i.label, i.notes) for i in by_class["SeverityLevel"]]))
    out.append(inserts(
        "support_entitlement",
        ["tier_code", "tier_rank", "grants_escalation_right", "response_target_hours"],
        # C-12 settles STANDARD as false. PREMIUM is unstated, so NULL.
        [(i.code, i.rank, False if i.code == "STANDARD" else None, None)
         for i in by_class["SupportEntitlement"]],
    ))

    def crm_value(text: str, kind: str):
        if text.startswith("Unconfirmed"):
            return None
        if kind == "bool":
            return {"Yes": True, "No": False}[text]
        return text

    crm_rows = []
    crm_table = table_with_header(ont.classes["CRM"].individuals_text, "systemCode", "CRM.md")
    for row in crm_table[1:]:
        cells = [strip_md(c) for c in row]
        crm_rows.append((cells[0], cells[1], crm_value(cells[2], "text"), crm_value(cells[3], "bool")))
    out.append(inserts("crm", ["system_code", "system_name", "ticket_term_used", "is_authoritative"],
                       crm_rows))
    return "\n".join(out)


CATALOG_DDL = """
CREATE TABLE ont_domain_type (
    domain_type VARCHAR(32) NOT NULL,
    sort_order INTEGER NOT NULL,
    CONSTRAINT pk_ont_domain_type PRIMARY KEY (domain_type)
);

CREATE TABLE ont_class (
    class_id VARCHAR(64) NOT NULL,       -- e.g. sup:Account
    class_name VARCHAR(64) NOT NULL,
    domain_type VARCHAR(32) NOT NULL,
    status VARCHAR(16) NOT NULL,
    version VARCHAR(16) NOT NULL,
    definition TEXT NOT NULL,
    identity_rule TEXT NOT NULL,
    table_name VARCHAR(64) NOT NULL,     -- the Part 1 table
    primary_key_columns VARCHAR(255) NOT NULL,
    CONSTRAINT pk_ont_class PRIMARY KEY (class_id),
    CONSTRAINT uq_ont_class_name UNIQUE (class_name),
    CONSTRAINT fk_ont_class_domain_type FOREIGN KEY (domain_type) REFERENCES ont_domain_type (domain_type),
    CONSTRAINT ck_ont_class_status CHECK (status IN ('Canonical', 'Proposed', 'Deprecated'))
);

CREATE TABLE ont_attribute (
    class_id VARCHAR(64) NOT NULL,
    property_name VARCHAR(64) NOT NULL,  -- datatype property, e.g. accountName
    datatype VARCHAR(255) NOT NULL,      -- as declared, e.g. enum(Active, Lapsed, Churned)
    is_required BOOLEAN NOT NULL,
    notes TEXT,
    column_name VARCHAR(64) NOT NULL,
    sql_type VARCHAR(32) NOT NULL,
    CONSTRAINT pk_ont_attribute PRIMARY KEY (class_id, property_name),
    CONSTRAINT fk_ont_attribute_class FOREIGN KEY (class_id) REFERENCES ont_class (class_id)
);

CREATE TABLE ont_relationship (
    property_name VARCHAR(64) NOT NULL,  -- the verb, read Domain property Range
    domain_class_id VARCHAR(64) NOT NULL,
    range_class_id VARCHAR(64) NOT NULL,
    cardinality VARCHAR(8) NOT NULL,     -- range instances per domain instance
    inverse_name VARCHAR(64) NOT NULL,
    inverse_cardinality VARCHAR(8) NOT NULL,
    relationship_group VARCHAR(32) NOT NULL,
    notes TEXT,
    implemented_as VARCHAR(16) NOT NULL,
    physical_table VARCHAR(64) NOT NULL,
    physical_columns VARCHAR(255) NOT NULL,
    constraint_name VARCHAR(64) NOT NULL,
    CONSTRAINT pk_ont_relationship PRIMARY KEY (property_name),
    CONSTRAINT uq_ont_relationship_inverse UNIQUE (inverse_name),
    CONSTRAINT fk_ont_relationship_domain FOREIGN KEY (domain_class_id) REFERENCES ont_class (class_id),
    CONSTRAINT fk_ont_relationship_range FOREIGN KEY (range_class_id) REFERENCES ont_class (class_id),
    CONSTRAINT ck_ont_relationship_implemented_as CHECK (implemented_as IN ('FOREIGN_KEY', 'JUNCTION_TABLE'))
);

CREATE TABLE ont_constraint (
    constraint_id VARCHAR(8) NOT NULL,   -- C-nn, permanent
    status VARCHAR(8) NOT NULL,
    enforcement_level VARCHAR(8),        -- Hard, Soft, Advisory; NULL when retired
    category VARCHAR(64) NOT NULL,
    statement TEXT NOT NULL,
    catches TEXT,
    retired_reason TEXT,
    enforcement VARCHAR(16),             -- how this schema enforces it; NULL when retired
    physical_object VARCHAR(64),
    enforcement_note TEXT,
    CONSTRAINT pk_ont_constraint PRIMARY KEY (constraint_id),
    CONSTRAINT ck_ont_constraint_status CHECK (status IN ('Active', 'Retired')),
    CONSTRAINT ck_ont_constraint_level CHECK (enforcement_level IN ('Hard', 'Soft', 'Advisory')),
    CONSTRAINT ck_ont_constraint_enforcement
        CHECK (enforcement IN ('DECLARATIVE', 'STRUCTURAL', 'VIOLATION_VIEW', 'NOT_ENFORCED')),
    CONSTRAINT ck_ont_constraint_active
        CHECK ((status = 'Active' AND enforcement_level IS NOT NULL AND enforcement IS NOT NULL)
            OR (status = 'Retired' AND enforcement_level IS NULL AND enforcement IS NULL))
);

CREATE TABLE ont_disjointness (
    class_a_id VARCHAR(64) NOT NULL,
    class_b_id VARCHAR(64) NOT NULL,
    reason TEXT NOT NULL,
    CONSTRAINT pk_ont_disjointness PRIMARY KEY (class_a_id, class_b_id),
    CONSTRAINT fk_ont_disjointness_a FOREIGN KEY (class_a_id) REFERENCES ont_class (class_id),
    CONSTRAINT fk_ont_disjointness_b FOREIGN KEY (class_b_id) REFERENCES ont_class (class_id)
);

CREATE TABLE ont_individual (
    class_id VARCHAR(64) NOT NULL,
    individual_code VARCHAR(64) NOT NULL,
    label VARCHAR(255),
    sort_rank INTEGER,
    notes TEXT,
    CONSTRAINT pk_ont_individual PRIMARY KEY (class_id, individual_code),
    CONSTRAINT fk_ont_individual_class FOREIGN KEY (class_id) REFERENCES ont_class (class_id)
);

CREATE TABLE ont_alias (
    alias_id INTEGER NOT NULL,
    class_id VARCHAR(64) NOT NULL,
    individual_code VARCHAR(64),         -- NULL: alias of the class itself
    alias_term VARCHAR(255) NOT NULL,
    alias_context VARCHAR(255) NOT NULL, -- the system or team that uses it
    note TEXT,
    CONSTRAINT pk_ont_alias PRIMARY KEY (alias_id),
    CONSTRAINT fk_ont_alias_class FOREIGN KEY (class_id) REFERENCES ont_class (class_id),
    CONSTRAINT fk_ont_alias_individual FOREIGN KEY (class_id, individual_code)
        REFERENCES ont_individual (class_id, individual_code)
);

CREATE TABLE ont_equivalence (
    eq_id VARCHAR(8) NOT NULL,
    title VARCHAR(255) NOT NULL,
    kind VARCHAR(16) NOT NULL,
    canonical_ref VARCHAR(255),
    equivalent_labels TEXT,
    varies_by VARCHAR(64),
    anchor_property VARCHAR(128),
    status_note TEXT,
    CONSTRAINT pk_ont_equivalence PRIMARY KEY (eq_id),
    CONSTRAINT ck_ont_equivalence_kind CHECK (kind IN ('EQUIVALENCE', 'COLLISION'))
);
"""


def part_2(model: Model) -> str:
    ont = model.ont
    out = [banner(
        "PART 2: ONTOLOGY CATALOG",
        "The ontology as data: what Part 1 was built from, one row per fact.",
    ), CATALOG_DDL]

    out.append(inserts("ont_domain_type", ["domain_type", "sort_order"],
                       [(t, i + 1) for i, t in enumerate(DOMAIN_TYPE_ORDER)]))
    out.append(inserts(
        "ont_class",
        ["class_id", "class_name", "domain_type", "status", "version", "definition",
         "identity_rule", "table_name", "primary_key_columns"],
        [(c.class_id, c.name, c.domain_type, c.status, c.version, c.definition, c.identity_rule,
          model.tables[c.name].name, ", ".join(model.tables[c.name].pk))
         for c in ont.ordered_classes()],
    ))

    attribute_rows = []
    for cls in ont.ordered_classes():
        table = model.tables[cls.name]
        for attr in cls.attributes:
            column = table.attr_by_property[attr.name]
            attribute_rows.append((cls.class_id, attr.name, attr.datatype, attr.required,
                                   attr.notes or None, column.name, column.sql_type))
    out.append(inserts("ont_attribute", ["class_id", "property_name", "datatype", "is_required",
                                         "notes", "column_name", "sql_type"], attribute_rows))

    out.append(inserts(
        "ont_relationship",
        ["property_name", "domain_class_id", "range_class_id", "cardinality", "inverse_name",
         "inverse_cardinality", "relationship_group", "notes", "implemented_as", "physical_table",
         "physical_columns", "constraint_name"],
        [(r.name, ont.classes[r.domain].class_id, ont.classes[r.range].class_id, r.cardinality,
          r.inverse, r.inverse_cardinality, r.group, r.notes or None, r.implemented_as,
          r.physical_table, r.physical_columns, r.constraint_name)
         for r in ont.relationships],
    ))

    constraint_rows = []
    for c in ont.constraints:
        if c.status == "Retired":
            constraint_rows.append((c.constraint_id, c.status, None, c.category, c.statement,
                                    None, c.retired_reason, None, None, None))
            continue
        kind, obj, note = enforcement_for(c.constraint_id, model)
        constraint_rows.append((c.constraint_id, c.status, c.level, c.category, c.statement,
                                c.catches, None, kind, obj, note))
    out.append(inserts(
        "ont_constraint",
        ["constraint_id", "status", "enforcement_level", "category", "statement", "catches",
         "retired_reason", "enforcement", "physical_object", "enforcement_note"],
        constraint_rows,
    ))

    out.append(inserts("ont_disjointness", ["class_a_id", "class_b_id", "reason"],
                       [(ont.classes[a].class_id, ont.classes[b].class_id, why)
                        for a, b, why in ont.disjointness]))

    out.append(inserts("ont_individual", ["class_id", "individual_code", "label", "sort_rank", "notes"],
                       [(ont.classes[i.class_name].class_id, i.code, i.label, i.rank, i.notes)
                        for i in ont.individuals]))

    alias_rows, alias_id = [], 0
    for cls in ont.ordered_classes():
        for context, term, note in cls.aliases:
            alias_id += 1
            alias_rows.append((alias_id, cls.class_id, None, term, context, note))
    for ind in ont.individuals:
        for term in ind.aliases:
            alias_id += 1
            alias_rows.append((alias_id, ont.classes[ind.class_name].class_id, ind.code, term,
                               f"{ind.class_name} individuals table", None))
    out.append(inserts("ont_alias", ["alias_id", "class_id", "individual_code", "alias_term",
                                     "alias_context", "note"], alias_rows))

    out.append(inserts(
        "ont_equivalence",
        ["eq_id", "title", "kind", "canonical_ref", "equivalent_labels", "varies_by",
         "anchor_property", "status_note"],
        [(e.eq_id, e.title, e.kind, e.canonical_ref, e.equivalent_labels, e.varies_by,
          e.anchor_property, e.status_note) for e in ont.equivalences],
    ))
    return "\n".join(out)


def enforcement_for(constraint_id: str, model: Model) -> tuple[str, str | None, str | None]:
    if constraint_id in TABLE_CHECKS:
        class_name, expr = TABLE_CHECKS[constraint_id]
        table = model.tables[class_name].name
        return "DECLARATIVE", f"ck_{table}_{constraint_id.replace('-', '').lower()}", f"CHECK ({expr})"
    if constraint_id in VIOLATION_VIEWS:
        return "VIOLATION_VIEW", view_name(constraint_id), None
    kind, note = OTHER_ENFORCEMENT[constraint_id]
    return kind, None, note


def view_name(constraint_id: str) -> str:
    return "v_violation_" + constraint_id.replace("-", "").lower()


MASKING_DDL = """
CREATE TABLE mask_action (
    action_code VARCHAR(16) NOT NULL,     -- as named in policy.py
    action_label VARCHAR(32) NOT NULL,
    output_form VARCHAR(128) NOT NULL,    -- what replaces the value in masked text
    recoverable_via_vault BOOLEAN NOT NULL,
    description TEXT NOT NULL,
    CONSTRAINT pk_mask_action PRIMARY KEY (action_code),
    CONSTRAINT ck_mask_action_code CHECK (action_code IN ('PSEUDONYMIZE', 'KEEP', 'REDACT'))
);

-- Every entity type the masker can emit, and the action it takes.
CREATE TABLE mask_entity_type (
    entity_type VARCHAR(64) NOT NULL,
    action_code VARCHAR(16) NOT NULL,
    confidence_threshold DECIMAL(3, 2) NOT NULL,  -- detections below this are dropped
    arbitration_precedence INTEGER NOT NULL,      -- higher wins an overlapping span
    is_atomic BOOLEAN NOT NULL,                   -- detections inside it are fragments
    bound_class_id VARCHAR(64),                   -- the ontology class it denotes
    bound_property_name VARCHAR(64),              -- or, more precisely, the attribute
    binding_gap TEXT,                             -- why no ontology class fits
    rationale TEXT NOT NULL,
    CONSTRAINT pk_mask_entity_type PRIMARY KEY (entity_type),
    CONSTRAINT fk_mask_entity_type_action FOREIGN KEY (action_code) REFERENCES mask_action (action_code),
    CONSTRAINT fk_mask_entity_type_class FOREIGN KEY (bound_class_id) REFERENCES ont_class (class_id),
    CONSTRAINT fk_mask_entity_type_attribute FOREIGN KEY (bound_class_id, bound_property_name)
        REFERENCES ont_attribute (class_id, property_name),
    CONSTRAINT ck_mask_entity_type_binding
        CHECK ((bound_class_id IS NOT NULL AND binding_gap IS NULL)
            OR (bound_class_id IS NULL AND bound_property_name IS NULL AND binding_gap IS NOT NULL))
);

-- Presidio's domain-neutral labels, renamed before arbitration.
CREATE TABLE mask_presidio_rename (
    presidio_label VARCHAR(64) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    CONSTRAINT pk_mask_presidio_rename PRIMARY KEY (presidio_label),
    CONSTRAINT fk_mask_presidio_rename_entity FOREIGN KEY (entity_type) REFERENCES mask_entity_type (entity_type)
);

-- Deny-lists: one per disjoint ontology class, each fed from a source system.
CREATE TABLE mask_deny_list (
    config_field VARCHAR(64) NOT NULL,
    cli_flag VARCHAR(32) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    source_description VARCHAR(255) NOT NULL,
    CONSTRAINT pk_mask_deny_list PRIMARY KEY (config_field),
    CONSTRAINT uq_mask_deny_list_flag UNIQUE (cli_flag),
    CONSTRAINT fk_mask_deny_list_entity FOREIGN KEY (entity_type) REFERENCES mask_entity_type (entity_type)
);

-- Terms that must survive masking. RECOGNIZER terms are detected and kept, so
-- they appear in the audit trail. ALLOW_LIST terms are never detected at all.
CREATE TABLE mask_protected_term (
    term VARCHAR(128) NOT NULL,
    mechanism VARCHAR(16) NOT NULL,
    entity_type VARCHAR(64),
    CONSTRAINT pk_mask_protected_term PRIMARY KEY (term, mechanism),
    CONSTRAINT fk_mask_protected_term_entity FOREIGN KEY (entity_type) REFERENCES mask_entity_type (entity_type),
    CONSTRAINT ck_mask_protected_term_mechanism
        CHECK ((mechanism = 'RECOGNIZER' AND entity_type IS NOT NULL)
            OR (mechanism = 'ALLOW_LIST' AND entity_type IS NULL))
);

-- PROPOSED data classification: the action for every ontology attribute.
-- Not enforced yet; the pipeline masks free text, not structured columns.
-- The action is stated in exactly one place per attribute:
--   BY_ENTITY_TYPE  the entity type's action applies (entity_type set)
--   FIXED           stated directly (action_code set)
--   SCAN            free text; the pipeline decides per detected span (neither set)
CREATE TABLE mask_attribute_rule (
    class_id VARCHAR(64) NOT NULL,
    property_name VARCHAR(64) NOT NULL,
    handling VARCHAR(16) NOT NULL,
    entity_type VARCHAR(64),
    action_code VARCHAR(16),
    rationale TEXT NOT NULL,
    status VARCHAR(16) NOT NULL,
    CONSTRAINT pk_mask_attribute_rule PRIMARY KEY (class_id, property_name),
    CONSTRAINT fk_mask_attribute_rule_attribute FOREIGN KEY (class_id, property_name)
        REFERENCES ont_attribute (class_id, property_name),
    CONSTRAINT fk_mask_attribute_rule_entity FOREIGN KEY (entity_type) REFERENCES mask_entity_type (entity_type),
    CONSTRAINT fk_mask_attribute_rule_action FOREIGN KEY (action_code) REFERENCES mask_action (action_code),
    CONSTRAINT ck_mask_attribute_rule_status CHECK (status IN ('Proposed', 'Confirmed')),
    CONSTRAINT ck_mask_attribute_rule_handling
        CHECK ((handling = 'BY_ENTITY_TYPE' AND entity_type IS NOT NULL AND action_code IS NULL)
            OR (handling = 'FIXED' AND entity_type IS NULL AND action_code IS NOT NULL)
            OR (handling = 'SCAN' AND entity_type IS NULL AND action_code IS NULL))
);
"""


def part_3(model: Model) -> str:
    ont = model.ont
    if set(ACTION_ROWS) != set(Action):
        raise OntologyError("ACTION_ROWS does not cover every Action in policy.py")

    out = [banner(
        "PART 3: MASKING LAYER",
        "The three actions (Pseudonymize, Keep, Reject), which entity types get",
        "which, and the proposed action for every ontology attribute. Exported from",
        "ticketmask/policy.py, ontology.py, arbitrate.py and recognizers.py.",
    ), MASKING_DDL]

    out.append(inserts(
        "mask_action",
        ["action_code", "action_label", "output_form", "recoverable_via_vault", "description"],
        [(a.name, *ACTION_ROWS[a]) for a in (Action.PSEUDONYMIZE, Action.KEEP, Action.REDACT)],
    ))

    entity_rows = []
    for entity_type in sorted(DEFAULT_POLICY):
        rule = DEFAULT_POLICY[entity_type]
        binding = ENTITY_BINDINGS[entity_type]
        class_id = prop = None
        if binding.sup_ref:
            class_name, _, prop = binding.sup_ref.removeprefix("sup:").partition(".")
            class_id = ont.classes[class_name].class_id
            prop = prop or None
        entity_rows.append((entity_type, rule.action.name, rule.threshold,
                            ENTITY_PRECEDENCE[entity_type], entity_type in _ATOMIC_TYPES,
                            class_id, prop, binding.gap, rule.rationale))
    out.append(inserts(
        "mask_entity_type",
        ["entity_type", "action_code", "confidence_threshold", "arbitration_precedence", "is_atomic",
         "bound_class_id", "bound_property_name", "binding_gap", "rationale"],
        entity_rows,
    ))

    out.append(inserts("mask_presidio_rename", ["presidio_label", "entity_type"],
                       sorted(PRESIDIO_RENAMES.items())))

    if set(DENY_LIST_FLAGS) != set(DENY_LIST_ENTITY_TYPES):
        raise OntologyError("cli.DENY_LIST_FLAGS and recognizers.DENY_LIST_ENTITY_TYPES disagree")
    out.append(inserts(
        "mask_deny_list", ["config_field", "cli_flag", "entity_type", "source_description"],
        [(f, DENY_LIST_FLAGS[f][0], DENY_LIST_ENTITY_TYPES[f], DENY_LIST_FLAGS[f][1])
         for f in DENY_LIST_FLAGS],
    ))

    protected = []
    for terms, entity_type in ((REGION_VALUES, "REGION"), (SEVERITY_TERMS, "SEVERITY_LEVEL"),
                               (ENTITLEMENT_TERMS, "SUPPORT_ENTITLEMENT"),
                               (DEFAULT_PRODUCTS, "PRODUCT")):
        protected += [(t, "RECOGNIZER", entity_type) for t in terms]
    protected += [(t, "ALLOW_LIST", None) for t in PROTECTED_VOCABULARY]
    out.append(inserts("mask_protected_term", ["term", "mechanism", "entity_type"], protected))

    ontology_attributes = {f"{c.name}.{a.name}" for c in ont.classes.values() for a in c.attributes}
    unruled = sorted(ontology_attributes - set(ATTRIBUTE_POLICY))
    stale = sorted(set(ATTRIBUTE_POLICY) - ontology_attributes)
    if unruled or stale:
        raise OntologyError(
            "policy.ATTRIBUTE_POLICY is out of step with the ontology.\n"
            f"  attributes with no rule: {unruled}\n  rules for no attribute:  {stale}")

    attribute_rows = []
    for cls in ont.ordered_classes():
        for attr in cls.attributes:
            rule = ATTRIBUTE_POLICY[f"{cls.name}.{attr.name}"]
            if rule.handling is Handling.BY_ENTITY_TYPE and rule.entity_type not in DEFAULT_POLICY:
                raise OntologyError(f"{cls.name}.{attr.name}: unknown entity type {rule.entity_type}")
            attribute_rows.append((cls.class_id, attr.name, rule.handling.name, rule.entity_type,
                                   rule.action.name if rule.action else None, rule.rationale,
                                   "Proposed"))
    out.append(inserts(
        "mask_attribute_rule",
        ["class_id", "property_name", "handling", "entity_type", "action_code", "rationale", "status"],
        attribute_rows,
    ))
    return "\n".join(out)


def part_4(model: Model) -> str:
    ont = model.ont
    active = {c.constraint_id for c in ont.constraints if c.status == "Active"}
    handled = set(TABLE_CHECKS) | set(VIOLATION_VIEWS) | set(OTHER_ENFORCEMENT)
    if active != handled:
        raise OntologyError(
            "constraint coverage is out of step with 04-Constraints-and-Rules.md.\n"
            f"  active but unhandled: {sorted(active - handled)}\n"
            f"  handled but not active: {sorted(handled - active)}")
    retired = {c.constraint_id for c in ont.constraints if c.status == "Retired"}
    if retired & handled:
        raise OntologyError(f"enforcement written for retired constraints: {sorted(retired & handled)}")

    out = [banner(
        "PART 4: VIEWS",
        "One view per cross-row constraint. Each returns the records that break it,",
        "and v_constraint_violations gathers them all. On a fresh load, expect C-10",
        "for all four regions (no sales reps loaded yet), plus C-50 for any CRM",
        "whose ticket term is still unconfirmed.",
    )]

    levels = {c.constraint_id: c for c in ont.constraints}
    for constraint_id in sorted(VIOLATION_VIEWS):
        c = levels[constraint_id]
        out.append(f"-- {constraint_id} ({c.level}): "
                   + "\n--   ".join(textwrap.wrap(c.statement, 72)))
        out.append(f"CREATE VIEW {view_name(constraint_id)} AS{VIOLATION_VIEWS[constraint_id]};\n")

    union = "\nUNION ALL\n".join(
        f"SELECT '{cid}' AS constraint_id, table_name, record_key, detail FROM {view_name(cid)}"
        for cid in sorted(VIOLATION_VIEWS))
    out.append(f"""CREATE VIEW v_constraint_violations AS
SELECT v.constraint_id, c.enforcement_level, v.table_name, v.record_key, v.detail
FROM (
{union}
) v
JOIN ont_constraint c ON c.constraint_id = v.constraint_id;
""")

    gaps = []
    for (class_name, prop), (question, reason) in UNCONFIRMED_SEED_COLUMNS.items():
        table = model.tables[class_name]
        column = table.attr_by_property[prop].name
        key = " || ':' || ".join(table.pk)
        gaps.append(f"SELECT '{table.name}' AS table_name, {key} AS record_key, "
                    f"{lit(prop)} AS property_name, {lit(question)} AS open_question, "
                    f"{lit(reason)} AS reason FROM {table.name} WHERE {column} IS NULL")
    out.append("-- Required values the ontology has not confirmed yet, left NULL rather than guessed.")
    out.append("CREATE VIEW v_seed_gaps AS\n" + "\nUNION ALL\n".join(gaps) + ";\n")

    out.append("""-- The action for every ontology attribute, resolved to one of the three.
-- SCAN rows have no single action: the pipeline decides per detected span.
CREATE VIEW v_attribute_masking AS
SELECT c.class_name,
       a.property_name,
       c.table_name,
       a.column_name,
       r.handling,
       r.entity_type,
       CASE WHEN r.handling = 'SCAN' THEN NULL
            ELSE COALESCE(e.action_code, r.action_code) END AS action_code,
       CASE WHEN r.handling = 'SCAN' THEN 'Scan per span'
            ELSE act.action_label END AS action_label,
       r.rationale,
       r.status
FROM ont_attribute a
JOIN ont_class c ON c.class_id = a.class_id
LEFT JOIN mask_attribute_rule r ON r.class_id = a.class_id AND r.property_name = a.property_name
LEFT JOIN mask_entity_type e ON e.entity_type = r.entity_type
LEFT JOIN mask_action act ON act.action_code = COALESCE(e.action_code, r.action_code);

-- Every masker entity type with its action and the ontology element it denotes.
CREATE VIEW v_entity_type_masking AS
SELECT e.entity_type,
       act.action_label,
       e.confidence_threshold,
       e.arbitration_precedence,
       c.class_name AS bound_class,
       e.bound_property_name AS bound_property,
       e.binding_gap
FROM mask_entity_type e
JOIN mask_action act ON act.action_code = e.action_code
LEFT JOIN ont_class c ON c.class_id = e.bound_class_id;

-- Ontology vocabulary the masker does not explicitly protect. A term here is
-- not necessarily masked: it is only at risk if NER happens to tag it.
CREATE VIEW v_unprotected_ontology_vocabulary AS
SELECT v.class_id, v.individual_code, v.term
FROM (
    SELECT class_id, individual_code, individual_code AS term FROM ont_individual
    UNION
    SELECT class_id, individual_code, label FROM ont_individual WHERE label IS NOT NULL
    UNION
    SELECT class_id, individual_code, alias_term FROM ont_alias WHERE individual_code IS NOT NULL
) v
WHERE v.class_id IN ('sup:Region', 'sup:SeverityLevel', 'sup:SupportEntitlement', 'sup:Product')
  AND NOT EXISTS (SELECT 1 FROM mask_protected_term p WHERE LOWER(p.term) = LOWER(v.term));
""")
    return "\n".join(out)


def render(model: Model) -> str:
    ont = model.ont
    entity_tables = len(model.tables)
    header = banner(
        "Support Organization Ontology: ER model, catalog and masking actions",
        "",
        "GENERATED by scripts/export_ontology_sql.py. Do not hand-edit.",
        f"Generated:  {date.today().isoformat()}",
        f"Ontology:   {ont.root.name}/Ontology (markdown source of truth)",
        f"Changelog:  {ont.changelog_head}",
        f"Contents:   {entity_tables} class tables, {len(model.junctions)} junction tables, "
        f"{len(ont.relationships)} relationships,",
        f"            {sum(len(c.attributes) for c in ont.classes.values())} attributes, "
        f"{sum(c.status == 'Active' for c in ont.constraints)} active constraints",
        "",
        "Dialect: a subset of PostgreSQL that SQLite also accepts. Load into an empty",
        "database. The SQLite load is tested (--check); PostgreSQL is untested. In",
        "SQLite, run PRAGMA foreign_keys = ON first or foreign keys go unchecked.",
        "",
        "For a plain ER diagram, import Part 1 only. Parts 2-4 are the ontology as",
        "data, the masking actions, and the violation views.",
    )
    return "\n".join([header, part_1(model), part_2(model), part_3(model), part_4(model)])


# =============================================================================
# --check: load into SQLite and exercise it
# =============================================================================

FIXTURE = """
INSERT INTO sales_representative (rep_id, is_active) VALUES ('U-REP', TRUE);
INSERT INTO region_is_covered_by_sales_representative (region_code, rep_id) VALUES ('NA', 'U-REP');
INSERT INTO customer_success_manager (csm_id, is_active) VALUES ('U-CSM', TRUE);
INSERT INTO account (account_id, account_name, is_strategic, account_status, created_at,
                     region_code, tier_code, rep_id, csm_id)
VALUES ('A1', 'Acme', FALSE, 'Active', '2025-01-01', 'EMEA', 'STANDARD', 'U-REP', 'U-CSM'),
       ('A2', 'Beta', TRUE, 'Lapsed', '2025-01-01', 'NA', 'PREMIUM', 'U-REP', NULL);
INSERT INTO contact (contact_id, email_address, is_support_authorised, account_id)
VALUES ('C2', 'x@beta.test', FALSE, 'A2');
INSERT INTO product (product_id, product_name, lifecycle_status, uses_platinum_naming, severity_term_used)
VALUES ('P1', 'ExampleAnalytics', 'GA', FALSE, 'Severity');
INSERT INTO partner (partner_id, partner_name) VALUES ('PT1', 'Litware');
INSERT INTO crm (system_code, system_name, ticket_term_used, is_authoritative)
VALUES ('LEGACY', 'Legacy helpdesk', NULL, NULL);
INSERT INTO support_agent (agent_id, tier, is_active) VALUES ('U-AG', 'T2', FALSE), ('U-REP', 'T1', TRUE);
INSERT INTO sla (level_code, tier_code, sla_name, target_response_minutes, target_resolution_minutes)
VALUES ('S1', 'STANDARD', 'Standard S1', 60, 480);
INSERT INTO ticket (system_code, ticket_number, subject, status, opened_at, account_id, contact_id,
                    partner_id, agent_id, level_code, sla_level_code, sla_tier_code, product_id)
VALUES ('SF', '00001', 'VPN drops', 'Open', '2026-03-04 09:00:00', 'A1', 'C2',
        'PT1', 'U-AG', 'S2', 'S1', 'STANDARD', 'P1');
INSERT INTO jira_issue (issue_key, issue_type, issue_status, is_resolved, created_at)
VALUES ('ENG-1', 'Bug', 'Done', TRUE, '2026-03-05 10:00:00');
INSERT INTO escalation (escalation_id, escalation_type, escalated_at, justification,
                        system_code, ticket_number, issue_key, agent_id)
VALUES ('e-1', 'Bug', '2026-03-05 09:00:00', 'defect', 'SF', '00001', 'ENG-1', 'U-AG');
"""

#: Each fixture record above is built to break exactly these rules.
FIXTURE_EXPECTED = {
    "C-08", "C-09", "C-10", "C-14", "C-16", "C-17", "C-28", "C-32",
    "C-35", "C-46", "C-50", "C-52", "C-56", "C-57",
}

#: Writes the schema itself must refuse: (setup, offending statement, the
#: constraint name SQLite must report). Matching the name matters. Without it,
#: a statement failing for some unrelated reason would pass as "rejected".
MUST_REJECT: dict[str, tuple[list[str], str, str]] = {
    "C-12": ([], "UPDATE support_entitlement SET grants_escalation_right = TRUE "
                 "WHERE tier_code = 'STANDARD'", "ck_support_entitlement_c12"),
    "C-13": (["INSERT INTO license (account_id, product_id, start_date, license_key, is_active, "
              "license_type, tier_code) VALUES ('A2', 'P1', '2026-01-01', 'K', TRUE, 'Trial', 'PREMIUM')"],
             "UPDATE license SET end_date = '2025-01-01' WHERE account_id = 'A2'", "ck_license_c13"),
    "C-22": ([], "INSERT INTO product (product_id, product_name, lifecycle_status, uses_platinum_naming, "
                 "severity_term_used) VALUES ('P9', 'Old', 'EndOfLife', FALSE, 'Priority')",
             "ck_product_c22"),
    "C-24": ([], "UPDATE ticket SET status = 'Closed' WHERE ticket_number = '00001'", "ck_ticket_c24"),
    "C-25": ([], "INSERT INTO severity_level (level_code, level_rank, level_name, definition) "
                 "VALUES ('S5', 5, 'Trivial', 'x')", "ck_severity_level_level_code"),
    "foreign key": ([], "INSERT INTO contact (contact_id, email_address, is_support_authorised, "
                        "account_id) VALUES ('C9', 'y@z.test', TRUE, 'NO-SUCH-ACCOUNT')",
                    "FOREIGN KEY constraint failed"),
}


def check(sql: str, model: Model) -> None:
    ont = model.ont
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(sql)

    def scalar(query: str):
        return conn.execute(query).fetchone()[0]

    def violations() -> set[str]:
        return {r[0] for r in conn.execute("SELECT DISTINCT constraint_id FROM v_constraint_violations")}

    failures = []

    def expect(label: str, ok: bool, detail: str = "") -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {label}{(': ' + detail) if detail and not ok else ''}")
        if not ok:
            failures.append(label)

    print("\nloaded into SQLite", sqlite3.sqlite_version)
    expect("no foreign key violations", not conn.execute("PRAGMA foreign_key_check").fetchall())
    expect(f"{len(ont.classes)} classes catalogued", scalar("SELECT COUNT(*) FROM ont_class") == len(ont.classes))
    expect(f"{len(ont.relationships)} relationships catalogued",
           scalar("SELECT COUNT(*) FROM ont_relationship") == len(ont.relationships))
    expect("every attribute has a masking rule",
           scalar("SELECT COUNT(*) FROM v_attribute_masking WHERE handling IS NULL") == 0)
    expect("every non-scan attribute resolves to an action",
           scalar("SELECT COUNT(*) FROM v_attribute_masking "
                  "WHERE handling <> 'SCAN' AND action_code IS NULL") == 0)
    expect("every active constraint has an enforcement",
           scalar("SELECT COUNT(*) FROM ont_constraint WHERE status = 'Active' AND enforcement IS NULL") == 0)

    views = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'view'")]
    broken = []
    for view in views:
        try:
            conn.execute(f"SELECT * FROM {view}").fetchall()
        except sqlite3.Error as exc:
            broken.append(f"{view}: {exc}")
    expect(f"all {len(views)} views query cleanly", not broken, "; ".join(broken))

    baseline = violations()
    # C-50 also fires on a fresh load while any CRM row is still unconfirmed.
    # The generic ontology ships with every template row confirmed.
    expect("fresh load flags only C-10 (and C-50 if a CRM is unconfirmed)",
           baseline in ({"C-10"}, {"C-10", "C-50"}), str(sorted(baseline)))

    conn.executescript(FIXTURE)
    found = violations()
    expect("fixture trips exactly the planted violations", found == FIXTURE_EXPECTED,
           f"missing {sorted(FIXTURE_EXPECTED - found)}, unexpected {sorted(found - FIXTURE_EXPECTED)}")

    for label, (setup, statement, constraint_name) in MUST_REJECT.items():
        for step in setup:
            conn.execute(step)  # must succeed; an error here is a broken test
        try:
            conn.execute(statement)
            outcome = "accepted"
        except sqlite3.IntegrityError as exc:
            outcome = str(exc)
        expect(f"schema rejects a {label} violation", constraint_name in outcome,
               f"expected {constraint_name}, got {outcome}")

    if failures:
        raise SystemExit(f"\n{len(failures)} check(s) failed")
    print("\nall checks passed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true", help="load the SQL into SQLite and test it")
    args = parser.parse_args()

    try:
        ontology = Ontology(ontology_dir())
        model = Model(ontology)
        sql = render(model)
    except OntologyError as exc:
        print(f"export failed: {exc}", file=sys.stderr)
        return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(sql, encoding="utf-8", newline="\n")

    rules = ATTRIBUTE_POLICY.values()
    print(f"wrote {args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out}")
    print(f"  {len(model.tables)} class tables + {len(model.junctions)} junction tables")
    print(f"  {len(ontology.relationships)} relationships: "
          f"{sum(r.implemented_as == 'FOREIGN_KEY' for r in ontology.relationships)} foreign keys, "
          f"{len(model.junctions)} junctions")
    print(f"  {sum(len(c.attributes) for c in ontology.classes.values())} attributes, "
          f"{sum(c.status == 'Active' for c in ontology.constraints)} active constraints "
          f"({len(TABLE_CHECKS)} CHECK, {len(VIOLATION_VIEWS)} views)")
    print(f"  attribute actions: "
          f"{sum(r.handling is Handling.SCAN for r in rules)} scan, "
          + ", ".join(
              f"{sum(1 for r in rules if r.handling is not Handling.SCAN and (r.action or DEFAULT_POLICY[r.entity_type].action) is a)} "
              f"{a.name.lower()}" for a in Action))

    if args.check:
        check(sql, model)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
