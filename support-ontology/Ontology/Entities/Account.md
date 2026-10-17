# Account

**Class ID:** `sup:Account`
**Type:** Customer
**Status:** Canonical
**Version:** 0.1.0

## Definition
A commercial customer organization that holds one or more licenses to our
products and is entitled to receive support. The Account is the unit that
entitlement, licensing, regional assignment and commercial ownership all hang
off. An Account is an organization, never an individual person — the people at
an account are modelled as `sup:Contact`.

## Canonical name and aliases
| Context | Term used |
|---|---|
| Canonical | Account |
| Salesforce | Account |
| Informal / internal speech | Customer |
| Some reporting | Organization, Org |

## Identity rule
The CRM account ID is authoritative. Where an organization exists as multiple
account records across brand-specific CRM orgs, they are the same `sup:Account`
only if they share a resolved parent organization ID. See `OQ-03` — account
de-duplication across brand orgs is unresolved.

## Datatype properties
| Property | Type | Required | Notes |
|---|---|---|---|
| `accountId` | string | Yes | CRM primary key |
| `accountName` | string | Yes | Legal or trading name |
| `isStrategic` | boolean | No | Drives CSM eligibility — see `C-08` |
| `accountStatus` | enum(Active, Lapsed, Churned) | Yes | Lapsed = no active license |
| `createdAt` | date | Yes | First became a customer |

## Object properties
| Property | Target | Cardinality | Inverse |
|---|---|---|---|
| `isLocatedIn` | `sup:Region` | `1..1` | `isRegionOf` |
| `hasEntitlement` | `sup:SupportEntitlement` | `1..1` | `entitles` |
| `holdsLicense` | `sup:License` | `0..*` | `isHeldBy` |
| `raises` | `sup:Ticket` | `0..*` | `belongsTo` |
| `hasSalesRep` | `sup:SalesRepresentative` | `1..1` | `manages` |
| `hasCSM` | `sup:CustomerSuccessManager` | `0..1` | `supports` |
| `hasContact` | `sup:Contact` | `0..*` | `worksFor` |
| `isRepresentedBy` | `sup:Partner` | `0..*` | `represents` |

## Subclasses and individuals
None. Account is a flat class; `isStrategic` and `accountStatus` carry the
distinctions that might otherwise tempt us into subclassing.

## Disjoint with
`sup:Contact` and the internal role classes. An account is an organization; it
is never a person, even when the customer is a sole trader with one named
contact.

## Constraints
- `C-01` — every Account has exactly one Region.
- `C-02` — every Account has exactly one SupportEntitlement.
- `C-07` — every Account has exactly one SalesRepresentative.
- `C-08` — an Account may only have a CSM if `isStrategic` is true.
- `C-09` — an Account with `accountStatus = Active` must hold at least one
  License with an unexpired end date.

## Provenance
| Source system | What it supplies | Authoritative for |
|---|---|---|
| CRM | Account record, region, ownership | `accountId`, `accountName`, `isStrategic` |
| Licensing system | Active license set | `accountStatus` (derived) |

## Competency questions answered
`CQ-01`, `CQ-02`, `CQ-03`, `CQ-05`, `CQ-11`, `CQ-14`, `CQ-19`, `CQ-22`,
`CQ-29`

## Open questions
`OQ-03` (cross-system de-duplication), `OQ-04` (account hierarchies — parent/child
for enterprise customers is not modelled), `OQ-42` (entitlement is bound to both
the Account and its Licenses).
