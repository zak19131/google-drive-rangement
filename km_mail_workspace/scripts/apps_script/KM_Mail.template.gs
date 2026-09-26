/**
 * KM_Mail — moteur de rangement Gmail (Google Apps Script, s'exécute DANS ton compte Google).
 * Aucune donnée ne sort du compte. Journal + rollback dans une Google Sheet « KM_Mail_Workspace ».
 *
 * Fichier GÉNÉRÉ par scripts/build_gmail_artifacts.py (ne pas éditer RULES/LABELS à la main).
 *
 * Mode d'emploi (détail : gouvernance/procedure_execution.md)
 *   1. script.google.com > Nouveau projet > coller ce fichier > Enregistrer.
 *   2. Exécuter `audit`            -> volumétrie réelle (Sheet, onglet « audit »).
 *   3. Exécuter `planDryRun`       -> ce qui serait fait, règle par règle (onglet « plan_dry_run »).
 *   4. Validation CEO. Puis CONFIG.DRY_RUN = false.
 *   5. Exécuter `setupLabels` puis `apply` (reprise automatique toutes les minutes jusqu'à la fin).
 *   6. En cas de problème : `rollback`.
 *   7. Routine : `installWeeklyTrigger`.
 */

const CONFIG = {
  DRY_RUN: true,               // true = aucune modification de la boîte
  RECENT_DAYS: 30,             // fils plus récents = candidats 01_ACTION
  BATCH: 100,                  // limite Gmail pour les opérations groupées
  MAX_RUNTIME_MS: 4.5 * 60 * 1000,
  FIRST_YEAR: 2004,
  MARK_ARCHIVES_READ: true,    // fils non classés > 30 j archivés en « lu »
  ALLOW_UNSUBSCRIBE: false,    // désabonnement réel uniquement si true ET lignes VALIDER=OUI
  ALLOW_TRASH: false,          // passage réel en Corbeille uniquement si true (après 30 j en 99_CORBEILLE)
  SPREADSHEET_NAME: 'KM_Mail_Workspace',
};

const LABELS = /*LABELS*/[]/*END_LABELS*/;
const RULES = /*RULES*/[]/*END_RULES*/;
const UNSUB_PREVALIDATED = /*UNSUB*/[]/*END_UNSUB*/;   // validés par le titulaire

const RB_ARCHIVED = 'zz_KM_ROLLBACK/ARCHIVED';
const RB_UNREAD = 'zz_KM_ROLLBACK/WAS_UNREAD';
const ACTION_LABEL = '01_ACTION';
const TRASH_LABEL = '99_CORBEILLE';
const RESUME_FN = 'resume';
const INVOICE_LABEL = '04_FINANCE/FACTURES';

// ---------------------------------------------------------------- utilitaires

function props_() { return PropertiesService.getScriptProperties(); }

function ss_() {
  const id = props_().getProperty('SPREADSHEET_ID');
  if (id) return SpreadsheetApp.openById(id);
  const ss = SpreadsheetApp.create(CONFIG.SPREADSHEET_NAME);
  props_().setProperty('SPREADSHEET_ID', ss.getId());
  return ss;
}

function sheet_(name, header) {
  const ss = ss_();
  let sh = ss.getSheetByName(name);
  if (!sh) {
    sh = ss.insertSheet(name);
    if (header) sh.appendRow(header);
  }
  return sh;
}

function appendRows_(name, header, rows) {
  if (!rows.length) return;
  const sh = sheet_(name, header);
  sh.getRange(sh.getLastRow() + 1, 1, rows.length, rows[0].length).setValues(rows);
}

function now_() { return new Date().toISOString(); }

function log_(action, detail) {
  appendRows_('actions_log', ['horodatage', 'run_id', 'mode', 'action', 'detail'],
    [[now_(), state_().runId || '', CONFIG.DRY_RUN ? 'DRY-RUN' : 'EXECUTE', action, String(detail)]]);
}

