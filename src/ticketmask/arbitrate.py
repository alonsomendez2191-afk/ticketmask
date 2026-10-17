"""Resolve competing detections into one non-overlapping decision per span.

Stacking recognizers means a single string like "ACCT-889231" can fire as
ACCOUNT_NUMBER, TICKET_ID, DATE_TIME and US_DRIVER_LICENSE at once. Presidio
returns all of them; something has to choose. That choice is here, in one
readable place, because "why was this masked as X" is the question a client
will ask most often.
"""

from __future__ import annotations

from dataclasses import dataclass

from presidio_analyzer import RecognizerResult

from .policy import Action, Rule, rule_for


#: Higher wins when two detections cover the same text. Specific, structurally
#: unambiguous identifiers outrank general NER; the historically noisy
#: recognizers sit at the bottom.
ENTITY_PRECEDENCE: dict[str, int] = {
    # Structurally unambiguous secrets and identifiers.
    "CREDIT_CARD": 100, "US_SSN": 100, "IBAN_CODE": 100, "CRYPTO": 100,
    "LICENSE_KEY": 100, "MAC_ADDRESS": 100,

    # CRM and directory deny-lists. Authoritative: they come from the client's
    # own systems, so they outrank both NER and the controlled vocabulary.
    # This ordering is what stops an account genuinely named "Premium Widgets"
    # from being half-kept as a SupportEntitlement term and half-leaked.
    "ACCOUNT": 95, "PARTNER": 95, "CONTACT": 95, "SUPPORT_AGENT": 95,
    "SALES_REPRESENTATIVE": 95, "CUSTOMER_SUCCESS_MANAGER": 95,

    "CONTACT_EMAIL": 90, "TICKET_NUMBER": 90, "ACCOUNT_ID": 90, "DEVICE_SERIAL": 90,
    "JIRA_ISSUE_KEY": 85,
    "PHONE_NUMBER": 80, "IP_ADDRESS": 80,

    # Ontology controlled vocabulary. Above NER so "EMEA" is not masked as a
    # location and "Platinum" is not masked as an organization; below the
    # deny-lists so a real customer name always wins.
    "REGION": 75, "SEVERITY_LEVEL": 75, "SUPPORT_ENTITLEMENT": 75, "PRODUCT": 75,

    # Bare NER. Cannot tell a contact from an agent, which is why these types
    # are named "unresolved" rather than being assigned a role.
    "PERSON_UNRESOLVED": 70, "ORGANIZATION_UNRESOLVED": 70, "LOCATION": 70,
    "CUSTOMER_DOMAIN": 60,
    "URL": 50, "DATE_TIME": 50,

    # Historically noisy recognizers.
    "US_DRIVER_LICENSE": 20, "US_PASSPORT": 20, "MEDICAL_LICENSE": 20, "NRP": 20,
    "US_BANK_NUMBER": 20, "US_ITIN": 20, "UK_NHS": 20,
}


@dataclass
class Decision:
    """One resolved span and what we are going to do about it."""
    start: int
    end: int
    entity_type: str
    score: float
    action: Action
    text: str

    @property
    def length(self) -> int:
        return self.end - self.start


#: NER entity types that are prone to tagging bare acronyms. Ticket text is
#: dense with them (KB, VPN, MFA, SLA, RMA) and spaCy scores them as
#: confidently as it scores real names.
#: Only the bare-NER types. The controlled-vocabulary recognizers (REGION,
#: SEVERITY_LEVEL, agent tiers) legitimately emit short uppercase tokens —
#: EMEA, S1, T3 — and must not be filtered here.
_ACRONYM_PRONE = {"PERSON_UNRESOLVED", "LOCATION", "ORGANIZATION_UNRESOLVED", "NRP"}


def _is_acronym_noise(text: str, entity_type: str) -> bool:
    stripped = text.strip().strip(".")
    return (
        entity_type in _ACRONYM_PRONE
        and len(stripped) <= 4
        and stripped.isupper()
        and stripped.isalpha()
    )


#: Types whose span is a single indivisible identifier. A detection landing
#: strictly inside one of these is a fragment, not a competing reading —
#: "contoso" inside "r.chen@contoso-industries.net" is not an Account mention,
#: it is part of an email address. Without this, a high-precedence deny-list
#: term shreds the identifier that contains it and the rest leaks.
_ATOMIC_TYPES = {
    "CONTACT_EMAIL", "URL", "CUSTOMER_DOMAIN", "LICENSE_KEY", "DEVICE_SERIAL",
    "ACCOUNT_ID", "TICKET_NUMBER", "JIRA_ISSUE_KEY", "IP_ADDRESS",
    "MAC_ADDRESS", "CREDIT_CARD", "IBAN_CODE", "US_SSN", "PHONE_NUMBER",
}


def _drop_fragments(results: list[RecognizerResult]) -> list[RecognizerResult]:
    """Remove detections strictly contained inside an atomic identifier."""
    atomic = [r for r in results if r.entity_type in _ATOMIC_TYPES]
    if not atomic:
        return results

    kept = []
    for candidate in results:
        contained = any(
            container is not candidate
            and container.start <= candidate.start
            and candidate.end <= container.end
            and (container.end - container.start) > (candidate.end - candidate.start)
            for container in atomic
        )
        if not contained:
            kept.append(candidate)
    return kept


def _rank(result: RecognizerResult) -> tuple[int, float, int]:
    return (
        ENTITY_PRECEDENCE.get(result.entity_type, 0),
        result.score,
        result.end - result.start,
    )


def arbitrate(
    text: str,
    results: list[RecognizerResult],
    policy: dict[str, Rule] | None = None,
) -> list[Decision]:
    """Threshold, then collapse overlaps, returning spans in document order.

    Two passes, both deliberately simple:
      1. drop anything below its per-entity confidence threshold
      2. greedily keep the strongest detection and discard anything overlapping it
    """
    surviving: list[RecognizerResult] = []
    for result in results:
        rule = rule_for(result.entity_type, policy)
        if result.score < rule.threshold:
            continue
        if _is_acronym_noise(text[result.start:result.end], result.entity_type):
            continue
        surviving.append(result)

    surviving = _drop_fragments(surviving)

    # Strongest first, so the greedy sweep below always keeps the winner.
    surviving.sort(key=_rank, reverse=True)

    kept: list[RecognizerResult] = []
    for candidate in surviving:
        overlaps = any(
            candidate.start < winner.end and winner.start < candidate.end
            for winner in kept
        )
        if not overlaps:
            kept.append(candidate)

    decisions = [
        Decision(
            start=r.start,
            end=r.end,
            entity_type=r.entity_type,
            score=r.score,
            action=rule_for(r.entity_type, policy).action,
            text=text[r.start:r.end],
        )
        for r in kept
    ]
    decisions.sort(key=lambda d: d.start)
    return decisions
