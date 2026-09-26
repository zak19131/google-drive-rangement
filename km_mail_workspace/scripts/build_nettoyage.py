#!/usr/bin/env python3
"""Génère build/Nettoyage.gs (mise à la corbeille du bruit) et build/filtres_nettoyage.xml (anti-repousse),
depuis rules.json (+ rules.local.json). Les règles sensibles sont toujours exclues."""
import json
from xml.sax.saxutils import quoteattr

from km_common import WORKSPACE, gmail_query, load_rules

NOISE_IDS = {"alertes_emploi", "alertes", "reseaux_sociaux", "social_catchall"}


def main():
    cfg = load_rules()
    rules = cfg["rules"]
    sensitive = sorted({d for r in rules if r.get("sensitive") for d in r.get("from_domains", [])})
    exclude = ("-from:(" + " OR ".join(sensitive) + ") -is:starred -from:me "
               "-subject:(facture OR invoice OR reçu OR receipt OR quittance OR relevé)")
    queries = []
    for r in rules:
        if r.get("sensitive"):
            continue
        noise = r["id"] in NOISE_IDS or r["label"] == "99_CORBEILLE"
        if not noise:
            continue
        q = gmail_query(r)
        if r["id"] == "promotions_catchall":
            q += " -has:attachment"          # prudence : une promo avec PJ peut être un justificatif
        queries.append({"nom": r["id"], "q": q})

    src = (WORKSPACE / "scripts" / "apps_script" / "Nettoyage.template.gs").read_text(encoding="utf-8")
    src = src.replace("/*QUERIES*/[]", json.dumps(queries, ensure_ascii=False, indent=2)).replace("/*EXCLUDE*/''", json.dumps(exclude, ensure_ascii=False))
    (WORKSPACE / "build" / "Nettoyage.gs").write_text(src, encoding="utf-8")

    light = "-is:starred -from:me -subject:(facture OR invoice OR reçu OR receipt OR quittance OR relevé)"
    filt = []
    for r in rules:
        if r.get("sensitive") or not (r["id"] in NOISE_IDS or r["label"] == "99_CORBEILLE"):
            continue
        if r.get("gmail_query"):       # fourre-tout (catégories) : exclusion complète des expéditeurs sensibles
            filt.append((r["id"], gmail_query(r) + (" -has:attachment" if r["id"] == "promotions_catchall" else "") + " " + exclude))
            continue
        doms = r.get("from_domains", []) + r.get("from_contains", [])
        chunk, n = [], 1
        for d in doms + [None]:
            if d is None or len("from:(" + " OR ".join(chunk + [d]) + ") " + light) > 1400:
                if chunk:
                    filt.append((f"{r['id']}_{n}", "from:(" + " OR ".join(chunk) + ") " + light)); n += 1
                chunk = [d] if d else []
            else:
                chunk.append(d)
    entries = []
    for nom, crit in filt:
        assert len(crit) <= 1500, (nom, len(crit))
        props = [("hasTheWord", crit), ("shouldTrash", "true"), ("sizeOperator", "s_sl"), ("sizeUnit", "s_smb")]
        body = "\n".join(f"    <apps:property name={quoteattr(k)} value={quoteattr(v)}/>" for k, v in props)
        entries.append(f"  <entry>\n    <category term='filter'></category>\n    <title>Nettoyage {nom}</title>\n    <content></content>\n{body}\n  </entry>")
    xml = ("<?xml version='1.0' encoding='UTF-8'?>\n<feed xmlns='http://www.w3.org/2005/Atom' xmlns:apps='http://schemas.google.com/apps/2006'>\n"
           "  <title>Filtres nettoyage</title>\n" + "\n".join(entries) + "\n</feed>\n")
    (WORKSPACE / "build" / "filtres_nettoyage.xml").write_text(xml, encoding="utf-8")
    print(f"{len(queries)} requêtes -> build/Nettoyage.gs, build/filtres_nettoyage.xml ; {len(sensitive)} domaines protégés")


if __name__ == "__main__":
    main()