function labelQuery_(name) {
  return 'label:' + name.toLowerCase().replace(/[\/ ]/g, '-');
}

function getLabel_(name) {
  return GmailApp.getUserLabelByName(name) || (CONFIG.DRY_RUN ? null : GmailApp.createLabel(name));
}

function yearsDesc_() {
  const out = [];
  for (let y = new Date().getFullYear(); y >= CONFIG.FIRST_YEAR; y--) out.push(y);
  return out;
}

function yearLabels_() {
  return yearsDesc_().map(y => '10_ARCHIVES/' + y).concat(yearsDesc_().map(y => INVOICE_LABEL + '/' + y));
}

function countQuery_(q) {
  let n = 0;
  for (let start = 0; ; start += 500) {
    const page = GmailApp.search(q, start, 500);
    n += page.length;
    if (page.length < 500) return n;
  }
}

// ---------------------------------------------------------------- état + reprise

function state_() {
  const raw = props_().getProperty('KM_STATE');
  return raw ? JSON.parse(raw) : {};
}

function saveState_(s) { props_().setProperty('KM_STATE', JSON.stringify(s)); }

function clearResumeTriggers_() {
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === RESUME_FN)
    .forEach(t => ScriptApp.deleteTrigger(t));
}

function scheduleResume_() {
  clearResumeTriggers_();
  ScriptApp.newTrigger(RESUME_FN).timeBased().after(60 * 1000).create();
}

/** Lance un job découpé en étapes ; reprend automatiquement si le temps d'exécution est dépassé. */
function startJob_(job, steps) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) throw new Error('Un job KM_Mail tourne déjà.');
  try {
    const cur = state_();
    if (cur.status === 'RUNNING') throw new Error('Job « ' + cur.job + ' » en cours. Utiliser resume() ou resetJob().');
    const runId = job + '_' + Utilities.formatDate(new Date(), 'UTC', 'yyyyMMdd_HHmmss');
    saveState_({ job: job, steps: steps, stepIndex: 0, offset: 0, runId: runId, status: 'RUNNING',
                 dryRun: CONFIG.DRY_RUN, startedAt: now_() });
  } finally {
    lock.releaseLock();
  }
  log_('job_start', job + ' (' + steps.length + ' étapes)');
  return resume();
}

function resume() {
  const s = state_();
  if (s.status !== 'RUNNING') { clearResumeTriggers_(); return s; }
  if (s.dryRun !== CONFIG.DRY_RUN) {
    s.status = 'ERROR'; saveState_(s);
    throw new Error('CONFIG.DRY_RUN a changé en cours de job. resetJob() puis relancer.');
  }
  const t0 = Date.now();
  try {
    while (s.stepIndex < s.steps.length) {
      if (!timeLeft_(t0)) { scheduleResume_(); return s; }
      const step = s.steps[s.stepIndex];
      const done = runStep_(step, s, t0);
      saveState_(s);
      if (!done) { scheduleResume_(); return s; }   // budget temps épuisé : reprise dans 1 min
      s.stepIndex++; s.offset = 0; saveState_(s);
    }
    s.status = 'DONE'; s.finishedAt = now_(); saveState_(s);
    clearResumeTriggers_();
    log_('job_done', s.job);
    return s;
  } catch (e) {
    s.status = 'ERROR'; s.error = String(e && e.stack || e); saveState_(s);
    clearResumeTriggers_();
    log_('job_error', s.error);   // arrêt net : aucune reprise automatique après erreur
    throw e;
  }
}

function resetJob() { clearResumeTriggers_(); props_().deleteProperty('KM_STATE'); }

function status() { const s = state_(); Logger.log(JSON.stringify(s, null, 2)); return s; }

function timeLeft_(t0) { return Date.now() - t0 < CONFIG.MAX_RUNTIME_MS; }

// ---------------------------------------------------------------- étapes

