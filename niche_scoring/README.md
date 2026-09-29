# Grille de scoring de niche v1.0 (2026-09-28)

Seuils extraits de Drop Ship Lifestyle (Anton Kraly) et MyWifeQuitHerJob (Steve Chou).
Citations et sources : [`criteres_bruts.md`](criteres_bruts.md). Config éditable : [`grille_scoring.json`](grille_scoring.json).

## Utilisation

```bash
cp exemple_niche.json ma_niche.json   # remplir avec des données MESURÉES
python3 score_niche.py ma_niche.json  # --json pour sortie machine
python3 tests/test_score_niche.py     # contrôle de la grille
```

Deux profils, parce que les deux auteurs ont des modèles incompatibles :
- `high_ticket` (DSL) : prix ≥ 200, dropship fournisseurs locaux, trafic Google Shopping/Search.
- `marketplace` (Chou) : prix 20–50 (jusqu'à 200), validation par données de ventes Amazon.

## 1. Règle CEO — plan de test (G1)

⛔ **Tout plan de test par achat d'espace publicitaire (Meta/Facebook, Instagram, TikTok, Google, Pinterest,
Snapchat Ads) est rejeté si le prix unitaire est < 30 €.** Test autorisé : organique ou marketplace.
Appui : Chou chiffre un CAC de 15–30 $ contre ≈ 5 $ de marge sur un produit à 28 $ (perte à chaque vente).
La niche n'est pas éliminée : c'est le **plan de test** qui l'est.

## 2. Éliminatoires (une seule = niche ÉLIMINÉE)

| # | Condition | Source |
|---|---|---|
| G2 | Marge brute < 25 % | DSL : marge 25–30 % |
| G3 | Saisonnalité forte (≈ 0 vente hors saison) | DSL test Evergreen ; Chou |
| G4 | Tendance en chute (fad) | Chou |
| G5 | Fidélité à la marque / prix de référence connu | DSL ; Chou |
| G6 | Taux de retour estimé ≥ 20 % | Chou : 20–25 % = échec |
| G7 | Prix < plancher du profil (200 high-ticket / 20 marketplace) | DSL ; Chou |

## 3. Score /100

| Bloc | Pts | high_ticket (DSL) | marketplace (Chou) |
|---|---|---|---|
| Demande | 25 | ≥ 30 000 rech./mois = 25 · ≥ 10 000 = 15 · ≥ 1 000 = 8 | Rech. ≥ 3 000 & KC ≤ 35 = 10 · ≥ 1 500 = 6 ; ventes 1re page ≥ 1 500/mois = 15 · ≥ 300 = 9 |
| Concurrence | 20 | 10–20 revendeurs actifs = 12 (5–30 = 6) ; pas de dominant = 8 | Avis moyens 1re page < 100 = 12 · < 500 = 6 ; pas de dominant = 8 |
| Économie unitaire | 20 | Prix 200–700 = 10 (> 700 = 5) ; marge ≥ 30 % = 10 · ≥ 25 % = 7 | Prix 20–50 = 10 (15–200 = 5) ; marge idem |
| Retours / SAV | 15 | Retours < 10 % = 10 · < 20 % = 4 ; non fragile = 5 | idem |
| LTV / upsells | 10 | Rachat récurrent = 5 ; upsells/accessoires = 5 | idem |
| Différenciation | 10 | Différenciation = 5 ; ≥ 20 fournisseurs = 5 (≥ 5 = 2) | Différenciation = 5 ; valeur perçue ambiguë = 5 |

**Verdict** : ≥ 75 GO TEST · 60–74 À APPROFONDIR · < 60 NO GO.
Les seuils de verdict et le barème des points sont un **calibrage COO** (hypothèse) ; les seuils des
critères sont ceux des auteurs.

## Limites connues

- **Poids du colis : aucun seuil chiffré chez les deux auteurs** → pas de critère de poids. À fixer par le CEO.
- Seuils des sources en USD, appliqués en EUR à valeur nominale (conservateur).
- Critères issus des articles écrits : les transcriptions vidéo n'ont pas pu être récupérées (blocage YouTube).
- Le score 2026 « A+ » de DSL repose sur un outil propriétaire non public ; le seuil 30 000 date de 2022.
