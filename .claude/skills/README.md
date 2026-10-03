# Skills projet — inventaire et procédure

Skills tiers installés au niveau projet : chargés automatiquement par Claude Code
(CLI et sessions cloud) lancé dans ce dépôt. Provenance exacte (dépôt, chemin,
commit, date) dans `SOURCES.tsv`. Tous audités avant installation (MIT ou Apache-2.0,
aucun hook, aucun postinstall hors binaire officiel agent-browser).

| Skill | Source | Déclenchement | Dépendances |
|---|---|---|---|
| grill-me (+ grilling) | mattpocock/skills | `/grill-me` uniquement (`disable-model-invocation`) | — |
| content-strategy | coreyhaines31/marketingskills | auto / `/content-strategy` | — |
| seo-audit | coreyhaines31/marketingskills | auto / `/seo-audit` | — |
| ai-seo | coreyhaines31/marketingskills | auto / `/ai-seo` | — |
| pricing | coreyhaines31/marketingskills | auto / `/pricing` | — |
| caveman | JuliusBrussee/caveman | `/caveman` | — (skill seul, hooks du repo non installés) |
| anti-ui-slop | github/awesome-copilot | auto / `/anti-ui-slop` | — |
| minimalist-ui | Leonxlnx/taste-skill (`skills/minimalist-skill`) | auto / `/minimalist-ui` | — |
| ui-ux-pro-max | nextlevelbuilder/ui-ux-pro-max-skill | auto / `/ui-ux-pro-max` | python3 (stdlib) |
| web-design-guidelines | vercel-labs/agent-skills | auto / `/web-design-guidelines` | réseau (récupère les guidelines à jour) |
| agent-browser | vercel-labs/agent-browser | auto / `/agent-browser` | CLI `agent-browser` (npm) + Chromium |
| find-skills | vercel-labs/skills | auto / `/find-skills` | CLI `skills` (npm), réseau skills.sh |
| video-use | browser-use/video-use | auto / `/video-use` | ffmpeg, librosa, matplotlib, pillow, numpy ; `ELEVENLABS_API_KEY` pour la transcription |
| video-lens | kar2phi/video-lens | `/video-lens <url YouTube>` | yt-dlp, youtube-transcript-api ; mlx-whisper (Apple Silicon) en repli |

`canvas-design` n'est pas ici : c'est le skill officiel Anthropic déjà fourni par le compte
(`anthropic-skills:canvas-design`).

Optionnel pour les skills marketing : un fichier `.agents/product-marketing.md` décrivant
le produit évite qu'ils reposent les mêmes questions.

## Sessions cloud

`.claude/hooks/session-start.sh` (SessionStart, cloud uniquement) réinstalle les CLI et
dépendances, exporte `NODE_USE_ENV_PROXY=1` (requis par `skills find`) et
`AGENT_BROWSER_EXECUTABLE_PATH`, et ajoute la CA du proxy de session au magasin NSS de
Chromium (sinon `ERR_CERT_AUTHORITY_INVALID`). Limite connue : YouTube bloque la
récupération de transcriptions depuis les IP cloud → video-lens complet uniquement en local.

## Commandes

```bash
# Vérifier
ls .claude/skills && claude -p "liste les skills du dossier .claude/skills"
agent-browser --version && skills --version && ffmpeg -version | head -1

# Découvrir / ajouter un skill (find-skills)
NODE_USE_ENV_PROXY=1 skills find "<besoin>"     # NODE_USE_ENV_PROXY seulement derrière un proxy
npx skills add <owner/repo>@<skill>              # auditer le SKILL.md avant usage

# Mettre à jour un skill : re-cloner la source listée dans SOURCES.tsv, auditer le diff,
# recopier le dossier, mettre à jour le commit dans SOURCES.tsv
git clone --depth 1 https://github.com/<owner>/<repo> /tmp/src && diff -r /tmp/src/<path> .claude/skills/<skill>

# Mettre à jour les CLI
npm i -g agent-browser@latest skills@latest

# Désinstaller un skill
git rm -r .claude/skills/<skill>    # puis retirer sa ligne de SOURCES.tsv

# Recharger : les skills projet sont lus au démarrage d'une session Claude Code
```
