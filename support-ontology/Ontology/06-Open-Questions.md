# Open Questions

**Version:** 0.2.1
**Last updated:** 2026-08-20

Unresolved modelling decisions. Every `Proposed` class and every assumption made
without confirmation has an entry here.

**Question IDs are permanent.** When one is resolved, mark it `Resolved`, record
the decision and the date, and leave it in place. The record of *why* we decided
something outlives the decision itself.

| Status | Meaning |
|---|---|
| 🔴 **Blocking** | Something depends on this. Competency questions are conditional or a class is unconfirmed. |
| 🟡 **Open** | Real question, nothing blocked on it yet. |
| 🟢 **Resolved** | Decided. Decision and date recorded. |
| ⚫ **Retired** | No longer applicable — the class it concerned went out of scope. |

---

## Priority — resolve these first

Three of the original four blockers were resolved on 2026-08-20 (`OQ-01`,
`OQ-38`, `OQ-19` — see **Resolved** below). What remains at the front of the
queue:

### `OQ-07` 🟡 Which products sell Platinum rather than Premium?
`EQ-02` establishes that the split exists. Nobody has written down which products
are on which side.
**Blocks:** `CQ-02`, `CQ-03`, `CQ-11`, `CQ-23` — every Premium-base question.
**Also:** is "Basic" a real label for the Standard tier anywhere, or invented?

**Interim decision, 2026-08-20.** Until the per-product list exists, treat
**Platinum and Premium as synonyms unconditionally** — any occurrence of either
label resolves to `tierCode = PREMIUM` regardless of which product it came from.
`sup:Product.usesPlatinumNaming` stays unpopulated.

*What this buys:* the Premium-base questions become answerable now, because the
count is correct either way — a Platinum row and a Premium row both land in the
same bucket.

*What it costs:* the ontology can no longer tell you which label a given product
*should* be showing a customer. Any question of the form "is this product using
the right tier name in its own documentation" is unanswerable until the list is
populated. Downgraded from 🔴 to 🟡 on that basis, not resolved.

### `OQ-15` 🔴 Product versions are not modelled.
Now the largest remaining blocker. See *Licensing and product* below.

### `OQ-42` 🔴 Entitlement is bound to both the Account and the License.
See *Customer and commercial* below.

### `OQ-30` 🔴 Is "the agent used this article" actually captured?
See *Knowledge* below. Cheap to verify; `CQ-12`, `CQ-24` and `CQ-26` lean on it.

### `OQ-50` 🟡 Enumerate CRM instances and populate `ticketTermUsed`.
The `Entities/CRM.md` individuals table ships with template rows. Each adopting
organization lists its own instances and the term each one uses.
**Blocks:** completion of `EQ-01`'s per-system mapping, and `C-50` compliance.
**Successor to:** `OQ-38`.

### `OQ-51` 🟡 Does live CRM data conform to the four-level standard?
`OQ-19` set one severity standard for all products. That is policy. Whether
every product's CRM records actually resolve to S1–S4 is a separate, unverified
question — a product configured with three levels before the standard existed
will still be emitting three.

**Check:** for each product, list the distinct severity values present in the
CRM and confirm each maps to exactly one of S1–S4.
**If a gap is found:** record the mapping explicitly in
`03-Vocabulary-and-Equivalence.md`. Do not add a fifth level (`C-25`).
**Successor to:** `OQ-19`.

---

## Vocabulary and alias mapping

### `OQ-39` 🟡 Vocabulary is anchored in two places — what if they disagree?
`CRM.ticketTermUsed` and `Product.severityTermUsed` / `usesPlatinumNaming` both
exist. A ticket has both a product and a CRM. If they imply different
vocabularies, which wins?

### `OQ-44` 🟡 Severity naming was described as varying by *brand*.
Brand is no longer modelled, so `severityTermUsed` now sits on Product. That is
the surviving axis, not evidence. If severity naming actually tracks something
else — the CRM, the acquired company, the support team — this is in the wrong
place.

### `OQ-13` 🟡 Can a product's vocabulary change over time?
If a product rebrands Platinum to Premium next year, do historical tickets keep
the old vocabulary? Effective dates on the `*TermUsed` properties would handle
it, at a cost in complexity.

