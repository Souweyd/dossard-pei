#!/usr/bin/env python3
"""Landing pages for Google (by discipline, by commune, by month) + a crawlable list of upcoming
races injected into index.html between <!--seo-list--> markers. Imported by gen_pages.main()."""
import os
import re
import unicodedata
from datetime import date
from html import escape as esc

import gen_pages as G

DISC_PAGES = {  # slug -> (disciplines, title, h1, intro)
    "trail-reunion": (["trail"], "Trails à La Réunion : calendrier {y}", "Trails à La Réunion",
                      "Tous les trails à venir sur l'île : du trail découverte de 10 km aux ultras dans les cirques, avec dates, distances, dénivelé et liens d'inscription."),
    "course-sur-route-reunion": (["route"], "Courses sur route à La Réunion : calendrier {y}", "Courses sur route à La Réunion",
                                 "Les 5 km, 10 km, semi-marathons et courses urbaines à venir à La Réunion, avec horaires, tarifs et liens d'inscription."),
    "multisport-reunion": (["multisport"], "Triathlons, swimruns et multisport à La Réunion : calendrier {y}", "Triathlon et multisport à La Réunion",
                           "Triathlons, duathlons, aquathlons, swimruns et raids multisport à venir à La Réunion."),
    "randonnee-marche-reunion": (["marche"], "Randonnées et marches à La Réunion : calendrier {y}", "Randos et marches à La Réunion",
                                 "Les randonnées et marches organisées à venir à La Réunion, souvent proposées en même temps que les courses."),
    "relais-reunion": (["relais"], "Courses en relais à La Réunion : calendrier {y}", "Courses en relais à La Réunion",
                       "Les courses à faire en équipe à La Réunion : relais, duos et formats par équipe."),
    "cross-et-jeunes-reunion": (["cross", "jeunes"], "Cross et courses jeunes à La Réunion : calendrier {y}", "Cross et courses jeunes à La Réunion",
                                "Les cross et les courses pour enfants et jeunes (marmailles) à venir à La Réunion."),
}
EXTRA_CSS = """
.land{max-width:1040px;margin:0 auto;padding:4px 16px 40px}
.land h1{font-size:clamp(1.7rem,4vw,2.4rem);letter-spacing:-.035em;line-height:1.1;margin:8px 0 10px}
.land .intro{color:var(--muted);max-width:68ch;margin:0 0 22px}
.land h2{font-size:1.15rem;letter-spacing:-.02em;margin:26px 0 8px;text-transform:capitalize}
.rlist{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.rlist a{display:grid;grid-template-columns:58px minmax(0,1fr) auto;gap:12px;align-items:center;padding:10px 12px;background:var(--surface);border-radius:14px;text-decoration:none;color:var(--fg);box-shadow:inset 0 0 0 1px var(--line)}
.rlist a:hover{box-shadow:inset 0 0 0 2px var(--accent)}
.rlist .d{text-align:center;line-height:1.05}.rlist .d small{display:block;color:var(--muted);font-size:.72rem;text-transform:uppercase}.rlist .d b{font-size:1.35rem}
.rlist .t b{display:block;font-weight:600}.rlist .t span{color:var(--muted);font-size:.86rem}
.rlist .k{font-size:.8rem;font-weight:600;color:var(--accent);white-space:nowrap}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:28px 0 0;padding:0;list-style:none}
.chips a{display:inline-block;padding:6px 12px;border-radius:99px;background:var(--surface);box-shadow:inset 0 0 0 1px var(--line);text-decoration:none;font-size:.88rem;color:var(--fg)}
.chips a:hover{box-shadow:inset 0 0 0 2px var(--accent)}
.land h3{font-size:.95rem;margin:30px 0 4px;color:var(--muted);font-weight:600}
"""
JOURS = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]
MOIS_C = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def discs(r):
    return {G.typ(e) for e in r.get("epreuves", [])} | {G.disc_of(r)}


def rows(rs):
    out = []
    for r in rs:
        d = G.d_of(r["date"])
        kms = sorted({e["km"] for e in r.get("epreuves", []) if e.get("km")}, reverse=True)
        k = " · ".join(f"{G.fmt_km(x)} km" for x in kms[:3])
        st = "Complet" if r.get("complet") else ""
        out.append(f'<li><a href="/course/{esc(r["id"])}/"><span class="d"><small>{JOURS[d.weekday()]}</small><b>{d.day}</b><small>{MOIS_C[d.month - 1]}</small></span>'
                   f'<span class="t"><b>{esc(r["nom"])}</b><span>{esc(r.get("commune", ""))} · {G.DISC[G.disc_of(r)]}{(" · " + st) if st else ""}</span></span><span class="k">{k}</span></a></li>')
    return "".join(out)


def by_month(rs):
    groups, cur = [], None
    for r in rs:
        m = r["date"][:7]
        if m != cur:
            groups.append((m, [])); cur = m
        groups[-1][1].append(r)
    return "".join(f'<h2>{G.MOIS[int(m[5:]) - 1]} {m[:4]}</h2><ul class="rlist">{rows(xs)}</ul>' for m, xs in groups)


def nav(coms, months):
    d = "".join(f'<li><a href="/{s}/">{esc(v[2])}</a></li>' for s, v in DISC_PAGES.items())
    c = "".join(f'<li><a href="/courses/{slug(x)}/">{esc(x)}</a></li>' for x in coms)
    m = "".join(f'<li><a href="/calendrier/{G.MOIS[int(x[5:]) - 1]}-{x[:4]}/">{G.MOIS[int(x[5:]) - 1].capitalize()} {x[:4]}</a></li>' for x in months)
    return f'<h3>Par discipline</h3><ul class="chips">{d}</ul><h3>Par commune</h3><ul class="chips">{c}</ul><h3>Par mois</h3><ul class="chips">{m}</ul>'


