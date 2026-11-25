#!/usr/bin/env python3
"""Clubs péi: links between races and clubs, and one static page per club (clubs/<id>/index.html).

Run from the repository root (gen_pages.py calls it at each build, so the links follow data.json).
- clubs/liens.json: the races (data.json, visible ones) organised by each club, and the reverse
  (race id -> club ids), used by the clubs page and by /clubs/lien.js on the race fiches.
  A race belongs to a club when its organiser ("org") names the club (short name, full name or
  an alias of clubs.json), or when its name is one of the club's "courses".
- clubs/<id>/index.html: the clubs page itself (same app, the club's fiche opens from the address)
  with the club's own title, description, canonical link, structured data (SportsClub) and a
  static summary in <noscript>. Pages of clubs removed from clubs.json are deleted.
Returns the links so gen_pages.py can name the club on the static race pages."""
import html, json, os, re, shutil, unicodedata

SITE = "https://dossardpei.re"
MARK = "<!-- page club (tools/gen_clubs.py) -->"
esc = lambda s: html.escape(str(s or ""), quote=True)


def fold(s):
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def same_race(course, race_name):
    sw = lambda x: " ".join(w for w in x.split() if w not in ("de", "du", "des", "la", "le", "les", "l", "d", "et"))
    a, b = sw(fold(re.sub(r"\(.*?\)", "", course))), sw(fold(race_name))
    if len(a) < 6 or len(b) < 6:
        return False
    a, b = a.replace("trans ", "trans"), b.replace("trans ", "trans")
    return a == b or f" {a} " in f" {b} " or f" {b} " in f" {a} "


def links(clubs, races):
    by_race, by_club = {}, {}
    for r in sorted(races, key=lambda r: r["date"]):
        org = f" {fold(r.get('org'))} "
        for c in clubs:
            names = [c["nom"], c.get("complet")] + list(c.get("alias") or [])
            hit = any(len(fold(n)) >= 3 and f" {fold(n)} " in org for n in names if n)
            hit = hit or any(same_race(x, r["nom"]) for x in c.get("courses", []))
            if hit:
                by_race.setdefault(r["id"], []).append(c["id"])
                by_club.setdefault(c["id"], []).append(r)
    out_clubs = {}
    for cid, rs in by_club.items():
        c = next(x for x in clubs if x["id"] == cid)
        autres = [x for x in c.get("courses", []) if not any(same_race(x, r["nom"]) for r in rs)]
        out_clubs[cid] = {"r": [[r["id"], r["nom"], r["date"]] for r in rs], "autres": autres}
    return {"courses": by_race, "clubs": out_clubs, "noms": {c["id"]: c["nom"] for c in clubs if c["id"] in by_club}}


MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def date_fr(s):
    y, m, d = (int(x) for x in s.split("-"))
    return f"{d} {MOIS[m - 1]} {y}"


KIND = {"Athlétisme": "club d’athlétisme", "Athlé + trail": "club d’athlétisme et de trail", "Trail": "club de trail",
        "Trail + rando": "club de trail et de randonnée", "Multisport": "club multisport"}


def a_lieu(commune):
    b = re.sub(r"\s*\(.*$", "", commune)
    for art, rep in (("Le ", "au "), ("Les ", "aux ")):
        if b.startswith(art): return rep + b[len(art):]
    return "à " + b