---

## Customer and commercial

### `OQ-42` 🔴 Entitlement is bound to both the Account and the License.
Added in v0.2.0 at the user's direction: a license is bound to an entitlement,
and an account also has one. Both are now modelled. If an account can hold
licenses at *different* tiers, then entitlement is really a property of the
license and `C-02` — "an Account has exactly one SupportEntitlement" — is wrong.

**Decide by measuring.** `C-54` flags mismatches rather than rejecting them, and
`CQ-29` asks the data directly. The first real violation settles it.

### `OQ-03` 🟡 How do we de-duplicate accounts across CRM instances?
One organization buying from several products may exist as several account
records. Are they one `sup:Account` or several? Affects every account-level
aggregate.

### `OQ-04` 🟡 Are account hierarchies needed?
Enterprise customers have parents and subsidiaries. Not modelled. "How many
tickets does <parent> have across all subsidiaries" is currently unanswerable.

### `OQ-05` 🟡 Is Region a property of the account or the license?
Currently the account. A multinational holding licenses in several regions
breaks that assumption — and it affects sales rep assignment via `C-46`.

### `OQ-41` 🟡 Regions are flat by decision.
Sub-regions (DACH, Benelux, ANZ) were removed in v0.2.0 because support assigns
coverage at the top level. Revisit only if a real reporting need for sub-regional
roll-ups appears — it would mean reinstating a transitive relationship.

### `OQ-37` 🟡 What determines `isStrategic`?
The ontology treats it as a given fact. Is it revenue-derived, entitlement-
derived, or a manual flag? If derived, the derivation belongs here.

### `OQ-34` 🟡 Is the renewal owner always the account owner?
`SalesRepresentative` assumes one commercial owner. Renewals may sit elsewhere.

### `OQ-35` 🟡 Can an account be owned by a rep outside its region?
`C-46` says no. Real organizations make documented exceptions. If they exist, we
need a way to record an approved exception rather than logging a violation every
night.

### `OQ-36` 🟡 Is TAM the same role as CSM?
Listed as an alias with a warning. If they are distinct jobs with distinct
responsibilities, TAM needs its own class.

---

## Licensing and product

### `OQ-09` 🟡 How do we represent tickets from lapsed accounts?
`C-14` flags them rather than rejecting. Confirm that is the wanted behaviour —
out-of-maintenance support requests are legitimate and common.

### `OQ-10` 🟡 Do trial licenses carry support entitlement?
`licenseType = Trial` exists but its entitlement implications are undefined.
Sharper now that `C-53` requires every license to be bound to a tier.

### `OQ-15` 🔴 Product versions are not modelled.
No `sup:ProductVersion` class. "Which version is affected?", "which version fixes
it?" and "is the customer on a supported version?" are all unanswerable. This is
the largest single gap in the model.

### `OQ-14` 🟡 Is the product list the right granularity?
The nineteen names came from the documentation folder structure and are
family-level, not SKU-level. Confirm the support organization does not need SKUs
underneath them.

---

## Tickets and escalation

### `OQ-16` 🟡 Ticket assignment history is not modelled.
Only the current agent. "Who had this before it was reassigned?" is
unanswerable. Would need a reified `Assignment` class — same pattern as
`Escalation`.

### `OQ-17` 🟡 Are there ticket types worth modelling explicitly?
Currently type is implied by whether an escalation exists and of what kind. If
the CRM has a real type field (Question / Defect / Request), it should be here.

### `OQ-18` 🟡 Ticket number collisions across CRM instances.
Handled by `recordedIn` + `ticketNumber` as composite identity. Confirm that
reporting tools actually do this — most do not, and silently merge.

### `OQ-20` 🔴 Does severity change over a ticket's life?
**Yes — confirmed 2026-08-20 by the severity standard adopted in `OQ-19`.** Two
named mechanisms change it: the customer may request an escalation or
de-escalation, and an S1 is automatically de-escalated to S2 when the customer
point of contact is unavailable for troubleshooting.

