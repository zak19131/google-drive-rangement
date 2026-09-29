#!/usr/bin/env python3
"""Tests de la grille de scoring : bornes sourcées, éliminatoires, règle CEO G1."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from score_niche import charger_grille, score  # noqa: E402

G = charger_grille()

HT_PARFAITE = {
    "nom": "Saunas d'extérieur", "profil": "high_ticket", "prix_unitaire_eur": 450, "marge_brute_pct": 30,
    "recherches_mensuelles": 40000, "revendeurs_actifs": 15, "vendeurs_dominants": False,
    "fournisseurs_identifies": 22, "saisonnalite": "aucune", "tendance": "stable", "fidelite_marque": False,
    "taux_retour_estime_pct": 5, "fragile": False, "rachat_recurrent": True, "upsells_accessoires": True,
    "differenciation": True, "plan_test": {"canal": "google_ads"},
}


def cas(**kw):
    return {**HT_PARFAITE, **kw}


# 1. Niche idéale : 100/100, GO TEST, aucun blocage
r = score(HT_PARFAITE, G)
assert r["score"] == 100 and r["verdict"] == "GO TEST", r
assert not r["eliminatoires"] and r["plan_test"] is None and not r["donnees_manquantes"], r

# 2. Règle CEO G1 : Ads payantes sur produit < 30 € → plan rejeté (toutes plateformes payantes)
for canal in ("meta_ads", "facebook_ads", "tiktok_ads", "google_ads"):
    r = score(cas(profil="marketplace", prix_unitaire_eur=25, plan_test={"canal": canal}), G)
    assert r["plan_test"] and r["plan_test"].startswith("G1"), (canal, r)
# ... borne : 30 € exactement autorisé ; organique toujours autorisé
assert score(cas(profil="marketplace", prix_unitaire_eur=30, plan_test={"canal": "tiktok_ads"}), G)["plan_test"] is None
assert score(cas(profil="marketplace", prix_unitaire_eur=12, plan_test={"canal": "organique"}), G)["plan_test"] is None

# 3. Éliminatoires sourcés
assert any(e.startswith("G2") for e in score(cas(marge_brute_pct=24), G)["eliminatoires"])
assert any(e.startswith("G3") for e in score(cas(saisonnalite="forte"), G)["eliminatoires"])
assert any(e.startswith("G4") for e in score(cas(tendance="chute"), G)["eliminatoires"])
assert any(e.startswith("G5") for e in score(cas(fidelite_marque=True), G)["eliminatoires"])
assert any(e.startswith("G6") for e in score(cas(taux_retour_estime_pct=20), G)["eliminatoires"])
assert not score(cas(taux_retour_estime_pct=19), G)["eliminatoires"]
assert any(e.startswith("G7") for e in score(cas(prix_unitaire_eur=199), G)["eliminatoires"])  # DSL : >= 200
assert not score(cas(profil="marketplace", prix_unitaire_eur=20), G)["eliminatoires"]
r =score(cas(profil="marketplace", prix_unitaire_eur=19), G)
assert any(e.startswith("G7") for e in r["eliminatoires"]), r  # Chou : >= 20 $
assert score(cas(marge_brute_pct=24), G)["verdict"] == "ÉLIMINÉE"

# 4. Seuils de demande DSL : 30 000 / 10 000 / milliers
assert score(cas(recherches_mensuelles=30000), G)["detail"]["demande"] == 25
assert score(cas(recherches_mensuelles=10000), G)["detail"]["demande"] == 15
assert score(cas(recherches_mensuelles=2000), G)["detail"]["demande"] == 8
assert score(cas(recherches_mensuelles=500), G)["detail"]["demande"] == 0

# 5. Profil marketplace (Chou) : recherches 3 000 + KC <= 35, ventes 1 500, avis < 100
mp = cas(profil="marketplace", prix_unitaire_eur=35, recherches_mensuelles=3000, keyword_competitiveness=30,
         ventes_mensuelles_page1=1500, avis_moyens_page1=80, valeur_percue_ambigue=True)
r = score(mp, G)
assert r["detail"]["demande"] == 25 and r["detail"]["concurrence"] == 20 and r["score"] == 100, r
assert score({**mp, "keyword_competitiveness": 50}, G)["detail"]["demande"] == 6 + 15  # KC > 35 : plus "excellent"
assert score({**mp, "avis_moyens_page1": 300}, G)["detail"]["concurrence"] == 14

# 6. Données manquantes : 0 point, listées, jamais devinées
r = score({"nom": "vide", "profil": "high_ticket"}, G)
assert r["score"] == 0 and "recherches_mensuelles" in r["donnees_manquantes"], r

print("OK — tous les tests de scoring passent")
