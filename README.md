# Rangement Google Drive — outillage

Scripts et règles de gouvernance issus de la réorganisation du Drive (septembre 2026).
Les données personnelles (inventaire, rapports, journaux) sont volontairement exclues de ce dépôt : `.gitignore`. Elles sont stockées dans le Drive privé, sous `01_ADMIN/Rangement_Drive`.

- `scripts/parse_inventory.py` : export brut → `drive_inventory.csv` (chemins, types, drapeaux).
- `scripts/find_duplicates.py` : doublons (nom + taille), versions multiples, fichiers vides.
- `scripts/build_plan.py` : plan de rangement en dry-run (cible + nom normalisé).
- `scripts/move_files.py` : exécution par lots, journalisation, rollback.
- `scripts/rename_files.py` : contrôle et génération de noms `AAAA-MM-JJ_NATURE_Sujet_vN.ext`.
- `scripts/weekly_check.sh` : contrôle hebdomadaire (racine, INBOX, profondeur, corbeille > 30 j).
- `gouvernance/` : règles de rangement, checklist hebdomadaire, procédure de retour arrière.
