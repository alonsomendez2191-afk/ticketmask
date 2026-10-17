# Conventions

**Version:** 0.2.0
**Last updated:** 2026-08-05

Read this before adding or editing anything in `Ontology/`.

---

## 1. Naming

| Thing | Style | Example |
|---|---|---|
| Class | `PascalCase`, singular noun | `SupportAgent`, `JiraIssue` |
| Object property | `camelCase`, verb phrase | `isLocatedIn`, `escalatedAs` |
| Datatype property | `camelCase`, noun | `accountName`, `openedAt` |
| Individual | `PascalCase` or code | `Premium`, `S1` |
| File | `PascalCase.md`, matches class | `Entities/SupportAgent.md` |

**Classes are singular.** `Ticket`, not `Tickets`. The class describes one
thing; the cardinality declaration handles quantity.

**Object properties are verbs, read left to right.** The property name must make
a readable sentence with its domain and range:
`Account isLocatedIn Region` ✅
`Account regionLink Region` ❌

**Boolean datatype properties start with `is` or `has`.** `isStrategic`,
`hasActiveMaintenance`.

## 2. Identifiers

Every class declares an **identity rule**: the property or combination of
properties that makes two records the same real-world thing.

| Rule type | Use when | Example |
|---|---|---|
| System key | One system is authoritative | `Ticket` → CRM case number |
| Composite | Identity spans systems | `License` → accountId + productId + startDate |
| Natural | The value is inherently unique | `Region` → region code |
| Surrogate | No stable natural key exists | `Escalation` → generated UUID |

Identity rules matter more than they look. If two systems both hold accounts and
we cannot say when two account records are the same account, every downstream
count is wrong.

Namespace-qualified IDs use the prefix `sup:` — e.g. `sup:Ticket`,
`sup:isLocatedIn`.

## 3. Status values

| Status | Meaning |
|---|---|
| `Canonical` | Confirmed against the real organization. Safe to ground an agent on. |
| `Proposed` | Inferred or drafted, not yet confirmed by a domain owner. Must have an entry in `06-Open-Questions.md`. |
| `Deprecated` | Superseded. Keep the file, record the replacement, do not delete. |

## 4. Cardinality notation

Written as `min..max` on the **range** side of a relationship.

| Notation | Meaning |
|---|---|
| `1..1` | Exactly one. Required, single. |
| `0..1` | At most one. Optional, single. |
| `1..*` | At least one. Required, many. |
| `0..*` | Any number. Optional, many. |

Always state both directions. `Account raises Ticket` is `0..*`, while its
inverse `Ticket belongsTo Account` is `1..1` — a ticket without an account is
invalid data, an account without tickets is a good customer.

**Self-referencing properties need both rows in the same file.** If a class
points at itself, its inverse has nowhere else to be declared. This is easy to
forget and `validate_ontology.py` check 4 exists to catch it.

## 5. Entity file template

Copy this exactly. Every heading must be present. If a section is empty, write
`None.` — do not delete the heading, because `build_graph.py` and
`validate_ontology.py` both parse against it.

```markdown
# ClassName

**Class ID:** `sup:ClassName`
**Type:** Customer | Product | Support | Engineering | Knowledge
**Status:** Canonical | Proposed | Deprecated
**Version:** 0.1.0

## Definition
One or two sentences. What this class is, in plain English, unambiguously
enough that someone could decide whether an arbitrary record belongs to it.

## Canonical name and aliases
| Context | Term used |
|---|---|
| Canonical | ClassName |
| <system or brand> | <what they call it> |

## Identity rule
How we decide two records are the same instance of this class.

## Datatype properties
| Property | Type | Required | Notes |
|---|---|---|---|

## Object properties
| Property | Target | Cardinality | Inverse |
|---|---|---|---|

## Subclasses and individuals
Named subclasses or the closed set of individuals, if any.

## Disjoint with
Classes an instance of this class can never simultaneously be.

## Constraints
Rules that must hold. Cross-reference IDs in `04-Constraints-and-Rules.md`.

## Provenance
| Source system | What it supplies | Authoritative for |
|---|---|---|

## Competency questions answered
Which questions in `05-Competency-Questions.md` this class participates in.

## Open questions
Cross-reference IDs in `06-Open-Questions.md`, or `None.`
```

## 6. Constraint IDs

Constraints are numbered `C-nn` in `04-Constraints-and-Rules.md` and referenced
by ID from entity files. Never renumber an existing constraint — retire it and
add a new one.

## 7. Competency question IDs

Questions are numbered `CQ-nn` in `05-Competency-Questions.md`. Same rule: never
renumber.

## 8. Open question IDs

Open questions are numbered `OQ-nn` in `06-Open-Questions.md`. When one is
resolved, mark it `Resolved` with the decision and the date — do not delete it.
The record of why we decided something is more valuable than a tidy file.

## 9. Aliases are always attributed

An alias entry without a source system is not usable. "Some systems call it a
case" cannot be acted on. "Salesforce (EMEA org) calls it a Case" can.

If the source is not yet known, record it as `UNVERIFIED` and raise an open
question. Do not record it as fact.

## 10. Editing rules

- One class per file. No exceptions.
- Never edit `Navigator/graph-data.js` — it is generated.
- Every edit gets a `CHANGELOG.md` entry.
- Re-run `build_graph.py` and `validate_ontology.py` before considering an edit
  finished.