def club_page(tpl, c, lk):
    url = f"{SITE}/clubs/{c['id']}/"
    full = c.get("complet") or ""
    kind = KIND.get(c["type"], "club")
    title = f"{c['nom']}{' (' + full + ')' if full and fold(full) != fold(c['nom']) else ''} : {kind} {a_lieu(c['commune'])} – Clubs péi"
    bits = [x for x in ("adresse" if c.get("adresse") or c.get("entrainement") else "", "contact" if c.get("tel") or c.get("mail") else "", "site" if c.get("site") else "") if x]
    desc = f"{c['nom']}, {kind} {a_lieu(c['commune'])} ({c['secteur']}, La Réunion)"
    desc += (" : " + ", ".join(bits) + (" et courses organisées." if lk else ".")) if bits else (" : courses organisées et infos du club." if lk else ".")
    same = [x for x in [c.get("site")] + [r["url"] for r in c.get("reseaux", [])] if x]
    ld = {"@context": "https://schema.org", "@type": "SportsClub", "name": c["nom"], "url": url,
          "sport": {"Athlétisme": "Athlétisme", "Trail": "Trail", "Athlé + trail": "Athlétisme et trail", "Trail + rando": "Trail et randonnée", "Multisport": "Multisport"}.get(c["type"], c["type"]),
          "address": {"@type": "PostalAddress", "addressLocality": re.sub(r"\s*\(.*$", "", c["commune"]), "addressRegion": "La Réunion", "addressCountry": "FR",
                      **({"streetAddress": c["adresse"]} if c.get("adresse") else {})}}
    if full: ld["alternateName"] = full
    if same: ld["sameAs"] = same
    if c.get("tel"): ld["telephone"] = c["tel"]
    if c.get("mail"): ld["email"] = c["mail"]
    if c.get("ffa"): ld["memberOf"] = {"@type": "SportsOrganization", "name": "Fédération française d'athlétisme"}
    ldj = json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")
    li = []
    if c.get("adresse"): li.append(f"<li>Adresse : {esc(c['adresse'])}</li>")
    if c.get("entrainement"): li.append(f"<li>Lieu d’entraînement : {esc(c['entrainement'])}</li>")
    if c.get("tel"): li.append(f"<li>Téléphone : {esc(c['tel'])}</li>")
    if c.get("mail"): li.append(f"<li>E-mail : <a href=\"mailto:{esc(c['mail'])}\">{esc(c['mail'])}</a></li>")
    if c.get("site"): li.append(f"<li>Site : <a href=\"{esc(c['site'])}\" rel=\"noopener\">{esc(c['site'])}</a></li>")
    for r in c.get("reseaux", []): li.append(f"<li><a href=\"{esc(r['url'])}\" rel=\"noopener\">{esc(r['url'])}</a></li>")
    rs = "".join(f"<li><a href=\"/course/{esc(r[0])}/\">{esc(r[1])}</a> ({esc(date_fr(r[2]))})</li>" for r in (lk or {}).get("r", []))
    rs += "".join(f"<li>{esc(x)}</li>" for x in ((lk or {}).get("autres") if lk else c.get("courses", [])))
    static = (f"<noscript><main class=\"static\"><h1>{esc(c['nom'])}</h1>" + (f"<p>{esc(full)}</p>" if full else "") +
              f"<p>{esc(c['type'])} · {esc(c['commune'])} · {esc(c['secteur'])}{' · Affilié FFA' if c.get('ffa') else ''}</p>" +
              (f"<ul>{''.join(li)}</ul>" if li else "") + (f"<h2>Courses organisées</h2><ul>{rs}</ul>" if rs else "") +
              "<p><a href=\"/clubs/\">Tous les clubs de La Réunion</a></p></main></noscript>")
    p = tpl
    p = re.sub(r"<title>.*?</title>", f"<title>{esc(title)}</title>", p, flags=re.S)
    p = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{esc(desc)}">', p)
    p = re.sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{url}">', p)
    p = re.sub(r'<meta property="og:url" content="[^"]*">', f'<meta property="og:url" content="{url}">', p)
    p = re.sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{esc(c["nom"])} – Clubs péi">', p)
    p = re.sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{esc(desc)}">', p)
    p = p.replace("</head>", f'<script type="application/ld+json">{ldj}</script>\n{MARK}\n</head>', 1)
    p = p.replace("<body>", "<body>\n" + static, 1)
    # one <h1> per page = the club's name: the big title « Clubs péi » becomes a <div> drawn exactly like it
    # (same rules as .hero2 .big h1 in site-hero.css and clubs.css, evening sky included)
    p = p.replace("<h1>Clubs péi</h1>", '<div class="bh">Clubs péi</div>', 1)
    p = p.replace("</head>", BH_CSS + "\n</head>", 1)
    return p


BH_CSS = ("<style>.hero2 .big .bh{font-family:var(--display);text-transform:none;font-weight:700;letter-spacing:-.045em;"
          "line-height:1.02;font-size:clamp(2rem,4.6vw,3.3rem);margin:0;text-wrap:balance;color:var(--fg)}"
          ":root[data-mood=soir] .hero2 .big .bh{color:#fff;text-shadow:0 1px 8px rgba(14,24,48,.55)}</style>")


def main(data=None):
    if not os.path.exists("clubs/clubs.json") or not os.path.exists("clubs/index.html"):
        return {"courses": {}, "clubs": {}}
    data = data or json.load(open("data.json", encoding="utf-8"))
    clubs = json.load(open("clubs/clubs.json", encoding="utf-8"))["clubs"]
    races = [r for r in data.get("races", []) if r.get("id") and r.get("date") and not r.get("hidden")]
    lk = links(clubs, races)
    s = json.dumps(lk, ensure_ascii=False, separators=(",", ":"))
    if not os.path.exists("clubs/liens.json") or open("clubs/liens.json", encoding="utf-8").read() != s:
        open("clubs/liens.json", "w", encoding="utf-8").write(s)
    tpl = open("clubs/index.html", encoding="utf-8").read()
    ids = set()
    for c in clubs:
        if not re.fullmatch(r"[a-z0-9-]+", c["id"]):
            continue
        ids.add(c["id"])
        out = club_page(tpl, c, lk["clubs"].get(c["id"]))
        p = f"clubs/{c['id']}/index.html"
        os.makedirs(f"clubs/{c['id']}", exist_ok=True)
        if not os.path.exists(p) or open(p, encoding="utf-8").read() != out:
            open(p, "w", encoding="utf-8").write(out)
    for d in os.listdir("clubs"):
        p = f"clubs/{d}/index.html"
        if d not in ids and os.path.isfile(p) and MARK in open(p, encoding="utf-8").read():
            shutil.rmtree(f"clubs/{d}")
    lk["ids"] = sorted(ids)
    return lk


if __name__ == "__main__":
    r = main()
    print(f"{len(r['ids'])} pages de club, {len(r['courses'])} courses reliées à un club")
