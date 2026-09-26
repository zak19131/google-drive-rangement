#!/usr/bin/env python3
"""Phase 4 (plan) — Classe l'inventaire selon rules.json (+ rules.local.json).
Produit logs/moves.csv (plan de déplacement, dry-run) et rapports/classification.md.
N'agit jamais sur la boîte : l'exécution réelle passe par l'Apps Script (KM_Mail.gs).

Usage : python3 classify_mails.py [--inventory inventaire/mailbox_inventory.csv] [--recent-days 30]
"""
import argparse
import csv
import datetime as dt
from collections import Counter
from pathlib import Path

from km_common import WORKSPACE, classify, load_rules, log_action, write_csv


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inventory", default=str(WORKSPACE / "inventaire" / "mailbox_inventory.csv"))
    ap.add_argument("--recent-days", type=int, default=30)
    ap.add_argument("--today", default=dt.date.today().isoformat())
    args = ap.parse_args()

    cfg = load_rules()
    today = dt.date.fromisoformat(args.today)
    moves, by_label, unmatched = [], Counter(), Counter()
    with open(args.inventory, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        rule = classify(r["from"], r.get("subject", ""), bool(r.get("list_unsubscribe")), cfg)
        date = dt.date.fromisoformat(r["date"][:10]) if r.get("date") else None
        recent = bool(date and (today - date).days <= args.recent_days)
        if rule:
            label, archive, mark_read = rule["label"], rule.get("archive", False), rule.get("mark_read", False)
            action = bool(rule.get("action_if_recent") and recent)
        elif recent:
            label, archive, mark_read, action = "01_ACTION", True, False, True
            unmatched[r["from_domain"]] += 1
        else:
            label = f"10_ARCHIVES/{date.year if date else 'SANS_DATE'}"
            archive, mark_read, action = True, True, False
            unmatched[r["from_domain"]] += 1
        # Historique : les fils sensibles anciens sortent aussi de INBOX (label conservé)
        if rule and not archive and not recent:
            archive = True
        by_label[label] += 1
        moves.append([r.get("message_id", ""), r.get("thread_id", ""), r.get("date", ""), r["from"],
                      rule["id"] if rule else "non_classe", label, archive, mark_read, action,
                      bool(rule and rule.get("sensitive"))])

    write_csv(WORKSPACE / "logs" / "moves.csv",
              ["message_id", "thread_id", "date", "from", "rule", "label", "archive", "mark_read",
               "add_01_ACTION", "sensitive"], moves)
    # Inverse exact de chaque déplacement planifié (côté Gmail : fonction rollback() de l'Apps Script)
    write_csv(WORKSPACE / "logs" / "rollback.csv",
              ["message_id", "thread_id", "retirer_label", "retirer_01_ACTION", "remettre_INBOX", "remettre_non_lu_si_tag_WAS_UNREAD"],
              [[m[0], m[1], m[5], m[8], m[6], m[7]] for m in moves])
    total = len(rows) or 1
    matched = sum(1 for m in moves if m[4] != "non_classe")
    lines = ["# Classification (dry-run)", "",
             f"- Messages analysés : {len(rows)}",
             f"- Couverts par une règle : {matched} ({matched / total:.0%})",
             f"- Non classés : {len(rows) - matched} (-> 01_ACTION si ≤{args.recent_days} j, sinon 10_ARCHIVES/AAAA)",
             "", "| Label cible | Messages | Part |", "|---|---:|---:|"]
    lines += [f"| {k} | {v} | {v / total:.0%} |" for k, v in by_label.most_common()]
    lines += ["", "## Domaines non couverts (candidats à une nouvelle règle)", "",
              "| Domaine | Messages |", "|---|---:|"]
    lines += [f"| {k or '(vide)'} | {v} |" for k, v in unmatched.most_common(40)]
    out = WORKSPACE / "rapports" / "classification.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log_action("classify_mails", f"{len(rows)} messages, {matched} couverts -> logs/moves.csv", dry_run=True)
    print(f"{len(rows)} messages, {matched} couverts ({matched / total:.0%}) -> {out}")


if __name__ == "__main__":
    main()
