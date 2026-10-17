# SeverityLevel

**Class ID:** `sup:SeverityLevel`
**Type:** Support
**Status:** Canonical
**Version:** 0.1.0

## Definition
The graded measure of a ticket's business impact and urgency, used to set
response expectations and routing. Every ticket has exactly one.

**Naming:** depending on the product, this is called *Severity* or *Priority*.
These are the same attribute under two labels. See `EQ-03`. The risk is
particularly sharp here because both words are also used loosely in conversation
to mean "how bad is it" — an agent must resolve the term against the product
before comparing values across products.

## Canonical name and aliases
| Context | Term used |
|---|---|
| Canonical | SeverityLevel |
| Products using severity naming | Severity, Sev |
| Products using priority naming | **Priority**, Pri |
| Escalation conversations | Impact, Urgency (informal, not a field) |

Which label a given product uses is recorded on `sup:Product.severityTermUsed`.

## Identity rule
Natural key: the canonical level code `S1`–`S4`. All product-specific labels
(`P1`, `Critical`, `High`, `1 - Urgent`) resolve to one of these four.

## Datatype properties
| Property | Type | Required | Notes |
|---|---|---|---|
| `levelCode` | enum(S1, S2, S3, S4) | Yes | Canonical code |
| `levelRank` | integer | Yes | 1 = most severe. Lower rank = more urgent |
| `levelName` | string | Yes | Canonical display name |
| `definition` | text | Yes | The impact test that puts a ticket at this level |

## Object properties
| Property | Target | Cardinality | Inverse |
|---|---|---|---|
| `appliesTo` | `sup:Ticket` | `0..*` | `hasSeverity` |

## Subclasses and individuals
Closed set of four individuals. **The definitions below are the organization's
single severity standard and apply to every product** (`OQ-19`).

| Canonical | Rank | Name | Common aliases |
|---|---|---|---|
| **S1** | 1 | System Down | P1, Critical, Urgent, 1 |
| **S2** | 2 | Work Stoppage | P2, High, 2 |
| **S3** | 3 | Medium | P3, Medium, Normal, 3 |
| **S4** | 4 | Low | P4, Low, Minor, 4 |

### `definition` — the impact test per level

These are **template definitions**. Replace them with your organization's own
support policy wording when you adopt the ontology; the structure (four ranked
levels, one impact test each) is what the rest of the model depends on.

**S1 — System Down.** A production environment is unavailable to all users, or
no user can sign in. Work has stopped. S1 handling assumes a customer contact is
available to troubleshoot; if nobody is, the ticket drops to S2.

**S2 — Work Stoppage.** Part of the product is unusable, or some users cannot
complete a critical task. Others can keep working, but a fix or workaround is
needed. A full outage of a non-production environment is also S2.

**S3 — Medium.** A problem that needs investigation or scheduled work but is
not stopping anyone. Resolution time is agreed with the customer.

**S4 — Low.** How-to questions, planned maintenance and upgrades, enhancement
requests and documentation issues. Usually closed on first contact.

### Who sets it, and when it changes
Support sets the severity. **The customer has the right to request an escalation
or de-escalation of a case**, and the S1 rule above de-escalates automatically
when the customer contact is unavailable.

Severity is therefore **mutable over a ticket's life**, by two named mechanisms.
The model currently stores only the current value — see `OQ-20`, which this
definition makes materially more important than it was.

**Do not compare severity values as raw strings across products.** "P1" and
"S1" are equal; "Priority 1" and "Severity 1" are equal. Because the standard is
now uniform, any product whose data does not resolve cleanly to S1–S4 is a data
conformance defect to be recorded, not a fifth level — see `OQ-51`.

## Disjoint with
None.

## Constraints
- `C-04` — every Ticket has exactly one SeverityLevel.
- `C-25` — the set of levels is closed at four. A product-specific value that
  does not resolve to S1–S4 is an alias gap to be recorded in
  `03-Vocabulary-and-Equivalence.md`, not a fifth level.
- `C-26` — comparisons and filters on severity must operate on `levelRank`,
  never on the customer-facing label.

## Provenance
| Source system | What it supplies | Authoritative for |
|---|---|---|
| CRM | The per-ticket value in the product's own vocabulary | Raw value only |
| This ontology | The canonical four levels and the alias map | `levelCode`, `levelRank` |
| Organization-wide support policy | Impact definitions | `definition` |

**Wording provenance.** The S1–S4 definitions above are generic templates
written for this open-source ontology. An adopting organization should replace
them with its own published support policy.

## Competency questions answered
`CQ-02`, `CQ-08`, `CQ-10`, `CQ-15`, `CQ-17`, `CQ-23`, `CQ-26`, `CQ-27`

## Open questions
`OQ-19` 🟢 resolved — one standard for all products, definitions above.
`OQ-51` — does every product's live CRM data actually conform to the four
levels? The standard is now set; conformance is unverified.
`OQ-20` — severity is confirmed mutable (customer request, and automatic S1→S2
de-escalation). Only the current value is stored; the history is not.
`OQ-44` (severity naming was described as varying by brand and is now anchored
on Product).
