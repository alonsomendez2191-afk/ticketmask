# Ticket Data → Knowledge Generation

Turns the tribal knowledge locked in support tickets into KB articles that an LLM-backed
chatbot can actually answer from. The masking layer comes first: nothing reaches a
model until raw customer data can be reliably de-identified.

Scope is deliberately narrow right now — **support ticket data only**. Teams, Slack and
email ingestion are a separate effort and are explicitly out of scope for this codebase
today.

## Status as of 2026-10-16

| Component | State |
|---|---|
| Presidio masking pipeline | **Working prototype.** 96.4% recall / 100% precision on the synthetic corpus. |
| Custom ticket recognizers | **Working prototype.** 7 pattern recognizers + 11 deny-lists. Needs tuning on real data. |
| Ontology binding | **Working.** Entity types are `sup:` class names; drift against the export is detected. |
| Measurement harness | **Working.** `scripts/measure.py`, gated on leak rate. |
| Sample dataset | **Working.** `samples/`: 20 labelled synthetic tickets plus deny-lists. |
| Bundled ontology | **Generic.** `support-ontology/` ships template products, CRMs and severity wording. |

## The two controls, and why both exist

They defend different things and neither substitutes for the other:

- **Masking** stops PII from surviving into the *output* — the KB article, the embeddings,
  the vector DB, logs, prompt cache, eval sets. A published article is durable and
  searchable, so this matters regardless of where inference runs.
- **Local inference** stops PII from reaching a *third party*.

Masking is therefore mandatory and non-bypassable. Local inference is a deployment mode:
the model provider must stay swappable behind one interface, never forked into a second
system.

## Architecture

Detect → arbitrate → link → mask → *(model)* → unmask.

| Module | Responsibility |
|---|---|
| `recognizers.py` | Presidio defaults + ticket-specific patterns, per-class deny-lists, product catalog |
| `policy.py` | Per-entity action + confidence threshold. The table a security reviewer reads. |
| `arbitrate.py` | Collapses competing detections into one decision per span |
| `linker.py` | Links name variants; sweeps the doc for repeats the detector missed |
| `vault.py` | Fernet-encrypted surrogate → original map, one per ticket |
| `pipeline.py` | Orchestration + the mask/unmask round trip |
| `corpus.py` | Loads `[[TYPE|value]]`-annotated ground truth |
| `ontology.py` | Binds every entity type to a `sup:` class; detects drift against the export |
| `support-ontology/` | Bundled generic ontology: markdown source, exports, validation scripts |
| `scripts/export_ontology_sql.py` | Generates `sql/support_ontology_er.sql`: ER model, ontology catalog, masking actions, constraint views |

`policy.ATTRIBUTE_POLICY` gives every ontology attribute an action (Keep,
Pseudonymize, Reject/REDACT, or Scan for free text). It is **Proposed and not
enforced**: the pipeline masks free text, not structured columns. The SQL export
fails if an ontology attribute has no rule, and also if a constraint in
`04-Constraints-and-Rules.md` has no enforcement.

## Grounded on the support ontology

Entity types are **ontology class names**, not Presidio's labels and not ours to
invent — the ontology's own rule is "never invent vocabulary."
`ticketmask compliance` prints the full binding. The generic copy lives in
`support-ontology/`; set `TICKETMASK_ONTOLOGY_DIR` to use a tailored one.

The consequences that matter:

- **`sup:Contact` and the three internal role classes are pairwise disjoint**
  (`C-52`). They are separate entity types, so a KB article can still tell
  "the customer reported" from "the agent did". All four are pseudonymized
  identically, so a misclassification is a labelling error, never a leak.
- **A name with no deny-list hit becomes `PERSON_UNRESOLVED`.** The ontology
  deliberately has no generic person layer (`OQ-47`), so there is no class to
  assign, and its rule 5 forbids guessing a mapping. Masked, not classified.
- **`sup:Ticket` and `sup:JiraIssue` are disjoint** (`EQ-04`) and both get
  called "ticket". `TICKET_NUMBER` and `JIRA_ISSUE_KEY` are separate types for
  exactly that reason.
- **`sup:Account` and `sup:Partner` are disjoint.** A partner raising a ticket
  on an account's behalf is not that account.
- **Controlled vocabulary is KEPT, never masked.** Masking `Platinum`, `EMEA`
  or `S1` would destroy the reasoning the ontology exists to enable — the
  alias resolution in `EQ-02` and `EQ-03` needs those labels intact.
