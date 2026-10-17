# Contact

**Class ID:** `sup:Contact`
**Type:** Customer
**Status:** Canonical
**Version:** 0.2.1

> **Confirmed 2026-08-20** (`OQ-01`). Originally inferred rather than stated,
> now kept as a class: an organization does not fill in a support form, and
> "which contacts open the most tickets" and "is this person authorised to raise
> a ticket" are both real questions.

## Definition
An individual person at a customer account who is authorised to raise support
tickets and use self-service tools. A Contact is a person in their capacity as a
customer representative. Internal staff are modelled as `sup:SupportAgent`,
`sup:SalesRepresentative` or `sup:CustomerSuccessManager`.

## Canonical name and aliases
| Context | Term used |
|---|---|
| Canonical | Contact |
| Salesforce | Contact |
| Ticket forms | Requester, Reporter, Submitter |

## Identity rule
CRM contact ID is authoritative.

## Datatype properties
| Property | Type | Required | Notes |
|---|---|---|---|
| `contactId` | string | Yes | CRM primary key |
| `emailAddress` | string | Yes | Also the join key to ticket submissions |
| `isSupportAuthorised` | boolean | Yes | Whether this contact may open tickets |
| `isPrimary` | boolean | No | Primary technical contact for the account |

## Object properties
| Property | Target | Cardinality | Inverse |
|---|---|---|---|
| `worksFor` | `sup:Account` | `1..1` | `hasContact` |
| `submits` | `sup:Ticket` | `0..*` | `submittedBy` |

## Subclasses and individuals
None.

## Disjoint with
`sup:Account` — an organization is not a person. Also disjoint with the internal
role classes: a Contact acts for the customer, an agent or rep acts for us.

## Constraints
- `C-15` — every Contact belongs to exactly one Account.
- `C-16` — a Ticket's submitting Contact must belong to the Ticket's Account.
  A mismatch is a data integrity error worth alerting on.
- `C-17` — only a Contact with `isSupportAuthorised = true` may submit a Ticket.

## Provenance
| Source system | What it supplies | Authoritative for |
|---|---|---|
| CRM | Contact record, authorisation flag | All contact facts |

## Competency questions answered
`CQ-06`

## Open questions
`OQ-01` 🟢 resolved 2026-08-20 — class confirmed. See `06-Open-Questions.md`.
`OQ-49` — can a partner contact and an account contact co-manage one ticket?
