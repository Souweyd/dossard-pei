#!/usr/bin/env python3
# (régénéré automatiquement par .github/workflows/course-pages.yml)
"""Generate one static page per race (course/<id>/index.html), its share image (og/<id>.jpg),
sitemap.xml and robots.txt from data.json. Run from the repository root.

The pages are light, readable on their own and indexable; the full app (map, track, profile)
stays at / and opens the same race with /#c-<id>."""
import html, json, os, re, shutil, sys
from datetime import date

SITE = "https://dossardpei.re"
FIRST = {}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
DISC = {"trail": "Trail", "route": "Route", "marche": "Rando / marche", "cross": "Cross", "multisport": "Multisport",
        "relais": "Relais", "jeunes": "Jeunes", "autre": "Autre"}
MULTI = {"triathlon", "duathlon", "aquathlon", "swimrun", "raid-multisport", "biathlon"}
SPORT = {"trail": "Trail running", "route": "Course sur route", "marche": "Randonnée", "cross": "Cross-country",
         "multisport": "Multisport", "relais": "Relais", "jeunes": "Course jeunes", "autre": "Course à pied"}

esc = lambda s: html.escape(str(s if s is not None else ""), quote=True)


def d_of(s):
    y, m, d = map(int, s.split("-")); return date(y, m, d)


def date_long(s):
    d = d_of(s); return f"{JOURS[d.weekday()]} {d.day} {MOIS[d.month - 1]} {d.year}"


def fmt_km(k):
    return (f"{k:.1f}".rstrip("0").rstrip(".")).replace(".", ",")


def typ(e):
    return "multisport" if e.get("type") in MULTI else e.get("type", "autre")


def disc_of(r):
    ts = [typ(e) for e in r.get("epreuves", [])]
    return next((t for t in ["trail", "route", "cross", "multisport", "relais", "marche", "autre", "jeunes"] if t in ts), "autre")


def summary(r):
    eps = [e for e in r.get("epreuves", []) if e.get("km")]
    parts = []
    for e in sorted(eps, key=lambda e: -e["km"])[:4]:
        s = f"{fmt_km(e['km'])} km"
        if e.get("dp"): s += f" ({e['dp']} m D+)"
        parts.append(s)
    return ", ".join(parts)


def note_html(e):
    return f'<div class=note>{esc(e["note"])}</div>' if e.get("note") else ""


def price_num(p):
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*€", p or "")
    return float(m.group(1).replace(",", ".")) if m else (0.0 if p and "gratuit" in p.lower() else None)


