# Competency Questions

**Version:** 0.2.0
**Last updated:** 2026-08-05

A competency question is a question the ontology must be able to answer. They
are the acceptance tests: if a question cannot be answered by traversing the
model, the model is incomplete, regardless of how tidy the diagram looks.

Question IDs are permanent. Never renumber. Questions that can no longer be
asked — because the classes they crossed went out of scope — are **Retired** at
the bottom, not deleted.

**28 active questions.**

---

## How to read a traversal

`Account ──raises──▶ Ticket` reads "from Account, follow `raises`, arrive at
Ticket". Filters are shown in brackets.

| Status | Meaning |
|---|---|
| ✅ Answerable | The path exists and the data is modelled. |
| ⚠ Conditional | The path exists but depends on an unpopulated alias map or a `Proposed` class. |

---

## Customer and commercial

### `CQ-01` — Which accounts in a given region have open tickets? ✅
```
Region ──isRegionOf──▶ Account ──raises──▶ Ticket [status ∈ Open, Pending, Escalated]
```

### `CQ-02` — How many open tickets does each entitlement tier have, by severity? ⚠
```
Account ──hasEntitlement──▶ SupportEntitlement
Account ──raises──▶ Ticket ──hasSeverity──▶ SeverityLevel
group by tierCode, levelRank
```
**Conditional on `EQ-02` and `EQ-03`.** Until Platinum resolves to Premium and
every product's severity values are mapped, this aggregate silently under-counts.
Group on `tierCode` and `levelRank`, never on labels — `C-26`.

### `CQ-03` — Which Premium accounts have tickets open longer than N days? ⚠
```
Account [hasEntitlement.tierCode = PREMIUM] ──raises──▶ Ticket [openedAt < today - N, unresolved]
```
Conditional on `EQ-02`. "Premium" here must include Platinum-labelled accounts.

### `CQ-04` — Which products is an account licensed for? ✅
```
Account ──holdsLicense──▶ License [isActive] ──grantsAccessTo──▶ Product
```

### `CQ-05` — Who owns account X commercially, and is that assignment valid? ✅
```
Account ──hasSalesRep──▶ SalesRepresentative ──covers──▶ Region
Account ──isLocatedIn──▶ Region
Account ──hasCSM──▶ CustomerSuccessManager
assert: rep's covered regions include the account's region  [C-46]
```
This question does double duty — it retrieves ownership and validates it.

### `CQ-06` — Which contacts at an account have raised tickets, and how many? ⚠
```
Account ──hasContact──▶ Contact ──submits──▶ Ticket
```
**Conditional on `OQ-01`** — `Contact` is a Proposed class.

### `CQ-13` — Which licenses expire in 90 days for accounts with open tickets? ✅
```
Account ──holdsLicense──▶ License [endDate within 90 days] ──grantsAccessTo──▶ Product
Account ──raises──▶ Ticket [unresolved]
```
The renewal conversation nobody wants to walk into unprepared.

### `CQ-14` — Which strategic accounts in region R have no CSM? ✅
```
Region ──isRegionOf──▶ Account [isStrategic = true, hasCSM is null]
```
Permitted by `C-08` but probably unintended — a coverage gap.

### `CQ-22` — What is the full commercial picture of account X? ✅
```
Account ──isLocatedIn──▶ Region
       ──hasEntitlement──▶ SupportEntitlement
       ──holdsLicense──▶ License ──grantsAccessTo──▶ Product
       ──hasSalesRep──▶ SalesRepresentative
       ──hasCSM──▶ CustomerSuccessManager
```
The account briefing an agent should be able to produce in one pass.

### `CQ-29` — Do any accounts hold licenses at a different tier than the account? ⚠
```
Account ──hasEntitlement──▶ SupportEntitlement  (A)
Account ──holdsLicense──▶ License ──isBoundTo──▶ SupportEntitlement  (B)
where A ≠ B   [C-54]
```
**New in v0.2.0.** This question exists to settle `OQ-42`. If the answer is
"none", entitlement genuinely belongs on the account. If the answer is "many",
it belongs on the license and `C-02` is wrong. The ontology is asking the data
to tell us which model is correct rather than guessing.

---

## Support operations