function runStep_(step, s, t0) {
  switch (step.type) {
    case 'count': return stepCount_(step, s);
    case 'plan': return stepPlan_(step, s, t0);
    case 'move': return stepMove_(step, s, t0);
    case 'rollback_label': return stepRollback_(step, s, t0);
    case 'plan_check': return stepPlanCheck_(step, s);
    default: throw new Error('Étape inconnue : ' + step.type);
  }
}

function stepCount_(step, s) {
  const n = countQuery_(step.q);
  const sample = n ? GmailApp.search(step.q, 0, 3).map(t => t.getFirstMessageSubject()).join(' | ') : '';
  appendRows_('audit', ['run_id', 'dimension', 'cle', 'requete', 'fils', 'exemples_objets'],
    [[s.runId, step.dim, step.key, step.q, n, sample]]);
  return true;
}

function stepPlan_(step, s, t0) {
  let q = step.q;
  let exact = true;
  let n;
  try {
    n = countQuery_(q + (step.exclude ? ' ' + step.exclude : ''));
  } catch (e) {   // requête trop longue : borne haute sans exclusion des règles précédentes
    exact = false;
    n = countQuery_(q);
  }
  const sample = n ? GmailApp.search(q, 0, 3).map(t => t.getFirstMessageSubject()).join(' | ') : '';
  appendRows_('plan_dry_run',
    ['run_id', 'etape', 'label', 'requete', 'fils_concernes', 'exact', 'archiver', 'marquer_lu', 'exemples'],
    [[s.runId, step.name, step.label, q, n, exact, !!step.archive, !!step.markRead, sample]]);
  s.planTotal = (s.planTotal || 0) + n;
  return true;
}

/** Contrôle de cohérence du dry-run : somme des étapes vs total INBOX (doit être égal si les exclusions ont marché). */
function stepPlanCheck_(step, s) {
  const total = countQuery_('in:inbox');
  appendRows_('plan_dry_run', ['run_id', 'etape', 'label', 'requete', 'fils_concernes', 'exact'],
    [[s.runId, 'CONTROLE', 'somme étapes = ' + s.planTotal, 'in:inbox', total, s.planTotal === total]]);
  return true;
}

/**
 * Déplacement : applique label (+ archive / lu) par lots de 100.
 * Chaque fil archivé reçoit RB_ARCHIVED, chaque fil passé en lu reçoit RB_UNREAD -> rollback exact.
 * Deux passes quand markRead : d'abord les non-lus (tagués RB_UNREAD), puis le reste.
 */
function stepMove_(step, s, t0) {
  if (!step.archive && !step.q.includes('has:nouserlabels') && !step.q.includes('-' + labelQuery_(step.label))) {
    throw new Error('Étape non auto-limitante : ' + step.name);   // garde-fou anti-boucle infinie
  }
  const target = getLabel_(step.label);
  const rbArch = getLabel_(RB_ARCHIVED);
  const rbUnread = getLabel_(RB_UNREAD);
  const action = step.addAction ? getLabel_(ACTION_LABEL) : null;
  const passes = step.markRead ? [' is:unread', ''] : [''];
  s.pass = s.pass || 0;
  const seen = {};
  while (s.pass < passes.length) {
    const q = step.q + passes[s.pass];
    let stall = 0;
    while (true) {
      if (!timeLeft_(t0)) return false;
      const found = GmailApp.search(q, 0, CONFIG.BATCH);
      if (!found.length) break;
      const threads = found.filter(t => !seen[t.getId()]);
      if (!threads.length) {             // index de recherche en retard : on attend, puis on s'arrête net
        if (++stall > 5) throw new Error('Index Gmail figé sur « ' + q + ' » : arrêt de sécurité.');
        Utilities.sleep(3000);
        continue;
      }
      stall = 0;
      threads.forEach(t => { seen[t.getId()] = true; });
      target.addToThreads(threads);
      if (action) action.addToThreads(threads);
      const wasUnread = step.markRead && passes[s.pass] === ' is:unread';
      if (wasUnread) { rbUnread.addToThreads(threads); GmailApp.markThreadsRead(threads); }
      if (step.archive) { rbArch.addToThreads(threads); GmailApp.moveThreadsToArchive(threads); }
      appendRows_('moves', ['horodatage', 'run_id', 'etape', 'label', 'thread_id', 'archive', 'marque_lu', '01_ACTION'],
        threads.map(t => [now_(), s.runId, step.name, step.label, t.getId(), !!step.archive, wasUnread, !!action]));
      s.moved = (s.moved || 0) + threads.length;
      if (step.label === TRASH_LABEL) markQuarantineStart_();
    }
    s.pass++;
  }
  s.pass = 0;
  log_('move', step.name + ' -> ' + step.label + ' (cumul run : ' + (s.moved || 0) + ')');
  return true;
}

