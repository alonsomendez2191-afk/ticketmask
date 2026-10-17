"""Measure masking recall against the annotated corpus.

The headline number is LEAK RATE: gold PII spans that came out of the pipeline
unmasked. A Contact masked as PERSON_UNRESOLVED is a type error, not a leak
— the value still never reaches the model. Those are tracked separately
because conflating them flatters the results.

Usage:
    python scripts/measure.py [--corpus tests/corpus/annotated_tickets.jsonl] [-v]
    python scripts/measure.py --corpus samples/tickets.annotated.jsonl --deny-lists samples/deny-lists -v
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ticketmask import RecognizerConfig, TicketMasker          # noqa: E402
from ticketmask.cli import DENY_LIST_FLAGS, read_list           # noqa: E402
from ticketmask.corpus import load                              # noqa: E402
from ticketmask.policy import Action, rule_for                  # noqa: E402
from ticketmask.ontology import (                               # noqa: E402
    Binding, ENTITY_BINDINGS, ONTOLOGY_CLASSES, verify_against_export,
)


def overlaps(a_start, a_end, b_start, b_end) -> bool:
    return a_start < b_end and b_start < a_end


def builtin_config() -> RecognizerConfig:
    # Deny-lists a real engagement would pull from the client's CRM and
    # helpdesk directory. Stated here so the numbers are honest about what
    # the pipeline was given.
    return RecognizerConfig(
        accounts=["Northwind Traders", "Contoso", "Fabrikam Logistics",
                  "Tailspin Toys", "Woodgrove Bank", "Adventure Works"],
        partners=["Litware Consulting"],
        support_agents=["jdoe", "asmith", "kpatel"],
        sales_representatives=["Greg Tan"],
        customer_success_managers=["Helen Novak"],
        # Deliberately partial, as a real CRM contact export would be: some
        # names resolve to sup:Contact, the rest fall through to
        # PERSON_UNRESOLVED. Both get masked; only the label differs.
        contacts=["Maria Gonzalez", "Robert Chen", "Priya Raghunathan"],
    )


def config_from_dir(directory: str) -> RecognizerConfig:
    """Deny-list files named after the CLI flags: accounts.txt, agents.txt..."""
    values = {}
    for field_name, (flag, _) in DENY_LIST_FLAGS.items():
        path = Path(directory) / f"{flag.lstrip('-')}.txt"
        if path.exists():
            values[field_name] = read_list(str(path))
    return RecognizerConfig(**values)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", default="tests/corpus/annotated_tickets.jsonl")
    parser.add_argument("--deny-lists", metavar="DIR",
                        help="folder of deny-list files named after the CLI flags "
                             "(accounts.txt, agents.txt, sites.txt, ...) instead of the built-in lists")
    parser.add_argument("-v", "--verbose", action="store_true", help="show every miss and false positive")
    args = parser.parse_args()

    tickets = load(args.corpus)
    config = config_from_dir(args.deny_lists) if args.deny_lists else builtin_config()
    masker = TicketMasker(config)

    per_type = defaultdict(lambda: {"gold": 0, "masked": 0, "type_ok": 0, "expected_keep": 0})
    leaks, type_errors, false_positives = [], [], []

    for ticket in tickets:
        result = masker.mask(ticket.text, ticket.doc_id)
        acted = [d for d in result.decisions if d.action is not Action.KEEP]

        for gold in ticket.gold:
            stats = per_type[gold.entity_type]
            stats["gold"] += 1

            if rule_for(gold.entity_type).action is Action.KEEP:
                stats["expected_keep"] += 1
                continue

            hits = [d for d in acted if overlaps(gold.start, gold.end, d.start, d.end)]
            if hits:
                stats["masked"] += 1
                if any(d.entity_type == gold.entity_type for d in hits):
                    stats["type_ok"] += 1
                else:
                    type_errors.append((ticket.doc_id, gold, hits[0].entity_type))
            else:
                leaks.append((ticket.doc_id, gold))

        for decision in acted:
            if not any(overlaps(decision.start, decision.end, g.start, g.end) for g in ticket.gold):
                false_positives.append((ticket.doc_id, decision))

    total_gold = sum(s["gold"] - s["expected_keep"] for s in per_type.values())
    total_masked = sum(s["masked"] for s in per_type.values())
    total_acted = total_masked + len(false_positives)

    print(f"\ncorpus: {args.corpus}  ({len(tickets)} tickets, {total_gold} maskable gold spans)\n")
    print(f"{'entity type':20} {'gold':>5} {'masked':>7} {'recall':>8} {'type ok':>8}")
    print("-" * 52)
    for entity_type in sorted(per_type):
        s = per_type[entity_type]
        maskable = s["gold"] - s["expected_keep"]
        if maskable == 0:
            print(f"{entity_type:20} {s['gold']:>5} {'—':>7} {'(kept)':>8} {'—':>8}")
            continue
        recall = s["masked"] / maskable
        type_rate = s["type_ok"] / maskable
        flag = "  <-- LEAK" if recall < 1.0 else ""
        print(f"{entity_type:20} {maskable:>5} {s['masked']:>7} {recall:>7.1%} {type_rate:>7.1%}{flag}")

    print("-" * 52)
    recall = total_masked / total_gold if total_gold else 1.0
    precision = total_masked / total_acted if total_acted else 1.0
    print(f"{'TOTAL':20} {total_gold:>5} {total_masked:>7} {recall:>7.1%}")
    print(f"\n  leak rate      {len(leaks) / total_gold:.1%}  ({len(leaks)} unmasked PII spans)")
    print(f"  type errors    {len(type_errors)}  (masked, but as the wrong type — not a leak)")
    print(f"  over-masking   {len(false_positives)}  (masked non-PII; costs article quality)")
    print(f"  precision      {precision:.1%}")

    if leaks:
        print("\n  LEAKS:")
        for doc_id, gold in leaks:
            print(f"    {doc_id}  {gold.entity_type:16} {gold.text!r}")

    # --- ontology compliance ------------------------------------------------
    drift = verify_against_export()
    print("\n  ontology binding")
    if drift:
        for problem in drift:
            print(f"    DRIFT: {problem}")
    else:
        print(f"    in sync with support-ontology ({len(ONTOLOGY_CLASSES)} classes)")

    unbound = {t for t in per_type if ENTITY_BINDINGS.get(t, Binding(None)).sup_ref is None}
    bound = {t for t in per_type if t not in unbound}
    print(f"    {len(bound)}/{len(per_type)} corpus entity types bound to a sup: class")
    if unbound:
        print(f"    unbound: {', '.join(sorted(unbound))}")

    if args.verbose:
        if type_errors:
            print("\n  TYPE ERRORS:")
            for doc_id, gold, got in type_errors:
                print(f"    {doc_id}  {gold.text!r}  expected {gold.entity_type}, got {got}")
        if false_positives:
            print("\n  OVER-MASKED:")
            for doc_id, d in false_positives:
                print(f"    {doc_id}  {d.entity_type:16} {d.text!r}")

    return 1 if leaks else 0


if __name__ == "__main__":
    raise SystemExit(main())
