# Product

**Class ID:** `sup:Product`
**Type:** Product
**Status:** Canonical
**Version:** 0.2.0

## Definition
A software product that customers license and raise support tickets about. The
Product is what a license grants access to, what a ticket concerns, and what
documentation describes. It is the join point between the commercial, support
and knowledge parts of the model.

Product is deliberately a **single flat level**. Brand and product-line
hierarchies exist commercially, but they sit outside the support organization
and modelling them added structure without answering a support question.

## Canonical name and aliases
| Context | Term used |
|---|---|
| Canonical | Product |
| Licensing system | SKU, Part number |
| Salesforce | Product2, Asset product |
| Support forms | Product, Component |
| KB tooling | Product, Product folder |
| Commercial reporting | Product line, Product family |

"Product line" is recorded here as an **alias**, not a separate class. Where
someone says "product line" in a support context they mean this class.

## Identity rule
The licensing system product ID is authoritative. Version is **not** part of
identity — a product and its versions are the same product. Version-specific
facts would need `sup:ProductVersion`, which is not modelled (`OQ-15`).

## Datatype properties
| Property | Type | Required | Notes |
|---|---|---|---|
| `productId` | string | Yes | Licensing system key |
| `productName` | string | Yes | |
| `currentVersion` | string | No | Latest generally available release |
| `lifecycleStatus` | enum(GA, Maintenance, EndOfLife) | Yes | EOL drives documentation retirement |
| `endOfLifeDate` | date | No | Required when `lifecycleStatus = EndOfLife` |
| `usesPlatinumNaming` | boolean | Yes | **True where Premium Support is sold as Platinum Support — alias anchor for `EQ-02`** |
| `severityTermUsed` | enum(Severity, Priority) | Yes | **Which word this product's support uses — alias anchor for `EQ-03`** |
| `documentationRootUrl` | string | No | Entry point for this product's KB |

The two vocabulary properties are the machine-readable form of "it depends on
the product". They are what lets an agent translate a question into a query and
translate the answer back into the asker's vocabulary.

Note that `severityTermUsed` sits here by necessity rather than by evidence: the
variation was originally described as varying *by brand*, and Brand is no longer
modelled. Product is the surviving axis. See `OQ-44`.

## Object properties
| Property | Target | Cardinality | Inverse |
|---|---|---|---|
| `isLicensedBy` | `sup:License` | `0..*` | `grantsAccessTo` |
| `isSubjectOf` | `sup:Ticket` | `0..*` | `concerns` |
| `isDescribedBy` | `sup:Documentation` | `0..*` | `describes` |
| `isSupportedBy` | `sup:SupportAgent` | `0..*` | `specialisesIn` |

## Subclasses and individuals
Populated per organization from the licensing system or the KB folder
structure. Placeholder examples: `ExampleAnalytics`, `ExampleDataWarehouse`,
`ExampleDesigner`.

Use family-level names (one per KB product folder) unless the organization
needs SKU-level granularity.
Whether the support organization needs SKU-level granularity underneath them is
`OQ-14`.

## Disjoint with
None.

## Constraints
- `C-22` — a Product with `lifecycleStatus = EndOfLife` must have an
  `endOfLifeDate`.
- `C-23` — documentation describing an EndOfLife product should be reviewed for
  retirement. Advisory; feeds the KB evaluation process.
- `C-51` — every Product declares `usesPlatinumNaming` and `severityTermUsed`.
  A product whose support vocabulary is unknown cannot have its tickets safely
  compared against another product's.

## Provenance
| Source system | What it supplies | Authoritative for |
|---|---|---|
| Licensing system | Product catalogue, SKUs | `productId`, `productName` |
| Product management | Lifecycle status and EOL dates | `lifecycleStatus`, `endOfLifeDate` |
| Release engineering | Current version | `currentVersion` |
| Pricing and packaging | Tier naming per product | `usesPlatinumNaming` |
| Support policy per product | Severity field naming | `severityTermUsed` |
| KB folder structure | Documentation grouping | `documentationRootUrl` |

## Competency questions answered
`CQ-04`, `CQ-07`, `CQ-08`, `CQ-09`, `CQ-12`, `CQ-13`, `CQ-16`, `CQ-22`,
`CQ-26`

## Open questions
`OQ-14` (is the KB folder list the right granularity, or do we need SKUs?),
`OQ-15` (product versions are not modelled),
`OQ-44` (severity naming was described as varying by brand; it is now anchored
on Product because Brand is out of scope — confirm that holds).
