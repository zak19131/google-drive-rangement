---
name: niche-validation
description: "Valide ou élimine une niche / un produit e-commerce (dropshipping high-ticket ou marketplace) avec la grille de scoring maison : critères sourcés Drop Ship Lifestyle + MyWifeQuitHerJob, saisonnalité et tendance mesurées sur Google Trends, éliminatoires G1–G7, score /100 et verdict. Utiliser quand l'utilisateur dit « valide cette niche », « score ce produit », « est-ce que je lance X », « quelle niche pour le Q4 », « compare ces niches », « test pub pour ce produit », ou donne un produit avec prix/marge à évaluer. Applique toujours la règle CEO : aucun test en publicité payante pour un produit < 30 €. Une fois la niche validée : for competitor research, see competitor-profiling ; for the offer, see offers ; for product pages, see copywriting."
metadata:
  version: 1.0.0
---

# Validation de niche

Tu évalues une niche avec des **données mesurées**, jamais supposées. Une donnée absente = 0 point et une
question ouverte, pas une estimation.

## Fichiers de référence (dans ce dépôt)

- `niche_scoring/criteres_bruts.md` : seuils chiffrés cités, avec sources (lire avant d'argumenter un seuil).
- `niche_scoring/grille_scoring.json` : seuils éditables, 2 profils (`high_ticket`, `marketplace`).
- `niche_scoring/score_niche.py` : moteur (éliminatoires + score /100 + verdict).
- `niche_scoring/q4_2026/trends_screen.py` : saisonnalité, tendance, poids Q4 via Google Trends (`pip install pytrends`).

## Procédure

1. **Profil.** Prix de vente ≥ 200 → `high_ticket` (méthode DSL) ; 20–200 → `marketplace` (méthode Chou) ;
   < 20 → éliminée (G7) sauf décision contraire du CEO.
2. **Forme de la demande.** Ajouter le mot-clé (langue du marché) à `NICHES` dans `trends_screen.py`, lancer
   `python3 niche_scoring/q4_2026/trends_screen.py --geo FR` → saisonnalité (G3), tendance (G4), poids Q4.
   Plus de 20 % de semaines à 0 = volume trop faible : le signaler, ne pas conclure.
3. **Volume et économie.** À mesurer (Keyword Planner, outil SEO, fiches concurrentes, devis fournisseurs) :
   `recherches_mensuelles`, `prix_unitaire_eur`, `marge_brute_pct`, `revendeurs_actifs` (ou
   `avis_moyens_page1` + `ventes_mensuelles_page1`), `fournisseurs_identifies`, `taux_retour_estime_pct`,
   `fragile`, `rachat_recurrent`, `upsells_accessoires`, `differenciation`, `fidelite_marque`.
   Si un connecteur de données refuse l'accès, le dire et demander l'export à l'utilisateur.
4. **Scorer.** Copier `niche_scoring/exemple_niche.json`, remplir, lancer
   `python3 niche_scoring/score_niche.py ma_niche.json` (ajouter `--json` pour la sortie machine).
5. **Plan de test.** Renseigner `plan_test.canal`. **G1 : canal payant (Meta, TikTok, Google, Pinterest,
   Snapchat…) + prix < 30 € = plan rejeté** → proposer organique ou marketplace. La niche n'est pas éliminée.

## Éliminatoires (une seule = ÉLIMINÉE)

G2 marge < 25 % · G3 saisonnalité forte · G4 tendance en chute · G5 fidélité à la marque / prix de référence
connu · G6 retours ≥ 20 % · G7 prix sous le plancher du profil. (G1 ne vise que le plan de test.)

## Verdict

≥ 75 GO TEST · 60–74 À APPROFONDIR · < 60 NO GO. Ces seuils et le barème sont un calibrage interne : le
rappeler quand un verdict est limite (± 5 points).

## Format de réponse

1. Verdict + score + profil en une ligne.
2. Tableau des 6 blocs de score.
3. Éliminatoires déclenchés et plan de test rejeté le cas échéant.
4. Données manquantes → la mesure à faire pour chacune.
5. Une recommandation : lancer / mesurer X d'abord / abandonner.

Distinguer toujours ce qui est **mesuré** (source + date), **cité** (auteur) et **supposé**.
