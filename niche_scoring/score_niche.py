#!/usr/bin/env python3
"""Scoring de niche e-commerce : éliminatoires + score /100, seuils sourcés dans grille_scoring.json.

Usage : python3 score_niche.py niche.json [--json]
Une donnée absente rapporte 0 point et est listée dans `donnees_manquantes` (jamais devinée).
"""
import json
import sys
from pathlib import Path

GRILLE = Path(__file__).resolve().parent / "grille_scoring.json"


def charger_grille(path=GRILLE):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _get(niche, cle, manquantes):
    v = niche.get(cle)
    if v is None:
        manquantes.append(cle)
    return v


def controle_plan_test(niche, grille):
    """G1 (règle CEO) : pas d'achat d'espace publicitaire pour un produit < 30 €."""
    regle = grille["regle_ceo_ads"]
    canal = (niche.get("plan_test") or {}).get("canal")
    prix = niche.get("prix_unitaire_eur")
    if canal in regle["canaux_payants"] and prix is not None and prix < regle["prix_min_eur"]:
        return (f"G1 REJETÉ : test en {canal} sur un produit à {prix} € (< {regle['prix_min_eur']} €). "
                "Tester en organique ou marketplace.")
    return None


def eliminatoires(niche, grille, profil):
    e = grille["eliminatoires_communs"]
    raisons = []
    marge = niche.get("marge_brute_pct")
    if marge is not None and marge < e["marge_brute_min_pct"]["valeur"]:
        raisons.append(f"G2 marge {marge} % < {e['marge_brute_min_pct']['valeur']} %")
    if niche.get("saisonnalite") == e["saisonnalite_interdite"]["valeur"]:
        raisons.append("G3 niche fortement saisonnière")
    if niche.get("tendance") == e["tendance_interdite"]["valeur"]:
        raisons.append("G4 tendance en chute (fad)")
    if niche.get("fidelite_marque") is True:
        raisons.append("G5 forte fidélité à la marque / prix de référence connu")
    retour = niche.get("taux_retour_estime_pct")
    if retour is not None and retour >= e["taux_retour_max_pct"]["valeur"]:
        raisons.append(f"G6 taux de retour estimé {retour} % >= {e['taux_retour_max_pct']['valeur']} %")
    prix = niche.get("prix_unitaire_eur")
    if prix is not None and prix < profil["prix_min"]["valeur"]:
        raisons.append(f"G7 prix {prix} € < plancher du profil ({profil['prix_min']['valeur']})")
    return raisons


def _dans(v, lo, hi):
    return v is not None and v >= lo and (hi is None or v <= hi)


def score(niche, grille):
    nom_profil = niche.get("profil", "high_ticket")
    profil = grille["profils"][nom_profil]
    manq = []
    d = {}

    # Demande (25)
    if nom_profil == "high_ticket":
        s = profil["demande_recherches_mois"]
        r = _get(niche, "recherches_mensuelles", manq)
        d["demande"] = 25 if r is not None and r >= s["excellent"] else 15 if r is not None and r >= s["bon"] \
            else 8 if r is not None and r >= s["minimum"] else 0
    else:
        s, v = profil["recherches_mois"], profil["ventes_mois_page1"]
        r = _get(niche, "recherches_mensuelles", manq)
        kc = niche.get("keyword_competitiveness")
        kc_ok = kc is None or kc <= s["kc_max"]
        pts = 10 if r is not None and r >= s["excellent"] and kc_ok else 6 if r is not None and r >= s["minimum"] else 0
        ventes = _get(niche, "ventes_mensuelles_page1", manq)
        pts += 15 if ventes is not None and ventes >= v["excellent"] else 9 if ventes is not None and ventes >= v["minimum"] else 0
        d["demande"] = pts

    # Concurrence (20)
    if nom_profil == "high_ticket":
        c = profil["revendeurs_actifs"]
        n = _get(niche, "revendeurs_actifs", manq)
        pts = 12 if _dans(n, c["min"], c["max"]) else 6 if _dans(n, c["min"] // 2, c["max"] + 10) else 0
    else:
        a = profil["avis_moyens_page1"]
        n = _get(niche, "avis_moyens_page1", manq)
        pts = 12 if n is not None and n < a["excellent"] else 6 if n is not None and n < a["maximum"] else 0
    dom = _get(niche, "vendeurs_dominants", manq)
    d["concurrence"] = pts + (8 if dom is False else 0)

    # Économie unitaire (20)
    prix = _get(niche, "prix_unitaire_eur", manq)
    pi, pl = profil["prix_ideal"], profil["prix_large"]
    pts = 10 if _dans(prix, pi["min"], pi["max"]) else 5 if _dans(prix, pl["min"], pl["max"]) else 0
    marge = _get(niche, "marge_brute_pct", manq)
    pts += 10 if marge is not None and marge >= 30 else 7 if marge is not None and marge >= 25 else 0
    d["economie"] = pts

    # Retours / SAV (15)
    ret = _get(niche, "taux_retour_estime_pct", manq)
    fragile = _get(niche, "fragile", manq)
    d["retours_sav"] = (10 if ret is not None and ret < 10 else 4 if ret is not None and ret < 20 else 0) \
        + (5 if fragile is False else 0)

    # LTV / upsells (10)
    d["ltv_upsells"] = (5 if _get(niche, "rachat_recurrent", manq) else 0) \
        + (5 if _get(niche, "upsells_accessoires", manq) else 0)

    # Différenciation & approvisionnement (10)
    pts = 5 if _get(niche, "differenciation", manq) else 0
    if nom_profil == "high_ticket":
        f = profil["fournisseurs"]
        nf = _get(niche, "fournisseurs_identifies", manq)
        pts += 5 if nf is not None and nf >= f["excellent"] else 2 if nf is not None and nf >= f["minimum"] else 0
    else:
        pts += 5 if _get(niche, "valeur_percue_ambigue", manq) else 0
    d["differenciation"] = pts

    total = sum(d.values())
    elim = eliminatoires(niche, grille, profil)
    v = grille["verdict"]
    if elim:
        verdict = "ÉLIMINÉE"
    elif total >= v["go_test"]:
        verdict = "GO TEST"
    elif total >= v["a_approfondir"]:
        verdict = "À APPROFONDIR"
    else:
        verdict = "NO GO"
    return {
        "niche": niche.get("nom"), "profil": nom_profil, "score": total, "detail": d,
        "verdict": verdict, "eliminatoires": elim, "plan_test": controle_plan_test(niche, grille),
        "donnees_manquantes": sorted(set(manq)),
    }


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    niche = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    res = score(niche, charger_grille())
    if "--json" in argv:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    print(f"{res['niche']} [{res['profil']}] — {res['score']}/100 — {res['verdict']}")
    for k, pts in res["detail"].items():
        print(f"  {k:<16} {pts}")
    for r in res["eliminatoires"]:
        print(f"  ✗ {r}")
    if res["plan_test"]:
        print(f"  ⛔ {res['plan_test']}")
    if res["donnees_manquantes"]:
        print(f"  ? données manquantes : {', '.join(res['donnees_manquantes'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
