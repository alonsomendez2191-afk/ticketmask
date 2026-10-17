# Escalation

**Class ID:** `sup:Escalation`
**Type:** Support
**Status:** Canonical
**Version:** 0.1.0

## Definition
The act of a support agent referring a ticket to development because it has been
identified as a defect or as a request for new functionality. The Escalation
produces a Jira issue and is the only legitimate way a Jira ID becomes
associated with a ticket.

**Why this is its own class.** It would be simpler to draw a direct line from
Ticket to JiraIssue. But the escalation carries its own facts — who escalated,
when, on what grounds, whether it was accepted, and whether the resulting issue
was a bug or an enhancement. Those facts belong to the escalation event, not to
the ticket and not to the Jira issue. This is a reified relationship: a
relationship promoted to a class because it has properties of its own.

## Canonical name and aliases
| Context | Term used |
|---|---|
| Canonical | Escalation |
| Agent conversation | Bug report, Dev handoff, "raising a Jira" |
| CRM | Escalation flag, Escalated case |

Note: "escalation" is also used loosely to mean *raising a ticket's severity* or
*involving a manager*. Those are different actions and are **not** this class.
See `OQ-21`.

## Identity rule
Surrogate: generated UUID. There is no natural key — the same ticket can be
escalated more than once, and the same Jira issue can receive escalations from
many tickets.

## Datatype properties
| Property | Type | Required | Notes |
|---|---|---|---|
| `escalationId` | uuid | Yes | Surrogate key |
| `escalationType` | enum(Bug, Enhancement) | Yes | The agent's classification |
| `escalatedAt` | datetime | Yes | |
| `justification` | text | Yes | Why the agent judged this a dev matter |
| `wasAccepted` | boolean | No | Whether development accepted the classification |
| `reproductionSteps` | text | No | Expected for Bug type |

## Object properties
| Property | Target | Cardinality | Inverse |
|---|---|---|---|
| `originatesFrom` | `sup:Ticket` | `1..1` | `escalatedAs` |
| `producedIssue` | `sup:JiraIssue` | `1..1` | `raisedBy` |
| `escalatedBy` | `sup:SupportAgent` | `1..1` | `escalates` |

## Subclasses and individuals
None. `escalationType` carries the Bug / Enhancement distinction rather than
subclassing, because the two share every property and differ only in
classification — and because the classification can be corrected after the fact.

## Disjoint with
`sup:Ticket`, `sup:JiraIssue`. The escalation is the link between them, not
either end of it.

## Constraints
- `C-05` — a Ticket may only carry a Jira reference through an Escalation.
- `C-06` — a Ticket with `status = Escalated` has at least one open Escalation.
- `C-27` — every Escalation produces exactly one JiraIssue, and the issue's
  `issueType` must match the escalation's `escalationType` at creation time. If
  development later reclassifies the Jira issue, the escalation retains the
  agent's original classification — that divergence is a signal worth reporting,
  not an error to overwrite.
- `C-28` — an Escalation of type Bug should have `reproductionSteps`. Advisory,
  not blocking.
- `C-29` — only a SupportAgent may create an Escalation.

## Provenance
| Source system | What it supplies | Authoritative for |
|---|---|---|
| CRM | Escalation record on the case, agent identity | `escalatedAt`, `escalatedBy`, `justification` |
| Jira | The resulting issue key, acceptance | `producedIssue`, `wasAccepted` |

## Competency questions answered
`CQ-11`, `CQ-15`, `CQ-17`, `CQ-18`, `CQ-19`, `CQ-23`, `CQ-27`

## Open questions
`OQ-21` (severity escalation and management escalation are different actions —
do they need their own classes?), `OQ-22` (de-escalation and rejected
escalations — how is a rejected classification represented?).
