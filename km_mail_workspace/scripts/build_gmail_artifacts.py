#!/usr/bin/env python3
"""Génère, depuis rules.json (+ rules.local.json) :
  - build/KM_Mail.gs        : Apps Script prêt à coller (RULES/LABELS injectés)
  - build/gmail_filters.xml : filtres Gmail à importer (Paramètres > Filtres > Importer)
Les deux sorties sont dans build/ (non versionné : peut contenir des règles personnelles).
"""
import json
from pathlib import Path
from xml.sax.saxutils import quoteattr

from km_common import WORKSPACE, gmail_query, load_rules, log_action

TEMPLATE = Path(__file__).resolve().parent / "apps_script" / "KM_Mail.template.gs"
BUILD = WORKSPACE / "build"
FILTER_CRITERIA_MAX = 1500  # prudence : au-delà, Gmail peut refuser le filtre


def script_rules(cfg):
    keys = ["archive", "mark_read", "sensitive", "newsletter", "action_if_recent", "catchall"]
    return [{"id": r["id"], "label": r["label"], "q": gmail_query(r), **{k: bool(r.get(k)) for k in keys}}
            for r in cfg["rules"]]


def build_script(cfg) -> str:
    src = TEMPLATE.read_text(encoding="utf-8")
    labels = json.dumps(cfg["labels"], ensure_ascii=False, indent=2)
    rules = json.dumps(script_rules(cfg), ensure_ascii=False, indent=2)
    unsub = json.dumps(cfg["unsubscribe_prevalidated"])
    src = (src.replace("/*LABELS*/[]/*END_LABELS*/", labels).replace("/*RULES*/[]/*END_RULES*/", rules)
              .replace("/*UNSUB*/[]/*END_UNSUB*/", unsub))
    assert "/*RULES*/" not in src and "/*LABELS*/" not in src and "/*UNSUB*/" not in src
    return src


def catchall_exclusion(cfg) -> str:
    """Les catch-all (category:promotions/social) excluent les domaines déjà couverts, sensibles en priorité."""
    sensitive = [d for r in cfg["rules"] if r.get("sensitive") for d in r.get("from_domains", [])]
    others = [d for r in cfg["rules"] if not r.get("sensitive") and not r.get("catchall")
              for d in r.get("from_domains", [])]
    chosen = []
    for d in list(dict.fromkeys(sensitive + others)):
        trial = chosen + [d]
        if len("-from:(" + " OR ".join(trial) + ")") > FILTER_CRITERIA_MAX - 40:
            break
        chosen = trial
    missing_sensitive = [d for d in sensitive if d not in chosen]
    if missing_sensitive:
        raise SystemExit(f"Exclusion trop longue : domaines sensibles non protégés {missing_sensitive}")
    return "-from:(" + " OR ".join(chosen) + ")"


def build_filters(cfg) -> tuple[str, list[str]]:
    entries, warnings = [], []
    excl = catchall_exclusion(cfg)
    for r in cfg["rules"]:
        q = gmail_query(r) + (" " + excl if r.get("catchall") else "")
        if len(q) > FILTER_CRITERIA_MAX:
            warnings.append(f"{r['id']}: critère de {len(q)} caractères")
        props = [("hasTheWord", q), ("label", r["label"])]
        if r.get("archive"):
            props.append(("shouldArchive", "true"))
        if r.get("mark_read"):
            props.append(("shouldMarkAsRead", "true"))
        if r.get("sensitive"):
            props.append(("shouldNeverSpam", "true"))
        props += [("sizeOperator", "s_sl"), ("sizeUnit", "s_smb")]
        body = "\n".join(f"    <apps:property name={quoteattr(k)} value={quoteattr(v)}/>" for k, v in props)
        entries.append(f"  <entry>\n    <category term='filter'></category>\n    <title>KM {r['id']}</title>\n"
                       f"    <content></content>\n{body}\n  </entry>")
    xml = ("<?xml version='1.0' encoding='UTF-8'?>\n"
           "<feed xmlns='http://www.w3.org/2005/Atom' xmlns:apps='http://schemas.google.com/apps/2006'>\n"
           "  <title>KM Mail Filters</title>\n" + "\n".join(entries) + "\n</feed>\n")
    return xml, warnings


def build_rules_doc() -> str:
    """Documentation publique : règles génériques seulement (jamais rules.local.json)."""
    base = json.loads((WORKSPACE / "rules.json").read_text(encoding="utf-8"))
    yes = lambda b: "oui" if b else "—"
    lines = ["# Règles de filtrage (générées depuis rules.json)", "",
             "Ordre = priorité : la première règle qui correspond gagne. Les règles personnelles (contacts, logement, école) "
             "sont dans `rules.local.json`, non versionné, et passent **avant** celles-ci.", "",
             "| # | Règle | Label | Critère Gmail | Archive | Lu | Sensible | Désabo. possible |",
             "|---:|---|---|---|---|---|---|---|"]
    for i, r in enumerate(base["rules"], 1):
        q = gmail_query(r).replace("|", "\\|")
        q = q if len(q) <= 160 else q[:157] + "..."
        lines.append(f"| {i} | {r['id']} | `{r['label']}` | `{q}` | {yes(r.get('archive'))} | {yes(r.get('mark_read'))} | "
                     f"{yes(r.get('sensitive'))} | {yes(r.get('newsletter') and not r.get('sensitive'))} |")
    lines += ["", "Étapes du moteur après les règles : factures -> `04_FINANCE/FACTURES/AAAA` ; sensibles récents non lus -> `01_ACTION` ; "
              "sensibles archivés (label conservé) ; non classés > 30 j -> `10_ARCHIVES/AAAA` ; non classés récents -> `01_ACTION`."]
    return "\n".join(lines) + "\n"


def main():
    cfg = load_rules()
    for lbl in cfg["labels"]:
        if len(lbl.split("/")) > 3:
            raise SystemExit(f"Profondeur > 3 : {lbl}")
    BUILD.mkdir(exist_ok=True)
    (BUILD / "KM_Mail.gs").write_text(build_script(cfg), encoding="utf-8")
    xml, warnings = build_filters(cfg)
    (BUILD / "gmail_filters.xml").write_text(xml, encoding="utf-8")
    (WORKSPACE / "gouvernance" / "regles_filtrage.md").write_text(build_rules_doc(), encoding="utf-8")
    for w in warnings:
        print("ATTENTION", w)
    log_action("build_gmail_artifacts", f"{len(cfg['rules'])} règles, {len(cfg['labels'])} labels", dry_run=True)
    print(f"{len(cfg['rules'])} règles -> build/KM_Mail.gs, build/gmail_filters.xml")


if __name__ == "__main__":
    main()
