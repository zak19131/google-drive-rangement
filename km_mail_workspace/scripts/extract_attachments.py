#!/usr/bin/env python3
"""Extraction des pièces jointes d'un export .mbox.
Nommage : AAAA-MM-JJ_EXPEDITEUR_NATURE_SUJET.ext, rangé dans exports/pieces_jointes/<LABEL>/.
- --dry-run par défaut : liste seulement (logs/attachments_plan.csv).
- Jamais d'écrasement : suffixe _v2, _v3...
- Catégories sensibles (ADMIN, FINANCE, FAMILLE) exclues sauf --include-sensitive (validation explicite requise).

Usage : python3 extract_attachments.py export.mbox [--execute] [--include-sensitive] [--min-kb 0]
"""
import argparse
import mailbox
from email.utils import parsedate_to_datetime
from pathlib import Path

from km_common import WORKSPACE, classify, load_rules, log_action, sender_address, slug, write_csv
from parse_mailbox import decode

NATURE = {"FACTURES": "FACTURE", "BANQUE": "BANQUE", "CRYPTO": "CRYPTO", "SANTE": "SANTE",
          "CAF": "CAF", "IMPOTS": "IMPOTS", "LOGEMENT": "LOGEMENT", "ETUDES": "ETUDES"}


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    n = 2
    while (candidate := path.with_name(f"{path.stem}_v{n}{path.suffix}")).exists():
        n += 1
    return candidate


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mbox")
    ap.add_argument("--execute", action="store_true", help="écrit réellement les fichiers")
    ap.add_argument("--include-sensitive", action="store_true")
    ap.add_argument("--min-kb", type=int, default=0)
    args = ap.parse_args()

    cfg = load_rules()
    out_root = WORKSPACE / "exports" / "pieces_jointes"
    plan, written, skipped_sensitive = [], 0, 0
    for msg in mailbox.mbox(args.mbox):
        sender = sender_address(decode(msg["From"]))
        subject = decode(msg["Subject"])
        rule = classify(sender, subject, bool(msg["List-Unsubscribe"]), cfg)
        label = rule["label"] if rule else "NON_CLASSE"
        try:
            day = parsedate_to_datetime(msg["Date"]).strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            day = "0000-00-00"
        for part in msg.walk():
            fname = part.get_filename()
            if part.get_content_maintype() == "multipart" or not fname:
                continue
            payload = part.get_payload(decode=True) or b""
            if len(payload) < args.min_kb * 1024:
                continue
            if rule and rule.get("sensitive") and not args.include_sensitive:
                skipped_sensitive += 1
                continue
            ext = Path(decode(fname)).suffix.lower() or ".bin"
            nature = NATURE.get(label.split("/")[-1], label.split("/")[-1])
            name = f"{day}_{slug(sender.split('@')[-1].split('.')[-2] if '.' in sender else sender, 20).upper()}_{nature}_{slug(subject)}{ext}"
            target = unique_path(out_root / label.replace("/", "_") / name)
            plan.append([day, sender, label, decode(fname), str(target.relative_to(WORKSPACE)), len(payload)])
            if args.execute:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
                written += 1

    write_csv(WORKSPACE / "logs" / "attachments_plan.csv",
              ["date", "from", "label", "original_name", "target", "bytes"], plan)
    log_action("extract_attachments", f"{len(plan)} PJ planifiées, {written} écrites, {skipped_sensitive} sensibles ignorées",
               dry_run=not args.execute)
    print(f"{len(plan)} PJ planifiées, {written} écrites, {skipped_sensitive} sensibles ignorées")


if __name__ == "__main__":
    main()
