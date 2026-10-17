"""What to do with each entity type, and how sure we need to be.

Kept as plain data on purpose. This table is the thing a client's security
reviewer will actually read, so it has to be legible without reading any code.

Entity type names are ontology class names — see ontology.py. They are not
Presidio's names and not ours to invent.
"""

from dataclasses import dataclass
from enum import Enum


class Action(str, Enum):
    #: Replace with a stable surrogate and record the mapping in the vault.
    #: Reversible. This is the default for anything a human could be identified by.
    PSEUDONYMIZE = "pseudonymize"

    #: Replace with a type marker. Not reversible, nothing stored.
    #: For values with no analytical value that we never want to be able to recover.
    REDACT = "redact"

    #: Leave the value in place. For identifiers that carry no personal
    #: information but that we need for provenance, and for the ontology's
    #: controlled vocabulary, which is meaning rather than data.
    KEEP = "keep"


@dataclass(frozen=True)
class Rule:
    action: Action
    #: Minimum Presidio confidence to act on. Below this the detection is dropped.
    #: Tune these against tests/corpus, do not guess them.
    threshold: float
    #: Human-readable justification. Shows up in the audit report.
    rationale: str


DEFAULT_POLICY: dict[str, Rule] = {
    # --- people (sup:Contact and the three internal roles) ------------------
    # All pseudonymized identically, so a misclassification between them is a
    # labelling error, never a leak. The distinction is kept because a KB
    # article that cannot tell "the customer reported" from "the agent did"
    # is worse than useless — it is misleading.
    "CONTACT": Rule(Action.PSEUDONYMIZE, 0.60, "Person at the customer account."),
    "SUPPORT_AGENT": Rule(Action.PSEUDONYMIZE, 0.50, "Internal staff. Employee PII is still PII."),
    "SALES_REPRESENTATIVE": Rule(Action.PSEUDONYMIZE, 0.50, "Internal staff."),
    "CUSTOMER_SUCCESS_MANAGER": Rule(Action.PSEUDONYMIZE, 0.50, "Internal staff."),
    "PERSON_UNRESOLVED": Rule(Action.PSEUDONYMIZE, 0.60, "Person with no resolved role. Masked, not classified."),

    # --- organizations (sup:Account, sup:Partner) ---------------------------
    "ACCOUNT": Rule(Action.PSEUDONYMIZE, 0.50, "Customer organization, from the CRM deny-list."),
    "PARTNER": Rule(Action.PSEUDONYMIZE, 0.50, "ISV/partner org. Disjoint from Account — never merge the two."),
    "ORGANIZATION_UNRESOLVED": Rule(Action.PSEUDONYMIZE, 0.85, "NER-detected org, role unresolved. High bar to limit over-masking."),

    # --- direct identifiers -------------------------------------------------
    "CONTACT_EMAIL": Rule(Action.PSEUDONYMIZE, 0.50, "sup:Contact.emailAddress. Also the CRM join key."),
    "PHONE_NUMBER": Rule(Action.PSEUDONYMIZE, 0.35, "Presidio scores these low; tuned against corpus."),
    "CUSTOMER_DOMAIN": Rule(Action.PSEUDONYMIZE, 0.50, "Identifies the account as surely as its name."),
    "ACCOUNT_ID": Rule(Action.PSEUDONYMIZE, 0.50, "sup:Account.accountId. Links a ticket to a paying customer."),
    "LICENSE_KEY": Rule(Action.REDACT, 0.50, "sup:License.licenseKey. Secret. Never recoverable."),
    "DEVICE_SERIAL": Rule(Action.PSEUDONYMIZE, 0.50, "Customer-linkable via RMA. No ontology class — see ontology.py."),
    "MAC_ADDRESS": Rule(Action.PSEUDONYMIZE, 0.50, "Hardware identifier."),
    "IP_ADDRESS": Rule(Action.PSEUDONYMIZE, 0.50, "Often the customer's own host; keep shape for triage."),

    # --- provenance, kept deliberately --------------------------------------
    # EQ-04: Ticket and JiraIssue are DISJOINT and both get called "ticket".
    # They are separate entity types here for exactly that reason.
    "TICKET_NUMBER": Rule(Action.KEEP, 0.50, "sup:Ticket.ticketNumber. The audit trail depends on it."),
    "JIRA_ISSUE_KEY": Rule(Action.KEEP, 0.50, "sup:JiraIssue.issueKey. Engineering-internal, not customer data."),
    "DATE_TIME": Rule(Action.KEEP, 0.60, "Sequence matters for troubleshooting steps."),
    "URL": Rule(Action.KEEP, 0.60, "Usually product documentation. CUSTOMER_DOMAIN covers the exception."),

    # --- ontology controlled vocabulary, kept ------------------------------
    # Masking these breaks the reasoning the ontology exists to enable.
    "REGION": Rule(Action.KEEP, 0.50, "sup:Region — closed four-value set (EMEA/NA/APAC/LATAM). Not PII."),
    "PRODUCT": Rule(Action.KEEP, 0.50, "sup:Product. An article about <PRODUCT_2> is worthless."),
    "SEVERITY_LEVEL": Rule(Action.KEEP, 0.50, "sup:SeverityLevel. EQ-03 alias resolution needs the label intact."),
    "SUPPORT_ENTITLEMENT": Rule(Action.KEEP, 0.50, "sup:SupportEntitlement. EQ-02: Platinum and Premium are one tier."),

    # --- quasi-identifiers --------------------------------------------------
    "LOCATION": Rule(Action.PSEUDONYMIZE, 0.60, "Site or postal address. Distinct from sup:Region."),
    "NRP": Rule(Action.REDACT, 0.60, "Nationality/religion/politics. Never belongs in a KB article."),

    # --- pure PII, irreversibly removed -------------------------------------
    "CREDIT_CARD": Rule(Action.REDACT, 0.40, "Never recoverable. PCI scope."),
    "US_SSN": Rule(Action.REDACT, 0.40, "Never recoverable."),
    "US_PASSPORT": Rule(Action.REDACT, 0.40, "Never recoverable."),
    "US_DRIVER_LICENSE": Rule(Action.REDACT, 0.70, "Never recoverable. Noisy recognizer — high threshold."),
    "US_BANK_NUMBER": Rule(Action.REDACT, 0.40, "Never recoverable."),
    "US_ITIN": Rule(Action.REDACT, 0.40, "Never recoverable."),
    "UK_NHS": Rule(Action.REDACT, 0.40, "Never recoverable. Special-category data."),
    "IBAN_CODE": Rule(Action.REDACT, 0.40, "Never recoverable."),
    "CRYPTO": Rule(Action.REDACT, 0.40, "Never recoverable."),
    "MEDICAL_LICENSE": Rule(Action.REDACT, 0.40, "Never recoverable."),
}


