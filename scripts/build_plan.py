#!/usr/bin/env python3
"""Construit le plan de rangement (DRY-RUN) : destination + nouveau nom pour chaque élément.

Entrées : inventaire/drive_inventory.csv, inventaire/doublons.csv
Sortie  : logs/plan_actions.csv  (aucune action sur le Drive)

Actions :
  MOVE_RENAME  déplacer vers la cible + renommer selon la convention
  FOLDER_MOVE  déplacer/renommer un dossier entier (séries photo : noms caméra conservés)
  TRASH        déplacer vers 99_CORBEILLE (doublon certain, vide, temporaire) — jamais de suppression
  INBOX        cas ambigu -> 00_INBOX, nom d'origine conservé
  SKIP         élément partagé par un tiers (non déplaçable) ou contenu d'un dossier déplacé en bloc
Convention : AAAA-MM-JJ_NATURE_SujetCamelCase_vN.ext
"""
import csv
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
INV = BASE / "inventaire" / "drive_inventory.csv"
DUP = BASE / "inventaire" / "doublons.csv"
OUT = BASE / "logs" / "plan_actions.csv"

A = "01_ADMIN"; F = "02_FINANCE"; P = "03_PROJETS"; B = "04_BUSINESS"; L = "05_APPRENTISSAGE"
V = "06_VEILLE"; PE = "07_PERSONNEL"; AR = "08_ARCHIVES/2023-2025"; T = "09_TEMPLATES"
DZ = f"{B}/DZ_Oils_Energies"

# Dossiers déplacés en bloc (séries photo) : (id, nouveau chemin parent, nouveau nom)
FOLDER_MOVES = {
    "1uTrptw6S3EyGMRkEXZkz4Kkd16ZZFM-B": (f"{PE}/Photos", "2026-05-08_PHOTO_Shooting"),
    "1hMiJSiVvvrnwKdskjySCKbNYZdpaEUOf": (f"{PE}/Photos", "2026-05-08_PHOTO_ShootingSelection"),
}
# Dossiers à vider puis mettre en corbeille (doublons intégraux / vides)
FOLDER_TRASH = {
    "1c6H07CzEeJFq-ozgYjNPQ0OG7rTTWut4": "Sélection dupliquée à l'identique dans /Séléctioné (15/15 nom+taille)",
    "1A61B7AwUSrjfKxrA6qhOmfAWr1URTEaL": "Dossier vide",
    "1USnyepSB9vo1zdNbcDUHWqaMfHOcoFOj": "Dossier vide",
}

