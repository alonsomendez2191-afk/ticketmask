"""Batch-mask a ticket export.

    python -m ticketmask mask data/in/tickets.csv \
        --id-field ticket_id --text-fields subject,description,comments \
        --orgs data/in/customers.txt --agents data/in/agents.txt \
        --out data/out

Writes three things:
  <out>/masked.jsonl   the de-identified corpus — this is what the model sees
  <out>/audit.csv      every masking decision, for the compliance reviewer
  <vault dir>/*.vault  encrypted reverse maps, for the audit path only

The vault directory is PII. It must not travel with masked.jsonl.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

from .pipeline import TicketMasker
from .recognizers import RecognizerConfig
from .vault import VaultStore


def load_dotenv(path: str = ".env") -> None:
    """Minimal .env reader so the CLI works without a shell export.

    Deliberately not python-dotenv: one fewer dependency to justify in a
    security review, and the format we use is three lines of KEY=value.
    Existing environment variables always win, so a KMS-injected key is never
    overwritten by a stale file.
    """
    env_file = Path(path)
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def read_rows(path: Path) -> list[dict]:
    """Read a ticket export. JSONL and CSV cover most helpdesk exports."""
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return payload
        if isinstance(payload.get("tickets"), list):
            return payload["tickets"]
        # Helpdesk exports wrap the array in one named key, and the name varies
        # by vendor ("Public tickets", "results", "issues"). Take it when the
        # payload is unambiguous rather than making every export a code change.
        arrays = [value for value in payload.values() if isinstance(value, list)]
        if len(arrays) == 1:
            return arrays[0]
        raise SystemExit(
            f"Cannot find the ticket array in {path.name}. "
            f"Top-level keys: {sorted(payload)}"
        )
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    raise SystemExit(f"Unsupported export format: {path.suffix}. Use .csv, .json or .jsonl")


#: Line-break and entity markup that helpdesk exports embed in ticket bodies.
#: Left in place it fuses with the adjacent word ("Maria..[br][br]"), which
#: defeats tokenisation and costs recall on exactly the sign-off names an
#: article must never carry. Only these known tokens are rewritten; arbitrary
#: bracketed text is content and is left alone.
MARKUP_RE = re.compile(r"\[br\]|<br\s*/?>|&nbsp;|&#160;", re.IGNORECASE)


def normalize_markup(text: str) -> str:
    """Replace embedded line-break markup with real whitespace."""
    return MARKUP_RE.sub("\n", text)


def read_list(path: str | None) -> list[str]:
    """One term per line. Blank lines and # comments ignored."""
    if not path:
        return []
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


#: CLI flag -> RecognizerConfig field. Each list maps to one ontology class,
#: because the ontology declares those classes disjoint: an Account is not a
#: Partner, a Contact is not a SupportAgent. One merged "names" list would mask
#: just as well and lose every distinction a KB article needs.
DENY_LIST_FLAGS = {
    "accounts": ("--accounts", "customer org names (sup:Account), from the CRM"),
    "partners": ("--partners", "partner/ISV org names (sup:Partner), from the CRM"),
    "contacts": ("--contacts", "customer contact names (sup:Contact), from the CRM"),
    "support_agents": ("--agents", "agent handles (sup:SupportAgent), from the helpdesk directory"),
    "sales_representatives": ("--sales-reps", "sales rep names (sup:SalesRepresentative)"),
    "customer_success_managers": ("--csms", "CSM names (sup:CustomerSuccessManager)"),
    "locations": ("--sites", "customer site/city names, from CRM account addresses"),
    "products": ("--products", "product names (sup:Product) — kept, never masked"),
}


def add_deny_list_flags(parser: argparse.ArgumentParser) -> None:
    for field_name, (flag, help_text) in DENY_LIST_FLAGS.items():
        parser.add_argument(flag, dest=field_name, help=f"file of {help_text}")


def config_from_args(args: argparse.Namespace) -> RecognizerConfig:
    values = {}
    for field_name in DENY_LIST_FLAGS:
        terms = read_list(getattr(args, field_name, None))
        if terms:
            values[field_name] = terms
    return RecognizerConfig(**values)