### `CQ-08` — Compare high-severity ticket volume across products. ⚠
```
Product ──isSubjectOf──▶ Ticket ──hasSeverity──▶ SeverityLevel [levelRank ≤ 2]
group by productId
```
**The hardest question in this set**, and a large part of why the ontology
exists. It crosses products that use different words for the field *and*
different values in it. Conditional on `EQ-03` being fully populated. Until
then an agent should refuse rather than estimate.

### `CQ-09` — Which tickets came from accounts with no active license for that product? ✅
```
Ticket ──concerns──▶ Product
Ticket ──belongsTo──▶ Account ──holdsLicense──▶ License [isActive] ──grantsAccessTo──▶ Product
where no matching license exists  [C-14]
```
Out-of-maintenance support. Flag, do not reject.

### `CQ-10` — What is each agent's open ticket load, by severity? ✅
```
SupportAgent ──handles──▶ Ticket [unresolved] ──hasSeverity──▶ SeverityLevel
group by agent, levelRank
```

### `CQ-15` — How many tickets did each agent escalate, and at what severity? ✅
```
SupportAgent ──escalates──▶ Escalation ──originatesFrom──▶ Ticket ──hasSeverity──▶ SeverityLevel
```

### `CQ-23` — Do Premium tickets get escalated faster than Standard? ⚠
```
Account ──hasEntitlement──▶ SupportEntitlement
Account ──raises──▶ Ticket ──hasSeverity──▶ SeverityLevel
Ticket ──escalatedAs──▶ Escalation [escalatedAt − openedAt]
group by tierCode, levelRank
```
Tests whether the entitlement tier means anything in practice. Conditional on
`EQ-02`.

### `CQ-27` — What is the escalation rate by tier and severity? ⚠
```
count(Ticket ──escalatedAs──▶ Escalation) ÷ count(Ticket)
grouped by hasEntitlement.tierCode and hasSeverity.levelRank
```
A high escalation rate at low severity suggests agents lack the documentation to
resolve things themselves — which links this question to `CQ-26`.

**Conditional on `EQ-02` and `EQ-03`.** It groups on both axes at once, so both
alias maps must be populated before either rate means anything.

### `CQ-30` — Which support agents have the most SLA breaches? ✅
```
SupportAgent ──handles──▶ Ticket [resolvedAt - openedAt > isGovernedBy.targetResolutionMinutes]
```

### `CQ-31` — What is the average SLA resolution time for Premium tickets? ⚠
```
Ticket ──isGovernedBy──▶ SLA
Ticket ──belongsTo──▶ Account ──hasEntitlement──▶ SupportEntitlement [PREMIUM]
average(resolvedAt - openedAt)
```
Conditional on `EQ-02`.

### `CQ-32` — Which partners raised the most tickets this month? ✅
```
Partner ──raisesOnBehalfOf──▶ Ticket [openedAt >= startOfMonth]
```

---

## Escalation and engineering

### `CQ-11` — Which Premium accounts are blocked on an unresolved Jira issue? ⚠
```
JiraIssue [isResolved = false] ──raisedBy──▶ Escalation ──originatesFrom──▶ Ticket ──belongsTo──▶ Account ──hasEntitlement──▶ SupportEntitlement [PREMIUM]
```
**The flagship question.** Unanswerable in any single system: the CRM does not
know the Jira status, Jira does not know the entitlement tier. Conditional on
`EQ-02`.

### `CQ-17` — Which unresolved bugs have the highest-severity tickets attached? ✅
```
JiraIssue [issueType = Bug, isResolved = false] ──raisedBy──▶ Escalation ──originatesFrom──▶ Ticket ──hasSeverity──▶ SeverityLevel
order by min(levelRank), count(tickets)
```
A prioritisation input development can act on directly.

### `CQ-18` — Who escalated issue X, when, and why? ✅
```
JiraIssue ──raisedBy──▶ Escalation [escalatedAt, justification] ──escalatedBy──▶ SupportAgent
Escalation ──originatesFrom──▶ Ticket ──recordedIn──▶ CRM
```
This is why `Escalation` is its own class. A direct Ticket→JiraIssue link could
not answer any part of it.