# Règles ordonnées : (regex sur le chemin, dossier cible, NATURE). None en cible = INBOX.
RULES = [
    # --- Identité / santé / logement
    (r"/cni[ _]|/cni\.pdf|/cni verso", f"{A}/Identite", "CNI"),
    (r"passeport", f"{A}/Identite", "PASSEPORT"),
    (r"journ[ée]e d[ée]fense", f"{A}/Identite", "ATTESTATION"),
    (r"carte vitale", f"{A}/Social_Sante", "CARTE"),
    (r"quittance", f"{A}/Logement", "QUITTANCE"),
    (r"attestation h[ée]bergement", f"{A}/Logement", "ATTESTATION"),
    (r"/dossier hlm/", f"{A}/Logement", "ATTESTATION"),
    (r"/edf ", f"{A}/Logement", "FACTURE"),
    # --- Finance
    (r"avis_d_impot|avis_de_situation|d[ée]claration d'impots|/declaration 20", f"{F}/Impots", "AVIS"),
    (r"payfip", f"{F}/Impots", "TICKET"),
    (r"/rib\.pdf|/rib-1\.pdf", f"{F}/Banque", "RIB"),
    (r"extrait de comptes", f"{F}/Banque", "RELEVE"),
    (r"preview-cnaf", f"{F}/Aides_Bourses", "ATTESTATION"),
    (r"/2024_08_bp_aout", f"{F}/Salaires", "BULLETIN"),
    # --- Dossiers clos 2024-2025 archivés en bloc logique
    (r"/dossier cic/", f"{AR}/Pret_CIC_2024", None),
    (r"/bourse 2024 2025/", f"{AR}/Bourse_2024-2025", None),
    (r"formulaire-asaa", f"{AR}/Bourse_2024-2025", "FORMULAIRE"),
    (r"/alternance 2024 2025/lm-", f"{AR}/Candidatures_2024", "LM"),
    (r"ade tl etudiants", f"{AR}/Scolarite_2024-2025", "PLANNING"),
    # --- Business DZ Oils Energies
    (r"statut\.docx|kbis|d[ée]p[ôo]t de capital|document_de_synthese|rib-shine", f"{DZ}/Juridique", None),
    (r"annexe\.pdf|pdfkeziw8", f"{DZ}/Juridique", "ANNEXE"),
    (r"budget_previsionnel|sommaire_projet_transport", f"{DZ}/Projets", None),
    (r"/dzoilsenergies/(site internet/)?(\d\.jpg|capture 23|capture\.jpg|original_photo|enhanced_new|selected_photo|logo|dz final|dz_final|professional business|pass visitor|photo 1)", f"{DZ}/Communication", None),
    (r"/dzoilsenergies/.*(cerfa|contrat|convention|fiche de poste|mission\.pdf|assistant-commercial|planning|renseignements|mutuelle|dpae|dsn_|variables de paie|payfit|affichagepdf|03698918|laghmara_abdel_karim|promesse)", f"{DZ}/RH_Paie", None),
    (r"/dzoilsenergies/justificatif/capture", f"{DZ}/RH_Paie", "CAPTURE"),
    (r"promesse _d_embauche", f"{DZ}/RH_Paie", "PROMESSE"),
    # --- Carrière
    (r"269-modele-cv", T, "MODELE"),
    (r"/cv |/cv final", f"{B}/Carriere", "CV"),
    (r"lettre de recommendation", f"{B}/Carriere", "RECOMMANDATION"),
    # --- Études
    (r"kedge", f"{L}/Kedge", None),
    (r"semestre|releve_de_notes|relev[ée] du note|bac es|cvec|certificat scolarit|notes_et_r|d[ée]tails_des_notes", f"{L}/Diplomes_Releves", None),
    (r"/dossier [ée]cole 2024/(karim/)?(lettre|dossier|attestation|complementdemat|ecmn)", f"{AR}/Candidatures_2024", None),
    (r"/dossier [ée]cole 2024/lettre de motivation lp mpl", f"{AR}/Candidatures_2024", "LM"),
    (r"lettre de motivation laghmara karim", f"{AR}/Candidatures_2024", "LM"),
    (r"upec|evaluation grid", f"{L}/UPEC", None),
    (r"/\d\. .*\.pdf$", f"{L}/Managing_Innovation", "COURS"),
    (r"m[ée]moire", f"{L}/Memoire", "MEMOIRE"),
    (r"ice_industry", f"{P}/ICE_Industry", None),
    # --- Projets / veille / perso
    (r"etm|elite_trade_map", f"{P}/Trading_ETM", None),
    (r"esprit du trader|market_maker|institutional_trading", f"{V}/Trading", None),
    (r"drixs", f"{PE}/Musique", "AUDIO"),
]

