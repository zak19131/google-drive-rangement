#!/usr/bin/env python3
"""Exécution traçable du plan (logs/plan_actions.csv).

Le MCP Google Drive n'est appelable que par l'agent : ce script prépare les lots et journalise.
  --dry-run            affiche les opérations restantes (défaut)
  --emit N [--size K]  imprime le lot N (JSON : fileId, parentId, title) des opérations restantes
  --record ID...       consigne comme exécutées les opérations des IDs fournis (après succès confirmé)
  --rollback           imprime les opérations inverses depuis logs/rollback.csv
Avec rclone configuré (remote 'gdrive:'), les mêmes lots peuvent être rejoués hors agent.
Journaux : logs/actions.log (append), logs/moves.csv, logs/renames.csv, logs/rollback.csv.
"""
import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PLAN = BASE / "logs" / "plan_actions.csv"
IDS = json.loads((BASE / "logs" / "folder_ids.json").read_text())
DONE = BASE / "logs" / "rollback.csv"
EXEC = {"MOVE_RENAME", "TRASH", "INBOX", "FOLDER_MOVE"}


def done_ids():
    if not DONE.exists():
        return set()
    return {r["id"] for r in csv.DictReader(DONE.open(encoding="utf-8"))}


def pending():
    d = done_ids()
    ops = []
    for p in csv.DictReader(PLAN.open(encoding="utf-8")):
        if p["action"] in EXEC and p["id"] not in d:
            ops.append(p)
    # Ordre : fichiers d'abord, dossiers ensuite (le contenu d'un dossier à corbeille ne bouge pas)
    return sorted(ops, key=lambda p: (p["kind"] == "folder", p["target"], p["new_title"]))


def call(p):
    title = p["new_title"] if p["action"] in ("MOVE_RENAME", "FOLDER_MOVE") else p["old_title"]
    return {"fileId": p["id"], "parentId": IDS[p["target"]], "title": title}


def append(path, row, cols):
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        if new:
            w.writeheader()
        w.writerow(row)


def record(ids):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    plan = {p["id"]: p for p in csv.DictReader(PLAN.open(encoding="utf-8"))}
    with (BASE / "logs" / "actions.log").open("a", encoding="utf-8") as log:
        for i in ids:
            p = plan[i]
            c = call(p)
            append(BASE / "logs" / "moves.csv", dict(ts=now, action=p["action"], id=i, old_path=p["old_path"],
                   new_path=f"{p['target']}/{c['title']}"), ["ts", "action", "id", "old_path", "new_path"])
            if c["title"] != p["old_title"]:
                append(BASE / "logs" / "renames.csv", dict(ts=now, id=i, old_title=p["old_title"], new_title=c["title"]),
                       ["ts", "id", "old_title", "new_title"])
            append(DONE, dict(ts=now, id=i, old_parent=p["old_parent"], old_title=p["old_title"],
                   new_parent=c["parentId"], new_title=c["title"]),
                   ["ts", "id", "old_parent", "old_title", "new_parent", "new_title"])
            log.write(f"{now} | {p['action']} | {p['old_path']} -> {p['target']}/{c['title']}\n")
    print(f"{len(ids)} opérations consignées")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--emit", type=int)
    ap.add_argument("--size", type=int, default=25)
    ap.add_argument("--record", nargs="+")
    ap.add_argument("--rollback", action="store_true")
    a = ap.parse_args()
    if a.record:
        return record(a.record)
    if a.rollback:
        for r in reversed(list(csv.DictReader(DONE.open(encoding="utf-8")))):
            print(json.dumps({"fileId": r["id"], "parentId": r["old_parent"], "title": r["old_title"]}, ensure_ascii=False))
        return 0
    ops = pending()
    if a.emit is not None:
        batch = ops[a.emit * a.size:(a.emit + 1) * a.size]
        for p in batch:
            print(json.dumps(call(p), ensure_ascii=False))
        return 0
    for p in ops:
        c = call(p)
        print(f"[DRY-RUN] {p['action']:12} {p['old_path']}  ->  {p['target']}/{c['title']}")
    print(f"{len(ops)} opérations restantes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