### `CQ-19` — How many accounts are waiting on Jira issue X, and who owns them? ⚠
```
JiraIssue ──raisedBy──▶ Escalation ──originatesFrom──▶ Ticket ──belongsTo──▶ Account
Account ──hasEntitlement──▶ SupportEntitlement
Account ──isLocatedIn──▶ Region
Account ──hasSalesRep──▶ SalesRepresentative
```
Turns an engineering backlog item into a commercial exposure figure — and gives
you the list of reps to notify when it ships.

**Conditional on `EQ-02`.** The account list is complete either way, but the
tier breakdown beside it under-counts Premium until Platinum resolves to it.

---

## Knowledge

### `CQ-12` — Which products have support load but thin documentation? ✅
```
Product ──isSubjectOf──▶ Ticket
Product ──isDescribedBy──▶ Documentation
Product ──isSupportedBy──▶ SupportAgent
compare ticket volume against article count
```
Feeds directly into the KB evaluation process.

### `CQ-16` — For product P, which agents specialise in it and what docs exist? ✅
```
Product ──isSupportedBy──▶ SupportAgent
Product ──isDescribedBy──▶ Documentation
```

### `CQ-24` — Which documentation resolves the most tickets? ✅
```
Documentation ──resolves──▶ Ticket
Documentation ──isConsultedBy──▶ SupportAgent
```
Identifies the load-bearing content — the articles where an error is most
expensive. Depends on citation capture being real — `OQ-30`.

### `CQ-26` — Which topics generate high-severity tickets but have no documentation? ✅
```
Ticket [levelRank ≤ 2] ──concerns──▶ Product ──isDescribedBy──▶ Documentation
where the documentation set is empty or does not cover the ticket subject
```
The knowledge-gap question, and the bridge between this ontology and the KB
evaluation work — it produces the candidate list for new articles.

---

## Vocabulary and meta

### `CQ-07` — What does a given product and CRM call a ticket, a severity, and the premium tier? ⚠
```
Product [severityTermUsed, usesPlatinumNaming]
Ticket ──recordedIn──▶ CRM [ticketTermUsed]
```
The question an agent must answer **for itself**, silently, before answering any
cross-product question a human asks. Conditional on `OQ-38` and `OQ-39` —
vocabulary is now anchored in two places and they could disagree.

---

## Coverage summary

| Status | Count |
|---|---|
| ✅ Answerable today | 17 |
| ⚠ Conditional | 11 |

Ten of the eleven conditional questions are blocked by one of three things: the
alias map is not populated (`OQ-07`, `OQ-19`), the `Contact` class is unconfirmed
(`OQ-01`), or the CRM list is unknown (`OQ-38`).

The eleventh, `CQ-29`, is conditional for a different reason and should not be
counted with the others: it is not waiting on an answer, it **is** the
measurement that answers `OQ-42`. Running it is how that question gets resolved.

**That is the priority order for the next round of work** — those four items
unblock ten of the twenty-eight questions.

---

## Retired questions

Retired in v0.2.0 because the classes they crossed went out of scope. Restore
them if the class comes back.

| ID | Was | Retired because |
|---|---|---|
| `CQ-20` | Which tickets were opened after the contact used the AI assistant? | `AIAssistant` deferred. |
| `CQ-21` | Which documentation articles are orphans? | Article link graph left to the KB evaluation tooling. |
| `CQ-25` | What share of a product's public articles ground the assistant? | `AIAssistant` deferred. |
| `CQ-28` | Which dev teams carry the most escalations? | `DevelopmentTeam` out of scope. |

---

## Questions the ontology cannot yet answer

Stated explicitly, so nobody assumes coverage that is not there:

| Question | Blocked by |
|---|---|
| "Which product version is affected by this bug?" | `OQ-15` — versions are not modelled |
| "Who handled this ticket before it was reassigned?" | `OQ-16` — no assignment history |
| "Did this ticket's severity get raised during its life?" | `OQ-20` — no severity history |
| "Are these two tickets duplicates?" | `OQ-40` — no ticket-to-ticket relationships |
| "How many tickets did the chatbot deflect?" | `OQ-46` — AI assistant out of scope for now |
| "Which team is fixing this issue?" | `OQ-43` — engineering ownership out of scope |