function stepRollback_(step, s, t0) {
  const lbl = GmailApp.getUserLabelByName(step.label);
  if (!lbl) return true;
  while (true) {
    if (!timeLeft_(t0)) return false;
    const threads = lbl.getThreads(0, CONFIG.BATCH);
    if (!threads.length) return true;
    if (step.label === RB_ARCHIVED) GmailApp.moveThreadsToInbox(threads);
    if (step.label === RB_UNREAD) GmailApp.markThreadsUnread(threads);
    lbl.removeFromThreads(threads);
    appendRows_('rollback', ['horodatage', 'run_id', 'label_retire', 'fils'], [[now_(), s.runId, step.label, threads.length]]);
  }
}

// ---------------------------------------------------------------- construction des plans

function moveSteps_() {
  const steps = [];
  const recent = CONFIG.RECENT_DAYS + 'd';
  // 1. Règles, dans l'ordre (première qui matche gagne grâce à has:nouserlabels)
  RULES.forEach(r => steps.push({
    type: 'move', name: 'regle_' + r.id, label: r.label,
    q: 'in:inbox (' + r.q + ') has:nouserlabels', archive: r.archive, markRead: r.mark_read,
  }));
  // 1b. Factures rangées par année (04_FINANCE/FACTURES/AAAA), où qu'elles soient
  yearsDesc_().forEach(y => steps.push({
    type: 'move', name: 'factures_' + y, label: INVOICE_LABEL + '/' + y, archive: false, markRead: false,
    q: labelQuery_(INVOICE_LABEL) + ' after:' + y + '/01/01 before:' + (y + 1) + '/01/01 -' + labelQuery_(INVOICE_LABEL + '/' + y),
  }));
  // 2. Fils sensibles laissés en INBOX : récents non lus -> 01_ACTION ; puis tout -> archive (label conservé)
  const kept = [...new Set(RULES.filter(r => !r.archive).map(r => r.label))];
  kept.forEach(l => {
    if (RULES.some(r => r.label === l && !r.archive && r.action_if_recent)) {
      steps.push({ type: 'move', name: 'action_' + l, label: ACTION_LABEL, archive: true, markRead: false,
                   q: 'in:inbox ' + labelQuery_(l) + ' newer_than:' + recent + ' is:unread' });
    }
    steps.push({ type: 'move', name: 'archive_' + l, label: l, archive: true, markRead: false,
                 q: 'in:inbox ' + labelQuery_(l) });
  });
  // 3. Non classés anciens -> 10_ARCHIVES/AAAA
  yearsDesc_().forEach(y => steps.push({
    type: 'move', name: 'archives_' + y, label: '10_ARCHIVES/' + y, archive: true, markRead: CONFIG.MARK_ARCHIVES_READ,
    q: 'in:inbox has:nouserlabels older_than:' + recent + ' after:' + y + '/01/01 before:' + (y + 1) + '/01/01',
  }));
  // 4. Non classés récents -> 01_ACTION (INBOX vidée vers la liste d'action)
  steps.push({ type: 'move', name: 'inbox_vers_action', label: ACTION_LABEL, archive: true, markRead: false,
               q: 'in:inbox has:nouserlabels' });
  return steps;
}

