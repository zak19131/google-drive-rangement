# Taxonomie Gmail — v2 (validée le 26/09/2026)

Principe : **INBOX = file d'arrivée, vidée chaque jour**. Un fil = un label de nature. `01_ACTION` s'ajoute quand il y a quelque chose à faire. Arborescence plate, sauf FINANCE et ARCHIVES (3 niveaux maximum).

```
INBOX                 à zéro chaque jour
01_ACTION             à traiter sous 48 h (retirer le label une fois traité)
02_ATTENTE            j'attends une réponse (relance à J+7)
03_ADMIN              SENSIBLE — santé, CAF, France Travail, impôts, État, logement
04_FINANCE/           SENSIBLE
   BANQUE             banques, néobanques, paiements
   CRYPTO             plateformes crypto (comptes, pas marketing)
   FACTURES/AAAA      factures et reçus, rangés par année
05_PRO                études, candidatures, alertes emploi (désabonnement validé)
06_PROJETS            un sous-label par projet (création manuelle)
07_PERSO              famille (sensible), achats, transport
09_NOTIFICATIONS      sécurité (-> 01_ACTION si récente), réseaux sociaux, alertes d'annonces
10_ARCHIVES/AAAA      non classés de plus de 30 jours
99_CORBEILLE          newsletters et promotions : quarantaine 30 j, puis Corbeille Gmail (30 j encore récupérable)
zz_KM_ROLLBACK/       technique (ARCHIVED, WAS_UNREAD) : retour arrière exact, supprimable à J+30
```

## Traitement
| Flux | Label | Archivé | Marqué lu | 01_ACTION si ≤ 30 j non lu |
|---|---|---|---|---|
| Admin, banque, famille | 03_ADMIN, 04_FINANCE/BANQUE, 07_PERSO | oui | **non** | oui |
| Alertes de sécurité | 09_NOTIFICATIONS | oui | **non** | oui |
| Crypto, factures | 04_FINANCE/CRYPTO, 04_FINANCE/FACTURES(/AAAA) | oui | non | non |
| Alertes emploi, réseaux sociaux, alertes d'annonces | 05_PRO, 09_NOTIFICATIONS | oui | oui | non |
| Transport, achats | 07_PERSO | oui | non | non |
| Newsletters, promotions | 99_CORBEILLE | oui | oui | non |
| Non classé récent / ancien | 01_ACTION / 10_ARCHIVES/AAAA | oui | non / oui | — |

Détail : `gouvernance/regles_filtrage.md`.