Only the current value is modelled, so "how many tickets were raised to S1 after
opening?" and "how often does the S1 unavailability rule fire?" are both
unanswerable — and the second one is an SLA-compliance question, not a curiosity.
Raised from 🟡 to 🔴: this is no longer speculative, the mutation is written into
the support policy.

**Would need** a reified `SeverityChange` class, same pattern as `Escalation`.

### `OQ-21` 🟡 Severity escalation and management escalation.
"Escalation" is used for at least three different actions: refer to development
(modelled), raise the severity (not modelled), involve a manager (not modelled).
A live confusion risk for any agent reading ticket notes.

### `OQ-22` 🟡 How are rejected escalations represented?
`wasAccepted = false` exists. What happens to the ticket then? And if development
reclassifies a Bug as an Enhancement, `C-27` says we keep the agent's original
classification — confirm that is wanted.

### `OQ-40` 🟡 Ticket-to-ticket relationships are not modelled.
No duplicates, no "related to", no parent/child for mass incidents. When one
outage generates two hundred tickets, there is no way to group them.

### `OQ-48` 🟡 How are business hours vs calendar hours calculated for SLAs?
`targetResolutionMinutes` exists, but support organizations often measure SLA timers
differently depending on the region's business hours. Is there a global calendar or per-region?

### `OQ-49` 🟡 Are there cases where a single ticket is co-managed by Partner and Account Contacts?
If a partner opens a ticket, can the customer's contact also engage with it?
This might affect visibility rules and `C-16`.

---

## Engineering

### `OQ-43` 🟡 Engineering ownership is out of scope.
`DevelopmentTeam` was removed in v0.2.0: the support organization tracks the
issue, not who builds the fix. The cost is that `CQ-28` is retired and "which
team is fixing this?" is unanswerable. Accepted deliberately.

### `OQ-24` 🟡 Jira issue hierarchies are not modelled.
Epics, stories and sub-tasks are flattened to `JiraIssue`. If a ticket escalates
to a sub-task whose parent epic holds the real status, `isResolved` is wrong.

### `OQ-25` 🟡 Should `fixVersion` link to a real version entity?
Depends on `OQ-15`.

---

## Knowledge

### `OQ-30` 🔴 Is "the agent used this article" actually captured?
`resolvedUsing` may be aspirational. If the CRM does not capture article
citations on resolution, `CQ-24` cannot be answered and the relationship should
be marked as a target state rather than a fact.
**Worth checking early** — it is cheap to verify and `CQ-12`, `CQ-24` and
`CQ-26` all lean on it.

### `OQ-45` 🟡 Link-graph analysis belongs to the KB tooling.
Article-to-article linking was removed in v0.2.0. Orphan detection now depends on
the KB evaluation tooling reading the live site. Confirm that division of labour —
the alternative is maintaining a second copy of the link graph here.

### `OQ-46` 🟡 The AI assistant is deferred, not rejected.
`AIAssistant` was removed in v0.2.0 to be reconsidered separately. When it comes
back it needs: what grounds it, who uses it, and how deflection is derived.
Constraints `C-38`, `C-42` and `C-43` were written for it and should be restored
rather than rewritten.

### `OQ-29` 🟡 Article versioning and localisation.
Identity is the canonical URL. Localised versions and revisions are not modelled.

---

## Cross-cutting

### `OQ-47` 🟡 There is no `Person` layer.
Support agents, sales reps and CSMs are modelled directly rather than as roles
played by a person. The cost: if one human holds two of those jobs, they are two
unlinked records, and "everything this person touches" cannot be asked. Accepted
as the right trade for a support-scoped model — revisit if cross-role reporting
is ever needed.

### `OQ-33` 🟡 Cross-system user resolution.
Agents appearing in more than one CRM are matched on corporate email. Confirm
that holds everywhere.

### `OQ-06` 🟡 Response targets by tier and severity.
`responseTargetHours` sits on the entitlement tier, but targets almost certainly
vary by tier **and** severity. Likely needs to move to the pair.

### `OQ-08` 🟡 Are there tiers above Premium?
The model closes the tier set at two (`C-11`). Named-engineer or mission-critical
tiers would break that.

