# Support Organization Ontology — Overview

**Version:** 0.2.0
**Last updated:** 2026-08-05
**Namespace prefix:** `sup:`

---

## What this is

A formal, machine-readable model of the concepts, relationships, rules and
meanings that our AI agents are allowed to use when reasoning about the support
organization.

It is not a database schema and not a data dictionary. A schema says *how data
is stored*. This says *what the data means* — including the fact that two
systems storing the same thing under different names are storing the same thing.

## Why it exists

Ask an agent: *"Which Platinum accounts in EMEA have open high-priority cases
that are blocked on a development bug?"*

Answering that requires knowing, all at once, that:

- "Platinum" and "Premium" are the same entitlement tier, named differently by
  product
- "case" and "ticket" are the same object, named differently by CRM
- "priority" and "severity" are the same attribute, named differently by product
- "blocked on a development bug" means the ticket has an escalation whose Jira
  issue is of type Bug and is not yet resolved
- "in EMEA" is a property of the account, not of the ticket

None of that is in any single system. It lives here.

## Scope

**In scope:** accounts and their commercial context, support entitlements,
licenses, products, tickets and their lifecycle, severity, support agents,
escalation to development, Jira issues, and the documentation agents use to
resolve tickets.

**Deliberately out of scope:** brand and product-line hierarchies, engineering
team structure, a general person/employee layer, AI assistants, billing and
renewals mechanics, marketing attribution, telemetry.

Everything in that second list was considered and cut. The reasoning is recorded
in `06-Open-Questions.md` — `OQ-43` (engineering teams), `OQ-46` (AI assistant),
`OQ-47` (person layer), `OQ-12` (brand and product line). None of them are
"forgotten"; they are scoped out, with the cost of doing so written down.

## Domain types

Every class has exactly one type. Types are a navigation and grouping aid — they
carry no inheritance and no logical force.

| Type | Colour in Navigator | Classes |
|---|---|---|
| **Customer** | blue | Account, Region, SupportEntitlement, License, Contact, SalesRepresentative, CustomerSuccessManager, Partner |
| **Product** | teal | Product |
| **Support** | amber | Ticket, SeverityLevel, Escalation, SupportAgent, CRM, SLA |
| **Engineering** | red | JiraIssue |
| **Knowledge** | violet | Documentation |

**17 classes, 26 relationships.**

## The core story, in one paragraph

An **Account** sits in a **Region**, holds a **SupportEntitlement** (Standard or
Premium — called Platinum for some products) and one or more **Licenses**, each
granting access to a **Product** and each bound to an entitlement of its own. The
account has a **SalesRepresentative** assigned by region, and — if it is a
valuable account — a **CustomerSuccessManager**. **Contacts** at the account open
**Tickets** (called Cases in some CRMs). Each ticket concerns a product, carries
a **SeverityLevel** (called Priority for some products), is recorded in a **CRM**,
and is assigned to a **SupportAgent**. Every ticket is governed by an **SLA**,
the response and resolution targets implied by its severity and its account's
entitlement. The agent consults **Documentation** to resolve it. If the agent
determines the ticket is caused by a defect or requires new functionality, they
create an **Escalation**, which produces a **JiraIssue** of type Bug or
Enhancement — and the Jira ID is linked back to the ticket. Where a customer buys
through a **Partner**, the partner may raise tickets on the account's behalf.

## The two hubs

`Account` and `Ticket` carry 8 and 10 relationships respectively. Between them
they touch every class except `JiraIssue`.

That is the shape of the domain, not a drawing accident: the support
organization exists at the intersection of *who the customer is* and *what they
asked for*. Almost every question worth asking starts at one of those two and
walks outward. The Navigator lays the graph out around exactly that — two
centres, spokes radiating from each.

## How to read this ontology

| File | What it tells you |
|---|---|
| `01-Conventions.md` | Naming rules and the entity file template. Read this before adding anything. |
| `Entities/*.md` | One file per class. Definition, properties, constraints, source systems. |
| `02-Relationships.md` | The full object property catalog — every arrow in the diagram. |
| `03-Vocabulary-and-Equivalence.md` | Canonical terms and what each system calls them. The alias map. |
| `04-Constraints-and-Rules.md` | Cardinality, disjointness, and validation rules. |
| `05-Competency-Questions.md` | The questions this ontology must answer, with traversal paths. |
| `06-Open-Questions.md` | What we have not decided yet, and what we decided to leave out. |

Or open `Navigator/index.html` and click around.

## Structural building blocks used

| Block | Where it lives |
|---|---|
| Classes | `Entities/*.md` |
| Individuals | `Entities/*.md` → "Subclasses and individuals" |
| Object properties | `02-Relationships.md` |
| Datatype properties | `Entities/*.md` → "Datatype properties" |
| Domain & range | `02-Relationships.md` |
| Cardinality | `02-Relationships.md` and `04-Constraints-and-Rules.md` |
| Disjointness | `04-Constraints-and-Rules.md` |
| Equivalence | `03-Vocabulary-and-Equivalence.md` |
| Inverse properties | `02-Relationships.md` |
| Constraints | `04-Constraints-and-Rules.md` |
| Provenance | `Entities/*.md` → "Provenance" |

Transitive properties are **not currently used**. Both candidates — sub-regions
and article link graphs — were scoped out in v0.2.0. The notation remains
supported if a genuine hierarchy appears.

## Status

`v0.2.0` is a **draft**. It has been modelled from a verbal description of the
organization, not from system inspection. Before it is used to ground a
production agent, every class marked `Status: Proposed` must be confirmed or
cut, and the alias tables in `03-` must be verified against real configuration.
See `06-Open-Questions.md`.