def rule_for(entity_type: str, policy: dict[str, Rule] | None = None) -> Rule:
    """Look up a rule, failing loudly on anything unmapped.

    A new Presidio version adding a recognizer should break the build, not
    quietly start leaking a new entity type into published articles.
    """
    table = DEFAULT_POLICY if policy is None else policy
    try:
        return table[entity_type]
    except KeyError:
        raise KeyError(
            f"No masking policy for entity type {entity_type!r}. "
            f"Add it to DEFAULT_POLICY in policy.py — refusing to guess."
        ) from None


# ---------------------------------------------------------------------------
# Structured fields: what to do with each ontology *attribute*.
#
# Status: PROPOSED. Not enforced — the pipeline today masks free text only, and
# nothing yet masks structured CRM columns. This table exists because the
# ontology has no data-classification layer (see CLAUDE.md, "Gaps"), so the
# decision "is Account.accountName personal data?" has nowhere else to live.
# scripts/export_ontology_sql.py exports it, and fails if any ontology
# attribute has no rule here.
# ---------------------------------------------------------------------------


class Handling(str, Enum):
    #: The field holds values of one masking entity type, and that type's Rule
    #: above decides the action. Stated once, so the two cannot disagree.
    BY_ENTITY_TYPE = "by_entity_type"

    #: No masking entity type fits, so the action is stated directly.
    FIXED = "fixed"

    #: Human-written text. There is no single action: it goes through the
    #: pipeline and each detected span gets its own.
    SCAN = "scan"


@dataclass(frozen=True)
class AttributeRule:
    handling: Handling
    entity_type: str | None = None
    action: Action | None = None
    rationale: str = ""


