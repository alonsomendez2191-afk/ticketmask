"""The sandwich: detect -> arbitrate -> link -> mask -> (model) -> unmask.

Note that the unmask half is for the *internal audit path only*. A published KB
article must stay de-identified — see mask_for_publication() vs the round trip
in unmask(). Getting this backwards builds a masking system that faithfully
reinserts every customer name into the final article.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .arbitrate import Decision, arbitrate
from .linker import link_variants, propagate_known_values
from .ontology import PRESIDIO_RENAMES, PROTECTED_VOCABULARY
from .policy import Action, Rule
from .recognizers import RecognizerConfig, build_analyzer
from .vault import DocumentVault

SURROGATE_RE = re.compile(r"<([A-Z_]+)_(\d+)>")


@dataclass
class MaskResult:
    doc_id: str
    masked_text: str
    vault: DocumentVault
    decisions: list[Decision] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        tally: dict[str, int] = {}
        for d in self.decisions:
            tally[d.entity_type] = tally.get(d.entity_type, 0) + 1
        return dict(sorted(tally.items()))

    def audit_rows(self) -> list[dict]:
        """Flat, printable record of every decision. This is the artifact a
        client's compliance reviewer asks for."""
        return [
            {
                "doc_id": self.doc_id,
                "entity_type": d.entity_type,
                "action": d.action.value,
                "score": round(d.score, 3),
                "start": d.start,
                "end": d.end,
                "original": d.text,
            }
            for d in self.decisions
        ]


class TicketMasker:
    def __init__(
        self,
        config: RecognizerConfig | None = None,
        policy: dict[str, Rule] | None = None,
        language: str = "en",
    ):
        self.config = config or RecognizerConfig()
        self.policy = policy
        self.language = language
        self.analyzer = build_analyzer(self.config)

    def mask(self, text: str, doc_id: str) -> MaskResult:
        raw = self.analyzer.analyze(
            text=text,
            language=self.language,
            allow_list=PROTECTED_VOCABULARY,
        )
        # Presidio's labels are domain-neutral. PERSON in particular must not
        # be taken at face value: which kind of person — Contact, agent, sales
        # rep — is exactly the distinction the ontology draws, and Presidio
        # cannot know it. Rename to the "unresolved" types, then let the
        # deny-list recognizers claim what they can.
        for result in raw:
            result.entity_type = PRESIDIO_RENAMES.get(result.entity_type, result.entity_type)

        decisions = arbitrate(text, raw, self.policy)
        decisions = propagate_known_values(text, decisions)
        canonical = link_variants(decisions)

        vault = DocumentVault(doc_id)
        out = []
        cursor = 0

        for decision in sorted(decisions, key=lambda d: d.start):
            if decision.start < cursor:      # defensive: overlap slipped through
                continue
            out.append(text[cursor:decision.start])

            if decision.action is Action.KEEP:
                out.append(decision.text)
            elif decision.action is Action.REDACT:
                # Nothing recorded. Deliberately unrecoverable.
                out.append(f"<{decision.entity_type}>")
            else:
                # Variants resolve to the canonical mention so that "Maria",
                # "Gonzalez" and "Maria Gonzalez" all become <CONTACT_1> —
                # and so that a role settled by the CRM deny-list carries to
                # the bare-surname mentions NER found on its own.
                key = (decision.entity_type, decision.text)
                canonical_text, canonical_type = canonical.get(
                    key, (decision.text, decision.entity_type)
                )
                surrogate = vault.surrogate_for(
                    canonical_text, canonical_type, decision.score
                )
                if (canonical_text, canonical_type) != (decision.text, decision.entity_type):
                    vault.alias(decision.text, canonical_type, surrogate)
                    # Record the resolved role in the audit trail, not the
                    # unresolved one we started from.
                    decision.entity_type = canonical_type
                out.append(surrogate)

            cursor = decision.end

        out.append(text[cursor:])
        return MaskResult(doc_id, "".join(out), vault, decisions)

    @staticmethod
    def unmask(text: str, vault: DocumentVault) -> str:
        """Restore originals. Internal/audit use only — never on published output."""
        def swap(match: re.Match) -> str:
            original = vault.original_for(match.group(0))
            return original if original is not None else match.group(0)

        return SURROGATE_RE.sub(swap, text)

    @staticmethod
    def residual_surrogates(text: str) -> list[str]:
        """Surrogates still present in generated output.

        Run this on every draft KB article before it ships. A hit means the
        model copied a placeholder verbatim into the article — which is a
        formatting bug, but a *miss* by the detector would leave a real name
        here instead, so this check is also the last line of defence.
        """
        return sorted({m.group(0) for m in SURROGATE_RE.finditer(text)})
