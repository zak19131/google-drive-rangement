# Taxonomie Gmail — arborescence cible

Principe : **INBOX = file d'arrivée, vidée chaque jour**. Tout fil porte un label de nature, et un seul. `01_ACTION` s'ajoute par-dessus quand il y a quelque chose à faire. Maximum 3 niveaux.

```
INBOX                              à zéro chaque jour
01_ACTION                          à traiter sous 48 h (retirer le label une fois traité)
02_ATTENTE                         j'attends une réponse (relance à J+7)
03_ADMIN/                          SENSIBLE — jamais marqué lu, jamais désabonné, jamais exporté sans accord
   SANTE · CAF · EMPLOI_PUBLIC · IMPOTS · ETAT · LOGEMENT
04_FINANCE/                        SENSIBLE
   BANQUE · CRYPTO · FACTURES/AAAA
05_PRO/
   ETUDES · ALERTES_EMPLOI
06_PROJETS/                        un sous-label par projet (création manuelle)
07_PERSO/
   FAMILLE (sensible) · ACHATS · TRANSPORT
08_NEWSLETTERS/                    archivées et lues automatiquement ; candidates au désabonnement
   MODE_SHOPPING · MEDIAS · CRYPTO_FINANCE · SERVICES · AUTRES
09_NOTIFICATIONS/
   SECURITE (sensible, non marqué lu) · RESEAUX_SOCIAUX · ALERTES
10_ARCHIVES/AAAA                   fils non classés de plus de 30 jours, rangés par année
99_CORBEILLE                       quarantaine de 30 jours avant la Corbeille Gmail (validation requise)
zz_KM_ROLLBACK/                    technique : ARCHIVED, WAS_UNREAD (retour arrière exact) — supprimable à J+30
```

## Traitement par nature

| Nature | Label | Sort de l'INBOX | Marqué lu | 01_ACTION si récent (≤ 30 j) non lu |
|---|---|---|---|---|
| Administration, banque, famille, logement | 03_ADMIN/*, 04_FINANCE/BANQUE, 07_PERSO/FAMILLE | oui, après le passage 01_ACTION | non | oui |
| Crypto, factures | 04_FINANCE/CRYPTO, 04_FINANCE/FACTURES | oui | non | non |
| Alertes de sécurité | 09_NOTIFICATIONS/SECURITE | oui | non | non (revue hebdomadaire) |
| Newsletters, alertes emploi, réseaux sociaux, alertes annonces | 08_*, 05_PRO/ALERTES_EMPLOI, 09_* | oui | oui | non |
| Transport, achats | 07_PERSO/TRANSPORT, 07_PERSO/ACHATS | oui | non | non |
| Non classé récent | 01_ACTION | oui | non | — |
| Non classé ancien | 10_ARCHIVES/AAAA | oui | oui | — |

Détail des règles : `gouvernance/regles_filtrage.md`. Conventions : `gouvernance/conventions.md`.
