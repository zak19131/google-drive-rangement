#!/usr/bin/env python3
"""Détecte doublons et versions multiples à partir de inventaire/drive_inventory.csv.

- Doublon CERTAIN : même nom normalisé + même taille (octets) + même extension.
- Doublon PROBABLE : même taille + même extension, noms différents (contenu à confirmer :
  le MCP Drive ne fournit pas de md5).
- Versions : même nom racine avec suffixes (1), (2), Copie, final, V1/V2, _unlocked.
Écrit rapports/doublons.md, rapports/versions.md et inventaire/doublons.csv.
Lecture seule sur le Drive.
"""
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
INV = BASE / "inventaire" / "drive_inventory.csv"

SUFFIX = re.compile(r"(\s*\(\d+\))+|\s*-\s*copie(\s*\(\d+\))?|_unlocked|\s+final", re.I)


def norm(title):
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", title)
    stem = SUFFIX.sub("", stem)
    return re.sub(r"[\s_]+", " ", stem).strip().lower()


def load():
    with INV.open(encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r["owner"] == "me" and r["kind"] != "folder"]


def pick_keeper(group):
    # Garder l'exemplaire au nom le plus propre (sans suffixe), puis le plus ancien créé.
    return sorted(group, key=lambda r: (bool(re.search(r"\(\d+\)|copie", r["title"], re.I)),
                                         r["created"], len(r["path"])))[0]


def main():
    rows = load()
    certain, probable = defaultdict(list), defaultdict(list)
    for r in rows:
        if int(r["size"]) == 0:
            continue  # fichiers vides traités à part
        certain[(norm(r["title"]), r["size"], r["ext"])].append(r)
        probable[(r["size"], r["ext"])].append(r)

    out_rows, md = [], ["# Rapport doublons", "",
                        "Méthode : nom normalisé + taille exacte + extension. Pas de md5 disponible via MCP : "
                        "les groupes « probables » (même taille, noms différents) restent à confirmer visuellement.", ""]
    n_certain_groups = n_certain_extra = bytes_extra = 0
    md += ["## Doublons certains (nom + taille identiques)", "",
           "| Groupe | Garder | Doublons -> 99_CORBEILLE | Taille | Emplacements |", "|---|---|---|---|---|"]
    seen_ids = set()
    for gi, (key, grp) in enumerate(sorted(((k, g) for k, g in certain.items() if len(g) > 1),
                                          key=lambda kg: -int(kg[0][1]) * len(kg[1])), 1):
        keep = pick_keeper(grp)
        extra = [r for r in grp if r["id"] != keep["id"]]
        n_certain_groups += 1
        n_certain_extra += len(extra)
        bytes_extra += sum(int(r["size"]) for r in extra)
        for r in grp:
            seen_ids.add(r["id"])
            out_rows.append(dict(groupe=f"C{gi:03d}", type="CERTAIN", decision="GARDER" if r is keep else "CORBEILLE",
                                 id=r["id"], path=r["path"], size=r["size"]))
        locs = "<br>".join(sorted({r["path"].rsplit("/", 1)[0] or "/" for r in grp}))
        md.append(f"| C{gi:03d} | `{keep['title']}` | {len(extra)} | {int(keep['size'])/1e6:.2f} Mo | {locs} |")

    md += ["", "## Doublons probables (même taille, noms différents) — à confirmer", "",
           "| Groupe | Fichiers | Taille |", "|---|---|---|"]
    n_prob = 0
    for key, grp in sorted(probable.items(), key=lambda kg: -int(kg[0][0])):
        rest = [r for r in grp if r["id"] not in seen_ids]
        names = {norm(r["title"]) for r in grp}
        if len(grp) > 1 and len(names) > 1 and rest:
            n_prob += 1
            for r in grp:
                out_rows.append(dict(groupe=f"P{n_prob:03d}", type="PROBABLE", decision="A_CONFIRMER",
                                     id=r["id"], path=r["path"], size=r["size"]))
            md.append(f"| P{n_prob:03d} | " + "<br>".join(f"`{r['path']}`" for r in grp) + f" | {int(key[0])/1e3:.0f} Ko |")

    empties = [r for r in rows if int(r["size"]) < 200]
    md += ["", "## Fichiers vides ou temporaires (< 200 octets)", "",
           "| Fichier | Taille | Nature |", "|---|---|---|"]
    for r in sorted(empties, key=lambda r: r["path"]):
        nature = "Verrou Office (~$)" if r["title"].startswith("~$") else ("desktop.ini" if r["ext"] == "ini" else "Upload avorté / vide")
        md.append(f"| `{r['path']}` | {r['size']} o | {nature} |")

    md[4:4] = [f"**Synthèse** : {n_certain_groups} groupes de doublons certains, {n_certain_extra} copies superflues, "
               f"{bytes_extra/1e6:.1f} Mo récupérables. {n_prob} groupes probables à confirmer. "
               f"{len(empties)} fichiers vides/temporaires.", ""]
    (BASE / "rapports" / "doublons.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    with (BASE / "inventaire" / "doublons.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["groupe", "type", "decision", "id", "path", "size"])
        w.writeheader()
        w.writerows(out_rows)

    # Versions multiples : même racine de nom, tailles différentes
    ver = defaultdict(list)
    for r in rows:
        ver[(norm(r["title"]), r["ext"])].append(r)
    vmd = ["# Rapport versions multiples", "",
           "Même nom racine, contenus différents (tailles différentes). Règle : la version la plus récente "
           "devient la version courante (_vN la plus haute), les autres partent en 08_ARCHIVES.", "",
           "| Document | Versions | Plus récente |", "|---|---|---|"]
    nv = 0
    for (name, ext), grp in sorted(ver.items()):
        sizes = {r["size"] for r in grp}
        if len(grp) > 1 and len(sizes) > 1 and int(max(sizes, key=int)) > 0:
            nv += 1
            latest = max(grp, key=lambda r: (r["modified"], int(r["size"])))
            vmd.append(f"| {name}.{ext} | {len(grp)} ({len(sizes)} contenus distincts) | `{latest['path']}` |")
    vmd.insert(2, f"**Synthèse** : {nv} documents existent en plusieurs versions distinctes.\n")
    (BASE / "rapports" / "versions.md").write_text("\n".join(vmd) + "\n", encoding="utf-8")
    print(f"Doublons certains: {n_certain_groups} groupes / {n_certain_extra} copies / {bytes_extra/1e6:.1f} Mo; "
          f"probables: {n_prob}; vides: {len(empties)}; versions: {nv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
