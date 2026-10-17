# SalesRepresentative

**Class ID:** `sup:SalesRepresentative`
**Type:** Customer
**Status:** Canonical
**Version:** 0.1.0

## Definition
An internal individual who commercially owns a set of accounts. Assignment is
driven by region: an account's sales representative is drawn from the
representatives covering that account's region.

## Canonical name and aliases
| Context | Term used |
|---|---|
| Canonical | SalesRepresentative |
| Salesforce | Account owner, Owner |
| Sales team | AE, Account executive, Rep |
| Renewals | Renewal owner (**may be a different person — see `OQ-34`**) |

## Identity rule
The CRM user ID is authoritative.

## Datatype properties
| Property | Type | Required | Notes |
|---|---|---|---|
| `repId` | string | Yes | CRM user ID |
| `isActive` | boolean | Yes | Currently holding the role |

## Object properties
| Property | Target | Cardinality | Inverse |
|---|---|---|---|
| `manages` | `sup:Account` | `0..*` | `hasSalesRep` |
| `covers` | `sup:Region` | `1..*` | `isCoveredBy` |

## Subclasses and individuals
None.

## Disjoint with
`sup:SupportAgent` and `sup:CustomerSuccessManager` — three distinct jobs.
See `C-52`.

## Constraints
- `C-07` — every Account has exactly one SalesRepresentative.
- `C-10` — every Region has at least one SalesRepresentative covering it.
- `C-46` — an Account's SalesRepresentative must cover the Account's Region.
  This is the machine-readable form of "assigned depending on the region", and
  it is the check most likely to fail against real data after a territory
  reshuffle.

## Provenance
| Source system | What it supplies | Authoritative for |
|---|---|---|
| CRM | Account ownership | `manages` |
| Sales operations territory model | Region coverage | `covers` |

## Competency questions answered
`CQ-05`, `CQ-19`, `CQ-22`

## Open questions
`OQ-34` (is the renewal owner always the same person as the account owner?),
`OQ-35` (can an account be owned by a rep outside its region as a documented
exception, and if so how is that recorded?).