- **CRM deny-lists outrank controlled vocabulary in `arbitrate.py`.** An
  account genuinely named "Premium Widgets" must mask whole rather than half-
  keep as an entitlement term.

Nothing here edits the ontology. Drift is reported, not fixed.

### Decisions already made — do not relitigate without reason

- **Presidio over PIIGhost.** PIIGhost's design ideas (stable placeholders, tolerant entity
  linking) are reimplemented here in `linker.py`; the dependency itself is too young to put
  in front of a client security review.
- **Typed placeholders (`<CONTACT_1>`), not realistic fake names.** If a surrogate leaks into
  a published article it must read as an obvious bug, not as a real customer.
- **Vault scoped per ticket, not globally.** A global surrogate space would let someone
  correlate `<CONTACT_7>` across the corpus, rebuilding the linkage we are breaking.
- **Unmasking is for the audit path only.** KB articles ship de-identified, permanently.
  `unmask()` exists so a reviewer can trace a claim back to its source ticket.
- **Unmapped entity types raise.** A new Presidio recognizer must break the build rather
  than silently leak a new entity type into articles.
- **Audit CSV excludes original values by default.** Otherwise the audit trail becomes a
  second, unencrypted PII store.

## Running it

Setup and the full command reference are in `README.md`. Installed with
`pip install -e .`, so there is a `ticketmask` command and no PYTHONPATH.

```bash
.venv/Scripts/python.exe scripts/measure.py -v
```

```bash
.venv/Scripts/ticketmask.exe compliance
```

`TICKETMASK_VAULT_KEY` must be set (see `.env.example`). In production it comes from a KMS.

## Working agreements

- **Tune thresholds against `scripts/measure.py`, never by intuition.** Every threshold
  change must be justified by a measured leak-rate or precision delta.
- **Leak rate is the headline metric**, not recall. A Contact masked as PERSON_UNRESOLVED
  is a type error, not a leak — the value still never reaches the model.
- **Over-masking is a real cost.** Masking product names produces articles about
  configuring `<PRODUCT_2>`, which are worthless. Precision matters here.
- Deny-lists are the highest-precision signal available, and each maps to one ontology
  class. Every engagement should populate all of them from the client's CRM, helpdesk
  directory and licensing system. See the table in `README.md`.
- `data/`, `vault/` and `.env` are gitignored and must stay that way.

## Gaps this work exposes in the ontology

Recorded here, not fixed there — the ontology has its own changelog and review
discipline. Raise them as open questions if they are worth acting on.

- **There is no data-classification layer.** Nothing marks which properties are
  personal data, so the masking policy in `policy.py` had to be invented rather
  than derived. This is the biggest gap: two systems now hold an opinion about
  what is sensitive, and only one of them is the source of truth.
- **No device or asset class.** `sup:License` covers licence keys (alias
  "Serial"); hardware serials in ticket bodies map to nothing.
- **`sup:Contact` models `emailAddress` but no phone property**, though phone
  numbers are everywhere in real ticket text.
- **No host/infrastructure class**, so IP and MAC addresses are unbound.
- **`Contact.emailAddress` is Required.** A de-identified export cannot satisfy
  that constraint, which is worth deciding deliberately.

## Known limitations

- **The product catalog does not match the ontology.** `DEFAULT_PRODUCTS` is a generic
  vendor list. Your own products (from `Product.md` or `--products`) are not on it, and
  neither are the severity names (System Down, Work Stoppage).
  `v_unprotected_ontology_vocabulary` in the SQL export lists every gap. A spot check did
  not over-mask them, but nothing protects them if NER tags one as an organization.

- **NER is weak on tabular data and on locations.** Both outstanding corpus
  leaks are place names — one inside a pasted CSV row, one that spaCy tags as a
  place in isolation but misses two words after "Region: APAC". Populating
  `--sites` from CRM account addresses takes the corpus to a 0% leak rate; that
  is the fix, not a threshold change.
- **Presidio's email regex is greedy on the local part**, so `user=r.chen@corp.com` in a log
  line masks as one span including `user=`. Legal per RFC 5322; costs a little readability,
  leaks nothing.
- **Serial/account patterns are format-specific.** They are defaults, not universals —
  override `RecognizerConfig` per engagement.
- **The synthetic corpora are small.** `tests/corpus/` (6 tickets) is the regression
  baseline; `samples/` (20 tickets, 120 spans, 95.0% recall with its deny-lists) holds
  deliberate gaps to tune against. Both are directional until measured against a real export.
