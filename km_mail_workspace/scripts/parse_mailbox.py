#!/usr/bin/env python3
"""Phase 1 — Audit. Lit un export .mbox (Google Takeout) et produit inventaire/mailbox_inventory.csv.
Lecture seule : ne modifie rien.

Usage : python3 parse_mailbox.py chemin/vers/Tous_les_messages.mbox [--out inventaire/mailbox_inventory.csv]
"""
import argparse
import mailbox
from pathlib import Path
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime

from km_common import WORKSPACE, domain_of, log_action, sender_address, write_csv

HEADER = ["message_id", "thread_id", "date", "year", "from", "from_domain", "subject",
          "gmail_labels", "size_bytes", "n_attachments", "attachment_names",
          "list_unsubscribe", "list_unsubscribe_post"]


def decode(value) -> str:
    if value is None:
        return ""
    try:
        return str(make_header(decode_header(str(value)))).replace("\n", " ").strip()
    except Exception:
        return str(value).replace("\n", " ").strip()


def attachments(msg):
    names = []
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        fname = part.get_filename()
        if fname or part.get("Content-Disposition", "").lower().startswith("attachment"):
            names.append(decode(fname) or "sans_nom")
    return names


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mbox")
    ap.add_argument("--out", default=str(WORKSPACE / "inventaire" / "mailbox_inventory.csv"))
    args = ap.parse_args()

    rows = []
    for msg in mailbox.mbox(args.mbox):
        try:
            date = parsedate_to_datetime(msg["Date"]) if msg["Date"] else None
        except (TypeError, ValueError):
            date = None
        sender = sender_address(decode(msg["From"]))
        atts = attachments(msg)
        rows.append([
            decode(msg["Message-ID"]), decode(msg["X-GM-THRID"]),
            date.isoformat() if date else "", date.year if date else "",
            sender, domain_of(sender), decode(msg["Subject"]), decode(msg["X-Gmail-Labels"]),
            len(msg.as_bytes()), len(atts), " | ".join(atts),
            decode(msg["List-Unsubscribe"]), decode(msg["List-Unsubscribe-Post"]),
        ])
    write_csv(Path(args.out), HEADER, rows)
    log_action("parse_mailbox", f"{len(rows)} messages inventoriés -> {args.out}", dry_run=True)
    print(f"{len(rows)} messages -> {args.out}")


if __name__ == "__main__":
    main()