# ---------------------------------------------------------------- share image (1200 x 630)
def og_image(r, out, fonts):
    try:
        from PIL import Image, ImageDraw, ImageFilter, ImageFont
    except ImportError:
        return False
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), "#f5efe6")
    src = r.get("poster_lg") or r.get("poster")
    if not (src and os.path.exists(src)): src = f"tools/art_{disc_of(r)}.png"
    x0 = 70
    if src and os.path.exists(src):
        p = Image.open(src).convert("RGB")
        bg = p.resize((W, int(W * p.height / p.width))).crop((0, 0, W, H)).filter(ImageFilter.GaussianBlur(28))
        img = Image.blend(img, bg, .28)
        ph = H - 90; pw = int(p.width * ph / p.height)
        if pw > 470: pw = 470; ph = int(p.height * pw / p.width)
        p = p.resize((pw, ph))
        shadow = Image.new("RGBA", (pw + 40, ph + 40), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle((20, 24, pw + 20, ph + 24), 22, fill=(0, 0, 0, 70))
        shadow = shadow.filter(ImageFilter.GaussianBlur(12))
        img.paste(shadow, (45 - 20, (H - ph) // 2 - 20), shadow)
        mask = Image.new("L", (pw, ph), 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, pw, ph), 20, fill=255)
        img.paste(p, (45, (H - ph) // 2), mask)
        x0 = 45 + pw + 50
    elif os.path.exists("tools/og_band.png"):
        band = Image.open("tools/og_band.png").convert("RGB").resize((W, 300))
        fade = Image.linear_gradient("L").resize((W, 300))  # black (top) to white (bottom)
        fade = fade.point(lambda v: min(255, int(v * 2.2)))
        img.paste(band, (0, H - 300), fade)
    d = ImageDraw.Draw(img)
    fb = lambda s: ImageFont.truetype(fonts["bold"], s)
    fm = lambda s: ImageFont.truetype(fonts["medium"], s)
    maxw = W - x0 - 50

    def wrap(text, font, maxw, maxl):
        words, lines, cur = text.split(), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if d.textlength(t, font=font) <= maxw: cur = t
            else:
                if cur: lines.append(cur)
                cur = w
        if cur: lines.append(cur)
        if len(lines) > maxl: lines = lines[:maxl]; lines[-1] = lines[-1].rstrip(".,") + "…"
        return lines

    dd = d_of(r["date"])
    y = 92
    d.text((x0, y), f"{JOURS[dd.weekday()].upper()} {dd.day} {MOIS[dd.month - 1].upper()} {dd.year}", font=fb(30), fill="#d2481e"); y += 62
    size = 64
    while size > 40:
        lines = wrap(r["nom"], fb(size), maxw, 3)
        if len(lines) <= 3 and all(d.textlength(l, font=fb(size)) <= maxw for l in lines): break
        size -= 4
    for l in lines:
        d.text((x0, y), l, font=fb(size), fill="#2a211c"); y += int(size * 1.12)
    y += 18
    d.text((x0, y), r.get("commune", ""), font=fm(34), fill="#5b4f45"); y += 52
    s = summary(r)
    if s:
        for l in wrap(s, fm(28), maxw, 2):
            d.text((x0, y), l, font=fm(28), fill="#776a5f"); y += 40
    d.text((x0, H - 78), "dossardpei.re", font=fb(30), fill="#0d6b67")
    img.save(out, "JPEG", quality=84, optimize=True, progressive=True)
    return True


# ---------------------------------------------------------------- related races
def related(r, races):
    today = date.today().isoformat()
    up = [x for x in races if x["id"] != r["id"] and x["date"] >= today]
    d = d_of(r["date"]); wd = d.weekday()
    sat = d.toordinal() - (wd - 5 if wd >= 5 else wd + 2)        # Saturday of that weekend (or the one before a weekday race)
    same_we = [x for x in up if sat <= d_of(x["date"]).toordinal() <= sat + 1] if wd >= 5 else [x for x in up if x["date"] == r["date"]]
    same_com = [x for x in up if x.get("commune") == r.get("commune") and x not in same_we]
    def block(title, xs):
        if not xs: return ""
        items = "".join(f'<li><a href="/course/{esc(x["id"])}/"><b>{esc(x["nom"])}</b><span>{d_of(x["date"]).day} {MOIS[d_of(x["date"]).month - 1]} · {esc(x.get("commune", ""))}{(" · " + summary(x)) if summary(x) else ""}</span></a></li>' for x in sorted(xs, key=lambda x: x["date"])[:6])
        return f'<section class="rel"><h2>{title}</h2><ul>{items}</ul></section>'
    out = block("Le même week-end" if wd >= 5 else "Le même jour", same_we) + block(f"Aussi à {esc(r.get('commune', ''))}", same_com)
    return f'<div class="rels">{out}</div>' if out else ""


# ---------------------------------------------------------------- page
CSS = """
:root{--bg:#f5efe6;--surface:#fffcf7;--fg:#2a211c;--muted:#776a5f;--line:#e6dccf;--accent:#0d6b67;--accent-soft:#dcece8;--hot:#e5502e;color-scheme:light dark}
@media (prefers-color-scheme:dark){:root{--bg:#14110e;--surface:#1f1a16;--fg:#f1eae2;--muted:#a89a8d;--line:#332b25;--accent:#5cc4bc;--accent-soft:#1d3532;--hot:#ff6a45}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 "Instrument Sans",system-ui,-apple-system,sans-serif}
a{color:var(--accent)}
.top{display:flex;align-items:center;justify-content:space-between;gap:12px;max-width:1040px;margin:0 auto;padding:14px 16px}
.brand{display:inline-flex;align-items:center;gap:10px;color:var(--fg);text-decoration:none;font-weight:700;font-size:1.15rem;letter-spacing:-.02em}
.brand svg{width:38px;height:38px}
.all{font-size:.92rem;font-weight:600;text-decoration:none}
main{max-width:1040px;margin:0 auto;padding:8px 16px 40px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:22px;padding:clamp(18px,3vw,32px);display:grid;gap:26px;grid-template-columns:minmax(0,300px) minmax(0,1fr)}
@media (max-width:720px){.card{grid-template-columns:minmax(0,1fr)}.card>div:first-child{width:min(68%,260px);margin:0 auto}td{white-space:nowrap}}
.poster{width:100%;height:auto;border-radius:14px;display:block;box-shadow:0 10px 30px rgba(0,0,0,.12)}
.ph{aspect-ratio:3/4;border-radius:14px;background:linear-gradient(transparent 45%,rgba(20,16,12,.62)),var(--art) center/cover,#9cc4d6;display:flex;align-items:flex-end;padding:18px;color:#fff;font-weight:700;font-size:1.4rem;line-height:1.1;box-shadow:0 10px 30px rgba(0,0,0,.12)}
.when{color:var(--hot);font-weight:700;text-transform:uppercase;letter-spacing:.04em;font-size:.9rem;margin:0}
h1{font-size:clamp(1.9rem,4.5vw,2.8rem);line-height:1.05;letter-spacing:-.03em;margin:6px 0 10px}
.where{color:var(--muted);margin:0 0 14px}
.tags{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 18px;padding:0;list-style:none}
.tags li{border:1px solid var(--line);border-radius:999px;padding:3px 12px;font-size:.88rem;font-weight:600}
.tags .st{background:var(--accent-soft);color:var(--accent);border-color:transparent}
.cta{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 22px}
.btn{display:inline-flex;align-items:center;gap:8px;border-radius:999px;padding:11px 20px;font-weight:700;text-decoration:none;border:1px solid var(--line);color:var(--fg);background:var(--surface)}
.btn.main{background:var(--hot);border-color:var(--hot);color:#fff}
.btn.map{color:var(--accent)}
.tbl{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:.95rem}
th,td{text-align:left;padding:9px 10px 9px 0;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:.78rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);font-weight:600}
td.n{white-space:nowrap}
.note{color:var(--muted);font-size:.86rem}
.src{margin-top:18px;color:var(--muted);font-size:.84rem}
.src a{color:inherit}
.rels{display:grid;gap:18px;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));margin-top:22px}
.rel h2{font-size:1.1rem;margin:0 0 10px;letter-spacing:-.02em}
.rel ul{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.rel a{display:grid;gap:2px;padding:12px 14px;border:1px solid var(--line);border-radius:14px;background:var(--surface);text-decoration:none;color:var(--fg)}
.rel a:hover{border-color:var(--accent)}
.rel span{color:var(--muted);font-size:.88rem}
footer{max-width:1040px;margin:0 auto;padding:0 16px 40px;color:var(--muted);font-size:.86rem}
"""


def page(r, logo, has_og, has_trk, races=(), data_date=None):
    rid = r["id"]; url = f"{SITE}/course/{rid}/"
    disc = disc_of(r); dl = date_long(r["date"])
    s = summary(r)
    title = f"{r['nom']} {d_of(r['date']).year} · {d_of(r['date']).day} {MOIS[d_of(r['date']).month - 1]} · {r.get('commune', '')} | Dossard Péi"
    desc = f"{r['nom']} : {DISC[disc].lower()} le {dl} à {r.get('commune', '')}, La Réunion."
    if s: desc += f" {s}."
    desc += " Horaires, tarifs, parcours et lien d'inscription."
    img = f"{SITE}/og/{rid}.jpg" if has_og else f"{SITE}/og/home.jpg"
    poster = r.get("poster_lg") or r.get("poster")
    lieu = r.get("lieu") if r.get("lieu") and r.get("lieu") != r.get("commune") else ""
    today = date.today().isoformat()
    past = r["date"] < today
    if r.get("complet"): st = "Complet"
    elif past: st = "Course passée"
    elif r.get("limite") and r["limite"] < today: st = "Inscriptions closes"
    elif r.get("limite"): st = f"Inscriptions jusqu'au {d_of(r['limite']).day} {MOIS[d_of(r['limite']).month - 1]}"
    else: st = ""

    # JSON-LD
    ev = {"@context": "https://schema.org", "@type": "SportsEvent", "name": r["nom"], "startDate": r["date"], "endDate": r.get("fin") or r["date"],
          "eventStatus": "https://schema.org/EventScheduled", "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
          "sport": SPORT[disc], "url": url, "description": desc,
          "location": {"@type": "Place", "name": lieu or r.get("commune", ""),
                       "address": {"@type": "PostalAddress", "addressLocality": r.get("commune", ""), "addressRegion": "La Réunion", "addressCountry": "RE"}}}
    if r.get("ll"): ev["location"]["geo"] = {"@type": "GeoCoordinates", "latitude": r["ll"][0], "longitude": r["ll"][1]}
    if poster or has_og: ev["image"] = [img] + ([f"{SITE}/{poster}"] if poster else [])
    org = {"@type": "Organization", "name": r.get("org") or r["nom"], **({"url": r["page"]} if r.get("page") else {})}
    ev["organizer"] = org
    ev["performer"] = {"@type": "PerformingGroup", "name": f"Participants · {r['nom']}"}
    prices = [price_num(e.get("prix")) for e in r.get("epreuves", [])]
    prices = [p for p in prices if p is not None]
    # an offer is only declared when its price is known (Google flags offers without price)
    if r.get("inscription") and prices:
        off = {"@type": "Offer", "url": r["inscription"], "priceCurrency": "EUR", "price": min(prices),
               "availability": "https://schema.org/SoldOut" if r.get("complet") else "https://schema.org/InStock",
               "validFrom": r.get("ouverture") or (data_date or today)}
        if r.get("limite"): off["validThrough"] = r["limite"]
        ev["offers"] = off
    ld = json.dumps(ev, ensure_ascii=False).replace("</", "<\\/")

    rows = "".join(
        f"<tr><td>{esc(e.get('nom'))}{note_html(e)}</td>"
        f"<td class=n>{fmt_km(e['km']) + ' km' if e.get('km') else '–'}</td><td class=n>{str(e['dp']) + ' m' if e.get('dp') else '–'}</td>"
        f"<td>{esc(e.get('cat') or DISC.get(typ(e), '–'))}</td><td class=n>{esc(e.get('h') or '–')}</td><td>{esc(e.get('prix') or '–')}</td></tr>"
        for e in r.get("epreuves", []))
    kms = sorted({e["km"] for e in r.get("epreuves", []) if e.get("km")}, reverse=True)
    tags = [f"<li>{DISC[disc]}</li>"] + [f"<li>{fmt_km(k)} km</li>" for k in kms[:5]] + ([f"<li class=st>{esc(st)}</li>"] if st else [])
    pw, ph = 600, 800
    if poster and os.path.exists(poster):
        try:
            from PIL import Image
            with Image.open(poster) as im: pw, ph = im.size
        except Exception: pass
    vis = f'<img class="poster" src="/{esc(poster)}" alt="Affiche : {esc(r["nom"])}" width="{pw}" height="{ph}">' if poster else f'<div class="ph" style="--art:url(/art/{disc}.svg)">{esc(r["nom"])}</div>'
    links = []
    fiche = r.get("fiche") or r.get("page")
    if fiche: links.append(f'<a href="{esc(fiche)}" rel="noopener">Fiche source</a>')
    if r.get("page") and r.get("page") != fiche: links.append(f'<a href="{esc(r["page"])}" rel="noopener">Site de la course</a>')
    if r.get("affiche"): links.append(f'<a href="{esc(r["affiche"])}" rel="noopener">Affiche</a>')

    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<link rel="icon" href="/favicon.ico" sizes="48x48"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/apple-touch-icon.png">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website"><meta property="og:site_name" content="Dossard Péi"><meta property="og:locale" content="fr_FR">
<meta property="og:title" content="{esc(r['nom'])} · {esc(dl)}"><meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}"><meta property="og:image" content="{img}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#f5efe6" media="(prefers-color-scheme: light)"><meta name="theme-color" content="#14110e" media="(prefers-color-scheme: dark)">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;600;700&display=swap">
<script type="application/ld+json">{ld}</script>
<script data-goatcounter="https://dossardpei.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
<style>{CSS}</style></head><body>
<header class="top"><a class="brand" href="/">{logo}<span>Dossard Péi</span></a><a class="all" href="/">Toutes les courses →</a></header>
<main><article class="card">
<div>{vis}</div>
<div>
<p class="when">{esc(dl)}</p>
<h1>{esc(r['nom'])}</h1>
<p class="where">{esc(r.get('commune', ''))}{' · ' + esc(lieu) if lieu else ''}{' · organisé par ' + esc(r['org']) if r.get('org') else ''}</p>
<ul class="tags">{''.join(tags)}</ul>
<div class="cta">{f'<a class="btn main" href="{esc(r["inscription"])}" rel="noopener" data-goatcounter-click="inscription/{esc(rid)}" data-goatcounter-title="Clic S’inscrire (page course)">S’inscrire</a>' if r.get('inscription') and not past else ''}<a class="btn map" href="/#c-{esc(rid)}">{'Carte et parcours' if has_trk else 'Voir sur la carte'} →</a></div>
{f'<div class="tbl"><table><thead><tr><th>Épreuve</th><th>Dist.</th><th>D+</th><th>Type</th><th>Départ</th><th>Tarif</th></tr></thead><tbody>{rows}</tbody></table></div>' if rows else ''}
<p class="src">Informations reprises des sources officielles, à vérifier auprès de l’organisateur avant de vous inscrire.{(' · ' + ' · '.join(links)) if links else ''} · <a href="/#contact-{esc(rid)}">Signaler une erreur</a></p>
</div></article>{related(r, races)}</main>
<footer>Dossard Péi · toutes les courses de La Réunion au même endroit · <a href="/">dossardpei.re</a> · <a href="/#contact">Nous contacter</a></footer>
</body></html>
"""


def main():
    data = json.load(open("data.json", encoding="utf-8"))
    global FIRST
    fs = "tools/first_seen.json"   # date a race first appeared on the site (stable "validFrom" for Google)
    FIRST = json.load(open(fs)) if os.path.exists(fs) else {}
    for r in data.get("races", []):
        if r.get("id") and r["id"] not in FIRST: FIRST[r["id"]] = date.today().isoformat()
    json.dump(FIRST, open(fs, "w"), indent=0, sort_keys=True)
    races = [r for r in data.get("races", []) if r.get("id") and r.get("date") and not r.get("hidden") and re.fullmatch(r"[a-z0-9-]+", r["id"])]
    idx = open("index.html", encoding="utf-8").read()
    m = re.search(r'<svg class="logo biglogo".*?</svg>', idx, re.S)
    logo = re.sub(r'class="logo biglogo"', 'aria-hidden="true"', m.group(0)) if m else ""
    logo = re.sub(r'\s(role|aria-label)="[^"]*"', "", logo)
    fonts = {"bold": "tools/fonts/Poppins-Bold.ttf", "medium": "tools/fonts/Poppins-Medium.ttf"}
    os.makedirs("og", exist_ok=True)
    keep = set()
    tracks = data.get("gpx", {})
    for r in races:
        rid = r["id"]; keep.add(rid)
        ogp = f"og/{rid}.jpg"
        has_og = os.path.exists(ogp)
        sig = json.dumps([r.get(k) for k in ("nom", "date", "commune", "epreuves", "poster", "poster_lg")] + ["art1"], ensure_ascii=False)
        sigp = f"og/.{rid}.sig"
        if not has_og or not os.path.exists(sigp) or open(sigp).read() != sig:
            has_og = og_image(r, ogp, fonts) or has_og
            if has_og: open(sigp, "w").write(sig)
        os.makedirs(f"course/{rid}", exist_ok=True)
        out = page(r, logo, has_og, rid in tracks, races, FIRST.get(rid))
        p = f"course/{rid}/index.html"
        if not os.path.exists(p) or open(p, encoding="utf-8").read() != out:
            open(p, "w", encoding="utf-8").write(out)
    # drop pages of races that left the data
    if os.path.isdir("course"):
        for d in os.listdir("course"):
            if d not in keep: shutil.rmtree(f"course/{d}", ignore_errors=True)
    for f in os.listdir("og"):
        base = f[1:-4] if f.startswith(".") else f[:-4]
        if f != "home.jpg" and base not in keep: os.remove(f"og/{f}")
    # sitemap + robots
    lastmod = (data.get("updatedAt") or date.today().isoformat())[:10]
    urls = [f"<url><loc>{SITE}/</loc><lastmod>{lastmod}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>"]
    for r in sorted(races, key=lambda r: r["date"]):
        urls.append(f"<url><loc>{SITE}/course/{r['id']}/</loc><lastmod>{lastmod}</lastmod><changefreq>weekly</changefreq></url>")
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n"
    if not os.path.exists("sitemap.xml") or open("sitemap.xml").read() != sm:
        open("sitemap.xml", "w").write(sm)
    open("robots.txt", "w").write(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
    print(f"{len(races)} pages de course")


if __name__ == "__main__":
    main()
