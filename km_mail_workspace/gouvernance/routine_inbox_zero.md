# Routine INBOX ZÉRO

## Automatique
- **À chaque mail entrant** : les filtres Gmail (importés depuis `build/gmail_filters.xml`) posent le label, archivent et marquent lu selon la nature. Les mails sensibles restent dans l'INBOX.
- **Chaque lundi à 7 h** : l'Apps Script `weeklyZeroInbox` reclasse ce qui a échappé aux filtres, passe les sensibles récents non lus en `01_ACTION` et vide l'INBOX.

## Quotidien (5 min)
1. INBOX : pour chaque fil, appliquer la règle des **4 D** :
   - **Faire** en moins de 2 min ;
   - **Différer** : label `01_ACTION` puis archiver ;
   - **Déléguer / attendre** : label `02_ATTENTE` ;
   - **Détruire** : archiver.
2. `01_ACTION` : traiter les plus anciens d'abord. Une fois traité, retirer `01_ACTION` (le label de nature reste).

## Hebdomadaire (lundi, 10 min)
- Lancer `scripts/weekly_zero_inbox.sh` (tests, artefacts, check-list).
- Parcourir `02_ATTENTE` : relancer tout ce qui a plus de 7 jours.
- Les alertes de sécurité récentes arrivent dans `01_ACTION` : toute connexion non reconnue entraîne un changement de mot de passe et l'activation de la 2FA.
- Sheet `KM_Mail_Workspace` > `actions_log` : le dernier `job_done` doit être présent et il ne doit y avoir aucun `job_error`.

## Mensuel (15 min)
- `listNewsletters`, puis validation et `unsubscribeValidated` pour les expéditeurs jamais lus.
- Survol de `99_CORBEILLE` (2 min) : retirer le label de tout mail à garder. Puis `purgeCorbeille` : les fils de plus de 30 jours partent en Corbeille Gmail (si `ALLOW_TRASH`, jamais avant J+30 de la première mise en quarantaine, jamais un fil sensible).
- Ajouter une règle pour tout nouveau domaine récurrent de `01_ACTION`.

## Indicateurs
| Indicateur | Cible |
|---|---|
| Fils dans l'INBOX le soir | 0 |
| Fils dans `01_ACTION` | < 15 |
| Fils `01_ACTION` de plus de 7 jours | 0 |
| Temps pour retrouver un mail | < 30 s (label + recherche Gmail) |
