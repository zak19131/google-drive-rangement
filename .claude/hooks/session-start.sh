#!/bin/bash
# Installe les dépendances runtime des skills de .claude/skills (sessions cloud uniquement).
# Idempotent : chaque étape est sautée si l'outil est déjà présent.
set -uo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

log() { echo "[session-start] $*" >&2; }

# Node fetch (skills CLI / find-skills) doit passer par le proxy de session
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo 'export NODE_USE_ENV_PROXY=1' >> "$CLAUDE_ENV_FILE"
  echo 'export NODE_NO_WARNINGS=1' >> "$CLAUDE_ENV_FILE"
  [ -x /opt/pw-browsers/chromium ] && echo 'export AGENT_BROWSER_EXECUTABLE_PATH=/opt/pw-browsers/chromium' >> "$CLAUDE_ENV_FILE"
fi

# CLI npm : agent-browser (skill agent-browser) et skills (skill find-skills)
command -v agent-browser >/dev/null || npm i -g agent-browser@0.38.2 >/dev/null 2>&1 || log "agent-browser: échec install"
command -v skills >/dev/null || npm i -g skills@1.7.0 >/dev/null 2>&1 || log "skills CLI: échec install"

# ffmpeg (video-use, video-lens) + certutil (confiance CA proxy pour Chromium)
if ! command -v ffmpeg >/dev/null || ! command -v certutil >/dev/null; then
  (apt-get update -qq && apt-get install -y -qq ffmpeg libnss3-tools) >/dev/null 2>&1 || log "apt: échec ffmpeg/libnss3-tools"
fi

# Dépendances Python : video-lens + video-use
python3 -c "import youtube_transcript_api, yt_dlp, librosa, matplotlib, PIL, requests" 2>/dev/null || \
  pip install -q "youtube-transcript-api>=0.6.3" "yt-dlp>=2026.8.19" requests librosa matplotlib pillow numpy >/dev/null 2>&1 || log "pip: échec deps vidéo"

# Chromium doit faire confiance à la CA d'interception du proxy (sinon ERR_CERT_AUTHORITY_INVALID)
CA=/root/.ccr/agent-proxy-ca.crt
NSS="sql:$HOME/.pki/nssdb"
if [ -f "$CA" ] && command -v certutil >/dev/null && ! certutil -d "$NSS" -L 2>/dev/null | grep -q ccr-agent-proxy-ca; then
  mkdir -p "$HOME/.pki/nssdb"
  [ -f "$HOME/.pki/nssdb/cert9.db" ] || certutil -d "$NSS" -N --empty-password
  tmp=$(mktemp -d)
  csplit -s -z -f "$tmp/ca-" "$CA" '/-----BEGIN CERTIFICATE-----/' '{*}'
  i=0; for c in "$tmp"/ca-*; do certutil -d "$NSS" -A -t "C,," -n "ccr-agent-proxy-ca-$i" -i "$c"; i=$((i+1)); done
  rm -rf "$tmp"
fi

exit 0
