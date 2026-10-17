# Partner

**Class ID:** `sup:Partner`
**Type:** Customer
**Status:** Proposed
**Version:** 0.1.0

## Definition
An Independent Software Vendor (ISV) or partner organization that represents one or more accounts. Partners can submit and manage support tickets on behalf of the customers they represent.

## Canonical name and aliases
| Context | Term used |
|---|---|
| Canonical | Partner |
| CRM | Partner / ISV |

## Identity rule
The CRM partner ID is authoritative.

## Datatype properties
| Property | Type | Required | Notes |
|---|---|---|---|
| `partnerId` | string | Yes | CRM primary key for the partner |
| `partnerName` | string | Yes | Legal or trading name of the partner |
| `partnershipLevel` | string | No | E.g., Gold, Silver |

## Object properties
| Property | Target | Cardinality | Inverse |
|---|---|---|---|
| `represents` | `sup:Account` | `0..*` | `isRepresentedBy` |
| `raisesOnBehalfOf` | `sup:Ticket` | `0..*` | `submittedByPartner` |

## Subclasses and individuals
None.

## Disjoint with
`sup:Account`, `sup:Contact`. A partner represents an account but is not the account itself.

## Constraints
- `C-57` — A Ticket raised by a Partner must belong to an Account that the Partner represents.

## Provenance
| Source system | What it supplies | Authoritative for |
|---|---|---|
| CRM | Partner record and relationships | `partnerId`, `partnerName` |

## Competency questions answered
`CQ-32`

## Open questions
`OQ-49` (Are there cases where a single ticket is co-managed by both Partner and Account Contacts?)
