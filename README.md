# ticketmask

Mask the personal data in support tickets on your own machine, so the text can
go to a local model and then a closed-source model (Claude, ChatGPT) without
customer data ever leaving.

![Workflow](docs/workflow.svg)

## What's in the box

| Part | Where | What it does |
|---|---|---|
| **Presidio masking app** | `src/ticketmask/`, `app/` | Detects and masks PII in ticket exports using [Microsoft Presidio](https://github.com/microsoft/presidio) plus ticket-specific recognizers and deny-lists. Per-ticket encrypted vault for audit. CLI and a Streamlit UI. |
| **Generic support ontology** | `support-ontology/` | 17 classes (Account, Contact, Ticket, Product, SeverityLevel…) that every masking entity type binds to. Template products, CRMs and severity wording to replace with your own. Browse it in `support-ontology/Navigator/index.html`. |
| **Sample tickets** | `samples/` | 20 synthetic tickets with ground-truth PII labels, matching deny-lists, and CSV/JSON exports for testing. |

Ticket data never leaves your machine: masking runs locally, and the model runs
locally through Ollama.

## Quick start

```bash
python -m venv .venv
.venv/bin/pip install -e .                 # Windows: .\.venv\Scripts\pip
.venv/bin/pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl
cp .env.example .env                       # then set TICKETMASK_VAULT_KEY
```

```bash
ticketmask mask tickets.csv --id-field ticket_id --text-fields subject,description --out data/out
```

`data/out/masked.jsonl` is the masked data: the only output meant to reach a
model, local or closed-source. `vault/` holds the way back and never leaves
your machine.

Or use the UI, which also maps your export's columns for you: `pip install -e .[app]`, then
`streamlit run app/streamlit_app.py`.

## Try it with the sample data

Everything in `samples/` is fictional. `tickets.annotated.jsonl` is the source
of truth, with every PII span labelled `[[TYPE|value]]`. `tickets.csv` and
`tickets.json` are the same tickets as a helpdesk would export them
(regenerate with `python scripts/build_samples.py`).

Measure leaks against the labels:

```bash
python scripts/measure.py --corpus samples/tickets.annotated.jsonl --deny-lists samples/deny-lists -v
```

Mask the export the way you would a real one:

```bash
ticketmask mask samples/tickets.csv --id-field ticket_id --text-fields subject,description,comments --accounts samples/deny-lists/accounts.txt --partners samples/deny-lists/partners.txt --contacts samples/deny-lists/contacts.txt --agents samples/deny-lists/agents.txt --sales-reps samples/deny-lists/sales-reps.txt --csms samples/deny-lists/csms.txt --sites samples/deny-lists/sites.txt --products samples/deny-lists/products.txt --out data/out
```

The contacts and sites lists are deliberately incomplete, as a real CRM export
would be. Some tickets also contain things no recognizer catches yet (a street
address, an untagged API key, a Windows username in a file path). Those leaks
are on purpose and show what to tune next.

## Browse the ontology

Open `support-ontology/Navigator/index.html` in a browser. It is an interactive
graph of the 17 classes and 26 relationships. Click a class to see its
definition, aliases, attributes and constraints. If your browser blocks local
scripts, serve the folder instead:

```bash
python -m http.server 8765 --directory support-ontology/Navigator
```

Rebuild it after editing the ontology with `python support-ontology/scripts/build_graph.py`.

## Making the ontology yours

The bundled ontology in `support-ontology/` is generic. To tailor it:

1. Edit the markdown in `support-ontology/Ontology/`, starting with
   `Entities/Product.md` (your products), `Entities/CRM.md` (your ticketing
   systems) and `Entities/SeverityLevel.md` (your severity policy).
2. Run `python support-ontology/scripts/validate_ontology.py`.
3. Regenerate the navigator and exports with `python support-ontology/scripts/build_graph.py`, `python support-ontology/scripts/export_glossary_csv.py`
   and `python support-ontology/scripts/export_rdf.py`.
4. Run `ticketmask compliance` to confirm the masker is still in sync.

To keep a private ontology outside the repo, point `TICKETMASK_ONTOLOGY_DIR` at
it. The folder needs the same `Ontology/` and `Export/` layout.

---

## Setup (once)

From a normal PowerShell window in this folder. Python 3.11+ required; built
and tested on 3.14.

```powershell
py -3.14 -m venv .venv
```

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

```powershell
.\.venv\Scripts\python.exe -m pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl
```

The spaCy model is a 400 MB download and is not on PyPI, which is why it is a
separate line rather than a dependency.

Then create a vault key:

```powershell
.\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print('TICKETMASK_VAULT_KEY=' + Fernet.generate_key().decode())" | Out-File -FilePath .env -Encoding utf8
```

`.env` is gitignored. In production this key comes from a KMS or Key Vault, not
a file — the CLI reads the environment first and only falls back to `.env`.

## Running it

Installing with `-e .` puts a `ticketmask` command inside the venv, so no
`PYTHONPATH` juggling is needed.

**Activate the venv once per shell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation script, either run this once for the
current user, or skip activation and call `.\.venv\Scripts\ticketmask.exe`
directly:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

**Mask an export:**

```powershell
ticketmask mask data\in\tickets.csv --id-field ticket_id --text-fields subject,description,comments --accounts data\in\accounts.txt --agents data\in\agents.txt --out data\out
```

**Check one snippet and see every decision:**

```powershell
ticketmask inspect --text "Maria Gonzalez at Contoso, ticket INC0044719, severity S2"
```

**Show how entity types bind to the ontology:**

```powershell
ticketmask compliance
```

**Export the ontology and masking actions as SQL (for an ER tool):**

```powershell
.\.venv\Scripts\python.exe scripts\export_ontology_sql.py --check
```

Writes `sql\support_ontology_er.sql`, regenerated from the ontology markdown and
`policy.py`, so never edit it by hand. `--check` loads it into SQLite and tests
it. The header of the SQL file explains the four parts. Import Part 1 alone for a
plain ER diagram.

**Measure recall against the annotated corpus:**

```powershell
.\.venv\Scripts\python.exe scripts\measure.py -v
```

Exits non-zero when leaks exist, so it drops straight into CI.

### On macOS or Linux

Same thing with forward slashes: `python3 -m venv .venv`,
`.venv/bin/pip install -e .`, then `.venv/bin/ticketmask`.

## Inputs

`mask` accepts `.csv`, `.json` or `.jsonl`. `--text-fields` names the columns to
mask; they are joined per ticket so one person keeps one surrogate across
subject and comments.

The deny-list files are one term per line, `#` for comments. They map to
ontology classes, which the ontology declares pairwise disjoint — a Contact is
not a SupportAgent, an Account is not a Partner:

| Flag | Ontology class | Source |
|---|---|---|
| `--accounts` | `sup:Account` | CRM account names |
| `--partners` | `sup:Partner` | CRM partner records |
| `--contacts` | `sup:Contact` | CRM contacts |
| `--agents` | `sup:SupportAgent` | helpdesk user directory |
| `--sales-reps` | `sup:SalesRepresentative` | CRM users |
| `--csms` | `sup:CustomerSuccessManager` | CRM users |
| `--sites` | (site addresses) | CRM account addresses |
| `--products` | `sup:Product` | licensing system — **kept, never masked** |

These are the highest-precision signal available. Everything else is inference.

## Outputs

| Path | Contents | Sensitivity |
|---|---|---|
| `data/out/masked.jsonl` | de-identified text — this is what the model sees | safe to move |
| `data/out/audit.csv` | every masking decision, no original values by default | safe to move |
| `vault/*.vault` | encrypted surrogate → original map, one per ticket | **PII** |

The vault must never travel with `masked.jsonl`. Pass `--no-vault` to make
masking one-way and write nothing recoverable.

## What it does not do

- **Teams, Slack and email are out of scope.** Ticket data only, deliberately.
- **`unmask()` is for the audit path only.** KB articles ship de-identified
  permanently; unmasking exists so a reviewer can trace a claim to its source
  ticket.
- **It does not replace local inference.** Masking stops PII reaching the
  *output*; local inference stops it reaching a *third party*. Different
  controls, different threats.

See [CLAUDE.md](CLAUDE.md) for the architecture and the decisions behind it.

## License

[MIT](LICENSE)
