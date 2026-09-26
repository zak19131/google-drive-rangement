# Procédure d'exécution (environ 30 min de manipulation, puis automatique)

Prérequis : `build/KM_Mail.gs` et `build/gmail_filters.xml` générés par `python3 scripts/build_gmail_artifacts.py`.

## Étape A — Installer le moteur (5 min)
1. Aller sur https://script.google.com, connecté au compte Gmail à ranger. Cliquer sur **Nouveau projet**, le nommer `KM_Mail`.
2. Remplacer le contenu de `Code.gs` par celui de `build/KM_Mail.gs`, puis **Enregistrer**.
3. Vérifier en haut du fichier : `DRY_RUN: true`.

## Étape B — Audit et plan à blanc (lecture seule)
4. Sélectionner la fonction `audit`, puis **Exécuter**. Accepter les autorisations Gmail, Sheets et déclencheurs : c'est ton script, dans ton compte.
5. Attendre la fin (reprise automatique chaque minute), qu'on suit avec `status`. Le résultat est dans Google Drive > Sheet **KM_Mail_Workspace** > onglet `audit`.
6. Exécuter `planDryRun`. Onglet `plan_dry_run` : fils concernés par règle. La ligne **CONTROLE** doit indiquer `TRUE` (somme = total INBOX).
7. Exécuter `listNewsletters`. Onglet `desabonnements` : liste des expéditeurs avec leur lien de désinscription.

## Étape C — Validation (décision)
8. Relire `plan_dry_run`. Si une règle déborde, corriger `rules.json`, relancer le build et recoller le script.
9. Donner la validation explicite pour l'exécution réelle (au-delà de 100 fils = validation obligatoire).

## Étape D — Exécution
10. Passer `DRY_RUN: false`, enregistrer, puis exécuter `apply`. Le job se découpe et reprend seul chaque minute jusqu'à `job_done` (onglet `actions_log`). Ordre de grandeur : quelques heures pour 55 000 fils.
11. Contrôle : INBOX vide, `01_ACTION` contient uniquement du récent utile, rien en Corbeille.
12. Gmail > Paramètres > Filtres et adresses bloquées > **Importer des filtres** > `build/gmail_filters.xml`. Ne **pas** cocher « appliquer aux conversations existantes » : l'existant est déjà traité par `apply`.
13. Exécuter `installWeeklyTrigger` (routine du lundi 7 h).

## Désabonnements (après validation ligne par ligne)
14. Onglet `desabonnements` : mettre `OUI` dans la colonne VALIDER des lignes retenues.
15. `ALLOW_UNSUBSCRIBE: true`, puis exécuter `unsubscribeValidated`. Seuls les liens « one-click » HTTPS sont appelés. Les liens `mailto` restent à traiter à la main.

## Retour arrière
- `rollback` : remet en INBOX tout ce qui a été archivé et en non-lu tout ce qui a été marqué lu.
- `rollbackLabels` : retire en plus les labels de taxonomie (retour exact à l'état initial).
- Arrêt d'urgence : `resetJob` (supprime la reprise automatique ; ce qui est déjà fait reste réversible par `rollback`).
- J+30, si tout est validé : `purgeRollbackLabels` (supprime les 2 labels techniques ; aucun mail touché).

## Garde-fous intégrés au code
- DRY_RUN par défaut. Un changement de DRY_RUN en cours de job provoque un arrêt.
- Arrêt net à la première erreur, sans reprise automatique.
- Lots de 100 fils au maximum. Anti-boucle : arrêt si l'index de recherche Gmail ne se met pas à jour.
- Fils sensibles : jamais marqués lus, jamais mis en corbeille, jamais proposés au désabonnement.
- Aucune suppression : la Corbeille n'est utilisée que par `purgeCorbeille`, avec `ALLOW_TRASH: true` et 30 jours de quarantaine.
