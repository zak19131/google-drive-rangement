# KM Mail — rangement Gmail traçable et réversible

Outillage pour passer une boîte Gmail saturée (dizaines de milliers de fils, 90 % non lus) à une **INBOX zéro** structurée, sans perte, avec dry-run, journal et retour arrière.

## Architecture
| Brique | Rôle | Où ça tourne |
|---|---|---|
| `rules.json` (+ `rules.local.json`, non versionné) | Source unique des règles de classement | — |
| `scripts/build_gmail_artifacts.py` | Génère le moteur Apps Script, les filtres Gmail et la doc des règles | Poste |
| `build/KM_Mail.gs` | Moteur : audit, plan dry-run, application par lots de 100, reprise automatique, rollback, désabonnement validé, corbeille à 30 j, routine hebdomadaire | Compte Google (Apps Script) |
| `build/gmail_filters.xml` | Filtres pour le flux entrant, à importer dans Gmail | Gmail |
| `scripts/*.py` | Mêmes règles appliquées hors ligne sur un export Takeout `.mbox` : inventaire, classification, doublons, pièces jointes, désabonnements | Poste |
| `scripts/tests/` | Moteur exécuté contre une boîte Gmail simulée (2 000 fils) + tests Python + contrôle de cohérence entre les deux moteurs | Poste |

## Démarrage
```bash
cd km_mail_workspace/scripts
python3 build_gmail_artifacts.py      # -> build/KM_Mail.gs, build/gmail_filters.xml
./weekly_zero_inbox.sh                # tests + check-list
```
Puis suivre `gouvernance/procedure_execution.md` (audit -> dry-run -> validation -> apply).

## Documentation
- `rapports/taxonomie.md` : arborescence cible.
- `gouvernance/regles_filtrage.md` : règles (générées).
- `gouvernance/conventions.md` : nommage, pièces jointes, opérations en masse.
- `gouvernance/routine_inbox_zero.md` : routines quotidienne, hebdomadaire et mensuelle.
- `gouvernance/securite_donnees.md` : confidentialité.

Les dossiers `inventaire/`, `logs/`, `exports/`, `build/` et `rapports/` contiennent des données personnelles : ils sont exclus du dépôt.