// ---------------------------------------------------------------- points d'entrée

/** Phase 1-2 : volumétrie réelle (lecture seule). */
function audit() {
  const steps = [];
  [['total_inbox', 'in:inbox'], ['non_lus_inbox', 'in:inbox is:unread'], ['envoyes', 'in:sent'],
   ['etoiles', 'is:starred'], ['pj_inbox', 'in:inbox has:attachment'], ['pj_>10Mo', 'larger:10M'],
   ['pj_>5Mo', 'larger:5M']].forEach(([k, q]) => steps.push({ type: 'count', dim: 'global', key: k, q: q }));
  ['promotions', 'social', 'updates', 'forums', 'primary'].forEach(c =>
    steps.push({ type: 'count', dim: 'categorie', key: c, q: 'in:inbox category:' + c }));
  yearsDesc_().forEach(y => steps.push({ type: 'count', dim: 'annee', key: String(y),
    q: 'in:inbox after:' + y + '/01/01 before:' + (y + 1) + '/01/01' }));
  RULES.forEach(r => steps.push({ type: 'count', dim: 'regle', key: r.id + ' -> ' + r.label, q: 'in:inbox (' + r.q + ')' }));
  return startJob_('audit', steps);
}

/** Phase 4 dry-run : ce que ferait apply(), étape par étape, sans rien modifier. */
function planDryRun() {
  const steps = [];
  const prior = [];
  RULES.forEach(r => {
    steps.push({ type: 'plan', name: 'regle_' + r.id, label: r.label, q: 'in:inbox (' + r.q + ')',
                 exclude: prior.map(p => '-(' + p + ')').join(' '), archive: r.archive, markRead: r.mark_read });
    prior.push(r.q);
  });
  const none = prior.map(p => '-(' + p + ')').join(' ');
  yearsDesc_().forEach(y => steps.push({ type: 'plan', name: 'archives_' + y, label: '10_ARCHIVES/' + y,
    q: 'in:inbox older_than:' + CONFIG.RECENT_DAYS + 'd after:' + y + '/01/01 before:' + (y + 1) + '/01/01',
    exclude: none, archive: true, markRead: CONFIG.MARK_ARCHIVES_READ }));
  steps.push({ type: 'plan', name: 'inbox_vers_action', label: ACTION_LABEL,
               q: 'in:inbox newer_than:' + CONFIG.RECENT_DAYS + 'd', exclude: none, archive: true });
  steps.push({ type: 'plan_check' });
  return startJob_('plan', steps);
}

/** Crée l'arborescence (max 3 niveaux) + labels de rollback. */
function setupLabels() {
  if (CONFIG.DRY_RUN) { log_('setupLabels', 'DRY-RUN : ' + LABELS.length + ' labels seraient créés'); return; }
  const all = LABELS.concat(yearLabels_(), [RB_ARCHIVED, RB_UNREAD]);
  all.forEach(name => {
    if (name.split('/').length > 3) throw new Error('Profondeur > 3 : ' + name);
    getLabel_(name);
  });
  log_('setupLabels', all.length + ' labels vérifiés/créés');
}

/** Phase 4 exécution : classement + archivage par année + INBOX vers 01_ACTION. */
function apply() {
  if (CONFIG.DRY_RUN) return planDryRun();
  setupLabels();
  return startJob_('apply', moveSteps_());
}

/** Annule apply() : remet en INBOX ce qui a été archivé, remet en non-lu, retire les labels de rollback. */
function rollback() {
  if (CONFIG.DRY_RUN) { log_('rollback', 'DRY-RUN : rien à faire'); return; }
  return startJob_('rollback', [RB_ARCHIVED, RB_UNREAD].map(l => ({ type: 'rollback_label', label: l })));
}

