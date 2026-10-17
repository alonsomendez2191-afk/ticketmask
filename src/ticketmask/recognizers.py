"""Ticket-specific recognizers layered on top of Presidio's defaults.

Entity types emitted here are ontology class names (see ontology.py), not
Presidio's domain-neutral labels. Every client's ticketing system stamps its
own identifier formats, so the patterns are defaults meant to be overridden per
engagement via RecognizerConfig rather than treated as universal truth.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from presidio_analyzer import (
    AnalyzerEngine,
    EntityRecognizer,
    Pattern,
    PatternRecognizer,
    RecognizerRegistry,
    RecognizerResult,
)
from presidio_analyzer.nlp_engine import NlpArtifacts

from .ontology import ENTITLEMENT_TERMS, REGION_VALUES, SEVERITY_TERMS

# Domains that appear in tickets but identify no account: vendor docs, public
# services, the support org's own mail. Anything NOT on this list that shows up
# in an email address is treated as an account-identifying domain.
DEFAULT_DOMAIN_ALLOWLIST = {
    "microsoft.com", "google.com", "github.com", "stackoverflow.com",
    "atlassian.net", "salesforce.com", "aws.amazon.com", "amazon.com",
    "apache.org", "python.org", "docs.python.org", "wikipedia.org",
    "gmail.com", "outlook.com", "hotmail.com", "yahoo.com",
    "example.com", "localhost",
}

# sup:Product instances. In an engagement this list comes from the licensing
# system, which the ontology names as authoritative for productId. Masking a
# product name produces an article about configuring "<PRODUCT_2>", which is
# worthless — so Product detections are KEPT, not masked.
DEFAULT_PRODUCTS = [
    "Microsoft", "Windows", "Azure", "Active Directory", "Office 365", "Microsoft 365",
    "Outlook", "Teams", "SharePoint", "Exchange", "SQL Server", "Intune", "Entra",
    "Google", "Gmail", "Chrome", "Android", "Apple", "macOS", "iOS", "iPhone",
    "Cisco", "Meraki", "Fortinet", "Palo Alto", "VMware", "Citrix", "Okta", "Duo",
    "AWS", "Amazon Web Services", "Salesforce", "ServiceNow", "Jira", "Zendesk",
    "Slack", "Zoom", "Linux", "Ubuntu", "Red Hat", "Docker", "Kubernetes",
    "Oracle", "SAP", "Adobe", "Dell", "HP", "Lenovo", "Intel", "NVIDIA",
]


@dataclass
class RecognizerConfig:
    """Per-engagement tuning.

    The four people lists and the two organization lists exist because the
    ontology declares those classes pairwise disjoint. A single "names to
    mask" list would mask just as effectively but would throw away the
    distinction, and the distinction is what makes a KB article readable.
    """

    # --- sup:Ticket / sup:JiraIssue ----------------------------------------
    ticket_number_patterns: list[tuple[str, str, float]] = field(default_factory=lambda: [
        ("servicenow_inc", r"\b(?:INC|RITM|CHG|PRB)\d{6,10}\b", 0.90),
        ("case_prefixed",  r"\b(?:CASE|TKT|SR|REQ|TICKET)[-#\s]?\d{4,10}\b", 0.85),
        ("zendesk_hash",   r"(?<=[Tt]icket )#\d{4,8}\b", 0.80),
    ])
    #: EQ-04: a Jira key is NOT a ticket number, though both get called
    #: "ticket" in conversation. The ontology declares the classes disjoint,
    #: so they are separate entity types here.
    jira_key_patterns: list[tuple[str, str, float]] = field(default_factory=lambda: [
        ("jira_key", r"\b[A-Z][A-Z0-9]{1,9}-\d{1,6}\b", 0.55),
    ])

    # --- organizations (sup:Account, sup:Partner — disjoint) ---------------
    accounts: list[str] = field(default_factory=list)
    partners: list[str] = field(default_factory=list)

    # --- people (sup:Contact and the three internal roles — disjoint) ------
    contacts: list[str] = field(default_factory=list)
    support_agents: list[str] = field(default_factory=list)
    sales_representatives: list[str] = field(default_factory=list)
    customer_success_managers: list[str] = field(default_factory=list)

    #: Customer site and address terms, from the CRM's account address
    #: fields. NER on locations is context-sensitive to the point of being
    #: unreliable in ticket text - spaCy tags "Melbourne" as a place on its
    #: own and misses it entirely two words after "Region: APAC". A
    #: gazetteer from the client's own data is the fix, not a threshold.
    locations: list[str] = field(default_factory=list)

    # --- controlled vocabulary and allow-lists -----------------------------
    products: list[str] = field(default_factory=lambda: list(DEFAULT_PRODUCTS))
    domain_allowlist: set[str] = field(default_factory=lambda: set(DEFAULT_DOMAIN_ALLOWLIST))


class CustomerDomainRecognizer(EntityRecognizer):
    """Flags email/URL domains that are not on the vendor allow-list.

    A pattern recognizer can't express "match a domain unless it is one of
    these 200", so this is a small explicit recognizer instead of an
    unreadable negative-lookahead regex.
    """

    DOMAIN_RE = r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,24}\b"

    def __init__(self, allowlist: set[str] | None = None):
        super().__init__(supported_entities=["CUSTOMER_DOMAIN"], name="CustomerDomainRecognizer")
        self.allowlist = {d.lower() for d in (allowlist or DEFAULT_DOMAIN_ALLOWLIST)}

    def load(self) -> None:  # required by EntityRecognizer
        pass

    @staticmethod
    def _has_real_tld(domain: str) -> bool:
        """Reject log noise like auth.svc or license.check.

        These match any "word.word" regex but are service names, not hosts.
        tldextract ships with Presidio already and knows the public suffix
        list, so this is a real check rather than another hand-kept list.
        """
        import tldextract

        extracted = tldextract.extract(domain)
        return bool(extracted.suffix and extracted.domain)

    def analyze(self, text: str, entities, nlp_artifacts: NlpArtifacts | None = None):
        results = []
        for match in re.finditer(self.DOMAIN_RE, text):
            domain = match.group().lower().rstrip(".")
            if any(domain == a or domain.endswith("." + a) for a in self.allowlist):
                continue
            if not self._has_real_tld(domain):
                continue
            results.append(
                RecognizerResult(
                    entity_type="CUSTOMER_DOMAIN",
                    start=match.start(),
                    end=match.end(),
                    score=0.60,
                )
            )
        return results


#: RecognizerConfig list field -> the entity type its deny-list emits.
#: Module-level so the SQL export can read the mapping instead of copying it.
DENY_LIST_ENTITY_TYPES = {
    "accounts": "ACCOUNT",
    "partners": "PARTNER",
    "contacts": "CONTACT",
    "support_agents": "SUPPORT_AGENT",
    "sales_representatives": "SALES_REPRESENTATIVE",
    "customer_success_managers": "CUSTOMER_SUCCESS_MANAGER",
    "locations": "LOCATION",
    # KEEP rather than mask, but detected the same way: the catalog has to
    # outrank NER, which would otherwise tag product names as organizations.
    "products": "PRODUCT",
}


def _pattern_recognizer(entity: str, patterns, context=None) -> PatternRecognizer:
    return PatternRecognizer(
        supported_entity=entity,
        patterns=[Pattern(name=n, regex=r, score=s) for n, r, s in patterns],
        context=context or [],
    )


def _deny_list(entity: str, terms: list[str], score: float = 0.95, name: str | None = None):
    return PatternRecognizer(
        supported_entity=entity,
        deny_list=terms,
        deny_list_score=score,
        name=name or f"{entity}DenyList",
    )


def build_custom_recognizers(config: RecognizerConfig | None = None) -> list[EntityRecognizer]:
    cfg = config or RecognizerConfig()
    recognizers: list[EntityRecognizer] = [
        _pattern_recognizer("TICKET_NUMBER", cfg.ticket_number_patterns,
                            context=["ticket", "case", "incident", "sr", "ref"]),
        _pattern_recognizer("JIRA_ISSUE_KEY", cfg.jira_key_patterns,
                            context=["jira", "issue", "bug", "defect", "escalation", "dev"]),

        _pattern_recognizer("ACCOUNT_ID", [
            ("acct_prefixed", r"\b(?:ACCT|ACCOUNT|CUST|CUSTOMER)[-#:\s]{0,2}\d{5,12}\b", 0.85),
            ("acct_labelled", r"(?<=account number[:\s])\s*[A-Z0-9-]{5,20}\b", 0.80),
        ], context=["account", "customer", "billing", "subscription"]),

        _pattern_recognizer("DEVICE_SERIAL", [
            ("sn_labelled", r"(?i)\b(?:S/N|SN|Serial(?:\s+No\.?|\s+Number)?)[:=\s#]{1,3}[A-Z0-9-]{6,24}\b", 0.85),
            ("sn_kv", r"(?i)\b(?:serial|serial_no|sn|device_sn)[:=][A-Z0-9-]{6,24}\b", 0.85),
        ], context=["serial", "device", "hardware", "rma", "appliance"]),

        _pattern_recognizer("MAC_ADDRESS", [
            ("mac_colon", r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b", 0.90),
        ], context=["mac", "nic", "adapter", "interface"]),

        _pattern_recognizer("LICENSE_KEY", [
            ("grouped_key", r"\b(?:[A-Z0-9]{4,6}-){3,5}[A-Z0-9]{4,6}\b", 0.75),
            ("bearer_token", r"\b(?:sk|pk|ghp|xox[baprs])[-_][A-Za-z0-9]{16,}\b", 0.90),
        ], context=["license", "key", "activation", "token", "secret"]),

        CustomerDomainRecognizer(cfg.domain_allowlist),

        # --- ontology controlled vocabulary. All KEEP: detected so they show
        # in the audit trail, and so they outrank NER, which would otherwise
        # mask "EMEA" as a location and "Platinum" as an organization.
        _deny_list("REGION", REGION_VALUES, 0.95, "RegionVocabulary"),
        _deny_list("SEVERITY_LEVEL", SEVERITY_TERMS, 0.95, "SeverityVocabulary"),
        _deny_list("SUPPORT_ENTITLEMENT", ENTITLEMENT_TERMS, 0.95, "EntitlementVocabulary"),
    ]

    # Deny-lists are the highest-precision signal available. Every engagement
    # should populate them from the client's CRM (accounts, contacts, partners)
    # and helpdesk directory (agents). Each maps to one disjoint ontology class.
    for field_name, entity in DENY_LIST_ENTITY_TYPES.items():
        terms = getattr(cfg, field_name)
        if terms:
            recognizers.append(_deny_list(entity, terms))

    return recognizers


def build_analyzer(config: RecognizerConfig | None = None) -> AnalyzerEngine:
    """Presidio's default recognizers plus the ticket-specific set."""
    registry = RecognizerRegistry()
    registry.load_predefined_recognizers()
    for recognizer in build_custom_recognizers(config):
        registry.add_recognizer(recognizer)
    return AnalyzerEngine(registry=registry)
