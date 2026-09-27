#!/usr/bin/env python3
"""Transforme inventaire/raw_drive_export.txt en inventaire/drive_inventory.csv.

Ajoute : chemin complet, profondeur, extension, famille de type, drapeaux
(sensible, fichier temporaire Office, fichier vide, sans titre, en racine).
Lecture seule sur le Drive : ce script ne touche qu'aux fichiers locaux.
"""
import csv
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "inventaire" / "raw_drive_export.txt"
OUT = BASE / "inventaire" / "drive_inventory.csv"
ROOT_ID = "0AKlPEcSlE9vRUk9PVA"

# Mots-clés de sensibilité (identité, banque, fiscal, santé, identifiants)
SENSITIVE = [
    r"\bcni\b", "passeport", "carte vitale", r"\brib\b", "rib-", "relev[eé]", "avis_d_impot",
    "avis_de_situation", "d[eé]claration", "impot", "extrait de comptes", "mot de passe",
    "bulletin", "paie", "dsn_", "dpae", "contrat", "kbis", "capital", "quittance",
    "attgdpub", "payfip", "carte", "c\\. c lyonnaise", "edf", "location",
]
FAMILY = {
    "pdf": "PDF", "doc": "TEXTE", "docx": "TEXTE", "odt": "TEXTE", "rtf": "TEXTE", "txt": "TEXTE",
    "md": "TEXTE", "xlsx": "TABLEUR", "pptx": "PRESENTATION", "jpg": "IMAGE", "jpeg": "IMAGE",
    "png": "IMAGE", "wav": "AUDIO", "mp3": "AUDIO", "mov": "VIDEO", "py": "CODE", "ini": "SYSTEME",
}
NATIVE = {"gdoc": "GDOC", "gsheet": "GSHEET", "gslides": "GSLIDES", "folder": "DOSSIER"}


def parse(raw_path):
    rows, section = [], None
    for line in raw_path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.lstrip("@").split("|")]
        if line.startswith("@"):
            pid, pname, cdef, mdef, owner = (parts + [""] * 5)[:5]
            section = dict(parent_id=pid, parent_name=pname, cdef=cdef, mdef=mdef, owner=owner)
            continue
        fid, title, kind, size, created, modified = (parts + [""] * 6)[:6]
        rows.append(dict(
            id=fid, title=title, kind=kind, size=int(size or 0),
            created=created or section["cdef"], modified=modified or section["mdef"],
            parent_id=section["parent_id"], owner=section["owner"],
        ))
    return rows


def build_paths(rows):
    by_id = {r["id"]: r for r in rows}

    def path_of(r, guard=0):
        if r["parent_id"] == ROOT_ID:
            return "/" + r["title"]
        if r["parent_id"] == "SHARED":
            return "[Partagés avec moi]/" + r["title"]
        parent = by_id.get(r["parent_id"])
        if parent is None or guard > 10:
            return "[?]/" + r["title"]
        return path_of(parent, guard + 1) + "/" + r["title"]

    for r in rows:
        r["path"] = path_of(r)
        r["depth"] = r["path"].count("/") if r["owner"] == "me" else ""
    return by_id


def enrich(rows, by_id):
    children = {}
    for r in rows:
        children.setdefault(r["parent_id"], []).append(r)
    for r in rows:
        title_l = r["title"].lower()
        m = re.search(r"\.([A-Za-z0-9]{1,5})$", r["title"])
        r["ext"] = m.group(1).lower() if (m and r["kind"] == "file") else ""
        r["family"] = NATIVE.get(r["kind"]) or FAMILY.get(r["ext"], "AUTRE")
        flags = []
        if r["owner"] != "me":
            flags.append("PARTAGE_EXTERNE")
        if any(re.search(p, title_l) for p in SENSITIVE):
            flags.append("SENSIBLE")
        if r["title"].startswith("~$") or r["ext"] == "ini":
            flags.append("TEMPORAIRE")
        if r["kind"] == "file" and r["size"] < 200:
            flags.append("VIDE_OU_CORROMPU")
        if "sans titre" in title_l or title_l in ("lettre (2)",):
            flags.append("SANS_TITRE")
        if r["parent_id"] == ROOT_ID and r["kind"] != "folder":
            flags.append("RACINE")
        if r["kind"] == "folder" and not children.get(r["id"]):
            flags.append("DOSSIER_VIDE")
        if r["kind"] == "folder" and r["owner"] == "me":
            r["nb_enfants"] = len(children.get(r["id"], []))
        else:
            r["nb_enfants"] = ""
        r["flags"] = ";".join(flags)
    return rows


def main():
    rows = parse(RAW)
    by_id = build_paths(rows)
    enrich(rows, by_id)
    cols = ["id", "path", "title", "kind", "family", "ext", "size", "created", "modified",
            "depth", "owner", "parent_id", "nb_enfants", "flags"]
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in sorted(rows, key=lambda x: x["path"].lower()):
            w.writerow(r)
    mine = [r for r in rows if r["owner"] == "me"]
    print(f"{len(rows)} éléments ({len(mine)} possédés, {len(rows) - len(mine)} partagés) -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