/** Retire aussi les labels de taxonomie posés (rollback complet). */
function rollbackLabels() {
  if (CONFIG.DRY_RUN) return;
  const labels = LABELS.concat(yearLabels_());
  return startJob_('rollback_labels', labels.map(l => ({ type: 'rollback_label', label: l })));
}

/** Après validation du résultat (J+30) : supprime les 2 labels techniques de rollback (les mails restent). */
function purgeRollbackLabels() {
  if (CONFIG.DRY_RUN) return;
  [RB_ARCHIVED, RB_UNREAD].forEach(n => { const l = GmailApp.getUserLabelByName(n); if (l) l.deleteLabel(); });
  log_('purgeRollbackLabels', 'labels techniques supprimés');
}

// ---------------------------------------------------------------- désabonnements

/** Liste les expéditeurs newsletter + en-tête List-Unsubscribe -> onglet « desabonnements » (colonne VALIDER). */
function listNewsletters() {
  const seen = {};
  const rows = [];
  const add = (msg, label) => {
    const from = msg.getFrom();
    const addr = (from.match(/<([^>]+)>/) || [null, from])[1].toLowerCase();
    const dom = addr.split('@')[1] || addr;
    if (seen[dom]) { seen[dom].n++; return; }
    const lu = msg.getHeader('List-Unsubscribe') || '';
    const post = (msg.getHeader('List-Unsubscribe-Post') || '').toLowerCase().includes('one-click');
    const https = (lu.match(/<(https:[^>]+)>/i) || [])[1] || '';
    const mailto = (lu.match(/<(mailto:[^>]+)>/i) || [])[1] || '';
    const pre = UNSUB_PREVALIDATED.some(p => dom === p || dom.endsWith('.' + p)) ? 'OUI' : '';
    seen[dom] = { n: 1, row: [dom, addr, label, 0, post && https ? https : '', mailto, pre, ''] };
  };
  RULES.filter(r => r.newsletter && !r.sensitive).forEach(r => {
    GmailApp.search(r.q + ' newer_than:180d', 0, 50).forEach(t => {
      const msgs = t.getMessages();
      add(msgs[msgs.length - 1], r.label);
    });
  });
  Object.keys(seen).forEach(d => { seen[d].row[3] = seen[d].n; rows.push(seen[d].row); });
  rows.sort((a, b) => (b[6] === 'OUI') - (a[6] === 'OUI') || b[3] - a[3]);
  appendRows_('desabonnements', ['domaine', 'expediteur', 'label', 'fils_180j_echantillon', 'https_one_click', 'mailto', 'VALIDER', 'resultat'], rows);
  log_('listNewsletters', rows.length + ' expéditeurs listés');
}

/** Exécute uniquement les lignes VALIDER=OUI, en one-click HTTPS (RFC 8058). mailto : traitement manuel. */
function unsubscribeValidated() {
  const sh = sheet_('desabonnements');
  const data = sh.getDataRange().getValues();
  for (let i = 1; i < data.length; i++) {
    const [dom, , , , https, , valider, resultat] = data[i];
    if (String(valider).trim().toUpperCase() !== 'OUI' || resultat) continue;
    let res;
    if (CONFIG.DRY_RUN || !CONFIG.ALLOW_UNSUBSCRIBE) res = 'DRY-RUN (non exécuté)';
    else if (https) {
      const r = UrlFetchApp.fetch(https, { method: 'post', payload: 'List-Unsubscribe=One-Click', muteHttpExceptions: true });
      res = 'HTTP ' + r.getResponseCode();
    } else res = 'MANUEL (pas de one-click)';
    if (!res.startsWith('DRY-RUN')) sh.getRange(i + 1, 8).setValue(res);
    log_('unsubscribe', dom + ' : ' + res);
  }
}

