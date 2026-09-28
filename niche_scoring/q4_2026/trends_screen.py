#!/usr/bin/env python3
"""Screen Google Trends (5 ans, hebdo) : saisonnalité (G3), tendance (G4) et poids du Q4 par niche.

Usage : python3 trends_screen.py [--geo FR] > trends_q4_2026.csv
Dépendance : pip install pytrends. Les indices Trends sont relatifs à chaque terme (0-100) :
ils mesurent la forme de la demande, pas son volume absolu.

Règles (calibrage COO, à valider) :
- saisonnalité "forte" si le mois le plus creux < 30 % du mois de pic (moyenne 24 derniers mois)
  -> traduit "next to no sales in the offseason" (DSL) ; "moderee" si < 60 %.
- tendance "chute" si moyenne 12 derniers mois < 70 % des 12 mois précédents ; "hausse" si > 115 %.
- q4_uplift = moyenne oct-déc / moyenne annuelle (3 dernières années complètes).
- série avec > 20 % de semaines à 0 -> "VOLUME TROP FAIBLE" (non éliminée, non mesurable).
"""
import csv
import sys
import time

from pytrends.request import TrendReq

# (mot-clé FR, niche, origine)
NICHES = [
    ("selle cheval", "Selles d'équitation", "DSL A+ 2026"),
    ("carport", "Carports", "DSL A+ 2026"),
    ("lit électrique", "Lits électriques / relevables", "DSL A+ 2026"),
    ("canapé", "Mobilier de salon", "DSL A+ 2026"),
    ("chariot de bar", "Dessertes de bar", "DSL A+ 2026"),
    ("appareil de musculation", "Home gym", "DSL A+ 2026"),
    ("machine cnc", "Machines CNC", "DSL A+ 2026"),
    ("hydroponie", "Systèmes hydroponiques", "DSL A+ 2026"),
    ("fauteuil cinéma", "Sièges home cinéma", "DSL A+ 2026"),
    ("four céramique", "Fours de potier", "DSL A+ 2026"),
    ("sauna", "Saunas", "DSL (2-7 k$)"),
    ("bain froid", "Bains froids / ice bath", "DSL 2024"),
    ("four à pizza", "Fours à pizza", "DSL 2023"),
    ("télescope", "Télescopes", "DSL 2023"),
    ("urne funéraire", "Urnes / mémorial", "MWQHJ boring niches"),
    ("fauteuil releveur", "Fauteuils releveurs (seniors)", "MWQHJ boring niches"),
]


def mensuel(series):
    m = series.resample("MS").mean()
    return m[m.index < m.index.max()]  # retire le mois en cours (partiel)


def analyse(df, kw):
    s = df[kw]
    m = mensuel(s)
    last24 = m.iloc[-24:]
    by_month = last24.groupby(last24.index.month).mean()
    creux_pic = by_month.min() / by_month.max() if by_month.max() else 0
    saison = "forte" if creux_pic < 0.30 else "moderee" if creux_pic < 0.60 else "aucune"
    a, b = m.iloc[-12:].mean(), m.iloc[-24:-12].mean()
    ratio = a / b if b else 0
    tendance = "chute" if ratio < 0.70 else "hausse" if ratio > 1.15 else "stable"
    full = m[(m.index.year >= m.index.max().year - 3) & (m.index.year < m.index.max().year)]
    q4 = full[full.index.month >= 10].mean() / full.mean() if full.mean() else 0
    pic = int(by_month.idxmax())
    return round(creux_pic, 2), saison, round(ratio, 2), tendance, round(q4, 2), pic


def main(argv):
    geo = argv[argv.index("--geo") + 1] if "--geo" in argv else "FR"
    p = TrendReq(hl="fr-FR", tz=-60, timeout=(10, 25))
    w = csv.writer(sys.stdout)
    w.writerow(["mot_cle", "niche", "origine", "creux_sur_pic", "saisonnalite", "ratio_12m",
                "tendance", "q4_uplift", "mois_pic", "g3_g4"])
    for kw, niche, src in NICHES:
        for essai in range(3):
            try:
                p.build_payload([kw], timeframe="today 5-y", geo=geo)
                df = p.interest_over_time()
                break
            except Exception as e:  # 429 Trends : on espace et on réessaie
                print(f"# {kw}: {type(e).__name__}, essai {essai + 1}", file=sys.stderr)
                time.sleep(20 * (essai + 1))
        else:
            w.writerow([kw, niche, src, "", "", "", "", "", "", "NON MESURÉ"])
            continue
        # > 20 % de semaines à 0 = série trop creuse : le creux/pic mesurerait le bruit, pas la saison
        if df.empty or (df[kw] == 0).mean() > 0.20:
            w.writerow([kw, niche, src, "", "", "", "", "", "", "VOLUME TROP FAIBLE"])
            continue
        cp, sai, ratio, tend, q4, pic = analyse(df, kw)
        g = "ÉLIMINÉ" if sai == "forte" or tend == "chute" else "OK"
        w.writerow([kw, niche, src, cp, sai, ratio, tend, q4, pic, g])
        sys.stdout.flush()
        time.sleep(4)


if __name__ == "__main__":
    main(sys.argv[1:])
