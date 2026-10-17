# SupportEntitlement

**Class ID:** `sup:SupportEntitlement`
**Type:** Customer
**Status:** Canonical
**Version:** 0.1.0

## Definition
The tier of support service an account is entitled to receive. The tier governs
response time targets, escalation rights and channel access. Entitlement is a
property of the account, not of an individual ticket or license.

**This class is the primary reason the ontology exists.** The same tier is
called *Premium Support* for most products and *Platinum Support* for others.
An agent that treats those as two tiers will under-count the premium base.

## Canonical name and aliases
| Context | Term used |
|---|---|
| Canonical | SupportEntitlement |
| Most products | Support Level, Support Plan |
| Salesforce | Entitlement |
| Premium tier — most products | Premium Support |
| Premium tier — Platinum-naming products | **Platinum Support** |
| Standard tier | Standard Support, Basic (unverified) |

The tier-value aliases are listed here as well as in the individuals table
below, because "Platinum" is the term someone is most likely to arrive with and
it should be findable at the top of this file. See also
`03-Vocabulary-and-Equivalence.md` → `EQ-02`.

## Identity rule
Natural key: the canonical tier code (`STANDARD`, `PREMIUM`). Entitlement is a
controlled vocabulary, not a per-account record — the per-account fact is the
`hasEntitlement` link, and its effective dates live on the link.

## Datatype properties
| Property | Type | Required | Notes |
|---|---|---|---|
| `tierCode` | enum(STANDARD, PREMIUM) | Yes | Canonical code |
| `tierRank` | integer | Yes | Higher = more entitled. Standard 1, Premium 2 |
| `grantsEscalationRight` | boolean | Yes | Whether the tier may demand escalation |
| `responseTargetHours` | integer | No | Varies by severity — see `OQ-06` |

## Object properties
| Property | Target | Cardinality | Inverse |
|---|---|---|---|
| `entitles` | `sup:Account` | `0..*` | `hasEntitlement` |
| `binds` | `sup:License` | `0..*` | `isBoundTo` |

The entitlement attaches at **two** levels: to the Account (who the customer is)
and to the License (what they bought). Both are real. The tension between them
is `OQ-42` — see Constraints below.

## Subclasses and individuals
Closed set of two individuals:

| Canonical individual | `tierCode` | Aliases and where they are used |
|---|---|---|
| **Standard** | `STANDARD` | "Basic", "Included Support" — usage unverified, see `OQ-07` |
| **Premium** | `PREMIUM` | **"Platinum Support"** for the products that use that naming — see `sup:Product.usesPlatinumNaming`. Same tier, different label. |

Premium and Platinum are declared **equivalent**, not related. See
`03-Vocabulary-and-Equivalence.md` → `EQ-02`.

## Disjoint with
None — but the two individuals are mutually exclusive per account at a given
time. See `C-02`.

## Constraints
- `C-02` — an Account has exactly one SupportEntitlement at any point in time.
- `C-11` — the set of tiers is closed. A value that is neither STANDARD nor
  PREMIUM after alias resolution is a data error, not a new tier.
- `C-12` — `grantsEscalationRight` is true only for PREMIUM.
- `C-53` — every License is bound to exactly one SupportEntitlement.
- `C-54` — a License's entitlement should match its Account's entitlement.
  **Soft, deliberately.** If an account holds licenses at different tiers, then
  entitlement is really a property of the license and `C-02` is wrong. Flagging
  rather than rejecting means the first real violation tells us which model is
  right, instead of the data being silently reshaped to fit our guess.

## Provenance
| Source system | What it supplies | Authoritative for |
|---|---|---|
| CRM | Entitlement field on account | Per-account tier |
| Support policy documentation | Tier definitions and response targets | `responseTargetHours` |

## Competency questions answered
`CQ-02`, `CQ-03`, `CQ-11`, `CQ-19`, `CQ-23`, `CQ-27`, `CQ-29`

## Open questions
`OQ-06` (response targets vary by severity — should the target be modelled on
the tier/severity pair?), `OQ-07` (is "Basic" a real label anywhere?),
`OQ-08` (are there tiers above Premium — e.g. a named-engineer tier?),
`OQ-42` (entitlement is now bound to both the Account and the License).