NATURE_KW = [
    ("facture", "FACTURE"), ("devis", "DEVIS"), ("admission", "ADMISSION"), ("contrat", "CONTRAT"),
    ("convention", "CONVENTION"), ("cerfa", "CERFA"), ("attestation", "ATTESTATION"), ("relev", "RELEVE"),
    ("avis", "AVIS"), ("kbis", "KBIS"), ("statut", "STATUTS"), ("rib", "RIB"), ("lettre de motivation", "LM"),
    ("lm-", "LM"), ("dossier", "DOSSIER"), ("planning", "PLANNING"), ("fiche", "FICHE"), ("dpae", "DPAE"),
    ("dsn", "DSN"), ("variables de paie", "PAIE"), ("laghmara_abdel_karim", "BULLETIN"), ("mutuelle", "ATTESTATION"),
    ("promesse", "PROMESSE"), ("budget", "BUDGET"), ("sommaire", "PROJET"), ("logo", "LOGO"), ("dz final", "LOGO"), ("dz_final", "LOGO"), ("photo", "PHOTO"),
    ("capture", "CAPTURE"), ("business card", "CARTEVISITE"), ("pass visitor", "BADGE"), ("semestre", "NOTES"),
    ("notes", "NOTES"), ("bac es", "DIPLOME"), ("cvec", "ATTESTATION"), ("certificat", "CERTIFICAT"),
    ("tuto", "TUTO"), (".py", "CODE"), ("reponses", "REPONSES"), ("trame", "TRAME"), ("grid", "GRILLE"),
    ("mission", "MISSION"), ("synthese", "SYNTHESE"), ("capital", "ATTESTATION"), ("complementdemat", "DOSSIER"),
    ("scan", "SCAN"), ("recapitulatif", "RECAP"), ("framework", "GUIDE"), ("esprit du trader", "LIVRE"),
    ("upec", "DOC"), ("assistant-commercial", "BROCHURE"), ("affichage", "DOC"), ("img_", "PHOTO"),
]
STOP = {"laghmara", "karim", "abdel", "klaghmara", "mr", "de", "du", "la", "le", "les", "des", "et", "d", "l",
        "a", "sur", "pdf", "copie", "final", "unlocked", "the", "and", "or", "what", "why", "do", "how", "to"}


