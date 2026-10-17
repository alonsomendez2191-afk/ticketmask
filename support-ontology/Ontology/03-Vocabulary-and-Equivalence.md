# Vocabulary and Equivalence

**Version:** 0.2.0
**Last updated:** 2026-08-05

This is the file that earns the ontology its keep.

Everything else here models what things *are*. This file models what things are
*called* — and, crucially, records that two different names refer to one thing
rather than two.

---

## Why equivalence is not synonymy

A thesaurus says two words are similar. An ontology says two identifiers denote
the **same entity**. The difference matters operationally:

- Similar → an agent might substitute one for the other, sometimes, unreliably.
- Equivalent → a query for one **must** return the other, always, or the answer
  is wrong.

When we declare `Ticket ≡ Case`, we are saying: any system that counts Cases and
any system that counts Tickets are counting the same population, and a report
that adds them together double-counts.

---

## Equivalence declarations

### `EQ-01` — Ticket ≡ Case

| | |
|---|---|
| **Canonical class** | `sup:Ticket` |
| **Equivalent labels** | Case, Incident, SR, Service Request |
| **Varies by** | CRM system |
| **Anchor property** | `sup:CRM.ticketTermUsed` |
| **Status** | Canonical. Per-system mapping populated per organization in `Entities/CRM.md` (`OQ-50`). Example: Salesforce → `Case`, Zendesk → `Ticket`. |

**Failure mode if ignored.** A user asks "how many cases are open?" against a
CRM that uses Ticket terminology, and gets zero. Zero looks like a valid
answer. Nobody notices.

**Additional hazard.** Development also calls Jira issues "tickets" — see
`EQ-04`. "Ticket" is therefore ambiguous in two directions at once: it can mean
a Case, or it can mean a Jira issue.

---

### `EQ-02` — Premium Support ≡ Platinum Support

| | |
|---|---|
| **Canonical individual** | `sup:SupportEntitlement` → `Premium` (`tierCode = PREMIUM`) |
| **Equivalent labels** | Platinum, Platinum Support |
| **Varies by** | Product |
| **Anchor property** | `sup:Product.usesPlatinumNaming` |
| **Status** | Canonical. Which products use Platinum naming is **not** populated (`OQ-07`). **Interim rule, 2026-08-20:** treat Platinum and Premium as synonyms unconditionally — either label resolves to `tierCode = PREMIUM` regardless of product. Tier counts are correct under this rule; "which label should this product be showing?" is not answerable until `OQ-07` closes. |

**Failure mode if ignored.** "How many Premium accounts do we have?" under-counts
by exactly the size of the Platinum-naming products. The number returned is
plausible, internally consistent, and wrong — the worst kind of wrong, because
nothing signals the error.

**Do not model Platinum as a third tier.** It is tempting, because it appears in
data as a distinct string. It is the same tier with a different label, and
modelling it as a tier makes tier comparisons (`tierRank`) meaningless.

---

### `EQ-03` — Severity ≡ Priority

| | |
|---|---|
| **Canonical class** | `sup:SeverityLevel` |
| **Equivalent labels** | Priority, Pri, Sev, Impact (informal) |
| **Varies by** | Product |
| **Anchor property** | `sup:Product.severityTermUsed` |
| **Status** | Canonical for the term split. **Value-level standard set 2026-08-20** (`OQ-19`): four levels, S1–S4, uniform across all products, definitions on `SeverityLevel`. Whether live CRM data conforms is still unverified (`OQ-51`). |

This one is harder than the other two, because it splits at both the **attribute
name** and the **value set**:

| Canonical | Rank | Value aliases seen |
|---|---|---|
| `S1` | 1 | P1, Critical, Urgent, 1, "1 - Critical" |
| `S2` | 2 | P2, High, 2, "2 - High" |
| `S3` | 3 | P3, Medium, Normal, 3 |
| `S4` | 4 | P4, Low, Minor, 4 |

**The three-level trap.** If any product uses three levels rather than four, its
"High" is not our `S2` — it is somewhere between `S1` and `S2`, and there is no
correct mapping, only a chosen one. That choice must be made explicitly and
recorded here, not inferred by whoever writes the next query. `OQ-19` is open
precisely because we do not yet know whether any product does this.

