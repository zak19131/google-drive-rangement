#!/usr/bin/env python3
"""Détection des doublons dans l'inventaire (lecture seule).
- Doublon strict : même Message-ID.
- Doublon probable : même expéditeur + objet + minute d'envoi + taille à ±1 %.
Produit rapports/doublons.md. Aucune suppression : les doublons validés passent par 99_CORBEILLE (Apps Script).
"""
import argparse
import csv
from collections import defaultdict

from km_common import WORKSPACE, log_action


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inventory", default=str(WORKSPACE / "inventaire" / "mailbox_inventory.csv"))
    args = ap.parse_args()
    with open(args.inventory, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    by_id, by_sig = defaultdict(list), defaultdict(list)
    for r in rows:
        if r.get("message_id"):
            by_id[r["message_id"]].append(r)
        by_sig[(r["from"], r.get("subject", "").strip().lower(), r.get("date", "")[:16])].append(r)

    strict = {k: v for k, v in by_id.items() if len(v) > 1}
    probable = {}
    for k, v in by_sig.items():
        if len(v) < 2 or all(x.get("message_id") in strict for x in v):
            continue
        sizes = [int(x.get("size_bytes") or 0) for x in v]
        if max(sizes) and (max(sizes) - min(sizes)) / max(sizes) <= 0.01:
            probable[k] = v

    extra_strict = sum(len(v) - 1 for v in strict.values())
    extra_prob = sum(len(v) - 1 for v in probable.values())
    lines = ["# Doublons", "", f"- Messages analysés : {len(rows)}",
             f"- Doublons stricts (Message-ID) : {len(strict)} groupes, {extra_strict} copies en trop",
             f"- Doublons probables : {len(probable)} groupes, {extra_prob} copies en trop",
             "", "Règle : on garde l'exemplaire le plus ancien. Les copies passent en 99_CORBEILLE après validation.",
             "", "## Doublons stricts", "", "| Message-ID | Copies | Expéditeur | Objet |", "|---|---:|---|---|"]
    lines += [f"| `{k[:60]}` | {len(v)} | {v[0]['from']} | {v[0].get('subject', '')[:60]} |" for k, v in list(strict.items())[:200]]
    lines += ["", "## Doublons probables", "", "| Expéditeur | Objet | Date | Copies |", "|---|---|---|---:|"]
    lines += [f"| {k[0]} | {k[1][:60]} | {k[2]} | {len(v)} |" for k, v in list(probable.items())[:200]]
    out = WORKSPACE / "rapports" / "doublons.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log_action("find_duplicates", f"{extra_strict} stricts, {extra_prob} probables", dry_run=True)
    print(f"stricts={extra_strict} probables={extra_prob} -> {out}")


if __name__ == "__main__":
    main()
