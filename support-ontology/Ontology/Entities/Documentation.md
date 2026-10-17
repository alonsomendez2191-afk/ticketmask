# Documentation

**Class ID:** `sup:Documentation`
**Type:** Knowledge
**Status:** Canonical
**Version:** 0.2.0

## Definition
Published product documentation and knowledge base content that support agents
consult to resolve tickets. One instance is one published unit — an article or
page — identified by its URL.

Documentation is the support organization's shared memory. A wrong article does
not produce one wrong answer; it produces one wrong answer per agent who reads
it.

## Canonical name and aliases
| Context | Term used |
|---|---|
| Canonical | Documentation |
| KB tooling | Article, KB article, Doc, Page |
| Agent conversation | The docs, the wiki |
| Content team | Content, Topic |

## Identity rule
The published URL is authoritative. Where content exists at several URLs
(localised or mirrored), the canonical URL is the identity and the others are
recorded as aliases.

## Datatype properties
| Property | Type | Required | Notes |
|---|---|---|---|
| `articleUrl` | string | Yes | Canonical published URL — the identity |
| `title` | string | Yes | |
| `lastReviewedAt` | date | No | Staleness signal for `C-40` |
| `isPublic` | boolean | Yes | Whether customers can reach it |

## Object properties
| Property | Target | Cardinality | Inverse |
|---|---|---|---|
| `describes` | `sup:Product` | `1..1` | `isDescribedBy` |
| `isConsultedBy` | `sup:SupportAgent` | `0..*` | `consults` |
| `resolves` | `sup:Ticket` | `0..*` | `resolvedUsing` |

Article-to-article linking is **not** modelled. Orphan detection and link-graph
analysis belong to the KB evaluation tooling, which reads the published site
directly; duplicating the link graph here would mean maintaining a second copy
of something already derivable. See `OQ-45`.

## Subclasses and individuals
None enumerated. Loaded from the KB source inventories.

## Disjoint with
None.

## Constraints
- `C-23` — documentation describing an EndOfLife product is a retirement
  candidate. Advisory.
- `C-40` — an article with no `lastReviewedAt` in the last 24 months is a review
  candidate. Advisory.
- `C-55` — every Documentation instance describes exactly one Product. Content
  that genuinely spans products is a signal it should be split — but this is
  `Soft`, because cross-product overview pages legitimately exist.

## Provenance
| Source system | What it supplies | Authoritative for |
|---|---|---|
| KB / documentation platform | The article and its content | Everything |
| KB source inventories (`sources.json` per product) | Which articles are tracked | Coverage set |
| CRM | Articles cited on resolved cases | `resolves` |

## Competency questions answered
`CQ-12`, `CQ-16`, `CQ-24`, `CQ-26`

## Open questions
`OQ-29` (article versioning and localisation),
`OQ-30` (is "the agent used this article" actually captured in the CRM, or is
`resolves` aspirational?),
`OQ-45` (link-graph and orphan analysis deliberately left to the KB evaluation
tooling — confirm that division of labour),
`OQ-46` (the AI assistants grounded in this documentation are out of scope for
now and will be modelled separately).
