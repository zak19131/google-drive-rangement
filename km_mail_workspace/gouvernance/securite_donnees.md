# Sécurité et confidentialité

- **Dépôt GitHub public** : on n'y versionne que l'outillage et des règles génériques. Sont exclus par `.gitignore` : `inventaire/`, `logs/`, `exports/`, `build/`, `rapports/` (sauf taxonomie) et `rules.local.json` (contacts personnels).
  Recommandation : passer le dépôt en **privé** (GitHub > Settings > Danger zone > Change visibility).
- **Moteur Apps Script** : il s'exécute dans le compte Google du titulaire. Aucune donnée ne quitte Google. Les journaux sont dans une Sheet privée du Drive.
- **Mails sensibles** (admin, finance, famille, sécurité) : jamais marqués lus, jamais mis en corbeille, jamais proposés au désabonnement. Leurs pièces jointes ne sont pas exportées sans l'option `--include-sensitive` (accord explicite requis).
- **Désabonnement** : uniquement le « one-click » normalisé (RFC 8058), sur les lignes validées. On ne clique jamais sur un lien dans le corps d'un mail (risque de phishing).
- **Autorisations** : le script demande l'accès Gmail, Sheets et déclencheurs. Pour le révoquer : https://myaccount.google.com/permissions.
