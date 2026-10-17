"""Annotated ticket corpus with ground-truth PII spans.

Tickets are authored with inline markers:  [[PERSON|Maria Gonzalez]]
The loader strips the markers and records where each value landed, so gold
offsets stay correct no matter how the surrounding text is edited.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

MARKER_RE = re.compile(r"\[\[([A-Z_]+)\|(.+?)\]\]", re.DOTALL)


@dataclass(frozen=True)
class GoldSpan:
    start: int
    end: int
    entity_type: str
    text: str


@dataclass
class AnnotatedTicket:
    doc_id: str
    text: str
    gold: list[GoldSpan]


def decode(doc_id: str, annotated: str) -> AnnotatedTicket:
    plain_parts: list[str] = []
    gold: list[GoldSpan] = []
    cursor = 0
    offset = 0

    for match in MARKER_RE.finditer(annotated):
        plain_parts.append(annotated[cursor:match.start()])
        offset += match.start() - cursor
        entity_type, value = match.group(1), match.group(2)
        gold.append(GoldSpan(offset, offset + len(value), entity_type, value))
        plain_parts.append(value)
        offset += len(value)
        cursor = match.end()

    plain_parts.append(annotated[cursor:])
    return AnnotatedTicket(doc_id, "".join(plain_parts), gold)


#: Free-text fields of a multi-field row, joined the way `ticketmask mask`
#: joins --text-fields, so measured offsets match what the CLI masks.
TEXT_FIELDS = ("subject", "description", "comments")


def load(path: str | Path) -> list[AnnotatedTicket]:
    """Rows are either {"doc_id", "annotated"} or a ticket with annotated
    subject / description / comments fields (see samples/)."""
    tickets = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        row = json.loads(line)
        if "annotated" in row:
            tickets.append(decode(row["doc_id"], row["annotated"]))
        else:
            merged = "\n\n".join(str(row.get(f) or "") for f in TEXT_FIELDS)
            tickets.append(decode(row["ticket_id"], merged))
    return tickets
