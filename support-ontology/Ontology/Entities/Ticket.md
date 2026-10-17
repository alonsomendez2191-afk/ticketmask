# Ticket

**Class ID:** `sup:Ticket`
**Type:** Support
**Status:** Canonical
**Version:** 0.1.0

## Definition
A single recorded request for support from a customer account, tracked from
submission to resolution. One ticket represents one customer problem. It is
owned by exactly one account, assigned to at most one agent at a time, carries
exactly one severity, is governed by exactly one SLA, and may be escalated to
development. It may be submitted by a Contact at the account or, where the
customer buys through one, by a Partner acting on the account's behalf.

**Naming:** some CRM systems call this a *Case*. Ticket and Case are the same
class — they are not related classes, not parent and child, and not similar
things. They are the same thing under two labels. See `EQ-01`.

## Canonical name and aliases
| Context | Term used |
|---|---|
| Canonical | Ticket |
| CRM systems using Case terminology | **Case** |
| ITSM-influenced teams | Incident |
| Older systems | SR, Service Request |

Which label a given system uses is recorded on `sup:CRM.ticketTermUsed`, not
guessed.

## Identity rule
The CRM ticket/case number is authoritative. Ticket numbers are unique within a
CRM but **not** across CRMs — a fully qualified ticket identity is
`systemCode` + `ticketNumber`. This is a real collision risk in reporting.

## Datatype properties
| Property | Type | Required | Notes |
|---|---|---|---|
| `ticketNumber` | string | Yes | CRM case number |
| `subject` | string | Yes | |
| `status` | enum(New, Open, Pending, Escalated, Resolved, Closed) | Yes | |
| `openedAt` | datetime | Yes | |
| `resolvedAt` | datetime | No | Required when status is Resolved or Closed |
| `resolutionSummary` | text | No | |

## Object properties
| Property | Target | Cardinality | Inverse |
|---|---|---|---|
| `belongsTo` | `sup:Account` | `1..1` | `raises` |
| `submittedBy` | `sup:Contact` | `0..1` | `submits` |
| `submittedByPartner` | `sup:Partner` | `0..1` | `raisesOnBehalfOf` |
| `assignedTo` | `sup:SupportAgent` | `0..1` | `handles` |
| `hasSeverity` | `sup:SeverityLevel` | `1..1` | `appliesTo` |
| `isGovernedBy` | `sup:SLA` | `1..1` | `governs` |
| `concerns` | `sup:Product` | `1..1` | `isSubjectOf` |
| `escalatedAs` | `sup:Escalation` | `0..*` | `originatesFrom` |
| `resolvedUsing` | `sup:Documentation` | `0..*` | `resolves` |
| `recordedIn` | `sup:CRM` | `1..1` | `records` |

## Subclasses and individuals
None. Ticket type distinctions (question vs defect vs request) are captured by
the presence and type of an `Escalation`, not by subclassing the ticket.

## Disjoint with
`sup:JiraIssue`. A ticket is a customer's request; a Jira issue is an internal
work item. They are linked through an Escalation and are routinely confused —
"the ticket is fixed" and "the bug is fixed" are different statements.

## Constraints
- `C-04` — every Ticket has exactly one Account, one SeverityLevel and one
  Product.
- `C-05` — a Ticket may carry a Jira ID **only** through an Escalation. A ticket
  with a Jira reference and no escalation record is invalid.
- `C-06` — a Ticket with `status = Escalated` must have at least one open
  Escalation.
- `C-16` — the submitting Contact must belong to the Ticket's Account.
- `C-24` — `resolvedAt` is required when status is Resolved or Closed, and must
  not precede `openedAt`.
- `C-56` — Every Ticket has exactly one SLA.
- `C-57` — A Ticket raised by a Partner must belong to an Account that the Partner represents.

## Provenance
| Source system | What it supplies | Authoritative for |
|---|---|---|
| CRM | The ticket record and all its fields | Everything except escalation links |
| Jira | Escalation linkage confirmation | Nothing on the ticket directly |

## Competency questions answered
`CQ-01`, `CQ-02`, `CQ-03`, `CQ-06`, `CQ-08`, `CQ-10`, `CQ-11`, `CQ-15`,
`CQ-17`, `CQ-18`, `CQ-23`, `CQ-26`, `CQ-27`, `CQ-30`, `CQ-31`, `CQ-32`

## Open questions
`OQ-16` (ticket reassignment history — we model the current agent only),
`OQ-17` (are there ticket types we should model explicitly?),
`OQ-18` (cross-org ticket number collisions in reporting),
`OQ-48` (SLA timers — business hours or calendar hours?),
`OQ-49` (can a Partner-raised ticket also be engaged by the account's Contact?).
