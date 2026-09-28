# Préparation Q4 2026 : screen de niches et rétroplanning

Mis à jour le 2026-09-28. Marché : **France** (hypothèse : prix en €, règle CEO des 30 €).
Données : Google Trends FR, 5 ans en hebdomadaire (`trends_screen.py` → `trends_q4_2026_FR.csv`).
Les indices Trends sont relatifs : ils mesurent **la forme de la demande** (saisonnalité, tendance,
poids du Q4), **pas son volume**. Ahrefs a été testé : accès API refusé (« Insufficient plan »).

## 1. Résultat du screen (critères éliminatoires G3 saisonnalité / G4 tendance)

| Niche (mot-clé FR) | Origine | Saisonnalité | Tendance 12 m | Poids Q4 | Mois pic | G3/G4 |
|---|---|---|---|---|---|---|
| Fours de potier (`four céramique`) | DSL A+ 2026 | modérée | stable (1,07) | **1,20** | déc. | OK |
| Télescopes | DSL 2023 | modérée | stable (1,11) | **1,14** | août | OK |
| Mobilier de salon (`canapé`) | DSL A+ 2026 | modérée | stable (0,92) | 1,13 | nov. | OK |
| Saunas | DSL | aucune | stable (1,07) | **1,10** | déc. | OK |
| Lits électriques | DSL A+ 2026 | aucune | stable (1,14) | 1,08 | janv. | OK |
| Fauteuils releveurs | MWQHJ (niches ennuyeuses) | aucune | stable (1,07) | 1,08 | janv. | OK |
| Urnes funéraires | MWQHJ (niches ennuyeuses) | aucune | stable (1,03) | 1,06 | oct. | OK |
| Selles d'équitation | DSL A+ 2026 | aucune | stable (0,92) | 1,05 | nov. | OK |
| Bains froids | DSL 2024 | aucune | stable (0,92) | 0,99 | juin | OK |
| Home gym (`appareil de musculation`) | DSL A+ 2026 | modérée | hausse (1,28) | 0,99 | janv. | OK |
| Carports | DSL A+ 2026 | modérée | hausse (1,18) | 0,84 | août | OK, creux au Q4 |
| Fours à pizza | DSL 2023 | modérée | stable (1,04) | 0,83 | juin | OK, creux au Q4 |
| Hydroponie | DSL A+ 2026 | modérée | stable (0,90) | 0,78 | avril | OK, creux au Q4 |
| Machines CNC | DSL A+ 2026 | **forte** | hausse (1,49) | 1,23 | févr. | ❌ G3 |
| Dessertes de bar (`chariot de bar`) | DSL A+ 2026 | — | — | — | — | Volume trop faible en FR |
| Sièges home cinéma (`fauteuil cinéma`) | DSL A+ 2026 | — | — | — | — | Volume trop faible en FR |

Lecture : un poids Q4 de 1,20 signifie que la demande d'octobre à décembre est 20 % au-dessus de la moyenne
annuelle, calculée sur les 3 dernières années complètes. La liste A+ 2026 de DSL est calibrée pour les
États-Unis : 2 niches sur 10 n'ont pas de demande mesurable en France.

## 2. Décision COO : shortlist Q4 2026

Règle appliquée : G3/G4 passés, **poids Q4 ≥ 1,05**, prix compatible avec le profil high-ticket
(≥ 200 €, donc la règle G1 ne bloque pas un test en publicité payante).

1. **Saunas** : aucune saisonnalité et pic en décembre, donc le Q4 est un bonus et la niche reste
   vendable le reste de l'année (DSL : 2 000–7 000 $). Premier choix.
2. **Fours de potier** : niche A+ 2026 de DSL, plus fort poids Q4 mesuré (1,20), pic en décembre.
   Reste à vérifier : le volume absolu en France.
3. **Télescopes** : cadeau de Noël (poids Q4 1,14). Risque G5 à vérifier : marques de référence
   (Celestron, Sky-Watcher) et fourchette de prix.

Plan B : **fauteuils releveurs**, niche sans aucune saisonnalité et à demande urgente (MWQHJ). C'est
la meilleure option si l'objectif est un business durable plutôt qu'un pic Q4.

Écartées pour le Q4 : **canapé**, malgré un poids Q4 de 1,13 (concurrence d'enseignes, risque G5
fidélité à la marque) ; **carports, fours à pizza, hydroponie** (creux au Q4) ; **machines CNC**
(saisonnalité forte).

## 3. Données encore manquantes, par niche de la shortlist (à remplir avant le GO)

`prix_unitaire_eur`, `marge_brute_pct`, `recherches_mensuelles` (volume absolu, via Google Keyword
Planner), `revendeurs_actifs` (10–20 visés), `fournisseurs_identifies` (≥ 20),
`taux_retour_estime_pct`, `fragile`. Remplir `../exemple_niche.json`, puis lancer `score_niche.py`.

## 4. Rétroplanning jusqu'au Black Friday (vendredi 27/11/2026)

Base : méthode DSL (lancement en 21 jours ; 20–30 fournisseurs contactés, ≥ 5 accords vers J15).

| Semaine | Dates 2026 | Livrable |
|---|---|---|
| S40 | 28/09 → 04/10 | Choix d'une niche : volumes, prix, marge et concurrents mesurés sur les 3 niches de la shortlist → verdict `score_niche.py` |
| S41–S42 | 05/10 → 18/10 | 20–30 fournisseurs contactés, ≥ 5 accords (J15 ≈ 13/10, J0 = 28/09) |
| S43 | 19/10 → 25/10 | Boutique en ligne (J21 ≈ 19/10), pages légales, test du tunnel de commande |
| S43–S47 | 19/10 → 22/11 | Test d'acquisition : 5 semaines de données avant le pic |
| S48–S49 | 23/11 → 30/11 | Black Friday (27/11) → Cyber Monday (30/11) |
| S49–S51 | 01/12 → 20/12 | Noël : date limite de commande à confirmer par chaque fournisseur (délai de livraison high-ticket) |

⚠️ Chemin critique : les accords fournisseurs. Un retard de 2 semaines en S41–S42 ne laisse que
3 semaines de test avant le Black Friday.
