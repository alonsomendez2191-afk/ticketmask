"""Binding between this masker's entity types and the support ontology.

The ontology in ./support-ontology is the source of truth for what things in a
support organization are called. A generic version ships with this repo; point
TICKETMASK_ONTOLOGY_DIR at your own copy once you have tailored it. This module
is the contract between it and the masking layer, and it exists because of one
rule in that ontology's conventions:

    "Never invent vocabulary."

Masking entity types are therefore named after ontology classes, not after
whatever Presidio happens to call them. Where no ontology class exists for
something we must still detect, that is recorded here as a gap rather than
papered over with an invented term — which mirrors the ontology's own rule 5,
"never invent a mapping; record it and flag it."

Nothing here edits the ontology. Drift is detected and reported, not fixed.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from pathlib import Path

#: Where the ontology lives. The generic copy bundled at the repo root by default.
DEFAULT_ONTOLOGY_DIR = Path(__file__).resolve().parents[2] / "support-ontology"


def ontology_dir() -> Path:
    return Path(os.environ.get("TICKETMASK_ONTOLOGY_DIR", DEFAULT_ONTOLOGY_DIR))


# ---------------------------------------------------------------------------
# The 17 canonical classes, as of ontology v0.2.0.
# Declared explicitly rather than parsed, so that an ontology change shows up
# as a verify_against_export() failure instead of silently changing behaviour.
# ---------------------------------------------------------------------------
ONTOLOGY_CLASSES = {
    "Account", "Region", "SupportEntitlement", "License", "Contact",
    "SalesRepresentative", "CustomerSuccessManager", "Partner", "Product",
    "Ticket", "SeverityLevel", "Escalation", "SupportAgent", "CRM", "SLA",
    "JiraIssue", "Documentation",
}


@dataclass(frozen=True)
class Binding:
    """What an entity type means in ontology terms."""
    #: `sup:` class or property this entity type denotes. None = ontology gap.
    sup_ref: str | None
    #: Why it is a gap, when sup_ref is None. Surfaces in the compliance report.
    gap: str | None = None


#: Every masking entity type, bound to the ontology. This is the table to read
#: when asking "does the masker understand a support organization".
ENTITY_BINDINGS: dict[str, Binding] = {
    # --- people. The ontology declares these pairwise disjoint (C-52), and
    # Contact disjoint from all internal roles. Collapsing them into one
    # PERSON type would erase the customer/internal distinction that every KB
    # article depends on: "the customer reported" vs "the agent did".
    "CONTACT": Binding("sup:Contact"),
    "SUPPORT_AGENT": Binding("sup:SupportAgent"),
    "SALES_REPRESENTATIVE": Binding("sup:SalesRepresentative"),
    "CUSTOMER_SUCCESS_MANAGER": Binding("sup:CustomerSuccessManager"),
    "PERSON_UNRESOLVED": Binding(
        None,
        "A person name that resolved to no role deny-list. The ontology "
        "deliberately has no generic person layer (OQ-47), so there is no "
        "class to assign. Masked all the same; the role is left unclaimed "
        "rather than guessed.",
    ),

    # --- organizations. Account and Partner are disjoint: a partner
    # represents an account but is not one. Masking both as one type would
    # assert an identity the ontology explicitly denies.
    "ACCOUNT": Binding("sup:Account"),
    "PARTNER": Binding("sup:Partner"),
    "ORGANIZATION_UNRESOLVED": Binding(
        None,
        "An organization name matching neither the Account nor the Partner "
        "deny-list. Could be either, or a vendor. Masked; not classified.",
    ),

    # --- identifiers
    "ACCOUNT_ID": Binding("sup:Account.accountId"),
    "TICKET_NUMBER": Binding("sup:Ticket.ticketNumber"),
    "JIRA_ISSUE_KEY": Binding("sup:JiraIssue.issueKey"),
    "LICENSE_KEY": Binding("sup:License.licenseKey"),
    "CONTACT_EMAIL": Binding("sup:Contact.emailAddress"),

    # --- controlled vocabulary that must survive masking intact
    "REGION": Binding("sup:Region"),
    "PRODUCT": Binding("sup:Product"),
    "SEVERITY_LEVEL": Binding("sup:SeverityLevel"),
    "SUPPORT_ENTITLEMENT": Binding("sup:SupportEntitlement"),

    # --- gaps the masking work exposes in the ontology itself
    "DEVICE_SERIAL": Binding(
        None,
        "Hardware serial in a ticket body. sup:License covers licence keys "
        "(alias 'Serial'), not physical devices. No asset/device class exists.",
    ),
    "PHONE_NUMBER": Binding(
        None,
        "sup:Contact models emailAddress but no telephone property, though "
        "phone numbers appear throughout real ticket text.",
    ),
    "LOCATION": Binding(
        None,
        "A site or postal address. Distinct from sup:Region, which is a "
        "four-value controlled vocabulary, not a place a customer sits.",
    ),
    "IP_ADDRESS": Binding(None, "No infrastructure or host class in scope."),

    # --- pure PII with no support-domain meaning. No binding expected.
    "CREDIT_CARD": Binding(None, "Out of ontology scope by design (billing)."),
    "US_SSN": Binding(None, "Out of ontology scope by design."),
    "US_PASSPORT": Binding(None, "Out of ontology scope by design."),
    "US_DRIVER_LICENSE": Binding(None, "Out of ontology scope by design."),
    "US_BANK_NUMBER": Binding(None, "Out of ontology scope by design."),
    "US_ITIN": Binding(None, "Out of ontology scope by design."),
    "IBAN_CODE": Binding(None, "Out of ontology scope by design."),
    "CRYPTO": Binding(None, "Out of ontology scope by design."),
    "MEDICAL_LICENSE": Binding(None, "Out of ontology scope by design."),
    "UK_NHS": Binding(None, "Out of ontology scope by design."),
    "NRP": Binding(None, "Special-category data. No ontology class, by design."),
    "DATE_TIME": Binding("sup:Ticket.openedAt", None),
    "URL": Binding("sup:Documentation", None),
    "CUSTOMER_DOMAIN": Binding(
        None,
        "An email/web domain identifying an account. sup:Account has no "
        "domain property, though it is the strongest account identifier in "
        "ticket text.",
    ),
    "MAC_ADDRESS": Binding(None, "No infrastructure or host class in scope."),
}


# ---------------------------------------------------------------------------
# Presidio's native entity names -> ontology-bound names.
# Presidio ships domain-neutral labels. PERSON and ORGANIZATION in particular
# must not be taken at face value: which *kind* of person is exactly the
# distinction the ontology cares about, and Presidio cannot know it.
# ---------------------------------------------------------------------------
PRESIDIO_RENAMES = {
    "PERSON": "PERSON_UNRESOLVED",
    "ORGANIZATION": "ORGANIZATION_UNRESOLVED",
    "EMAIL_ADDRESS": "CONTACT_EMAIL",
}


# ---------------------------------------------------------------------------
# Controlled vocabulary. These are ontology *values*, not customer data —
# masking any of them silently destroys the reasoning the ontology exists to
# support. "Which Platinum accounts in EMEA have open S1 tickets" cannot be
# answered from a corpus where Platinum, EMEA and S1 were masked as entities.
# ---------------------------------------------------------------------------
#: sup:SupportEntitlement tiers and their aliases (EQ-02). "Platinum" and
#: "Premium" are the same tier under two labels — masking either one breaks
#: entitlement questions across exactly the products that use the other word.
ENTITLEMENT_TERMS: list[str] = [
    "Standard Support", "Premium Support", "Platinum Support", "Support Level",
    "Standard", "Premium", "Platinum", "Basic",
]

#: sup:SeverityLevel codes and aliases (EQ-03). The ontology's rule is to
#: filter on levelRank, never on the label — which requires the labels to
#: still be in the text.
SEVERITY_TERMS: list[str] = [
    "S1", "S2", "S3", "S4", "P1", "P2", "P3", "P4",
    "Sev 1", "Sev 2", "Sev 3", "Sev 4",
    "Critical", "Urgent", "Minor",
]

#: sup:Region — a closed, stable, four-value set. Never PII.
REGION_VALUES: list[str] = [
    "EMEA", "APAC", "LATAM",
    "Europe", "North America", "Asia Pacific", "Latin America",
]

#: Safety net: ordinary support words that carry ontology meaning and should
#: never be masked, but are not worth a recognizer of their own because
#: nothing would be gained by recording them in the audit trail.
PROTECTED_VOCABULARY: list[str] = [
    # Ticket lifecycle (sup:Ticket.status)
    "New", "Open", "Pending", "Escalated", "Resolved", "Closed",
    # License types and product lifecycle
    "Subscription", "Perpetual", "Trial", "NFR",
    "GA", "Maintenance", "EndOfLife",
    # Escalation / Jira issue types
    "Bug", "Enhancement", "Defect", "Story",
    # Agent tiers (sup:SupportAgent.tier)
    "T1", "T2", "T3",
    # Vocabulary anchors themselves
    "Severity", "Priority", "Sev", "Pri", "Entitlement", "SLA",
]


def unbound_entities() -> dict[str, str]:
    """Entity types with no ontology class, and why. The compliance report."""
    return {
        name: binding.gap
        for name, binding in ENTITY_BINDINGS.items()
        if binding.sup_ref is None and binding.gap
    }


def verify_against_export(path: Path | None = None) -> list[str]:
    """Check our class list still matches the ontology's glossary export.

    Returns a list of drift descriptions; empty means in sync. The ontology
    regenerates Export/ from its markdown, so this catches a class being
    added, renamed or cut without this file being updated.
    """
    glossary = (path or ontology_dir()) / "Export" / "support-ontology-glossary.csv"
    if not glossary.exists():
        return [f"ontology export not found at {glossary} — cannot verify"]

    exported: set[str] = set()
    with glossary.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.reader(handle):
            # Term rows carry the class ID inside the notes column.
            for cell in row:
                marker = "Ontology class sup:"
                if marker in cell:
                    tail = cell.split(marker, 1)[1]
                    exported.add(tail.split()[0].strip("(),."))

    problems = []
    for missing in sorted(ONTOLOGY_CLASSES - exported):
        problems.append(f"class {missing!r} is declared here but absent from the export")
    for added in sorted(exported - ONTOLOGY_CLASSES):
        problems.append(f"class {added!r} exists in the ontology but is unknown here")

    referenced = {
        b.sup_ref.split(".")[0].removeprefix("sup:")
        for b in ENTITY_BINDINGS.values()
        if b.sup_ref
    }
    for unknown in sorted(referenced - ONTOLOGY_CLASSES):
        problems.append(f"entity binding references unknown class {unknown!r}")

    return problems
