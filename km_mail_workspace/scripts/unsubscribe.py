#!/usr/bin/env python3
"""Désabonnements — en 2 temps, validation obligatoire.
1) (défaut) Liste les expéditeurs newsletter avec leur en-tête List-Unsubscribe
   -> rapports/newsletters.md + logs/desabonnements.csv (colonne VALIDER vide).
2) Après que tu as mis VALIDER=OUI sur des lignes : --execute
   -> désabonnement « one-click » RFC 8058 (POST HTTPS) uniquement pour ces lignes.
   Les liens mailto ne sont jamais envoyés automatiquement (listés à traiter à la main).
Règles sensibles (banque, admin...) : jamais proposées.
"""
import argparse
import csv
import re
import urllib.request
from collections import defaultdict

from km_common import WORKSPACE, classify, load_rules, log_action, write_csv

CSV_PATH = WORKSPACE / "logs" / "desabonnements.csv"
HEADER = ["domaine", "expediteur_exemple", "label", "messages", "derniere_date", "https_one_click",
          "mailto", "VALIDER", "resultat"]


def parse_header(value: str):
    urls = re.findall(r"<([^>]+)>", value or "")
    https = next((u for u in urls if u.lower().startswith("https://")), "")
    mailto = next((u for u in urls if u.lower().startswith("mailto:")), "")
    return https, mailto


def build(inventory: str):
    cfg = load_rules()
    agg = defaultdict(lambda: {"n": 0, "last": "", "from": "", "label": "", "https": "", "mailto": "", "post": False})
    with open(inventory, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rule = classify(r["from"], r.get("subject", ""), bool(r.get("list_unsubscribe")), cfg)
            if not rule or not rule.get("newsletter") or rule.get("sensitive"):
                continue
            a = agg[r["from_domain"]]
            a["n"] += 1
            a["label"] = rule["label"]
            if r.get("date", "") >= a["last"]:
                a["last"], a["from"] = r.get("date", ""), r["from"]
                https, mailto = parse_header(r.get("list_unsubscribe", ""))
                a["https"] = https or a["https"]
                a["mailto"] = mailto or a["mailto"]
                a["post"] = a["post"] or "one-click" in (r.get("list_unsubscribe_post") or "").lower()
    pre = cfg["unsubscribe_prevalidated"]
    is_pre = lambda d: any(d == p or d.endswith("." + p) for p in pre)
    rows = sorted(agg.items(), key=lambda kv: (not is_pre(kv[0]), -kv[1]["n"]))
    write_csv(CSV_PATH, HEADER, [[d, a["from"], a["label"], a["n"], a["last"][:10],
                                  a["https"] if a["post"] else "", a["mailto"], "OUI" if is_pre(d) else "", ""]
                                 for d, a in rows])
    lines = ["# Newsletters et abonnements", "", f"- Expéditeurs newsletter : {len(rows)}",
             f"- Messages concernés : {sum(a['n'] for _, a in rows)}", "",
             f"Pré-validés par le titulaire (VALIDER=OUI déjà rempli) : {', '.join(pre) or 'aucun'}.",
             "Validation : ouvrir logs/desabonnements.csv, mettre OUI dans VALIDER, puis `python3 unsubscribe.py --execute`.",
             "", "| Domaine | Label | Messages | Dernier | One-click |", "|---|---|---:|---|---|"]
    lines += [f"| {d} | {a['label']} | {a['n']} | {a['last'][:10]} | {'oui' if a['post'] and a['https'] else 'non'} |" for d, a in rows]
    (WORKSPACE / "rapports" / "newsletters.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log_action("unsubscribe", f"{len(rows)} expéditeurs listés", dry_run=True)
    print(f"{len(rows)} expéditeurs newsletter -> rapports/newsletters.md, logs/desabonnements.csv")


def execute():
    with CSV_PATH.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    done = 0
    for r in rows:
        if r["VALIDER"].strip().upper() != "OUI" or r["resultat"]:
            continue
        if r["https_one_click"]:
            req = urllib.request.Request(r["https_one_click"], data=b"List-Unsubscribe=One-Click", method="POST",
                                         headers={"Content-Type": "application/x-www-form-urlencoded"})
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    r["resultat"] = f"HTTP {resp.status}"
            except Exception as exc:  # on trace et on continue, sans retenter en boucle
                r["resultat"] = f"ECHEC {type(exc).__name__}"
        else:
            r["resultat"] = "MANUEL (mailto / pas de one-click)"
        done += 1
        log_action("unsubscribe", f"{r['domaine']}: {r['resultat']}", dry_run=False)
    write_csv(CSV_PATH, HEADER, [[r[h] for h in HEADER] for r in rows])
    print(f"{done} lignes validées traitées")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inventory", default=str(WORKSPACE / "inventaire" / "mailbox_inventory.csv"))
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    execute() if args.execute else build(args.inventory)


if __name__ == "__main__":
    main()
