"""Local front end for masking a ticket export.

Runs entirely on this machine. It calls the same code the CLI calls, so
anything demonstrated here is reproducible from a terminal, and nothing here
is a second implementation of the masking rules.

The part that earns the UI is field mapping. Which column holds the ticket
text and which columns hold names differs for every helpdesk export; the
pipeline downstream of that does not care. Those two mappings are the only
things that change between engagements, so they are the only things this app
asks about.

    .venv/Scripts/python.exe -m streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ticketmask import RecognizerConfig, TicketMasker          # noqa: E402
from ticketmask.cli import load_dotenv, normalize_markup, read_rows  # noqa: E402
from ticketmask.vault import VaultStore                        # noqa: E402


load_dotenv(str(ROOT / ".env"))

# Column-name guesses, ordered best-first. Only ever preselect a dropdown —
# the mapping is always the operator's to confirm.
ID_HINTS = ("id", "ticket_id", "ticket_number", "number", "key", "case_number")
TEXT_HINTS = ("title", "subject", "content", "description", "body", "summary",
              "comments", "comment", "notes", "resolution")
CONTACT_HINTS = ("created_by", "requester", "reporter", "contact", "customer", "author")
AGENT_HINTS = ("responsible", "assignee", "completed_by", "agent", "assigned_to", "owner")
ACCOUNT_HINTS = ("user_team", "account", "organization", "organisation", "company", "org")

JUNK = {"-", "", "n/a", "none", "null", "users", "unassigned", "unknown", "public"}

st.set_page_config(page_title="ticketmask", page_icon="🛡️", layout="wide")
st.title("ticketmask")
st.caption("De-identify a ticket export on this machine. Only the masked data leaves.")


def guess(columns: list[str], hints: tuple[str, ...]) -> list[str]:
    lowered = {c.lower(): c for c in columns}
    return [lowered[h] for h in hints if h in lowered]


def state(key, default=None):
    return st.session_state.get(key, default)


# ---------------------------------------------------------------- 1. source

st.header("1 · Ticket export")

candidates = sorted(
    p for folder in ("samples", "data/in", "Ticket examples")
    for p in (ROOT / folder).glob("*")
    if p.suffix.lower() in {".json", ".jsonl", ".ndjson", ".csv"}
    and ".annotated" not in p.name      # ground-truth labels, not an export
)

if not candidates:
    st.warning("No exports found in `samples/` or `data/in/`.")
    st.stop()

source = st.selectbox(
    "Export file",
    candidates,
    format_func=lambda p: str(p.relative_to(ROOT)),
)

try:
    rows = read_rows(Path(source))
except SystemExit as exc:
    st.error(str(exc))
    st.stop()

if not rows:
    st.error("That export parsed to zero tickets.")
    st.stop()

columns = sorted({key for row in rows[:50] for key in row})
st.success(f"{len(rows)} tickets · {len(columns)} columns")

with st.expander("Preview first ticket"):
    st.json(rows[0], expanded=False)

# --------------------------------------------------------- 2. field mapping

st.header("2 · Field mapping")
st.caption(
    "The only per-export configuration. Everything after this step is the same "
    "for every helpdesk."
)

left, right = st.columns(2)

with left:
    st.subheader("What to mask")
    id_guess = guess(columns, ID_HINTS)
    id_field = st.selectbox(
        "Ticket ID column", columns,
        index=columns.index(id_guess[0]) if id_guess else 0,
    )
    text_fields = st.multiselect(
        "Ticket text columns", columns, default=guess(columns, TEXT_HINTS),
        help="Free-text to mask. Skip count columns — a `comments` "
             "column holding \"8\" is a reply count, not the replies.",
    )
    for field in text_fields:
        sample = str(rows[0].get(field, ""))
        if sample.strip().isdigit():
            st.warning(f"`{field}` looks like a count (first value: {sample!r}), not text.")

with right:
    st.subheader("Where the names are")
    st.caption("Structured columns beat NER. Each maps to one ontology class.")
    contact_cols = st.multiselect("Customer contacts (sup:Contact)", columns,
                                  default=guess(columns, CONTACT_HINTS))
    agent_cols = st.multiselect("Support agents (sup:SupportAgent)", columns,
                                default=guess(columns, AGENT_HINTS))
    account_cols = st.multiselect("Accounts (sup:Account)", columns,
                                  default=guess(columns, ACCOUNT_HINTS))


def harvest(cols: list[str]) -> list[str]:
    values = set()
    for row in rows:
        for col in cols:
            value = str(row.get(col) or "").strip()
            if value.lower() not in JUNK:
                values.add(value)
    return sorted(values, key=str.lower)


contacts, agents, accounts = harvest(contact_cols), harvest(agent_cols), harvest(account_cols)
st.info(f"Deny-lists harvested — {len(contacts)} contacts · {len(agents)} agents · {len(accounts)} accounts")

strip_markup = st.checkbox(
    "Normalize `[br]` / `<br>` markup before masking", value=True,
    help="Markup fuses with adjacent words and defeats tokenisation, which costs "
         "recall on sign-off names. Leave on unless you have a reason.",
)

# ---------------------------------------------------------------- 3. masking

st.header("3 · Mask")

if not text_fields:
    st.warning("Pick at least one ticket text column above.")
elif st.button("Mask tickets", type="primary"):
    out_dir = ROOT / "data" / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    masker = TicketMasker(RecognizerConfig(
        contacts=contacts, support_agents=agents, accounts=accounts,
    ))
    store = VaultStore(str(ROOT / "vault"))

    masked_path = out_dir / "masked.jsonl"
    totals: dict[str, int] = {}
    progress = st.progress(0.0, text="Masking…")

    with masked_path.open("w", encoding="utf-8") as handle:
        for index, row in enumerate(rows, start=1):
            doc_id = str(row.get(id_field) or f"row-{index}")
            merged = "\n\n".join(str(row.get(f) or "") for f in text_fields)
            if strip_markup:
                merged = normalize_markup(merged)

            result = masker.mask(merged, doc_id)
            store.save(result.vault)
            handle.write(json.dumps(
                {"doc_id": doc_id, "text": result.masked_text, "entity_counts": result.counts},
                ensure_ascii=False,
            ) + "\n")

            for entity, count in result.counts.items():
                totals[entity] = totals.get(entity, 0) + count
            progress.progress(index / len(rows), text=f"Masking… {index}/{len(rows)}")

    progress.empty()
    st.session_state["masked_path"] = str(masked_path)
    st.session_state["totals"] = totals
    st.success(f"Masked {len(rows)} tickets → `{masked_path.relative_to(ROOT)}`")

if state("totals"):
    st.bar_chart(state("totals"), horizontal=True, height=280)

# Spot-check: paste values you know are in the raw export and confirm none of
# them survived. This is the check a client's security reviewer will ask for.
if state("masked_path"):
    with st.expander("Leak spot-check"):
        needles = st.text_input(
            "Known PII from the raw export, comma-separated",
            placeholder="Maria Gonzalez, contoso.com, maria.gonzalez@contoso.com",
        )
        if needles.strip():
            blob = Path(state("masked_path")).read_text(encoding="utf-8").lower()
            for needle in [n.strip() for n in needles.split(",") if n.strip()]:
                if needle.lower() in blob:
                    st.error(f"LEAKED — `{needle}` survived masking")
                else:
                    st.success(f"clean — `{needle}`")

# ---------------------------------------------------------- 4. masked data

if state("masked_path"):
    st.header("4 · Masked data")
    st.caption("This file is what may go to a local or closed-source model. "
               "The vault stays here.")
    masked = Path(state("masked_path")).read_text(encoding="utf-8")
    st.download_button("Download masked.jsonl", masked, file_name="masked.jsonl",
                       mime="application/jsonl")
