# Règles de rangement du Drive — référence

## 1. Où ranger (arbre de décision, 10 secondes)

1. Je ne sais pas → **00_INBOX** (tri le dimanche).
2. Pièce d'identité, logement, santé → **01_ADMIN** (Identite / Logement / Social_Sante).
3. Argent : banque, impôts, aides, fiches de paie perso → **02_FINANCE**.
4. Projet perso en cours (ICE Industry, Trading ETM…) → **03_PROJETS/<Projet>**.
5. Société DZ Oils Energies ou carrière (CV, recommandations) → **04_BUSINESS**.
6. Cours, diplômes, relevés, école → **05_APPRENTISSAGE**.
7. Lecture, veille, guides externes → **06_VEILLE**.
8. Photos, musique → **07_PERSONNEL**.
9. Dossier terminé (candidature, bourse, prêt clos) → **08_ARCHIVES/<période>**.
10. Modèle réutilisable → **09_TEMPLATES**.
11. À supprimer → **99_CORBEILLE**, jamais de suppression directe.

## 2. Convention de nommage

`AAAA-MM-JJ_NATURE_SujetCamelCase_vN.ext`, par exemple `2026-09-27_FACTURE_EDFMars_v1.pdf`.

- La date est celle du document (pas celle de l'upload).
- NATURE est choisie dans le vocabulaire fermé de `rapports/taxonomie.md`, en majuscules.
- Nouveau contenu du même document : `_v2`, `_v3`… L'ancienne version va dans 08_ARCHIVES si elle n'est plus utile.
- Pas d'espaces, pas d'accents, pas de `(1)`, pas de `Copie`, pas de `final`.
- Générateur : `python3 scripts/rename_files.py --suggest "titre brut" --date AAAA-MM-JJ`.
- Exceptions : les séries photo (noms caméra conservés, seul le dossier est nommé) et les Google Docs natifs (sans extension).

## 3. Règles de structure

- 3 niveaux de dossiers maximum sous la racine.
- Aucun fichier à la racine.
- Un document n'existe qu'une seule fois. Pour une démarche (prêt, bourse), on joint une copie et on ne la stocke pas.
- 99_CORBEILLE : 30 jours minimum, puis suppression définitive uniquement après validation explicite du CEO.

## 4. Fichiers sensibles

- Zones sensibles : 01_ADMIN/Identite, 01_ADMIN/Social_Sante, 02_FINANCE/*, 04_BUSINESS/DZ_Oils_Energies/RH_Paie.
- Aucun partage par lien public sur ces zones. Si un partage est nécessaire, partager un fichier précis, nominativement, avec une date d'expiration.
- Aucun mot de passe ni identifiant dans le Drive : ils vont dans un gestionnaire de mots de passe.