### `OQ-23` 🟡 Where does agent product specialisation come from?
Routing configuration, or informal team knowledge? If informal, `specialisesIn`
has no authoritative source and should be marked as such.

---

## Resolved

### `OQ-01` 🟢 Does the `Contact` class exist?
**Decision:** yes. `sup:Contact` is confirmed and promoted to Canonical.
**Decided by:** user on 2026-08-20.
**Rationale:** an organization does not fill in a support form, and both "which
contacts open the most tickets" and "is this person authorised to raise a
ticket" are questions the support organization actually asks. Folding the
requester into a bare `requesterEmail` on Ticket would answer neither.
**Changes made:** `Entities/Contact.md` status Proposed → Canonical, proposed-class
banner replaced with the confirmation note; `CQ-06` unblocked.

### `OQ-38` 🟢 What are the actual CRM systems?
**Decision:** class confirmed. Instances are enumerated per organization.
**Decided by:** user on 2026-08-20.
**Rationale:** most support organizations run more than one ticketing system,
and each has its own ID space and vocabulary.
**Changes made:** `Entities/CRM.md` status Proposed → Canonical, template
individuals added; per-system population deferred to `OQ-50`.
**Note:** with more than one instance, `OQ-18` (ticket number collisions across
CRM instances) stops being hypothetical.

### `OQ-19` 🟢 Are the severity value mappings correct?
**Decision:** there is **one severity standard for all products** — S1 System
Down, S2 Work Stoppage, S3 Medium, S4 Low — with the impact definitions now
recorded in full on `Entities/SeverityLevel.md`.
**Decided by:** user on 2026-08-20.
**Rationale:** the original risk was that a product might use three levels
rather than four, leaving its "High" with no correct mapping. That is settled by
policy: four levels, uniform, everywhere.
**Changes made:** `Entities/SeverityLevel.md` — individuals renamed to the
standard's names, `definition` populated per level, escalation/de-escalation
mechanics and wording provenance recorded; `EQ-03` status updated.
**Two things this surfaced:**
- Severity is **mutable** — the customer may request escalation or
  de-escalation, and an S1 auto-de-escalates to S2 when the customer contact is
  unavailable. Only the current value is stored, which promotes `OQ-20` from a
  nice-to-have to a real gap.
- Setting the standard is not the same as verifying the data conforms to it.
  Conformance moves to `OQ-51`.

### `OQ-12` 🟢 Are `Brand` and `ProductLine` two levels or one?
**Decision:** neither. Both classes removed; collapsed into a single flat
`Product` class.
**Decided by:** user, 2026-08-05.
**Rationale:** brand and product-line hierarchies sit outside the support
organization. Modelling them added structure without answering a support
question. "Product line" is retained as an alias on `Product`.
**Changes made:** `Brand.md` and `ProductLine.md` deleted; `Product.md`
rewritten to absorb the vocabulary anchors and the documentation/agent links;
`C-18`–`C-21` retired; `C-51` added.

### `OQ-02` 🟢 Person vs Contact overlap.
**Decision:** moot — `Person` removed entirely. See `OQ-47`.
**Decided by:** user, 2026-08-05.
**Rationale:** the internal roles are known and finite. A Person layer added
indirection without adding an answer.

---

## Retired

| ID | Was | Retired because |
|---|---|---|
| `OQ-11` | Anonymous chatbot sessions | `AIAssistant` deferred — see `OQ-46`. |
| `OQ-26` | Team-to-Jira-project mapping | `DevelopmentTeam` out of scope — see `OQ-43`. |
| `OQ-27` | Team membership not modelled | `DevelopmentTeam` out of scope. |
| `OQ-28` | Are AI grounding chunks a modelled thing? | `AIAssistant` deferred. |
| `OQ-31` | Is the deflection derivation rule agreed? | `AIAssistant` deferred. |
| `OQ-32` | Should the assistant conversation be its own class? | `AIAssistant` deferred. |

---

## Resolution format

```
### `OQ-nn` 🟢 <original question>
**Decision:** <what was decided>
**Decided by:** <who> on <YYYY-MM-DD>
**Rationale:** <why>
**Changes made:** <files updated, changelog entry>
```
