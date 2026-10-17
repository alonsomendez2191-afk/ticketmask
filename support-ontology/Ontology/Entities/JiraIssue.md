# JiraIssue

**Class ID:** `sup:JiraIssue`
**Type:** Engineering
**Status:** Canonical
**Version:** 0.1.0

## Definition
A unit of engineering work tracked in Jira, created as the result of a support
escalation, representing either a defect to fix or a capability to build. Its
key is the identifier that gets associated back to the originating ticket.

## Canonical name and aliases
| Context | Term used |
|---|---|
| Canonical | JiraIssue |
| Everyday speech | Jira, Jira ID, ticket (**dangerous — see below**) |
| Development | Issue, Story, Bug, Defect |
| CRM field | Jira reference, Dev ID |

**Vocabulary hazard.** Developers routinely call a Jira issue a "ticket". Support
agents call a customer request a "ticket". In a mixed conversation — or in an
agent's prompt context — "the ticket is closed" is genuinely ambiguous and the
two are often in different states at the same time. Always disambiguate.
See `EQ-04`.

## Identity rule
The Jira issue key (e.g. `PROJ-1234`) is authoritative and globally unique.

## Datatype properties
| Property | Type | Required | Notes |
|---|---|---|---|
| `issueKey` | string | Yes | e.g. `PROJ-1234` |
| `issueType` | enum(Bug, Enhancement) | Yes | Matches escalation type at creation |
| `issueStatus` | string | Yes | Jira workflow status — varies by project |
| `isResolved` | boolean | Yes | Normalised across the varying workflows |
| `fixVersion` | string | No | Release that carries the fix |
| `createdAt` | datetime | Yes | |

## Object properties
| Property | Target | Cardinality | Inverse |
|---|---|---|---|
| `raisedBy` | `sup:Escalation` | `1..*` | `producedIssue` |

Note the `1..*` on `raisedBy`: several tickets from several accounts commonly
escalate into the same underlying defect. That fan-in is what makes
"how many customers are waiting on this bug?" answerable — see `CQ-19`.

## Subclasses and individuals
None. `issueType` carries the Bug / Enhancement distinction, kept consistent
with `sup:Escalation.escalationType`.

## Disjoint with
`sup:Ticket`. This is the single most important disjointness declaration in the
ontology, because natural language constantly merges them.

## Constraints
- `C-27` — issue type matches the originating escalation's type at creation.
- `C-33` — every JiraIssue traces back to at least one Escalation. A Jira issue
  with no escalation is engineering-initiated work and is **out of scope** for
  this ontology — it should not be loaded.
- `C-34` — `isResolved` must be derived from a per-project mapping of Jira
  statuses, not from the raw status string. Projects use different workflows.
- `C-35` — a resolved JiraIssue with unresolved originating tickets is a
  follow-up gap worth reporting: the fix shipped, the customers were not told.

## Provenance
| Source system | What it supplies | Authoritative for |
|---|---|---|
| Jira | The issue and all its fields | Everything |
| Jira project configuration | Status-to-resolved mapping | `isResolved` derivation |
| Salesforce | The Jira key stored on the case | Nothing — mirror only |

## Competency questions answered
`CQ-11`, `CQ-17`, `CQ-18`, `CQ-19`

## Open questions
`OQ-24` (Jira issue hierarchies — epics and sub-tasks are not modelled),
`OQ-25` (should `fixVersion` link to a `ProductVersion` class once `OQ-15` is
resolved?), `OQ-43` (issue ownership by development team is out of scope — the
support organization tracks the issue, not who builds the fix).
