#!/usr/bin/env python3
"""Tests des scripts Python : mbox synthétique -> parse -> classify -> doublons -> PJ -> désabonnements,
+ cohérence avec le moteur Apps Script (fichiers produits par test_km_mail.js)."""
import csv
import mailbox
import subprocess
import sys
from email.message import EmailMessage
from pathlib import Path

import os
import shutil
import tempfile

REAL = Path(__file__).resolve().parents[2]
S = REAL / "scripts"
# Espace isolé : les tests n'écrivent jamais dans les vrais rapports/logs/exports
WS = Path(tempfile.mkdtemp(prefix="km_test_"))
for f in ("rules.json", "rules.local.json"):
    if (REAL / f).exists():
        shutil.copy(REAL / f, WS / f)
for d in ("logs", "rapports", "exports", "build", "inventaire", "gouvernance"):
    (WS / d).mkdir()
ENV = {**os.environ, "KM_WORKSPACE": str(WS)}
TMP = WS / "logs" / "test_tmp"
TMP.mkdir(parents=True, exist_ok=True)


def run(*args):
    r = subprocess.run([sys.executable, *map(str, args)], cwd=S, capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def make_mbox(path: Path):
    if path.exists():
        path.unlink()
    box = mailbox.mbox(str(path))
    specs = [
        ("Arlettie <reply@email.arlettie.fr>", "Vente privée", "Fri, 25 Sep 2026 10:00:00 +0000", "<a1@x>", True, None),
        ("Arlettie <reply@email.arlettie.fr>", "Vente privée", "Fri, 25 Sep 2026 10:00:00 +0000", "<a1@x>", True, None),
        ("CIC <nepasrepondre@cic.fr>", "Relevé", "Thu, 24 Sep 2026 09:00:00 +0000", "<c1@x>", False, ("releve.pdf", b"%PDF-1.4 cic")),
        ("Fournisseur <facturation@fournisseur.fr>", "Votre facture", "Tue, 01 Sep 2026 09:00:00 +0000", "<f1@x>", False, ("facture.pdf", b"%PDF-1.4 f")),
        ("Ami <ami@gmail.com>", "Photos vacances", "Mon, 03 Aug 2020 09:00:00 +0000", "<p1@x>", False, ("photo.jpg", b"\xff\xd8jpg")),
        ("Ami <ami@gmail.com>", "Photos vacances", "Mon, 03 Aug 2020 09:00:00 +0000", "<p1@x>", False, ("photo.jpg", b"\xff\xd8jpg")),
    ]
    for frm, subj, date, mid, unsub, att in specs:
        m = EmailMessage()
        m["From"], m["To"], m["Subject"], m["Date"], m["Message-ID"] = frm, "titulaire@example.com", subj, date, mid
        if unsub:
            m["List-Unsubscribe"] = "<https://unsub.example/1>, <mailto:u@example.com>"
            m["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
        m.set_content("corps")
        if att:
            m.add_attachment(att[1], maintype="application", subtype="octet-stream", filename=att[0])
        box.add(m)
    box.flush()


def main():
    run(S / "build_gmail_artifacts.py")
    r = subprocess.run(["node", str(S / "tests" / "test_km_mail.js")], capture_output=True, text=True, env=ENV)
    print(r.stdout)
    assert r.returncode == 0, r.stderr
    mbox = TMP / "test.mbox"
    make_mbox(mbox)
    inv = TMP / "inv.csv"
    print(run(S / "parse_mailbox.py", mbox, "--out", inv))
    rows = list(csv.DictReader(inv.open()))
    assert len(rows) == 6 and rows[2]["n_attachments"] == "1"
    print("  OK  parse_mailbox : 6 messages, PJ détectées")

    print(run(S / "classify_mails.py", "--inventory", inv, "--today", "2026-09-26"))
    moves = {r["message_id"]: r for r in csv.DictReader((WS / "logs" / "moves.csv").open())}
    assert moves["<c1@x>"]["label"] == "04_FINANCE/BANQUE" and moves["<c1@x>"]["add_01_ACTION"] == "True"
    assert moves["<f1@x>"]["label"] == "04_FINANCE/FACTURES"
    assert moves["<p1@x>"]["label"] == "10_ARCHIVES/2020"
    assert moves["<a1@x>"]["label"] == "99_CORBEILLE"
    print("  OK  classify_mails : banque->01_ACTION, facture, archive 2020, newsletter -> 99_CORBEILLE")

    print(run(S / "find_duplicates.py", "--inventory", inv))
    rep = (WS / "rapports" / "doublons.md").read_text()
    assert "Doublons stricts (Message-ID) : 2 groupes, 2 copies" in rep
    print("  OK  find_duplicates : 2 doublons stricts")

    out = run(S / "extract_attachments.py", mbox)
    assert "0 écrites" in out and "sensibles ignorées" in out
    out = run(S / "extract_attachments.py", mbox, "--execute")
    written = sorted(p.name for p in (WS / "exports" / "pieces_jointes").rglob("*") if p.is_file())
    assert any(n.startswith("2020-08-03_GMAIL_") and n.endswith(".jpg") for n in written), written
    assert any("_v2" in n for n in written), "pas d'écrasement attendu -> suffixe _v2"
    assert not any("CIC" in n or "FACTURE" in n for n in written), "sensibles exportés sans --include-sensitive"
    print("  OK  extract_attachments : dry-run par défaut, nommage AAAA-MM-JJ_EXPEDITEUR_NATURE_SUJET, _v2, sensibles exclus")

    print(run(S / "unsubscribe.py", "--inventory", inv))
    d = list(csv.DictReader((WS / "logs" / "desabonnements.csv").open()))
    assert d[0]["domaine"] == "email.arlettie.fr" and d[0]["https_one_click"] and d[0]["VALIDER"] == ""
    assert all("cic" not in r["domaine"] for r in d)
    print("  OK  unsubscribe : liste avec VALIDER vide, sensibles exclus, rien exécuté")

    # Cohérence Apps Script <-> Python (produit par test_km_mail.js)
    gs = {r["thread_id"]: r["label"] for r in csv.DictReader((WS / "logs" / "test_appsscript_result.csv").open())}
    run(S / "classify_mails.py", "--inventory", WS / "logs" / "test_inventory.csv")
    py = {r["thread_id"]: r["label"] for r in csv.DictReader((WS / "logs" / "moves.csv").open())}
    diff = {k: (gs[k], py[k]) for k in gs if gs[k] != py[k]}
    assert not diff, list(diff.items())[:10]
    print(f"  OK  cohérence Apps Script / Python : {len(gs)} fils, 0 écart")
    shutil.rmtree(WS)
    print("\nTOUS LES TESTS PASSENT (Apps Script + Python)")


if __name__ == "__main__":
    main()