// ---------------------------------------------------------------- corbeille (30 jours)

function markQuarantineStart_() {
  if (!props_().getProperty('CORBEILLE_SINCE')) props_().setProperty('CORBEILLE_SINCE', now_());
}

/** Place en 99_CORBEILLE les fils d'une requête validée (jamais les sensibles). */
function markForTrash(query) {
  const sensitive = RULES.filter(r => r.sensitive).map(r => '-(' + r.q + ')').join(' ');
  const q = query + ' ' + sensitive;
  if (CONFIG.DRY_RUN) { log_('markForTrash', 'DRY-RUN : ' + countQuery_(q) + ' fils pour « ' + query + ' »'); return; }
  const lbl = getLabel_(TRASH_LABEL);
  let n = 0;
  while (true) {
    const threads = GmailApp.search(q + ' -' + labelQuery_(TRASH_LABEL), 0, CONFIG.BATCH);
    if (!threads.length) break;
    lbl.addToThreads(threads);
    GmailApp.moveThreadsToArchive(threads);
    appendRows_('corbeille', ['thread_id', 'date_ajout', 'requete', 'statut'], threads.map(t => [t.getId(), now_(), query, '']));
    n += threads.length;
  }
  if (n) markQuarantineStart_();
  log_('markForTrash', n + ' fils -> ' + TRASH_LABEL + ' (« ' + query + ' »)');
}

/**
 * Passe en Corbeille Gmail les fils 99_CORBEILLE de plus de 30 jours, jamais avant J+30 de la première mise en quarantaine,
 * jamais un fil sensible. Uniquement si ALLOW_TRASH. La Corbeille Gmail garde encore 30 jours (untrash possible).
 */
function purgeCorbeille() {
  const since = props_().getProperty('CORBEILLE_SINCE');
  const limit = Date.now() - 30 * 24 * 3600 * 1000;
  if (!since || new Date(since).getTime() > limit) {
    log_('purgeCorbeille', 'quarantaine en cours depuis ' + since + ' : rien à faire');
    return 0;
  }
  const sensitive = RULES.filter(r => r.sensitive).map(r => '-(' + r.q + ')').join(' ');
  const q = labelQuery_(TRASH_LABEL) + ' older_than:30d ' + sensitive;
  if (CONFIG.DRY_RUN || !CONFIG.ALLOW_TRASH) {
    const n = countQuery_(q);
    log_('purgeCorbeille', n + ' fils éligibles (non exécuté : DRY_RUN ou ALLOW_TRASH=false)');
    return n;
  }
  let n = 0;
  while (true) {
    const threads = GmailApp.search(q, 0, CONFIG.BATCH);
    if (!threads.length) break;
    GmailApp.moveThreadsToTrash(threads);
    appendRows_('corbeille', ['thread_id', 'date_ajout', 'requete', 'statut'], threads.map(t => [t.getId(), now_(), 'purge', 'CORBEILLE_GMAIL']));
    n += threads.length;
  }
  log_('purgeCorbeille', n + ' fils mis en Corbeille Gmail');
  return n;
}

// ---------------------------------------------------------------- routine hebdomadaire

/** Chaque lundi 7h : re-classe ce qui est arrivé hors filtres, remet l'INBOX à zéro. */
function weeklyZeroInbox() {
  if (state_().status === 'RUNNING') { log_('weekly', 'job en cours, semaine sautée'); return; }
  if (CONFIG.DRY_RUN) return planDryRun();
  return startJob_('weekly', moveSteps_());
}

function installWeeklyTrigger() {
  ScriptApp.getProjectTriggers().filter(t => t.getHandlerFunction() === 'weeklyZeroInbox')
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('weeklyZeroInbox').timeBased().onWeekDay(ScriptApp.WeekDay.MONDAY).atHour(7).create();
  log_('installWeeklyTrigger', 'lundi 7h');
}
