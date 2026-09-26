/* Test d'intégration de build/KM_Mail.gs contre une boîte Gmail simulée.
 * Usage : node scripts/tests/test_km_mail.js   (depuis km_mail_workspace/, après build_gmail_artifacts.py)
 * Vérifie : dry-run sans effet, plan cohérent, apply -> INBOX à zéro sans perte, reprise après timeout,
 *           sensibles jamais marqués lus, rollback exact, cohérence avec classify_mails.py (via CSV exporté). */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const WS = path.resolve(__dirname, '..', '..');
const OWN = 'titulaire@example.com';
const DAY = 86400000;
const NOW = Date.now();

// ------------------------------------------------------------ jeu de données déterministe
let seed = 42;
const rnd = () => ((seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648);
const pick = a => a[Math.floor(rnd() * a.length)];
const SENDERS = [
  ['donotreply@jobalert.indeed.com', 'Offre vendeur', 'updates', 1], ['alert@indeed.com', 'Nouvelles offres', 'updates', 1],
  ['reply@email.arlettie.fr', 'Vente privée', 'promotions', 1], ['editorpicks@nytimes.com', 'Stories', 'promotions', 1],
  ['hello@official.asos.com', 'Nouveautés', 'promotions', 1], ['uber@uber.com', '50% offerts', 'promotions', 1],
  ['noreply@uber.com', 'Votre course', 'updates', 0], ['news@info.mexc.com', 'Promo card', 'promotions', 1],
  ['info@mail.mexc.com', '[MEXC] New Device/IP Login', 'updates', 0], ['noreply@wise.com', 'Argent reçu', 'updates', 0],
  ['NEPASREPONDRE@cic.fr', 'Virement instantané exécuté', 'updates', 0], ['assurance-maladie@info.ameli.fr', 'Remboursement', 'updates', 0],
  ['nepasrepondre@emailing.caf.fr', 'Votre dossier', 'updates', 0], ['noreply@email.francetravail.fr', 'Rendez-vous', 'updates', 0],
  ['residence@logement.example', 'Rappel interventions', 'primary', 0], ['parent@famille.example', 'Coucou', 'primary', 0],
  ['no-reply@accounts.google.com', 'Alerte de sécurité', 'updates', 0], ['notification@service.tiktok.com', 'Message', 'social', 0],
  ['friendsuggestion@facebookmail.com', 'Suggestion', 'social', 0], ['annonces@alertes.seloger.com', 'Nouvelle annonce', 'updates', 1],
  ['no.reply@leboncoin.fr', 'Nouvelle annonce de VENDEUR', 'updates', 0], ['no-reply@vinted.fr', 'Votre commande', 'updates', 0],
  ['service@paypal.fr', 'Reçu de paiement', 'updates', 0], ['boutique@exemple-inconnu.com', 'Soldes', 'promotions', 1],
  ['ami.inconnu@gmail.com', 'Salut', 'primary', 0], ['facturation@fournisseur.fr', 'Votre facture septembre', 'updates', 0],
  ['prof@univ.example', 'Cours', 'primary', 0], [OWN, 'Note perso', 'primary', 0],
];
const threads = [];
for (let i = 0; i < 2000; i++) {
  const [from, subject, category, lu] = pick(SENDERS);
  let ageDays = Math.floor(rnd() * 4000);
  if (ageDays > 27 && ageDays < 33) ageDays = 40;           // pas de cas limite autour de 30 j
  threads.push({ id: 't' + i, from: from.toLowerCase(), subject, category, listUnsub: !!lu,
                 date: new Date(NOW - ageDays * DAY - 3600000), inbox: rnd() < 0.97, unread: rnd() < 0.9,
                 labels: new Set(), trashed: false });
}
const snapshot = () => threads.map(t => [t.id, t.inbox, t.unread, [...t.labels].sort().join(',')].join('|')).join('\n');
const initial = snapshot();

// ------------------------------------------------------------ évaluateur de requêtes Gmail (sous-ensemble utilisé)
function parse(q) {
  let i = 0;
  const ws = () => { while (q[i] === ' ') i++; };
  function seq(end) {
    const terms = [];
    for (;;) { ws(); if (i >= q.length || q[i] === end) break; terms.push(term()); }
    if (end) i++;
    return terms;
  }
  function valueList() {                       // après "key:" : (a OR b) ou mot
    if (q[i] === '(') {
      let depth = 0, j = i;
      for (; j < q.length; j++) { if (q[j] === '(') depth++; if (q[j] === ')' && --depth === 0) break; }
      const inner = q.slice(i + 1, j); i = j + 1;
      return inner.split(/ OR /).map(s => s.trim().replace(/^"|"$/g, ''));
    }
    if (q[i] === '"') { const j = q.indexOf('"', i + 1); const v = q.slice(i + 1, j); i = j + 1; return [v]; }
    let j = i; while (j < q.length && !' ()}'.includes(q[j])) j++;
    const v = q.slice(i, j); i = j; return [v];
  }
  function term() {
    ws();
    let neg = false;
    if (q[i] === '-') { neg = true; i++; }
    let node;
    if (q[i] === '(') { i++; node = { and: seq(')') }; }
    else if (q[i] === '{') { i++; node = { or: seq('}') }; }
    else {
      let j = i; while (q[j] !== ':' ) j++;
      const key = q.slice(i, j); i = j + 1;
      node = { key, values: valueList() };
    }
    return neg ? { not: node } : node;
  }
  return { and: seq(null) };
}
const labelKey = n => n.toLowerCase().replace(/[\/ ]/g, '-');
function evalNode(n, t) {
  if (n.not) return !evalNode(n.not, t);
  if (n.and) return n.and.every(x => evalNode(x, t));
  if (n.or) return n.or.some(x => evalNode(x, t));
  const v = n.values;
  switch (n.key) {
    case 'in': return v[0] === 'inbox' ? t.inbox && !t.trashed : false;   // in:sent -> aucun dans le jeu simulé
    case 'larger': return false;
    case 'is': return v[0] === 'unread' ? t.unread : false;                // is:starred -> aucun
    case 'has': return v[0] === 'nouserlabels' ? t.labels.size === 0 : false; // has:attachment -> aucun
    case 'category': return t.category === v[0];
    case 'label': return [...t.labels].some(l => labelKey(l) === v[0]);
    case 'from': return v.some(x => (x === 'me' ? t.from === OWN : t.from.includes(x.toLowerCase())));
    case 'subject': return v.some(x => t.subject.toLowerCase().includes(x.toLowerCase()));
    case 'newer_than': return NOW - t.date.getTime() < parseInt(v[0], 10) * DAY;
    case 'older_than': return NOW - t.date.getTime() > parseInt(v[0], 10) * DAY;
    case 'after': return t.date >= new Date(v[0].replace(/\//g, '-') + 'T00:00:00');
    case 'before': return t.date < new Date(v[0].replace(/\//g, '-') + 'T00:00:00');
    default: throw new Error('opérateur non simulé : ' + n.key);
  }
}
let searchCalls = 0;
function search(q, start, max) {
  searchCalls++;
  const ast = parse(q);
  return threads.filter(t => !t.trashed && evalNode(ast, t)).sort((a, b) => b.date - a.date)
    .slice(start, start + max).map(wrap);
}

// ------------------------------------------------------------ mocks Apps Script
const labelObjs = {};
function labelObj(name) {
  return labelObjs[name] || (labelObjs[name] = {
    getName: () => name,
    addToThreads: ts => { assert(ts.length <= 100); ts.forEach(w => w._t.labels.add(name)); },
    removeFromThreads: ts => ts.forEach(w => w._t.labels.delete(name)),
    getThreads: (s, m) => threads.filter(t => t.labels.has(name)).slice(s, s + m).map(wrap),
    deleteLabel: () => { threads.forEach(t => t.labels.delete(name)); delete labelObjs[name]; },
  });
}
function wrap(t) {
  return { _t: t, getId: () => t.id, getFirstMessageSubject: () => t.subject, isUnread: () => t.unread,
    getLabels: () => [...t.labels].map(labelObj), moveToTrash: () => { t.trashed = true; },
    getMessages: () => [{ getFrom: () => 'X <' + t.from + '>',
      getHeader: h => (h === 'List-Unsubscribe' && t.listUnsub ? '<https://u.example/' + t.id + '>' : h === 'List-Unsubscribe-Post' && t.listUnsub ? 'List-Unsubscribe=One-Click' : '') }] };
}
const batch = fn => ts => { assert(ts.length <= 100, 'lot > 100'); ts.forEach(w => fn(w._t)); };
const GmailApp = {
  search, getUserLabelByName: n => labelObjs[n] || null, createLabel: n => labelObj(n),
  markThreadsRead: batch(t => { t.unread = false; }), markThreadsUnread: batch(t => { t.unread = true; }),
  moveThreadsToArchive: batch(t => { t.inbox = false; }), moveThreadsToInbox: batch(t => { t.inbox = true; }),
  getThreadById: id => wrap(threads.find(t => t.id === id)),
};
const sheets = {};
function sheetObj(name) {
  const rows = [];
  return (sheets[name] = { rows, appendRow: r => rows.push(r), getLastRow: () => rows.length,
    getRange: (r, c, nr, nc) => ({ setValues: vals => { vals.forEach((v, k) => { rows[r - 1 + k] = v; }); },
                                   setValue: v => { rows[r - 1][c - 1] = v; } }),
    getDataRange: () => ({ getValues: () => rows.map(r => r.slice()) }) });
}
const ss = { getId: () => 'SS', getSheetByName: n => sheets[n] || null, insertSheet: n => sheetObj(n) };
const store = {};
let triggers = [];
let clock = NOW;
class FakeDate extends Date { static now() { clock += 7000; return clock; } }   // 7 s par appel -> force des reprises
const ctx = {
  GmailApp, console, JSON, Math, Object, Array, String, Set,
  SpreadsheetApp: { create: () => ss, openById: () => ss },
  PropertiesService: { getScriptProperties: () => ({ getProperty: k => store[k] ?? null,
    setProperty: (k, v) => { store[k] = v; }, deleteProperty: k => { delete store[k]; } }) },
  LockService: { getScriptLock: () => ({ tryLock: () => true, releaseLock: () => {} }) },
  ScriptApp: { getProjectTriggers: () => triggers, deleteTrigger: t => { triggers = triggers.filter(x => x !== t); },
    WeekDay: { MONDAY: 'MONDAY' },
    newTrigger: fn => { const b = { timeBased: () => b, after: () => b, onWeekDay: () => b, atHour: () => b,
      create: () => { const t = { getHandlerFunction: () => fn }; triggers.push(t); return t; } }; return b; } },
  Utilities: { formatDate: () => '20260926_120000', sleep: () => {} },
  Logger: { log: () => {} }, UrlFetchApp: { fetch: () => ({ getResponseCode: () => 200 }) },
  Date: FakeDate,
};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(process.env.KM_WORKSPACE || WS, 'build', 'KM_Mail.gs'), 'utf8') + '\n;this.CONFIG = CONFIG; this.RULES = RULES;', ctx);
const run = (fn, ...a) => vm.runInContext(fn + '(' + a.map(x => JSON.stringify(x)).join(',') + ')', ctx);
function drain() {
  let s = JSON.parse(store.KM_STATE); let guard = 0;
  while (s.status === 'RUNNING') { assert(triggers.length, 'reprise non planifiée'); run('resume'); s = JSON.parse(store.KM_STATE); assert(++guard < 5000); }
  assert.strictEqual(s.status, 'DONE', s.error);
  return s;
}
const ok = m => console.log('  OK  ' + m);

// ------------------------------------------------------------ 1. DRY-RUN
console.log('DRY-RUN');
run('audit'); drain(); run('resetJob');
const inboxTotal = threads.filter(t => t.inbox).length;
const totalRow = sheets.audit.rows.find(r => r[2] === 'total_inbox');
assert.strictEqual(totalRow[4], inboxTotal); ok('audit : total INBOX = ' + inboxTotal);
run('planDryRun'); const planState = drain(); run('resetJob');
const check = sheets.plan_dry_run.rows.find(r => r[1] === 'CONTROLE');
assert.strictEqual(check[5], true, 'plan incohérent : ' + JSON.stringify(check)); ok('plan : somme des étapes = total INBOX (' + check[4] + ')');
run('listNewsletters');
const des = sheets.desabonnements.rows.slice(1);
assert(des.length > 0 && des[0][6] === 'OUI' && des[0][0].endsWith('indeed.com'), JSON.stringify(des[0]));
assert(des.filter(r => r[6] === 'OUI').every(r => /indeed\.com|hellowork\.com|jobrapidoalert\.com$/.test(r[0])));
ok('listNewsletters : alertes emploi pré-validées en tête, autres lignes VALIDER vide');
run('unsubscribeValidated');
assert(sheets.desabonnements.rows.slice(1).every(r => r[7] === ''), 'désabonnement exécuté en DRY_RUN');
ok('unsubscribeValidated : rien exécuté en DRY_RUN');
run('setupLabels'); run('apply'); drain(); run('resetJob');
assert.strictEqual(snapshot(), initial); ok('aucune modification de la boîte en DRY_RUN (audit, plan, setupLabels, apply)');

// ------------------------------------------------------------ 2. EXECUTION
console.log('EXECUTION');
ctx.CONFIG.DRY_RUN = false;
const before = threads.map(t => ({ ...t, labels: new Set(t.labels) }));
run('apply'); const st = drain(); run('resetJob');
assert(st.stepIndex > 0 && searchCalls > 0);
assert.strictEqual(threads.filter(t => t.inbox).length, 0); ok('INBOX à zéro');
assert.strictEqual(threads.filter(t => t.trashed).length, 0); ok('aucun fil supprimé / mis en corbeille (' + threads.length + ' fils)');
const TAX = l => /^(0[2-9]|10|99)_/.test(l) && !/^04_FINANCE\/FACTURES\/\d{4}$/.test(l);
const byId = Object.fromEntries(threads.map(t => [t.id, t]));
before.filter(t => t.inbox).forEach(t => {
  const now = byId[t.id];
  const tax = [...now.labels].filter(TAX);
  const hasAction = now.labels.has('01_ACTION');
  assert(tax.length === 1 || (tax.length === 0 && hasAction), t.id + ' labels ' + [...now.labels]);
  assert(now.labels.has('zz_KM_ROLLBACK/ARCHIVED'));
});
ok('chaque fil de l\'INBOX a exactement 1 label de taxonomie (ou 01_ACTION seul)');
const factures = threads.filter(t => t.labels.has('04_FINANCE/FACTURES'));
assert(factures.length > 0);
factures.forEach(t => assert(t.labels.has('04_FINANCE/FACTURES/' + t.date.getFullYear()), 'facture sans année : ' + t.id));
ok('factures rangées par année : ' + factures.length + ' fils -> 04_FINANCE/FACTURES/AAAA');
const sensitiveLabels = new Set(ctx.RULES.filter(r => r.sensitive).map(r => r.label));
before.filter(t => t.inbox && t.unread).forEach(t => {
  const now = byId[t.id];
  if ([...now.labels].some(l => sensitiveLabels.has(l))) assert(now.unread, 'sensible marqué lu : ' + t.id);
});
ok('aucun fil sensible marqué lu');
before.filter(t => !t.inbox).forEach(t => assert.strictEqual(byId[t.id].labels.size, 0));
ok('fils hors INBOX non touchés');
const moves = sheets.moves.rows.length - 1;
assert.strictEqual(new Set(sheets.moves.rows.slice(1).map(r => r[4] + r[2])).size, moves);
ok('journal moves : ' + moves + ' lignes, sans doublon');

// export pour contrôle croisé avec classify_mails.py
const csv = ['message_id,thread_id,date,year,from,from_domain,subject,gmail_labels,size_bytes,n_attachments,attachment_names,list_unsubscribe,list_unsubscribe_post'];
const result = ['thread_id,label'];
before.filter(t => t.inbox).forEach(t => {
  const d = t.date.toISOString();
  csv.push([t.id, t.id, d, d.slice(0, 4), t.from, t.from.split('@')[1], '"' + t.subject + '"', '', 1000, 0, '',
            t.category === 'promotions' && t.listUnsub ? '<https://u.example>' : '', ''].join(','));
  const tax = [...byId[t.id].labels].filter(TAX);
  result.push(t.id + ',' + (tax[0] || '01_ACTION'));
});
const tmp = path.join(process.env.KM_WORKSPACE || WS, 'logs');
fs.mkdirSync(tmp, { recursive: true });
fs.writeFileSync(path.join(tmp, 'test_inventory.csv'), csv.join('\n') + '\n');
fs.writeFileSync(path.join(tmp, 'test_appsscript_result.csv'), result.join('\n') + '\n');

// ------------------------------------------------------------ 3. ROLLBACK
console.log('ROLLBACK');
run('rollback'); drain(); run('resetJob');
run('rollbackLabels'); drain(); run('resetJob');
assert.strictEqual(snapshot(), initial); ok('état initial restauré à l\'identique (INBOX, lu/non lu, labels)');
console.log('\nTOUS LES TESTS PASSENT — ' + searchCalls + ' recherches simulées');