**Rule.** Always filter and compare on `levelRank`. Never on the label.

---

### `EQ-04` — "Ticket" is ambiguous across support and development

| | |
|---|---|
| **Not an equivalence — a collision** | |
| **Classes involved** | `sup:Ticket` and `sup:JiraIssue` |
| **Declared** | **Disjoint** — see `04-Constraints-and-Rules.md` |

Support says "ticket" and means a customer request. Development says "ticket"
and means a Jira issue. Both are correct in their own context. In a shared
context — a status meeting, a report, an AI agent's prompt — the word resolves to
whichever one the reader assumed.

This is recorded here not because the two are equivalent, but because a
vocabulary map that only handled equivalence would miss the more dangerous case:
**one word, two entities.** An agent must ask which is meant, or infer it from
context and say which it inferred.

---

## Alias resolution rules

For an agent working against this ontology:

1. **Resolve inbound terms before querying.** Map the user's word to the
   canonical class or individual first. If the term is ambiguous (`EQ-04`),
   resolve it from context or ask.
2. **Resolve the product or system before mapping a value.** "P1" only means
   `S1` if the source is a product using priority naming. Without knowing the
   source, the mapping is a guess.
3. **Query on canonical identifiers.** Never on labels.
4. **Translate outbound.** Answer in the vocabulary the user asked in. Someone
   who asks about Platinum accounts should be told about Platinum accounts, not
   corrected to Premium — the canonical form is for querying, not for lecturing
   the user about their own terminology.
5. **Never invent a mapping.** If a value does not resolve, that is an alias gap.
   Record it and flag it. Do not guess the nearest match — a guessed severity
   mapping produces a confidently wrong answer.

---

## Canonical term registry

The complete list of preferred terms. Where a term appears in an alias column,
it must not be used as a class or property name.

| Canonical | Class / individual | Common aliases | Splits by |
|---|---|---|---|
| Account | `sup:Account` | Customer, Organization, Org | — |
| Contact | `sup:Contact` | Requester, Reporter, End user | — |
| Ticket | `sup:Ticket` | **Case**, Incident, SR | CRM |
| Severity | `sup:SeverityLevel` | **Priority**, Sev, Pri | Product |
| Premium | `sup:SupportEntitlement/Premium` | **Platinum** | Product |
| Standard | `sup:SupportEntitlement/Standard` | Basic, Included | Unverified |
| License | `sup:License` | Asset, Subscription, Serial | System |
| SupportAgent | `sup:SupportAgent` | Case owner, Support engineer, T1/T2/T3 | — |
| Escalation | `sup:Escalation` | Dev handoff, Bug report | — |
| JiraIssue | `sup:JiraIssue` | Jira, Jira ID, **ticket** ⚠ | — |
| Documentation | `sup:Documentation` | Article, KB article, Doc, Page | — |
| CRM | `sup:CRM` | Org, Instance, System of record | — |
| SalesRepresentative | `sup:SalesRepresentative` | AE, Account executive, Owner | — |
| CustomerSuccessManager | `sup:CustomerSuccessManager` | CSM, TAM ⚠ (`OQ-36`) | — |
| Region | `sup:Region` | Territory, Geo | — |
| Product | `sup:Product` | SKU, **Product line**, Product family | — |

⚠ = the alias is contested or ambiguous, not a clean synonym.

---

## Populating the alias map

The declarations above establish **that** the splits exist. The per-product and
per-system values — which one uses which word — are placeholders until verified
against real configuration.

Verification steps, in order:

1. List the actual CRM instances and confirm each one's ticket terminology
   (`OQ-38`).
2. For each product, confirm whether it sells Premium or Platinum (`OQ-07`).
3. For each product, confirm the severity field label **and its full value
   list** (`OQ-19`) — the value list matters more than the label.
4. Populate `CRM.ticketTermUsed`, `Product.usesPlatinumNaming` and
   `Product.severityTermUsed` from those findings.
5. Only then may an agent be grounded on this ontology for cross-product
   reporting. Until step 4 is complete, cross-product aggregates are unsafe and
   should be refused rather than estimated.

Note that vocabulary is now anchored in **two** places — the CRM for ticket
naming, the Product for severity and tier naming. If they ever imply different
vocabularies for the same ticket, `OQ-39` decides which wins.
