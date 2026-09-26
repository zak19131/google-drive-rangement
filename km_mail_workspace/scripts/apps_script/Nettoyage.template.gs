/**
 * NETTOYAGE — met à la corbeille les pubs, newsletters, alertes emploi (Indeed, HelloWork...),
 * notifications de réseaux sociaux et alertes d'annonces.
 * JAMAIS touchés : banque, crypto, CAF, santé, impôts, France Travail, logement, famille, factures/reçus,
 *                  mails suivis (étoile), mails envoyés par toi.
 * Récupérable 30 jours : Gmail > Corbeille > sélectionner > « Déplacer vers la boîte de réception ».
 *
 * Utilisation : script.google.com > Nouveau projet > coller > Enregistrer > choisir « nettoyer » > Exécuter.
 * Le script se relance tout seul chaque minute jusqu'à la fin (journal : « Exécutions »).
 * Pour voir le total d'abord sans rien supprimer : exécuter « compter ».
 */
const QUERIES = /*QUERIES*/[];
const EXCLUDE = /*EXCLUDE*/'';
const BUDGET_MS = 4.5 * 60 * 1000;

function nettoyer() {
  const t0 = Date.now();
  const props = PropertiesService.getScriptProperties();
  let total = Number(props.getProperty('total') || 0);
  const seen = {};
  let idx = Number(props.getProperty('idx') || 0);   // reprise à la catégorie en cours, pas au début
  for (; idx < QUERIES.length; idx++) {
    props.setProperty('idx', String(idx));
    const item = QUERIES[idx];
    const q = item.q + ' ' + EXCLUDE;
    let stall = 0;
    while (true) {
      if (Date.now() - t0 > BUDGET_MS) {
        props.setProperty('total', String(total));
        relancer_();
        Logger.log('Pause (limite de temps), reprise dans 1 min. Total : ' + total);
        return total;
      }
      const found = GmailApp.search(q, 0, 100);
      if (!found.length) break;
      const threads = found.filter(t => !seen[t.getId()]);
      if (!threads.length) {                       // index Gmail pas encore à jour
        if (++stall > 5) break;
        Utilities.sleep(3000);
        continue;
      }
      stall = 0;
      threads.forEach(t => { seen[t.getId()] = true; });
      GmailApp.moveThreadsToTrash(threads);
      total += threads.length;
      Logger.log(item.nom + ' : +' + threads.length + ' (total ' + total + ')');
    }
  }
  props.setProperty('total', String(total));
  props.deleteProperty('idx');
  arreter_();
  Logger.log('TERMINÉ : ' + total + ' conversations mises à la corbeille.');
  return total;
}

/** Aperçu sans rien supprimer : nombre de conversations visées par catégorie. */
function compter() {
  const ids = {};
  QUERIES.forEach(item => {
    let n = 0;
    for (let s = 0; ; s += 500) {
      const p = GmailApp.search(item.q + ' ' + EXCLUDE, s, 500);
      p.forEach(t => { if (!ids[t.getId()]) { ids[t.getId()] = true; n++; } });   // chaque fil compté une seule fois
      if (p.length < 500) break;
    }
    Logger.log(item.nom + ' : ' + n + ' (nouveaux)');
  });
  const all = Object.keys(ids).length;
  Logger.log('TOTAL visé : ' + all + ' conversations');
  return all;
}

function relancer_() {
  arreter_();
  ScriptApp.newTrigger('nettoyer').timeBased().after(60 * 1000).create();
}

function arreter_() {
  ScriptApp.getProjectTriggers().filter(t => t.getHandlerFunction() === 'nettoyer').forEach(t => ScriptApp.deleteTrigger(t));
}
