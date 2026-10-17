# License

**Class ID:** `sup:License`
**Type:** Customer
**Status:** Canonical
**Version:** 0.1.0

## Definition
A grant of the right to use a specific product, held by a specific account, for
a defined period and quantity. The license is what makes a support request
legitimate: an account may only raise tickets about products it is licensed for.

## Canonical name and aliases
| Context | Term used |
|---|---|
| Canonical | License |
| Salesforce | Asset |
| Licensing system | Entitlement key, Serial |
| Renewals reporting | Subscription |

Note the collision: Salesforce uses "Entitlement" for the **support tier**, and
"Asset" for the license. Do not let the word "entitlement" cross between
`sup:SupportEntitlement` and `sup:License`.

## Identity rule
Composite: `accountId` + `productId` + `startDate`. A renewal produces a new
License instance rather than mutating the existing one, so that historical
coverage questions stay answerable.

## Datatype properties
| Property | Type | Required | Notes |
|---|---|---|---|
| `licenseKey` | string | Yes | Licensing system identifier |
| `seatCount` | integer | No | Null for unlimited or site licenses |
| `startDate` | date | Yes | |
| `endDate` | date | No | Null = perpetual |
| `isActive` | boolean | Yes | Derived: `endDate` is null or in the future |
| `licenseType` | enum(Subscription, Perpetual, Trial, NFR) | Yes | |

## Object properties
| Property | Target | Cardinality | Inverse |
|---|---|---|---|
| `isHeldBy` | `sup:Account` | `1..1` | `holdsLicense` |
| `grantsAccessTo` | `sup:Product` | `1..1` | `isLicensedBy` |
| `isBoundTo` | `sup:SupportEntitlement` | `1..1` | `binds` |

## Subclasses and individuals
None. `licenseType` carries the distinction.

## Disjoint with
`sup:SupportEntitlement`. A license grants product usage; an entitlement grants
service level. They are routinely conflated in conversation and must not be
conflated here.

## Constraints
- `C-09` — an Active account holds at least one active License.
- `C-53` — every License is bound to exactly one SupportEntitlement.
- `C-54` — a License's entitlement should match its Account's entitlement. Soft.
- `C-13` — `endDate`, when present, must be later than `startDate`.
- `C-14` — a Ticket's product must be covered by an active License held by the
  ticket's account at the time the ticket was opened. Violations are legitimate
  support scenarios (out-of-maintenance customers) and must be *flagged*, not
  rejected — see `OQ-09`.

## Provenance
| Source system | What it supplies | Authoritative for |
|---|---|---|
| Licensing system | License keys, seats, dates | All license facts |
| CRM | Asset records mirrored from licensing | Nothing — mirror only |

## Competency questions answered
`CQ-04`, `CQ-09`, `CQ-13`, `CQ-22`, `CQ-29`

## Open questions
`OQ-42` — entitlement is bound to both the Account and the License. If the two
ever disagree, one of them is the wrong place for it.
`OQ-09` — how to represent tickets from accounts whose license has lapsed.
`OQ-10` — whether trial licenses carry any support entitlement at all.