def cmd_mask(args: argparse.Namespace) -> int:
    source = Path(args.source)
    rows = read_rows(source)
    if not rows:
        raise SystemExit(f"No rows found in {source}")

    text_fields = [f.strip() for f in args.text_fields.split(",")]
    available = set(rows[0].keys())
    missing = [f for f in text_fields + [args.id_field] if f not in available]
    if missing:
        raise SystemExit(
            f"Fields not in export: {missing}\nAvailable columns: {sorted(available)}"
        )

    config = config_from_args(args)
    masker = TicketMasker(config)
    store = None if args.no_vault else VaultStore(args.vault_dir)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    masked_path = out_dir / "masked.jsonl"
    audit_path = out_dir / "audit.csv"

    totals: dict[str, int] = {}
    audit_rows: list[dict] = []

    with masked_path.open("w", encoding="utf-8") as masked_out:
        for index, row in enumerate(rows, start=1):
            doc_id = str(row.get(args.id_field) or f"row-{index}")
            record = {"doc_id": doc_id}

            # One vault per ticket, shared across that ticket's fields, so the
            # same person keeps one surrogate across subject and comments.
            merged = "\n\n".join(str(row.get(f) or "") for f in text_fields)
            if not args.keep_markup:
                merged = normalize_markup(merged)
            result = masker.mask(merged, doc_id)

            record["text"] = result.masked_text
            record["entity_counts"] = result.counts
            masked_out.write(json.dumps(record, ensure_ascii=False) + "\n")

            audit_rows.extend(result.audit_rows())
            for entity_type, count in result.counts.items():
                totals[entity_type] = totals.get(entity_type, 0) + count

            if store:
                store.save(result.vault)

            if index % 100 == 0:
                print(f"  ...{index} tickets", file=sys.stderr)

    if args.audit_originals:
        fieldnames = ["doc_id", "entity_type", "action", "score", "start", "end", "original"]
    else:
        # Default: the audit file records WHAT was masked, not the values.
        # Including originals turns the audit trail into a second PII store.
        fieldnames = ["doc_id", "entity_type", "action", "score", "start", "end"]
        audit_rows = [{k: v for k, v in r.items() if k != "original"} for r in audit_rows]

    with audit_path.open("w", encoding="utf-8", newline="") as audit_out:
        writer = csv.DictWriter(audit_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(audit_rows)

    print(f"\nmasked {len(rows)} tickets -> {masked_path}")
    print(f"audit trail          -> {audit_path}")
    if store:
        print(f"encrypted vaults     -> {store.directory}  (PII — keep separate)")
    else:
        print("vaults               -> NOT written (--no-vault): masking is one-way")
    print("\nentities masked:")
    for entity_type, count in sorted(totals.items(), key=lambda kv: -kv[1]):
        print(f"  {entity_type:20} {count:>6}")
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    """Mask a single string and show every decision. For tuning."""
    config = config_from_args(args)
    text = Path(args.file).read_text(encoding="utf-8") if args.file else args.text
    result = TicketMasker(config).mask(text, "inspect")

    print("--- masked ---")
    print(result.masked_text)
    print("\n--- decisions ---")
    for d in result.decisions:
        print(f"  {d.entity_type:18} {d.action.value:14} {d.score:.2f}  {d.text!r}")
    return 0


def cmd_compliance(args: argparse.Namespace) -> int:
    """Show how every entity type binds to the support ontology."""
    from .ontology import (
        ENTITY_BINDINGS, ONTOLOGY_CLASSES, ontology_dir,
        unbound_entities, verify_against_export,
    )
    from .policy import DEFAULT_POLICY

    print(f"ontology: {ontology_dir()}")
    drift = verify_against_export()
    if drift:
        for problem in drift:
            print(f"  DRIFT: {problem}")
    else:
        print(f"  in sync — {len(ONTOLOGY_CLASSES)} classes")

    print("\nentity type -> ontology binding -> action")
    for entity_type in sorted(DEFAULT_POLICY):
        binding = ENTITY_BINDINGS.get(entity_type)
        ref = binding.sup_ref if binding and binding.sup_ref else "—"
        action = DEFAULT_POLICY[entity_type].action.value
        print(f"  {entity_type:26} {ref:30} {action}")

    gaps = unbound_entities()
    print(f"\n{len(gaps)} entity types have no ontology class:")
    for name, reason in sorted(gaps.items()):
        print(f"  {name}\n      {reason}")
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="ticketmask")
    sub = parser.add_subparsers(dest="command", required=True)

    m = sub.add_parser("mask", help="mask a ticket export")
    m.add_argument("source", help="path to .csv / .json / .jsonl export")
    m.add_argument("--id-field", default="id")
    m.add_argument("--text-fields", default="description",
                   help="comma-separated fields to mask, e.g. subject,description,comments")
    add_deny_list_flags(m)
    m.add_argument("--keep-markup", action="store_true",
                   help="skip [br]/<br> normalization before masking (lowers recall)")
    m.add_argument("--out", default="data/out")
    m.add_argument("--vault-dir", default=os.environ.get("TICKETMASK_VAULT_DIR", "./vault"))
    m.add_argument("--no-vault", action="store_true",
                   help="do not write reverse maps — masking becomes irreversible")
    m.add_argument("--audit-originals", action="store_true",
                   help="include original values in audit.csv (makes it a PII file)")
    m.set_defaults(func=cmd_mask)

    i = sub.add_parser("inspect", help="mask one snippet and explain every decision")
    i.add_argument("--text", default="")
    i.add_argument("--file")
    add_deny_list_flags(i)
    i.set_defaults(func=cmd_inspect)

    c = sub.add_parser("compliance", help="report the ontology binding and any drift")
    c.set_defaults(func=cmd_compliance)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
