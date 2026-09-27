#!/usr/bin/env bash
# Contrôle hebdomadaire du Drive (lecture seule).
# Prérequis : un export frais dans inventaire/raw_drive_export.txt (produit par l'agent via MCP Drive,
# ou par `rclone lsjson -R gdrive:` converti). Le script ne modifie jamais le Drive.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 scripts/parse_inventory.py >/dev/null
python3 scripts/find_duplicates.py >/dev/null

python3 - <<'EOF'
import csv, sys
from datetime import date, datetime
rows = [r for r in csv.DictReader(open("inventaire/drive_inventory.csv", encoding="utf-8")) if r["owner"] == "me"]
alerts = []
root = [r for r in rows if "RACINE" in r["flags"]]
inbox = [r for r in rows if r["path"].startswith("/00_INBOX/")]
depth = [r for r in rows if r["depth"] and int(r["depth"]) > 4 and "/07_PERSONNEL/Photos/" not in r["path"]]
trash = [r for r in rows if r["path"].startswith("/99_CORBEILLE/")]
old_trash = [r for r in trash if (date.today() - datetime.strptime(r["modified"][:10], "%Y-%m-%d").date()).days > 30]
if root: alerts.append(f"{len(root)} fichier(s) en vrac à la racine -> déplacer dans 00_INBOX")
if len(inbox) > 20: alerts.append(f"00_INBOX contient {len(inbox)} éléments (> 20) -> trier")
if depth: alerts.append(f"{len(depth)} élément(s) au-delà de 3 niveaux")
if old_trash: alerts.append(f"{len(old_trash)} élément(s) en 99_CORBEILLE depuis > 30 jours -> suppression définitive à valider")
print(f"Drive : {len(rows)} éléments | INBOX {len(inbox)} | CORBEILLE {len(trash)}")
print("\n".join("ALERTE : " + a for a in alerts) or "OK : aucune alerte")
EOF

python3 scripts/rename_files.py --check inventaire/drive_inventory.csv | tail -1
grep -m1 "Synthèse" rapports/doublons.md || true
