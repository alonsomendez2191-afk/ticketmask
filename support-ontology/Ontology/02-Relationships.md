# Relationships (Object Property Catalog)

**Version:** 0.2.0
**Last updated:** 2026-08-05

Every arrow in the Navigator diagram is one row in this file. Each relationship
is declared once in its forward direction, with its inverse named — the inverse
is not a second relationship, it is the same fact read from the other end.

Cardinality is stated on the **range** side: `Account raises Ticket 0..*` means
one account has zero or more tickets.

**26 relationships across 17 classes.**

---

## Reading the catalog

| Column | Meaning |
|---|---|
| Property | The verb. Read as `Domain property Range`. |
| Domain | The class the relationship starts from. |
| Range | The class it points to. |
| Card. | How many range instances per domain instance. |
| Inverse | The same relationship read backwards. |
| Notes | Derivation or hazards. |

---

## Customer

| Property | Domain | Range | Card. | Inverse | Notes |
|---|---|---|---|---|---|
| `isLocatedIn` | Account | Region | `1..1` | `isRegionOf` | Drives sales rep assignment via `C-46` |
| `hasEntitlement` | Account | SupportEntitlement | `1..1` | `entitles` | Premium ≡ Platinum — resolve before comparing |
| `holdsLicense` | Account | License | `0..*` | `isHeldBy` | |
| `hasContact` | Account | Contact | `0..*` | `worksFor` | Contact is `Proposed` |
| `hasSalesRep` | Account | SalesRepresentative | `1..1` | `manages` | Rep must cover the account's region — `C-46` |
| `hasCSM` | Account | CustomerSuccessManager | `0..1` | `supports` | **Conditional** — only if `isStrategic` — `C-08` |
| `isCoveredBy` | Region | SalesRepresentative | `1..*` | `covers` | |
| `binds` | SupportEntitlement | License | `0..*` | `isBoundTo` | Entitlement also attaches to the license — `OQ-42` |
| `grantsAccessTo` | License | Product | `1..1` | `isLicensedBy` | |
| `represents` | Partner | Account | `0..*` | `isRepresentedBy` | |
| `raisesOnBehalfOf` | Partner | Ticket | `0..*` | `submittedByPartner` | |

## Support

| Property | Domain | Range | Card. | Inverse | Notes |
|---|---|---|---|---|---|
| `raises` | Account | Ticket | `0..*` | `belongsTo` | |
| `submits` | Contact | Ticket | `0..*` | `submittedBy` | Contact must belong to the ticket's account — `C-16` |
| `concerns` | Ticket | Product | `1..1` | `isSubjectOf` | |
| `assignedTo` | Ticket | SupportAgent | `0..1` | `handles` | At most one at a time — `C-31` |
| `hasSeverity` | Ticket | SeverityLevel | `1..1` | `appliesTo` | Severity ≡ Priority — compare on `levelRank` only |
| `escalatedAs` | Ticket | Escalation | `0..*` | `originatesFrom` | The **only** route to a Jira ID — `C-05` |
| `resolvedUsing` | Ticket | Documentation | `0..*` | `resolves` | May be aspirational — `OQ-30` |
| `recordedIn` | Ticket | CRM | `1..1` | `records` | Disambiguates ticket numbers across systems |
| `isGovernedBy` | Ticket | SLA | `1..1` | `governs` | SLA affects response/resolution times — `C-56` |
| `escalatedBy` | Escalation | SupportAgent | `1..1` | `escalates` | Only agents may escalate — `C-29` |
| `specialisesIn` | SupportAgent | Product | `0..*` | `isSupportedBy` | Source may be informal — `OQ-23` |
| `consults` | SupportAgent | Documentation | `0..*` | `isConsultedBy` | |
| `measuredAgainst` | SupportAgent | SLA | `0..*` | `measures` | |

## Engineering

| Property | Domain | Range | Card. | Inverse | Notes |
|---|---|---|---|---|---|
| `producedIssue` | Escalation | JiraIssue | `1..1` | `raisedBy` | Inverse is `1..*` — many escalations, one issue |

## Knowledge

| Property | Domain | Range | Card. | Inverse | Notes |
|---|---|---|---|---|---|
| `describes` | Documentation | Product | `1..1` | `isDescribedBy` | Soft cardinality — `C-55` |

---

## The two hubs

`Account` and `Ticket` carry 8 and 10 relationships respectively — between them
they touch every other class except `JiraIssue`. That is not an accident of
drawing; it is the shape of the domain. The support organization exists at the
intersection of *who the customer is* and *what they asked for*, and almost
every question worth asking starts at one of those two and walks outward.

The Navigator lays the graph out around exactly that: two centres, spokes
radiating from each.

---

## The escalation chain

The most important traversal in this ontology, because it is the one natural
language keeps collapsing:

```
Account ──raises──▶ Ticket ──escalatedAs──▶ Escalation ──producedIssue──▶ JiraIssue
```

Read backwards, it answers the question that matters commercially:

```
JiraIssue ──raisedBy──▶ Escalation ──originatesFrom──▶ Ticket ──belongsTo──▶ Account ──hasEntitlement──▶ SupportEntitlement
```

*"Which Premium accounts are waiting on this bug?"* is that chain plus a filter.
It is unanswerable in any single system, because the CRM does not know the Jira
issue's status and Jira does not know the account's entitlement tier.

The `1..*` on `Escalation → JiraIssue`'s inverse is what makes the fan-in work:
twelve tickets from nine accounts can all converge on one defect.

---

## The knowledge path

```
Documentation ──isConsultedBy──▶ SupportAgent ──handles──▶ Ticket
Documentation ──resolves──▶ Ticket
```

Documentation reaches tickets two ways: through the agent who reads it, and as
the recorded resolution. Both matter — the first is how the knowledge is used,
the second is the only evidence we have that it was useful.

---

## Relationships deliberately not modelled

| Not modelled | Why |
|---|---|
| Ticket → JiraIssue direct link | Would bypass Escalation and lose who escalated, when, and why. `C-05` forbids it. |
| Region → Region (sub-regions) | Support assigns coverage at the top level. A hierarchy adds traversal cost without answering a question anyone asks. `OQ-41`. |
| Documentation → Documentation (links) | Orphan and link-graph analysis belongs to the KB evaluation tooling, which reads the live site. Duplicating it here means maintaining a second copy. `OQ-45`. |
| Account → Product | Always mediated by a License. An account does not "have" a product; it holds a license that grants access to one. |
| JiraIssue → owning team | Engineering ownership sits outside the support organization. `OQ-43`. |
| Any class → Person | Support agents, sales reps and CSMs are modelled directly. A separate Person layer added indirection without adding an answer. `OQ-47`. |
| Ticket → Ticket (duplicates, related) | Real and useful, but not yet described. `OQ-40`. |
