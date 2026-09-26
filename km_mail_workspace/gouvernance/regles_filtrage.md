# Règles de filtrage (générées depuis rules.json)

Ordre = priorité : la première règle qui correspond gagne. Les règles personnelles (contacts, logement, école) sont dans `rules.local.json`, non versionné, et passent **avant** celles-ci.

| # | Règle | Label | Critère Gmail | Archive | Lu | Sensible | Désabo. possible |
|---:|---|---|---|---|---|---|---|
| 1 | securite | `09_NOTIFICATIONS` | `{from:(accounts.google.com) subject:("alerte de sécurité" OR "security alert" OR "nouvelle connexion" OR "new login" OR "new device" OR "code de vérification...` | — | — | oui | — |
| 2 | sante | `03_ADMIN` | `from:(ameli.fr OR assurance-maladie.fr OR monespacesante.fr OR doctolib.fr)` | — | — | oui | — |
| 3 | caf | `03_ADMIN` | `from:(caf.fr)` | — | — | oui | — |
| 4 | emploi_public | `03_ADMIN` | `from:(francetravail.fr OR pole-emploi.fr)` | — | — | oui | — |
| 5 | impots | `03_ADMIN` | `from:(impots.gouv.fr OR dgfip.finances.gouv.fr)` | — | — | oui | — |
| 6 | etat | `03_ADMIN` | `from:(ants.gouv.fr OR service-public.fr OR urssaf.fr OR franceconnect.gouv.fr OR interieur.gouv.fr OR messervices.etudiant.gouv.fr OR crous.fr)` | — | — | oui | — |
| 7 | newsletters_crypto | `99_CORBEILLE` | `{from:(info.mexc.com OR mkt.mexc.com OR news.crypto.com OR substack.com) from:(news@kucoin.com)}` | oui | oui | — | oui |
| 8 | banque | `04_FINANCE/BANQUE` | `from:(cic.fr OR creditmutuel.fr OR labanquepostale.fr OR monabanq.com OR boursorama.fr OR bnpparibas.com OR societegenerale.fr OR credit-agricole.fr OR lcl.f...` | — | — | oui | — |
| 9 | crypto | `04_FINANCE/CRYPTO` | `{from:(binance.com OR coinbase.com OR kraken.com OR mexc.com OR kucoin.com OR bybit.com OR bybit.eu OR crypto.com OR bitpanda.com OR ledger.com) from:(bybit)}` | oui | — | oui | — |
| 10 | factures | `04_FINANCE/FACTURES` | `subject:(facture OR invoice OR reçu OR receipt OR "avis d'échéance" OR échéancier OR quittance)` | oui | — | oui | — |
| 11 | alertes_emploi | `05_PRO` | `from:(jobalert.indeed.com OR indeed.com OR hellowork.com OR jobrapidoalert.com OR welcometothejungle.com OR jobteaser.com OR apec.fr OR meteojob.com OR monst...` | oui | oui | — | oui |
| 12 | etudes | `05_PRO` | `from:(ecandidats.fr OR parcoursup.fr OR campusfrance.org OR superprof.com)` | — | — | — | — |
| 13 | transport | `07_PERSO` | `{from:(ouigo.com OR sncf.fr OR sncf-connect.com OR li.me OR account.heetch.com OR maratp.fr OR ratp.fr OR blablacar.fr OR flixbus.fr) from:(noreply@uber.com)}` | oui | — | — | — |
| 14 | alertes | `09_NOTIFICATIONS` | `{from:(alertes.seloger.com OR seloger.com OR leboncoin.fr) subject:("nouvelle annonce")}` | oui | oui | — | — |
| 15 | achats | `07_PERSO` | `{from:(vinted.fr OR stockx.com) subject:("votre commande" OR "your order" OR expédié OR shipped OR livraison)}` | oui | — | — | — |
| 16 | reseaux_sociaux | `09_NOTIFICATIONS` | `from:(facebookmail.com OR service.tiktok.com OR tiktok.com OR mail.instagram.com OR discord.com OR x.com OR twitter.com OR snapchat.com OR linkedin.com OR qu...` | oui | oui | — | — |
| 17 | medias | `99_CORBEILLE` | `from:(nytimes.com OR newyorktimes.com OR e.nytimes.com OR actu.mytf1.fr OR fashionunited.fr OR newsletter.letudiant.fr OR e.change.org OR socialgood.inc OR e...` | oui | oui | — | oui |
| 18 | mode_shopping | `99_CORBEILLE` | `from:(email.arlettie.fr OR official.asos.com OR info.versace.com OR enews.versace.com OR news-longchamp.com OR newsletters.nyxcosmetics.com OR news-hb.hugobo...` | oui | oui | — | oui |
| 19 | services | `99_CORBEILLE` | `{from:(emails.betclic.fr OR metricool.com OR mkt.voiapp.io OR hello.heetch.com OR parclick.com OR legrandrex.com OR trenitalia.fr OR email.tacobell.com OR se...` | oui | oui | — | oui |
| 20 | promotions_catchall | `99_CORBEILLE` | `category:promotions` | oui | oui | — | oui |
| 21 | social_catchall | `09_NOTIFICATIONS` | `category:social` | oui | oui | — | — |

Étapes du moteur après les règles : factures -> `04_FINANCE/FACTURES/AAAA` ; sensibles récents non lus -> `01_ACTION` ; sensibles archivés (label conservé) ; non classés > 30 j -> `10_ARCHIVES/AAAA` ; non classés récents -> `01_ACTION`.
