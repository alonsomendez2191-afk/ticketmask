# CustomerSuccessManager

**Class ID:** `sup:CustomerSuccessManager`
**Type:** Customer
**Status:** Canonical
**Version:** 0.1.0

## Definition
An internal individual assigned to accounts considered valuable, with
responsibility for adoption, retention and relationship health. Unlike the sales
representative, CSM assignment is **conditional** — most accounts do not have
one.

## Canonical name and aliases
| Context | Term used |
|---|---|
| Canonical | CustomerSuccessManager |
| Everyday use | CSM |
| Salesforce | Customer Success Manager, Success owner |
| Some teams | TAM, Technical account manager (**may be a distinct role — `OQ-36`**) |

## Identity rule
The CRM user ID is authoritative.

## Datatype properties
| Property | Type | Required | Notes |
|---|---|---|---|
| `csmId` | string | Yes | CRM user ID |
| `isActive` | boolean | Yes | Currently holding the role |

## Object properties
| Property | Target | Cardinality | Inverse |
|---|---|---|---|
| `supports` | `sup:Account` | `0..*` | `hasCSM` |

## Subclasses and individuals
None.

## Disjoint with
`sup:SupportAgent` and `sup:SalesRepresentative` — three distinct jobs.
See `C-52`.

## Constraints
- `C-08` — an Account may only have a CSM if `isStrategic = true`. This encodes
  "they might also have a CSM assigned if they are considered a valuable
  account". Note the direction: being strategic permits a CSM, it does not
  require one. An account can be strategic and still awaiting assignment.
- `C-47` — an Account has at most one CSM.

## Provenance
| Source system | What it supplies | Authoritative for |
|---|---|---|
| CRM | CSM field on the account | `supports` |
| Customer success operations | Assignment criteria and book of business | Coverage rules |

## Competency questions answered
`CQ-05`, `CQ-14`, `CQ-22`

## Open questions
`OQ-36` (is TAM the same role or a distinct one?), `OQ-37` (what actually
determines `isStrategic` — revenue, entitlement tier, or a manual flag? The
ontology currently treats it as a given fact rather than a derived one).
