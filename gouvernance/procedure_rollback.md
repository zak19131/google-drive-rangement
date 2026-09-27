# Procédure de retour arrière

Chaque opération exécutée est consignée dans `logs/rollback.csv` avec l'ancien parent, l'ancien nom, le nouveau parent et le nouveau nom (292 opérations au 2026-09-27).

## Annuler une opération précise

1. Chercher le fichier dans `logs/rollback.csv` (colonne `new_title`).
2. Appliquer l'opération inverse : déplacer vers `old_parent` et renommer en `old_title`, via le MCP Drive `update_file`, rclone, ou à la main dans Drive.

## Annuler tout

`python3 scripts/move_files.py --rollback` imprime les opérations inverses, de la plus récente à la plus ancienne, au format JSON (`fileId`, `parentId`, `title`). On les rejoue une par une.

## Ce qui n'est pas réversible automatiquement

- La date de modification Drive (`modifiedTime`) a été mise à jour par les déplacements avec renommage. C'est pour ça que la date d'origine est figée dans le nom de chaque fichier.
- Aucune suppression définitive n'a été faite : tout ce qui a été retiré se trouve dans 99_CORBEILLE.
