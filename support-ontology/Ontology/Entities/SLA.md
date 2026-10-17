# SLA

**Class ID:** `sup:SLA`
**Type:** Support
**Status:** Proposed
**Version:** 0.1.0

## Definition
The Service Level Agreement that governs a ticket, dictating the target times for response and resolution. An SLA is determined by the severity of the ticket and the entitlement of the customer account. Support agents are measured against their ability to meet these SLA targets.

## Canonical name and aliases
| Context | Term used |
|---|---|
| Canonical | SLA |
| CRM | Service Level Agreement |
| ITSM | SLA |

## Identity rule
A composite of `severityLevel` + `entitlementTier`.

## Datatype properties
| Property | Type | Required | Notes |
|---|---|---|---|
| `slaName` | string | Yes | E.g., "Premium S1" |
| `targetResponseMinutes` | integer | Yes | |
| `targetResolutionMinutes` | integer | Yes | |

## Object properties
| Property | Target | Cardinality | Inverse |
|---|---|---|---|
| `governs` | `sup:Ticket` | `0..*` | `isGovernedBy` |
| `measures` | `sup:SupportAgent` | `0..*` | `measuredAgainst` |

## Subclasses and individuals
None.

## Disjoint with
`sup:Ticket`, `sup:SeverityLevel`, `sup:SupportEntitlement`. An SLA is the rule, not the ticket itself or its priority.

## Constraints
- `C-56` — Every Ticket has exactly one SLA, which must align with its SeverityLevel and its Account's SupportEntitlement.

## Provenance
| Source system | What it supplies | Authoritative for |
|---|---|---|
| CRM | SLA matrix configuration | `targetResponseMinutes`, `targetResolutionMinutes` |

## Competency questions answered
`CQ-30`, `CQ-31`

## Open questions
`OQ-48` (How are business hours vs calendar hours calculated for SLAs?)
