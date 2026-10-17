"""Tie together the many ways one entity is written inside a single ticket.

Three distinct problems, all endemic to ticket text:

  1. NER reliably tags the first "Maria Gonzalez" and then misses the six
     later "Maria" and "Gonzalez" mentions in the comment thread.
  2. The same person appears as a name, an email local-part, and a signature
     block, and each gets its own surrogate — which tells a reader they are
     three different people.
  3. The CRM deny-list resolves "Maria Gonzalez" to a sup:Contact, but the
     bare "Maria" three lines later falls through to NER and loses the role.
     The ontology says a Contact is disjoint from an agent; losing the role
     mid-document silently discards that distinction.

All three are fixed by treating a confirmed detection as a known value and
sweeping the document for it, rather than trusting per-span NER recall.
"""

from __future__ import annotations

import re

from .arbitrate import Decision
from .policy import Action

#: Person roles. The ontology declares these pairwise disjoint (C-52), so
#: variants may only link *within* this group, and only to upgrade an
#: unresolved mention — never to convert one resolved role into another.
PERSON_ROLES = {
    "CONTACT", "SUPPORT_AGENT", "SALES_REPRESENTATIVE",
    "CUSTOMER_SUCCESS_MANAGER", "PERSON_UNRESOLVED",
}

#: Organization roles. sup:Account and sup:Partner are likewise disjoint.
ORG_ROLES = {"ACCOUNT", "PARTNER", "ORGANIZATION_UNRESOLVED"}

#: Types where a partial mention (a first name, a bare surname) is worth
#: linking back to the full mention. Structural identifiers are excluded —
#: a substring of an account number is not the account number.
LINKABLE_TYPES = PERSON_ROLES | ORG_ROLES

#: The "I could not resolve a role" members of each group. Only these may be
#: upgraded by linking.
UNRESOLVED = {"PERSON_UNRESOLVED", "ORGANIZATION_UNRESOLVED"}

#: Ignore fragments this short when sweeping; "Al" would match half the corpus.
MIN_SWEEP_LENGTH = 4

_ORG_NOISE = re.compile(r"\b(inc|llc|ltd|corp|corporation|co|gmbh|plc|sa|bv)\b\.?", re.I)


def _normalize(value: str) -> str:
    value = _ORG_NOISE.sub("", value.lower())
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _group_of(entity_type: str) -> frozenset[str] | None:
    if entity_type in PERSON_ROLES:
        return frozenset(PERSON_ROLES)
    if entity_type in ORG_ROLES:
        return frozenset(ORG_ROLES)
    return None


def link_variants(decisions: list[Decision]) -> dict[tuple[str, str], tuple[str, str]]:
    """Map each variant spelling onto the canonical mention of the same entity.

    Returns {(entity_type, variant_text): (canonical_text, canonical_type)}.
    The canonical form is the longest mention seen, on the assumption that
    "Maria Gonzalez" is the full identity and "Maria" is a reference to it.

    Linking crosses entity types only within a disjointness group, and only to
    resolve an unresolved mention. Two *differently resolved* roles that look
    like variants of each other are left alone: if the CRM says one name is a
    Contact and another is an agent, that is a fact, not a spelling variant.
    """
    canonical: dict[tuple[str, str], tuple[str, str]] = {}

    linkable = [d for d in decisions if d.entity_type in LINKABLE_TYPES]
    # Longest first: full names become the canonical form for their parts.
    ordered = sorted({(d.text, d.entity_type) for d in linkable},
                     key=lambda pair: len(pair[0]), reverse=True)

    for full_text, full_type in ordered:
        group = _group_of(full_type)
        norm = _normalize(full_text)
        if not group or not norm:
            continue

        for part_text, part_type in ordered:
            if part_text == full_text or part_type not in group:
                continue
            # Only ever upgrade an unresolved mention. Never rewrite a role
            # the deny-lists already settled.
            if part_type not in UNRESOLVED:
                continue
            part_norm = _normalize(part_text)
            if not part_norm or len(part_norm) < MIN_SWEEP_LENGTH:
                continue
            # "maria" is a whole-token subset of "maria gonzalez"
            if set(part_norm.split()) < set(norm.split()):
                canonical.setdefault((part_type, part_text), (full_text, full_type))

    return canonical


def propagate_known_values(text: str, decisions: list[Decision]) -> list[Decision]:
    """Sweep the document for repeat occurrences the detector missed.

    Only values already confirmed by a recognizer are swept, so this raises
    recall without inventing new entity types. Matches are case-insensitive
    and **word-bounded** — without the boundary, sweeping a confirmed "Chen"
    matches inside "r.chen@corp.com" and shreds the email address. Anything
    overlapping an existing decision is skipped.
    """
    known = {
        d.text: d
        for d in decisions
        if d.action is not Action.KEEP and len(d.text) >= MIN_SWEEP_LENGTH
    }
    if not known:
        return decisions

    taken = [(d.start, d.end) for d in decisions]
    additions: list[Decision] = []

    for value, source in known.items():
        pattern = r"(?<![\w.@-])" + re.escape(value) + r"(?![\w.@-])"
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            start, end = match.start(), match.end()
            if any(start < t_end and t_start < end for t_start, t_end in taken):
                continue
            additions.append(
                Decision(
                    start=start,
                    end=end,
                    entity_type=source.entity_type,
                    # Swept matches inherit slightly reduced confidence: the
                    # value is confirmed, this particular occurrence is not.
                    score=min(source.score, 0.95),
                    action=source.action,
                    text=text[start:end],
                )
            )
            taken.append((start, end))

    merged = decisions + additions
    merged.sort(key=lambda d: d.start)
    return merged
