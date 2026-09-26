#!/usr/bin/env bash
# Routine hebdomadaire INBOX ZÉRO — côté poste de travail.
# Le tri automatique réel est fait dans Gmail par :
#   - les filtres importés (build/gmail_filters.xml) pour chaque mail entrant ;
#   - le déclencheur Apps Script weeklyZeroInbox (lundi 7h) pour le reste.
# Ce script : régénère les artefacts, rejoue les tests, et si on lui passe un export Takeout .mbox,
# rejoue audit + diagnostic en DRY-RUN. Il ne modifie jamais la boîte mail.
# Usage : ./weekly_zero_inbox.sh [chemin/export.mbox]
set -euo pipefail
cd "$(dirname "$0")"

echo "== 1. Artefacts (règles -> Apps Script + filtres)"
python3 build_gmail_artifacts.py

echo "== 2. Tests (moteur simulé + scripts Python, espace isolé)"
python3 tests/test_python.py | tail -1

if [[ "${1:-}" == *.mbox ]]; then
  echo "== 3. Diagnostic DRY-RUN sur $1"
  python3 parse_mailbox.py "$1"
  python3 classify_mails.py
  python3 find_duplicates.py
  python3 unsubscribe.py
fi

cat <<'TXT'
== 4. Check-list manuelle (10 min, lundi)
  [ ] Sheet KM_Mail_Workspace > actions_log : dernier job_done présent, aucun job_error
  [ ] Gmail > INBOX : vide (sinon lancer weeklyZeroInbox à la main)
  [ ] Gmail > 01_ACTION : traiter / répondre / passer en 02_ATTENTE ; retirer 01_ACTION une fois traité
  [ ] Gmail > 02_ATTENTE : relancer ce qui a plus de 7 jours
  [ ] Gmail > 09_NOTIFICATIONS/SECURITE : vérifier toute connexion non reconnue
  [ ] rapports/classification.md > « Domaines non couverts » : ajouter une règle si un domaine revient
TXT
