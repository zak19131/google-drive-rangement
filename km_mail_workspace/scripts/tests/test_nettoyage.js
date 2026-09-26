/* Test de build/Nettoyage.gs sur la boîte simulée de test_km_mail.js (même jeu de données, même évaluateur). */
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm'), assert = require('assert');
const WS = process.env.KM_WORKSPACE || path.resolve(__dirname, '..', '..');
const base = fs.readFileSync(path.join(__dirname, 'test_km_mail.js'), 'utf8');
const a = base.indexOf('// ------------------------------------------------------------ jeu de données');
const b = base.indexOf('// ------------------------------------------------------------ mocks Apps Script');
eval(base.slice(base.indexOf("const OWN"), base.indexOf("// ------------------------------------------------------------ jeu de données")) + base.slice(a, b)
  + `
let trig = [], store = {}, clock = NOW;
class FD extends Date { static now() { clock += 7000; return clock; } }
const wrapT = t => ({ getId: () => t.id });
const ctx = { console, JSON, Math, Object, Array, String, Number, Date: FD,
  GmailApp: { search: (q, s, m) => { const ast = parse(q); return threads.filter(t => !t.trashed && evalNode(ast, t)).slice(s, s + m).map(t => ({ getId: () => t.id, _t: t })); },
              moveThreadsToTrash: ts => { assert(ts.length <= 100); ts.forEach(w => { w._t.trashed = true; }); } },
  PropertiesService: { getScriptProperties: () => ({ getProperty: k => store[k] ?? null, setProperty: (k, v) => { store[k] = v; }, deleteProperty: k => { delete store[k]; } }) },
  ScriptApp: { getProjectTriggers: () => trig, deleteTrigger: t => { trig = trig.filter(x => x !== t); },
    newTrigger: fn => { const o = { timeBased: () => o, after: () => o, create: () => { const t = { getHandlerFunction: () => fn }; trig.push(t); return t; } }; return o; } },
  Utilities: { sleep: () => {} }, Logger: { log: () => {} } };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(WS, 'build', 'Nettoyage.gs'), 'utf8'), ctx);
const before = threads.map(t => ({ ...t }));
const vise = vm.runInContext('compter()', ctx);
assert(!threads.some(t => t.trashed)); console.log('  OK  compter : ' + vise + ' fils visés, rien supprimé');
let total = vm.runInContext('nettoyer()', ctx), runs = 1;
while (trig.length) { total = vm.runInContext('nettoyer()', ctx); runs++; assert(runs < 500); }
const trashed = threads.filter(t => t.trashed);
assert.strictEqual(trashed.length, vise); console.log('  OK  nettoyer : ' + trashed.length + ' fils à la corbeille en ' + runs + ' exécutions (reprise auto)');
trashed.forEach(t => assert(!/@(mail\\.mexc|cic|wise|info\\.ameli|emailing\\.caf|email\\.francetravail|accounts\\.google|paypal)/.test(t.from) && !/facture|Reçu/.test(t.subject) && t.from !== OWN,
  'protégé supprimé : ' + t.from + ' ' + t.subject));
console.log('  OK  aucun mail protégé touché (banque, CAF, santé, France Travail, sécurité, factures, reçus, envoyés)');
['jobalert.indeed.com', 'alert@indeed.com', 'arlettie', 'asos', 'uber@uber.com', 'tiktok', 'facebookmail', 'seloger', 'exemple-inconnu']
  .forEach(s => assert(threads.filter(t => t.from.includes(s)).every(t => t.trashed), 'bruit restant : ' + s));
console.log('  OK  bruit éliminé : Indeed, pubs, newsletters, réseaux sociaux, alertes annonces, promos inconnues');
assert(threads.filter(t => t.from.includes('mexc.com')).every(t => !t.trashed));
console.log('  OK  crypto (mexc.com) intégralement protégé, pubs comprises : choix de sécurité');
console.log('TEST NETTOYAGE OK');
`);