def _by(entity_type: str, rationale: str) -> AttributeRule:
    return AttributeRule(Handling.BY_ENTITY_TYPE, entity_type=entity_type, rationale=rationale)


def _fixed(action: Action, rationale: str) -> AttributeRule:
    return AttributeRule(Handling.FIXED, action=action, rationale=rationale)


def _scan(rationale: str) -> AttributeRule:
    return AttributeRule(Handling.SCAN, rationale=rationale)


_KEEP = Action.KEEP
_PSEUDO = Action.PSEUDONYMIZE

#: Keyed "Class.property", exactly as the ontology entity files name them.
ATTRIBUTE_POLICY: dict[str, AttributeRule] = {
    # --- sup:Account
    "Account.accountId": _by("ACCOUNT_ID", "CRM key; links every record to a paying customer."),
    "Account.accountName": _by("ACCOUNT", "The customer organization's name."),
    "Account.isStrategic": _fixed(_KEEP, "Classification flag; identifies no one."),
    "Account.accountStatus": _fixed(_KEEP, "Lifecycle enum; identifies no one."),
    "Account.createdAt": _by("DATE_TIME", "Dates are kept; troubleshooting depends on sequence."),

    # --- sup:CRM — describes a system, not a customer
    "CRM.systemCode": _fixed(_KEEP, "Provenance: disambiguates ticket numbers across systems."),
    "CRM.systemName": _fixed(_KEEP, "Vendor system name."),
    "CRM.ticketTermUsed": _fixed(_KEEP, "EQ-01 alias anchor. Vocabulary, not data."),
    "CRM.isAuthoritative": _fixed(_KEEP, "System property."),

    # --- sup:Contact — the ontology models no contact name, only these
    "Contact.contactId": _fixed(_PSEUDO, "CRM key for a person. No entity type exists for it."),
    "Contact.emailAddress": _by("CONTACT_EMAIL", "Direct identifier and the ticket join key."),
    "Contact.isSupportAuthorised": _fixed(_KEEP, "Permission flag; identifies no one."),
    "Contact.isPrimary": _fixed(_KEEP, "Role flag; identifies no one."),

    # --- internal roles: identifiers are CRM user IDs, i.e. employees
    "CustomerSuccessManager.csmId": _fixed(_PSEUDO, "CRM user ID. Employee PII is still PII."),
    "CustomerSuccessManager.isActive": _fixed(_KEEP, "Status flag."),
    "SalesRepresentative.repId": _fixed(_PSEUDO, "CRM user ID. Employee PII is still PII."),
    "SalesRepresentative.isActive": _fixed(_KEEP, "Status flag."),
    "SupportAgent.agentId": _fixed(_PSEUDO, "CRM user ID. Employee PII is still PII."),
    "SupportAgent.tier": _fixed(_KEEP, "T1-T3 is ontology vocabulary."),
    "SupportAgent.isActive": _fixed(_KEEP, "Status flag."),

    # --- sup:Documentation
    "Documentation.articleUrl": _by("URL", "Documentation URL; the article's identity."),
    "Documentation.title": _scan("Author-written; internal articles can name customers."),
    "Documentation.lastReviewedAt": _by("DATE_TIME", "Staleness signal for C-40."),
    "Documentation.isPublic": _fixed(_KEEP, "Visibility flag."),

    # --- sup:Escalation
    "Escalation.escalationId": _fixed(_KEEP, "Generated UUID; carries no personal data."),
    "Escalation.escalationType": _fixed(_KEEP, "Bug/Enhancement vocabulary."),
    "Escalation.escalatedAt": _by("DATE_TIME", "Sequence matters."),
    "Escalation.justification": _scan("Agent-written; routinely quotes the customer."),
    "Escalation.wasAccepted": _fixed(_KEEP, "Outcome flag."),
    "Escalation.reproductionSteps": _scan("Agent-written; often pastes logs with hosts and users."),

    # --- sup:JiraIssue — engineering-internal
    "JiraIssue.issueKey": _by("JIRA_ISSUE_KEY", "EQ-04: kept, never conflated with a ticket number."),
    "JiraIssue.issueType": _fixed(_KEEP, "Bug/Enhancement vocabulary."),
    "JiraIssue.issueStatus": _fixed(_KEEP, "Workflow status."),
    "JiraIssue.isResolved": _fixed(_KEEP, "Normalised status flag."),
    "JiraIssue.fixVersion": _fixed(_KEEP, "Release identifier; what a KB article must cite."),
    "JiraIssue.createdAt": _by("DATE_TIME", "Sequence matters."),

    # --- sup:License
    "License.licenseKey": _by("LICENSE_KEY", "A secret. Never recoverable."),
    "License.seatCount": _fixed(_KEEP, "Quantity; not identifying on its own."),
    "License.startDate": _by("DATE_TIME", "Coverage questions (C-14) need the dates."),
    "License.endDate": _by("DATE_TIME", "Coverage questions (C-14) need the dates."),
    "License.isActive": _fixed(_KEEP, "Derived flag."),
    "License.licenseType": _fixed(_KEEP, "Subscription/Perpetual/Trial/NFR vocabulary."),

    # --- sup:Partner
    "Partner.partnerId": _fixed(_PSEUDO, "CRM key for a third-party organization."),
    "Partner.partnerName": _by("PARTNER", "Partner organization name. Disjoint from Account."),
    "Partner.partnershipLevel": _fixed(_KEEP, "Gold/Silver tier; identifies no one."),

    # --- sup:Product — the thing articles are about; masking it ruins them
    "Product.productId": _fixed(_KEEP, "Licensing system key for a product."),
    "Product.productName": _by("PRODUCT", "Articles about <PRODUCT_2> are worthless."),
    "Product.currentVersion": _fixed(_KEEP, "Release identifier."),
    "Product.lifecycleStatus": _fixed(_KEEP, "GA/Maintenance/EndOfLife vocabulary."),
    "Product.endOfLifeDate": _by("DATE_TIME", "Drives documentation retirement (C-23)."),
    "Product.usesPlatinumNaming": _fixed(_KEEP, "EQ-02 alias anchor."),
    "Product.severityTermUsed": _fixed(_KEEP, "EQ-03 alias anchor."),
    "Product.documentationRootUrl": _by("URL", "Public KB entry point."),

    # --- controlled vocabulary. Masking any of it breaks alias resolution.
    "Region.regionCode": _by("REGION", "Closed four-value set. Not PII."),
    "Region.regionName": _by("REGION", "Display name of a closed set."),
    "Region.timeZoneRange": _fixed(_KEEP, "Coverage-hours input."),
    "SeverityLevel.levelCode": _by("SEVERITY_LEVEL", "S1-S4. C-26 filters need it intact."),
    "SeverityLevel.levelRank": _fixed(_KEEP, "C-26: the only field severity may be compared on."),
    "SeverityLevel.levelName": _by("SEVERITY_LEVEL", "System Down, Work Stoppage, and so on."),
    "SeverityLevel.definition": _fixed(_KEEP, "Published contractual standard; no customer data."),
    "SupportEntitlement.tierCode": _by("SUPPORT_ENTITLEMENT", "EQ-02: Premium and Platinum are one tier."),
    "SupportEntitlement.tierRank": _fixed(_KEEP, "Ordering of a closed set."),
    "SupportEntitlement.grantsEscalationRight": _fixed(_KEEP, "C-12 policy flag."),
    "SupportEntitlement.responseTargetHours": _fixed(_KEEP, "Service target."),
    "SLA.slaName": _fixed(_KEEP, "Composed of vocabulary, e.g. Premium S1."),
    "SLA.targetResponseMinutes": _fixed(_KEEP, "Service target."),
    "SLA.targetResolutionMinutes": _fixed(_KEEP, "Service target."),

    # --- sup:Ticket
    "Ticket.ticketNumber": _by("TICKET_NUMBER", "Provenance; the audit trail depends on it."),
    "Ticket.subject": _scan("Customer-written. Regularly contains names and hosts."),
    "Ticket.status": _fixed(_KEEP, "Lifecycle vocabulary."),
    "Ticket.openedAt": _by("DATE_TIME", "Sequence matters."),
    "Ticket.resolvedAt": _by("DATE_TIME", "Sequence matters."),
    "Ticket.resolutionSummary": _scan("Agent-written; the richest source of KB content and of PII."),
}