def ascii_fold(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def split_ext(title, kind):
    m = re.search(r"\.([A-Za-z0-9]{1,5})$", title)
    if kind == "file" and m:
        return title[: m.start()], "." + m.group(1).lower()
    return title, ""


def doc_date(title, modified):
    t = title
    for pat, fmt in [(r"(20\d\d)[-_](\d\d)[-_](\d\d)", "ymd"), (r"(\d\d)-(\d\d)-(20\d\d)", "dmy"),
                     (r"(20\d\d)[-_](\d\d)(?!\d)", "ym"), (r"(\d\d)_(20\d\d)", "my")]:
        m = re.search(pat, t)
        if m:
            g = m.groups()
            if fmt == "ymd":
                return f"{g[0]}-{g[1]}-{g[2]}"
            if fmt == "dmy":
                return f"{g[2]}-{g[1]}-{g[0]}"
            if fmt == "ym":
                return f"{g[0]}-{g[1]}-01"
            return f"{g[1]}-{g[0]}-01"
    return modified


def nature_of(title, forced):
    if forced:
        return forced
    tl = title.lower()
    for kw, nat in NATURE_KW:
        if kw in tl:
            return nat
    if re.search(r"\.(jpe?g|png)$", tl):
        return "PHOTO"
    return "DOC"


def subject_of(stem, nature):
    s = ascii_fold(stem)
    s = re.sub(r"\(\d+\)|~\$", " ", s)
    s = re.sub(r"20\d\d[-_]\d\d[-_]\d\d(T[\d_]+)?|\d\d-\d\d-20\d\d", " ", s)
    s = re.sub(r"[^A-Za-z0-9]+", " ", s)
    words = [w for w in s.split() if w.lower() not in STOP and w.upper() != nature]
    subj = "".join(w[:1].upper() + w[1:].lower() if not w.isupper() or len(w) > 4 else w for w in words)
    return (subj or "Document")[:40]


def main():
    inv = list(csv.DictReader(INV.open(encoding="utf-8")))
    dups = {r["id"]: r for r in csv.DictReader(DUP.open(encoding="utf-8")) if r["type"] == "CERTAIN"}
    by_id = {r["id"]: r for r in inv}
    bulk_parents = set(FOLDER_MOVES) | set(FOLDER_TRASH)
    plan = []

    for r in inv:
        base = dict(id=r["id"], kind=r["kind"], old_path=r["path"], old_title=r["title"],
                    old_parent=r["parent_id"], size=r["size"], flags=r["flags"])
        if r["owner"] != "me":
            plan.append({**base, "action": "SKIP", "target": "", "new_title": r["title"], "reason": "Partagé par un tiers : non déplaçable"})
            continue
        if r["id"] in FOLDER_MOVES:
            tgt, name = FOLDER_MOVES[r["id"]]
            plan.append({**base, "action": "FOLDER_MOVE", "target": tgt, "new_title": name, "reason": "Série photo déplacée en bloc, noms caméra conservés"})
            continue
        if r["id"] in FOLDER_TRASH:
            plan.append({**base, "action": "TRASH", "target": "99_CORBEILLE", "new_title": r["title"], "reason": FOLDER_TRASH[r["id"]]})
            continue
        if r["parent_id"] in bulk_parents:
            # Contenu d'un dossier déplacé en bloc : suit son dossier. Exception : IMG_2471 absente des originaux.
            reason = "Suit le dossier parent (déplacement en bloc)"
            if r["parent_id"] == "1c6H07CzEeJFq-ozgYjNPQ0OG7rTTWut4":
                reason = "Suit le dossier parent -> 99_CORBEILLE (copie de /Séléctioné)"
            plan.append({**base, "action": "SKIP", "target": "", "new_title": r["title"], "reason": reason})
            continue
        if r["kind"] == "folder":
            plan.append({**base, "action": "TRASH_IF_EMPTY", "target": "99_CORBEILLE", "new_title": r["title"],
                         "reason": "Ancien dossier : corbeille uniquement une fois vidé et vérifié"})
            continue
        d = dups.get(r["id"])
        if d and d["decision"] == "CORBEILLE":
            plan.append({**base, "action": "TRASH", "target": "99_CORBEILLE", "new_title": r["title"],
                         "reason": f"Doublon certain {d['groupe']} (nom+taille identiques)"})
            continue
        if "TEMPORAIRE" in r["flags"] or "VIDE_OU_CORROMPU" in r["flags"]:
            plan.append({**base, "action": "TRASH", "target": "99_CORBEILLE", "new_title": r["title"],
                         "reason": "Fichier vide (0-43 o) ou verrou Office/desktop.ini"})
            continue
        if "SANS_TITRE" in r["flags"]:
            plan.append({**base, "action": "TRASH", "target": "99_CORBEILLE", "new_title": r["title"],
                         "reason": "Document natif sans titre de 0-1 Ko (vide)"})
            continue
        path_l = r["path"].lower()
        target, forced = None, None
        for pat, tgt, nat in RULES:
            if re.search(pat, path_l):
                target, forced = tgt, nat
                break
        if target is None:
            plan.append({**base, "action": "INBOX", "target": "00_INBOX", "new_title": r["title"],
                         "reason": "Cas ambigu : contenu/propriétaire non déterminable sans ouverture"})
            continue
        stem, ext = split_ext(r["title"], r["kind"])
        nature = nature_of(r["title"], forced)
        date = doc_date(r["title"], r["modified"])
        subj = subject_of(stem, nature)
        plan.append({**base, "action": "MOVE_RENAME", "target": target,
                     "new_title": f"{date}_{nature}_{subj}", "ext": ext, "reason": "Règle de classement"})

    # Versionnage : même nom de base dans un même dossier cible -> v1..vN par date de modification
    groups = defaultdict(list)
    for p in plan:
        if p["action"] == "MOVE_RENAME":
            groups[(p["target"], p["new_title"].split("_", 1)[1], p.get("ext", ""))].append(p)
    for (_, _, ext), grp in groups.items():
        grp.sort(key=lambda p: (by_id[p["id"]]["modified"], int(p["size"])))
        for i, p in enumerate(grp, 1):
            p["new_title"] = f"{p['new_title']}_v{i}{ext}"
            if len(grp) > 1:
                p["reason"] += f" | {len(grp)} versions distinctes"
    # Collisions de nom exact dans une cible
    seen = defaultdict(int)
    for p in plan:
        if p["action"] == "MOVE_RENAME":
            key = (p["target"], p["new_title"])
            seen[key] += 1
            if seen[key] > 1:
                p["new_title"] = p["new_title"].replace("_v", f"_{seen[key]}_v", 1)

    cols = ["action", "id", "kind", "old_path", "target", "new_title", "old_title", "old_parent", "size", "flags", "reason"]
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for p in sorted(plan, key=lambda p: (p["action"], p["target"], p["new_title"])):
            w.writerow(p)
    counts = defaultdict(int)
    for p in plan:
        counts[p["action"]] += 1
    print("DRY-RUN plan ->", OUT, dict(counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
