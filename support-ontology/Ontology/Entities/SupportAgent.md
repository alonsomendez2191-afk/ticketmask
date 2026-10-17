# SupportAgent

**Class ID:** `sup:SupportAgent`
**Type:** Support
**Status:** Canonical
**Version:** 0.1.0

## Definition
An internal member of the support organization who is assigned tickets, resolves
them using documentation, and escalates to development when a ticket is caused
by a defect or requires new functionality.

## Canonical name and aliases
| Context | Term used |
|---|---|
| Canonical | SupportAgent |
| CRM | Case owner, Assigned to, Owner |
| Team language | Support engineer, Technical support, Analyst |
| Tiered teams | T1, T2, T3 agent |

## Identity rule
The CRM user ID is authoritative. Agents appearing in more than one CRM are
matched on corporate email.

## Datatype properties
| Property | Type | Required | Notes |
|---|---|---|---|
| `agentId` | string | Yes | CRM user ID |
| `tier` | enum(T1, T2, T3) | No | Support tier, where the team is tiered |
| `isActive` | boolean | Yes | Currently holding the role |

## Object properties
| Property | Target | Cardinality | Inverse |
|---|---|---|---|
| `handles` | `sup:Ticket` | `0..*` | `assignedTo` |
| `escalates` | `sup:Escalation` | `0..*` | `escalatedBy` |
| `consults` | `sup:Documentation` | `0..*` | `isConsultedBy` |
| `specialisesIn` | `sup:Product` | `0..*` | `isSupportedBy` |
| `measuredAgainst` | `sup:SLA` | `0..*` | `measures` |

## Subclasses and individuals
None. `tier` carries the seniority distinction.

## Disjoint with
`sup:Contact` — an agent acts for us, a contact acts for the customer. Also
disjoint with `sup:SalesRepresentative` and `sup:CustomerSuccessManager`:
these are three distinct jobs. See `C-52`.

## Constraints
- `C-29` — only a SupportAgent may create an Escalation.
- `C-52` — SupportAgent, SalesRepresentative and CustomerSuccessManager are
  pairwise disjoint.
- `C-31` — a Ticket may be assigned to at most one SupportAgent at a time.
  Reassignment replaces the assignment; history is not modelled (`OQ-16`).
- `C-32` — an inactive agent (`isActive = false`) must not hold open tickets.
  Violations are a real operational problem worth alerting on.

## Provenance
| Source system | What it supplies | Authoritative for |
|---|---|---|
| CRM | User record, case ownership | `agentId`, `handles` |
| Support team structure | Tier and product specialisation | `tier`, `specialisesIn` |

## Competency questions answered
`CQ-10`, `CQ-12`, `CQ-15`, `CQ-16`, `CQ-18`, `CQ-30`

## Open questions
`OQ-16` (assignment history not modelled), `OQ-23` (does an agent's product
specialisation come from routing configuration or is it informal?),
`OQ-48` (SLA timers — business hours or calendar hours — which decides whether
an agent actually breached).