def shell(path, title, desc, h1, intro, body, logo, n):
    url = f"{G.SITE}/{path}"
    ld = '{"@context":"https://schema.org","@type":"CollectionPage","name":%s,"url":%s,"inLanguage":"fr"}' % (
        __import__("json").dumps(h1, ensure_ascii=False), __import__("json").dumps(url))
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<link rel="icon" href="/favicon.ico" sizes="48x48"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/apple-touch-icon.png"><link rel="manifest" href="/manifest.webmanifest">
<title>{esc(title)} | Dossard Péi</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website"><meta property="og:site_name" content="Dossard Péi"><meta property="og:locale" content="fr_FR">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{url}"><meta property="og:image" content="{G.SITE}/og/home.jpg?v=3">
<meta name="theme-color" content="#f5efe6" media="(prefers-color-scheme: light)"><meta name="theme-color" content="#14110e" media="(prefers-color-scheme: dark)">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;600;700&display=swap">
<script type="application/ld+json">{ld}</script>
<script data-goatcounter="https://dossardpei.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
<style>{G.CSS}{EXTRA_CSS}</style></head><body>
<header class="top"><a class="brand" href="/">{logo}<span>Dossard Péi</span></a><a class="all" href="/">Carte et calendrier →</a></header>
<main class="land"><h1>{esc(h1)}</h1><p class="intro">{esc(intro)} <b>{n} course{"s" if n > 1 else ""} à venir.</b></p>
{body}</main>
<footer>Dossard Péi · toutes les courses de La Réunion au même endroit · <a href="/">dossardpei.re</a> · <a href="/#contact">Nous contacter</a></footer>
</body></html>
"""


def build(races, logo):
    """Write the landing pages; return (list of paths, html list for the home page)."""
    today = date.today().isoformat()
    up = sorted([r for r in races if r["date"] >= today], key=lambda r: (r["date"], r["nom"]))
    y = date.today().year
    coms = sorted({r.get("commune") for r in up if r.get("commune")}, key=lambda c: slug(c))
    months = sorted({r["date"][:7] for r in up})
    nv = nav(coms, months)
    paths = []

    def write(path, html):
        os.makedirs(path, exist_ok=True)
        open(f"{path}/index.html", "w", encoding="utf-8").write(html)
        paths.append(path + "/")

    for s, (ds, title, h1, intro) in DISC_PAGES.items():
        rs = [r for r in up if discs(r) & set(ds)]
        if not rs:
            continue
        t = title.format(y=y if up[0]["date"][:4] == up[-1]["date"][:4] else f"{y}-{y + 1}")
        write(s, shell(s + "/", t, f"{h1} : {len(rs)} courses à venir, avec dates, distances, dénivelé et liens d'inscription.", h1, intro, by_month(rs) + nv, logo, len(rs)))
    for c in coms:
        rs = [r for r in up if r.get("commune") == c]
        h1 = f"Courses à pied à {c}"
        write(f"courses/{slug(c)}", shell(f"courses/{slug(c)}/", f"Courses à pied et trails à {c} (La Réunion)",
              f"Toutes les courses à venir à {c} : trails, courses sur route, randos. Dates, distances et liens d'inscription.", h1,
              f"Les courses à venir à {c}, à La Réunion : trails, courses sur route, randos et autres épreuves.", by_month(rs) + nv, logo, len(rs)))
    for m in months:
        rs = [r for r in up if r["date"].startswith(m)]
        mn = G.MOIS[int(m[5:]) - 1]
        h1 = f"Courses à La Réunion en {mn} {m[:4]}"
        write(f"calendrier/{mn}-{m[:4]}", shell(f"calendrier/{mn}-{m[:4]}/", h1, f"Le calendrier des courses à La Réunion en {mn} {m[:4]} : {len(rs)} courses, trails et courses sur route, avec liens d'inscription.",
              h1, f"Toutes les courses prévues à La Réunion en {mn} {m[:4]}, jour par jour.", f'<ul class="rlist">{rows(rs)}</ul>' + nv, logo, len(rs)))
    # crawlable list for the home page
    home = (f'<section class="seolist" aria-labelledby="seo-h"><h2 id="seo-h">Calendrier des courses à La Réunion</h2>'
            + "".join(f'<h3>{G.MOIS[int(m[5:]) - 1].capitalize()} {m[:4]}</h3><ul>' + "".join(
                f'<li><a href="/course/{esc(r["id"])}/">{esc(r["nom"])}</a> · {G.d_of(r["date"]).day} {G.MOIS[G.d_of(r["date"]).month - 1]} · {esc(r.get("commune", ""))}</li>'
                for r in up if r["date"].startswith(m)) + "</ul>" for m in months)
            + '<p class="seonav">' + " · ".join(f'<a href="/{s}/">{esc(v[2])}</a>' for s, v in DISC_PAGES.items()) + "</p>"
            + '<p class="seonav">' + " · ".join(f'<a href="/courses/{slug(c)}/">{esc(c)}</a>' for c in coms) + "</p></section>")
    return paths, home


def inject_home(home):
    p = "index.html"
    s = open(p, encoding="utf-8").read()
    block = f"<!--seo-list-->{home}<!--/seo-list-->"
    if "<!--seo-list-->" in s:
        s = re.sub(r"<!--seo-list-->.*?<!--/seo-list-->", lambda m: block, s, flags=re.S)
    else:
        s = s.replace('<footer class="sitefoot">', block + '<footer class="sitefoot">', 1)
    open(p, "w", encoding="utf-8").write(s)
