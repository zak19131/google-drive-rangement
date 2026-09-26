"""Fonctions partagées : chargement des règles, classification, journalisation."""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import re
from email.utils import parseaddr
from pathlib import Path

# KM_WORKSPACE permet aux tests de travailler dans un espace isolé
WORKSPACE = Path(os.environ.get("KM_WORKSPACE") or Path(__file__).resolve().parent.parent)
LOG_DIR = WORKSPACE / "logs"
ACTIONS_LOG = LOG_DIR / "actions.log"


def load_rules(workspace: Path = WORKSPACE) -> dict:
    """Règles génériques + règles locales (en tête). Retourne {labels, rules, own_addresses}."""
    base = json.loads((workspace / "rules.json").read_text(encoding="utf-8"))
    local_path = workspace / "rules.local.json"
    local = json.loads(local_path.read_text(encoding="utf-8")) if local_path.exists() else {}
    rules = local.get("rules", []) + base["rules"]
    labels = list(dict.fromkeys(base["labels"] + [r["label"] for r in rules]))
    return {
        "labels": labels,
        "rules": rules,
        "own_addresses": [a.lower() for a in local.get("own_addresses", [])],
        "unsubscribe_prevalidated": base.get("unsubscribe_prevalidated", {}).get("domains", []),
    }


def sender_address(raw_from: str) -> str:
    return parseaddr(raw_from or "")[1].lower() or (raw_from or "").strip().lower()


def domain_of(address: str) -> str:
    return address.rsplit("@", 1)[-1] if "@" in address else ""


def _domain_matches(domain: str, suffixes: list[str]) -> bool:
    return any(domain == s or domain.endswith("." + s) for s in suffixes)


def match_rule(rule: dict, sender: str, subject: str, has_list_unsubscribe: bool,
               own_addresses: list[str]) -> bool:
    if sender in own_addresses and rule["id"] == "famille":
        return False
    dom = domain_of(sender)
    subj = (subject or "").casefold()
    if rule.get("from_domains") and _domain_matches(dom, rule["from_domains"]):
        return True
    if rule.get("from_contains") and any(c.lower() in sender for c in rule["from_contains"]):
        return True
    if rule.get("subject_keywords") and any(k.casefold() in subj for k in rule["subject_keywords"]):
        return True
    if rule.get("python_list_unsubscribe") and has_list_unsubscribe:
        return True
    return False


def classify(sender_raw: str, subject: str, has_list_unsubscribe: bool, cfg: dict) -> dict | None:
    """Première règle qui matche, ou None (non classé)."""
    sender = sender_address(sender_raw)
    for rule in cfg["rules"]:
        if match_rule(rule, sender, subject, has_list_unsubscribe, cfg["own_addresses"]):
            return rule
    return None


def gmail_query(rule: dict) -> str:
    """Traduction d'une règle en requête Gmail (même sémantique OR que match_rule)."""
    if rule.get("gmail_query"):
        return rule["gmail_query"]
    parts = []
    if rule.get("from_domains"):
        parts.append("from:(" + " OR ".join(rule["from_domains"]) + ")")
    if rule.get("from_contains"):
        parts.append("from:(" + " OR ".join(rule["from_contains"]) + ")")
    if rule.get("subject_keywords"):
        kws = [f'"{k}"' if " " in k else k for k in rule["subject_keywords"]]
        parts.append("subject:(" + " OR ".join(kws) + ")")
    if not parts:
        raise ValueError(f"Règle vide : {rule['id']}")
    return parts[0] if len(parts) == 1 else "{" + " ".join(parts) + "}"


def log_action(script: str, message: str, dry_run: bool) -> None:
    """Append-only : logs/actions.log."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().isoformat(timespec="seconds")
    mode = "DRY-RUN" if dry_run else "EXECUTE"
    with ACTIONS_LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp}\t{script}\t{mode}\t{message}\n")


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def slug(text: str, max_len: int = 40) -> str:
    text = re.sub(r"[^\w-]+", "-", (text or "").strip(), flags=re.UNICODE)
    return re.sub(r"-{2,}", "-", text).strip("-")[:max_len] or "SANS-OBJET"
