# Constraints and Rules

**Version:** 0.2.0
**Last updated:** 2026-08-05

Constraints are what turn a diagram into something an agent can be held to. A
relationship says a connection is *possible*. A constraint says what is
*required*, *forbidden*, or *suspicious*.

**Constraint IDs are permanent.** Never renumber. When a constraint stops
applying — because the class it governed was removed from scope — it is
**Retired**, not deleted. The retired list at the bottom is part of the record.

---

## Enforcement levels

| Level | Meaning | On violation |
|---|---|---|
| **Hard** | The data is invalid. The model cannot be true and the data cannot both be right. | Reject or quarantine the record. |
| **Soft** | Valid data, but almost certainly an operational problem. | Alert. Do not block. |
| **Advisory** | A signal worth acting on, not an error. | Report in a review queue. |

The distinction matters. A support organization is full of legitimately messy
states — customers out of maintenance, agents who left with tickets still open.
Treating those as hard errors means the validator gets switched off.

---

## Cardinality constraints

| ID | Level | Constraint |
|---|---|---|
| `C-01` | Hard | Every Account is located in exactly one Region. |
| `C-02` | Hard | Every Account has exactly one SupportEntitlement at a given point in time. |
| `C-04` | Hard | Every Ticket has exactly one Account, exactly one SeverityLevel, and exactly one Product. |
| `C-07` | Hard | Every Account has exactly one SalesRepresentative. |
| `C-10` | Hard | Every Region is covered by at least one SalesRepresentative. |
| `C-15` | Hard | Every Contact belongs to exactly one Account. |
| `C-27` | Hard | Every Escalation produces exactly one JiraIssue. |
| `C-31` | Hard | A Ticket is assigned to at most one SupportAgent at a time. |
| `C-33` | Hard | Every JiraIssue in scope traces back to at least one Escalation. Engineering-initiated issues are out of scope and must not be loaded. |
| `C-47` | Hard | An Account has at most one CustomerSuccessManager. |
| `C-48` | Hard | Every Ticket is recorded in exactly one CRM. |
| `C-53` | Hard | Every License is bound to exactly one SupportEntitlement. |
| `C-55` | Soft | Every Documentation instance describes exactly one Product. Cross-product overview pages legitimately exist, so this flags rather than rejects. |
| `C-56` | Hard | Every Ticket has exactly one SLA, determined by its SeverityLevel and Account's SupportEntitlement. |

---

## Conditional constraints

The rules that encode "it depends" — where the source description said *might*,
*if*, or *depending on*.

| ID | Level | Constraint |
|---|---|---|
| `C-08` | Hard | An Account may have a CSM **only if** `isStrategic = true`. Note the direction: strategic *permits* a CSM, it does not require one. A strategic account with no CSM is valid (awaiting assignment); a non-strategic account with a CSM is not. |
| `C-05` | Hard | A Ticket may carry a Jira reference **only** through an Escalation. A Jira ID on a ticket with no escalation record is invalid — the link exists but the reason, the author and the date have been lost. |
| `C-06` | Hard | A Ticket with `status = Escalated` has at least one open Escalation. |
| `C-12` | Hard | `grantsEscalationRight` is true only for the PREMIUM tier. |
| `C-17` | Hard | Only a Contact with `isSupportAuthorised = true` may submit a Ticket. |
| `C-22` | Hard | A Product with `lifecycleStatus = EndOfLife` must have an `endOfLifeDate`. |
| `C-29` | Hard | Only a SupportAgent may create an Escalation. Not a CSM, not a sales rep. |
| `C-46` | Soft | An Account's SalesRepresentative must cover the Account's Region. This is "assigned depending on the region" made checkable — and it is the constraint most likely to fail after a territory reshuffle. |
| `C-50` | Hard | Every CRM declares `ticketTermUsed`. A system whose vocabulary is unknown cannot have its records safely translated. |
| `C-51` | Hard | Every Product declares `usesPlatinumNaming` and `severityTermUsed`. A product whose support vocabulary is unknown cannot have its tickets safely compared against another product's. |

---

## Closed vocabulary constraints

| ID | Level | Constraint |
|---|---|---|
| `C-11` | Hard | The SupportEntitlement tier set is closed at STANDARD and PREMIUM. A value that does not resolve to one of these after alias resolution is a **data error or an alias gap**, never a new tier. |
| `C-25` | Hard | The SeverityLevel set is closed at S1–S4. A product-specific value that does not resolve is an alias gap to record in `03-Vocabulary-and-Equivalence.md`, not a fifth level. |
| `C-26` | Hard | Severity comparisons, filters and sorts operate on `levelRank` only — never on the customer-facing label. `"High" > "Critical"` is true as a string comparison and false as a fact. |
| `C-34` | Hard | `JiraIssue.isResolved` is derived from a per-project status mapping, not from the raw status string. Jira projects use different workflows and "Done" is not universal. |

---

## Disjointness

Classes an instance can never simultaneously belong to.

