# CRM

**Class ID:** `sup:CRM`
**Type:** Support
**Status:** Canonical
**Version:** 0.2.1

> Class confirmed (`OQ-38`). The individuals table below is a template —
> enumerate your organization's real CRM instances there. See `OQ-50`.

## Definition
A customer relationship management system that records tickets. Each distinct
CRM instance is a distinct instance of this class, because each carries its own
ticket numbering, its own user records, and — critically — its own vocabulary.

The CRM is modelled for two reasons: **identity**, because ticket numbers are
unique within a CRM and not across them, and **vocabulary**, because the CRM is
what determines whether a support request is called a ticket or a case.

## Canonical name and aliases
| Context | Term used |
|---|---|
| Canonical | CRM |
| CRM administration | Org, Instance, Tenant |
| Data engineering | Source, System of record, Upstream |
| Everyday use | Salesforce, "the system" |

## Identity rule
Natural key: the system code (e.g. `SF_EMEA`, `SF_AMER`). Each org is a
separate instance even when several orgs run on the same platform, because the
ID spaces and the vocabulary do not carry across.

## Datatype properties
| Property | Type | Required | Notes |
|---|---|---|---|
| `systemCode` | string | Yes | Stable short code |
| `systemName` | string | Yes | |
| `ticketTermUsed` | enum(Ticket, Case) | Yes | **The alias anchor for `EQ-01`** |
| `isAuthoritative` | boolean | Yes | Whether this system is the source of truth or a mirror |

## Object properties
| Property | Target | Cardinality | Inverse |
|---|---|---|---|
| `records` | `sup:Ticket` | `0..*` | `recordedIn` |

## Subclasses and individuals
Template rows. Replace with the organization's real instances.

| `systemCode` | `systemName` | `ticketTermUsed` | `isAuthoritative` | Source of this entry |
|---|---|---|---|---|
| `SF` | Salesforce | **Case** | Yes | Example: `Case` is the platform's own object name |
| `ZD` | Zendesk | **Ticket** | Yes | Example: `Ticket` is the platform's own object name |

**`ticketTermUsed` is the alias anchor for `EQ-01`** and `C-50` requires every
CRM to declare it. Populate it from the platform's own object name or the
org's field labels. Mark a value *Unconfirmed* rather than guessing — an alias
map populated from assumption is worse than one that is visibly incomplete.

## Disjoint with
All domain classes. A CRM is a system that holds facts about the organization,
not a part of the organization itself.

## Constraints
- `C-48` — every Ticket is recorded in exactly one CRM. This is what makes
  ticket identity unambiguous: full identity is `systemCode` + `ticketNumber`.
- `C-49` — a fact from a CRM with `isAuthoritative = false` must not override a
  fact from an authoritative system for the same property. Mirrors lag; the
  licensing system beats the CRM's copy of a license every time.
- `C-50` — every CRM declares `ticketTermUsed`. A system whose vocabulary is
  unknown cannot have its records safely translated.

## Provenance
| Source system | What it supplies | Authoritative for |
|---|---|---|
| Integration inventory | The list of CRM instances | System set |
| CRM administration | Org configuration and field labels | `ticketTermUsed` |
| This ontology | Trust ranking | `isAuthoritative` |

## Competency questions answered
`CQ-07`, `CQ-18`

## Open questions
`OQ-38` 🟢 resolved — class confirmed.
`OQ-50` — enumerate the organization's CRM instances and populate
`ticketTermUsed` for each.
`OQ-39` (vocabulary is now anchored on both the CRM and the Product — what
happens when they disagree?).
`OQ-18` (ticket number collisions across instances — now concrete, with more
than one system confirmed).
