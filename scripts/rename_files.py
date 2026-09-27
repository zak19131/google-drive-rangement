#!/usr/bin/env python3
"""Contrôle et proposition de noms selon la convention AAAA-MM-JJ_NATURE_SujetCamelCase_vN.ext.

Usage :
  rename_files.py --check FICHIER.csv     liste les noms non conformes (colonnes path,title,kind)
  rename_files.py --suggest "titre" [--date AAAA-MM-JJ] [--nature NATURE]
Aucune action sur le Drive : les renommages s'exécutent via move_files.py (journalisés, réversibles).
"""
import argparse
import csv
import re
import sys
from datetime import date

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from build_plan import doc_date, nature_of, split_ext, subject_of  # noqa: E402

CONVENTION = re.compile(r"^\d{4}-\d{2}-\d{2}_[A-Z]+_[A-Za-z0-9]+(_\d+)?_v\d+(\.[a-z0-9]{1,5})?$")
# Exceptions validées : séries photo (noms caméra) et dossiers de structure.
EXEMPT = re.compile(r"/07_PERSONNEL/Photos/[^/]+/|/00_INBOX/|/99_CORBEILLE/")


def is_valid(title):
    return bool(CONVENTION.match(title))


def suggest(title, d=None, nature=None, kind="file"):
    stem, ext = split_ext(title, kind)
    nat = nature_of(title, nature)
    return f"{doc_date(title, d or date.today().isoformat())}_{nat}_{subject_of(stem, nat)}_v1{ext}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check")
    ap.add_argument("--suggest")
    ap.add_argument("--date")
    ap.add_argument("--nature")
    a = ap.parse_args()
    if a.suggest:
        print(suggest(a.suggest, a.date, a.nature))
        return 0
    if a.check:
        bad = 0
        for r in csv.DictReader(open(a.check, encoding="utf-8")):
            if r.get("kind") == "folder" or EXEMPT.search(r["path"]):
                continue
            if not is_valid(r["title"]):
                bad += 1
                print(f"NON CONFORME  {r['path']}  ->  {suggest(r['title'], kind=r.get('kind', 'file'))}")
        print(f"{bad} nom(s) non conforme(s)")
        return 1 if bad else 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