| Class A | Class B | Why it matters |
|---|---|---|
| `Ticket` | `JiraIssue` | **The most important one.** Natural language collapses them constantly. A ticket is the customer's request; a Jira issue is internal work. They have different lifecycles and are routinely in different states — "it's fixed" is true of one and false of the other. |
| `Account` | `Contact` | An account is an organization. Even a one-person customer is an organization holding a license. |
| `Contact` | the internal role classes | A Contact acts for the customer; an agent, rep or CSM acts for us. |
| `License` | `SupportEntitlement` | A license grants product usage; an entitlement grants service level. Salesforce's use of "Entitlement" for the tier and "Asset" for the license makes this collision live. |
| `Escalation` | `Ticket` / `JiraIssue` | The escalation is the link, not either end of it. |
| `CRM` | every domain class | A CRM holds facts about the organization; it is not part of it. |
| `Partner` | `Account` | A partner represents an account but is a separate organization. |

| ID | Level | Constraint |
|---|---|---|
| `C-52` | Hard | `SupportAgent`, `SalesRepresentative` and `CustomerSuccessManager` are pairwise disjoint. These are three distinct jobs in the support and commercial organization. |

---

## Referential and temporal integrity

| ID | Level | Constraint |
|---|---|---|
| `C-13` | Hard | `License.endDate`, when present, is later than `startDate`. |
| `C-16` | Soft | A Ticket's submitting Contact must belong to the Ticket's Account. |
| `C-24` | Hard | `Ticket.resolvedAt` is required when status is Resolved or Closed, and must not precede `openedAt`. |
| `C-49` | Hard | A fact from a CRM with `isAuthoritative = false` must not override a fact from an authoritative system for the same property. Mirrors lag. |
| `C-57` | Hard | A Ticket raised by a Partner must belong to an Account that the Partner represents. |

---

## Operational rules (Soft and Advisory)

These are the ones that find real problems in real data.

| ID | Level | Constraint | What it catches |
|---|---|---|---|
| `C-09` | Soft | An Account with `accountStatus = Active` holds at least one active License. | Accounts marked active after everything lapsed. |
| `C-14` | Soft | A Ticket's product should be covered by an active License at the time it was opened. | Out-of-maintenance support requests. **Legitimate and common** — flag, never reject. |
| `C-23` | Advisory | Documentation describing an EndOfLife product is a retirement candidate. | Feeds the KB evaluation process. |
| `C-28` | Advisory | An Escalation of type Bug should have `reproductionSteps`. | Escalations development will bounce back. |
| `C-32` | Soft | An inactive SupportAgent must not hold open tickets. | Tickets orphaned when someone leaves. Real, common, and invisible until a customer chases. |
| `C-35` | Soft | A resolved JiraIssue with unresolved originating Tickets. | **The fix shipped and nobody told the customer.** Probably the highest-value check here. |
| `C-40` | Advisory | Documentation not reviewed in 24 months is a review candidate. | Stale content agents are still trusting. |
| `C-54` | Soft | A License's SupportEntitlement should match its Account's SupportEntitlement. | **The model's own open question, made checkable.** If accounts routinely hold licenses at different tiers, entitlement belongs on the license and `C-02` is wrong. Flagging rather than rejecting means the first real violation tells us which model is right, instead of the data being quietly reshaped to fit our guess. See `OQ-42`. |

---

## Retired constraints

Retired because the class or relationship they governed was taken out of scope
in v0.2.0. Kept so that a reference to an old ID in a report or a query resolves
to an explanation rather than to nothing.

| ID | Was | Retired because |
|---|---|---|
| `C-03` | `hasSubRegion` transitive and acyclic | Sub-regions removed — regions are flat. |
| `C-18` | Every Brand declares its three vocabulary properties | `Brand` removed; replaced by `C-51` on Product and `C-50` on CRM. |
| `C-19` | Every ProductLine belongs to one Brand | Both classes removed. |
| `C-20` | ProductLine naming agrees with its Brand | Both classes removed. |
| `C-21` | Every Product belongs to one ProductLine | `ProductLine` removed; Product is now flat. |
| `C-30` | Role instances disjoint, persons not | `Person` removed; replaced by `C-52`. |
| `C-36` | Every JiraIssue owned by one DevelopmentTeam | `DevelopmentTeam` out of scope. |
| `C-37` | Every Product has an owning DevelopmentTeam | `DevelopmentTeam` out of scope. |
| `C-38` | AI-indexed articles must be public | `AIAssistant` deferred. |
| `C-39` | Articles with no inbound link are orphans | Article link graph left to the KB evaluation tooling. |
| `C-41` | No article may be its own ancestor | Article link graph removed. |
| `C-42` | Every AIAssistant is grounded in ≥1 article | `AIAssistant` deferred. |
| `C-43` | Article changes trigger re-indexing | `AIAssistant` deferred. |
| `C-44` | Unemployed Person holds no active roles | `Person` removed. |
| `C-45` | Every role instance held by exactly one Person | `Person` removed. |

`C-38`, `C-42` and `C-43` should be **restored, not rewritten**, when the AI
assistant is brought back into scope. They were correct; they simply have
nothing to attach to right now.

---

## What these constraints buy an agent

An agent grounded on this ontology can refuse rather than guess:

- Asked to compare severity across products before `C-51` is satisfied for every
  product → **refuse**, the comparison is not yet safe.
- Asked for "Premium account count" before `EQ-02` is populated → **answer with
  a stated caveat** that Platinum-naming products may be excluded.
- Asked "is the ticket fixed?" → **disambiguate** via the `Ticket`/`JiraIssue`
  disjointness, because those are different questions with different answers.

Refusing a specific question for a stated reason is a feature. A confident wrong
number is the failure this whole exercise exists to prevent.
