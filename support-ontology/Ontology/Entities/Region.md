# Region

**Class ID:** `sup:Region`
**Type:** Customer
**Status:** Canonical
**Version:** 0.1.0

## Definition
A geographic territory used to distribute accounts and assign commercial and
support coverage. Regions determine which sales representative owns an account
and which support team's working hours apply to its tickets.

## Canonical name and aliases
| Context | Term used |
|---|---|
| Canonical | Region |
| Sales operations | Territory |
| Support scheduling | Geo, Coverage zone |

## Identity rule
Natural key: the region code (`EMEA`, `NA`, `APAC`, `LATAM`). Codes are stable
and never reused.

## Datatype properties
| Property | Type | Required | Notes |
|---|---|---|---|
| `regionCode` | string | Yes | Short stable code |
| `regionName` | string | Yes | Display name |
| `timeZoneRange` | string | No | Used to derive support coverage hours |

## Object properties
| Property | Target | Cardinality | Inverse |
|---|---|---|---|
| `isRegionOf` | `sup:Account` | `0..*` | `isLocatedIn` |
| `isCoveredBy` | `sup:SalesRepresentative` | `1..*` | `covers` |

## Subclasses and individuals
Flat closed set:
- `EMEA` — Europe, Middle East and Africa
- `NA` — North America
- `APAC` — Asia Pacific
- `LATAM` — Latin America

Regions are deliberately **flat**. Sub-regions (DACH, Benelux, ANZ) are not
modelled: the support organization assigns coverage and routes tickets at the
top level, so a hierarchy would add traversal cost without answering a question
anyone asks. If regional roll-ups are ever needed below this level, that is a
new modelling decision — see `OQ-41`.

## Disjoint with
None.

## Constraints
- `C-10` — every Region has at least one SalesRepresentative covering it.

## Provenance
| Source system | What it supplies | Authoritative for |
|---|---|---|
| Salesforce | Territory assignment on the account | `regionCode` per account |
| Sales operations spreadsheet | Region definitions and rep coverage | Region set, coverage map |

## Competency questions answered
`CQ-01`, `CQ-05`, `CQ-14`, `CQ-19`

## Open questions
`OQ-05` — whether region is a property of the account or of the license.
Multinational customers may hold licenses in several regions.
`OQ-41` — regions are flat by decision. Revisit only if a real reporting need
for sub-regional roll-ups appears.
