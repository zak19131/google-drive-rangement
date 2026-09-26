# Conventions

## Labels
- MAJUSCULES, underscores, préfixe numérique à 2 chiffres (ordre d'affichage stable), maximum 3 niveaux (`A/B/C`).
- Un fil = un seul label de nature. `01_ACTION` et `02_ATTENTE` sont des **statuts** qui s'ajoutent au label de nature.
- Nouveau projet : `06_PROJETS/NOM_PROJET`. Nouvelle catégorie : ajouter la règle dans `rules.json` (ou `rules.local.json` si elle est personnelle), puis lancer `build_gmail_artifacts.py`.

## Fils de discussion
- Objet original conservé, jamais renommé. Un fil n'est jamais scindé : les opérations se font **au niveau du fil** (label, archive, lu).

## Pièces jointes extraites
- Nom : `AAAA-MM-JJ_EXPEDITEUR_NATURE_SUJET.ext`, par exemple `2026-09-24_CIC_BANQUE_Releve-septembre.pdf`.
- Dossier : `exports/pieces_jointes/<LABEL>/`. Jamais d'écrasement : un doublon de nom reçoit le suffixe `_v2`, `_v3`, etc.
- Catégories sensibles exclues par défaut (option `--include-sensitive` uniquement après accord explicite).

## Filtres
- Un filtre par famille d'expéditeurs récurrents, ou par mot-clé d'objet. La source unique est `rules.json` (+ `rules.local.json`).
- Les filtres sont générés automatiquement dans `build/gmail_filters.xml`, jamais écrits à la main dans Gmail.

## Opérations en masse
- Toujours en DRY-RUN d'abord (`CONFIG.DRY_RUN = true`, valeur par défaut).
- Validation obligatoire avant : taxonomie, règles, suppression, désabonnement, toute opération sur plus de 100 fils.
- Tout est tracé : Sheet `KM_Mail_Workspace` (onglets actions_log, moves, rollback, corbeille, desabonnements) et `logs/actions.log` en ajout seul.
- Aucune suppression directe : passage par `99_CORBEILLE` pendant 30 jours, puis Corbeille Gmail (30 jours de plus).
- Cas ambigu -> `01_ACTION`.
