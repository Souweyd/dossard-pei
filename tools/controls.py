#!/usr/bin/env python3
"""Checks run after the hourly sync (tools/sync_sources.py), all free on GitHub Actions.

- statut  : every race gets a verification state in verif.json, read by the site:
            "ok"     its registration state was read on its platform during this run (sync steps);
            "nv"     no automatic reading possible (platform blocks robots or builds pages in JS):
                     the site invites to confirm on the organiser's page;
            "alerte" the registration page shows a closure ("inscriptions closes", "complet"...)
                     while the site shows the race open: the site shows "À vérifier" and an alert
                     is raised (never "Ouvert" on something we could not confirm).
- qualite : consistency of data.json, compared with the previous published version.
- liens   : once a day, every link of every fiche (404 / site gone).
Returns plain lists of problems; tools/alerts.py turns them into GitHub issues (e-mailed).
"""
import datetime as dt
import html
import re
import urllib.error
import urllib.request

import net  # one honest User-Agent, polite delay, size and time limits on every request

COMMUNES = {"Bras-Panon", "Cilaos", "Entre-Deux", "L'Étang-Salé", "La Plaine-des-Palmistes", "La Possession",
            "Le Port", "Le Tampon", "Les Avirons", "Les Trois-Bassins", "Trois-Bassins", "Petite-Île", "Saint-André",
            "Saint-Benoît", "Saint-Denis", "Saint-Joseph", "Saint-Leu", "Saint-Louis", "Saint-Paul", "Saint-Philippe",
            "Saint-Pierre", "Sainte-Marie", "Sainte-Rose", "Sainte-Suzanne", "Salazie"}
BROWSER = {"User-Agent": net.UA,   # honest identification (never a browser's User-Agent)
           "Accept-Language": "fr-FR,fr;q=0.9"}
CLOSED = re.compile(r"(?i)inscriptions?\s+(?:sont\s+|est\s+)?(?:closes?|ferm[ée]es?|termin[ée]es?|cl[ôo]tur[ée]es?)"
                    r"|inscription\s+termin[ée]e|plus\s+de\s+places?\s+disponibles?|sold\s*out|guichets?\s+ferm[ée]s?")
FULL = re.compile(r"(?i)\b(?:complet|épuisé)\b")


def plain(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", s, flags=re.S)))


# platforms read by the sync adapters (tools/sync_sources.py, step 3c and Sportpro / chronometrage):
# when the adapter could not read the page, the race stays "non vérifiable"; the generic text scan
# below is not used on them (their menus list other events "Inscription terminée": false alerts)
ADAPTED = re.compile(r"(?i)//(?:www\.)?(?:utoi\.re|utoi-inscriptions\.com|sportpro\.re|chronometrage\.com|"
                     r"[^/]*topchrono[^/]*|webservices\.re|sportinnovation\.fr|klikego\.com|in\.njuko\.com|"
                     r"foulee-solidaire-polio\.netlify\.app)/")


def main_text(page):
    """page text without the site navigation (menus, header, footer, sidebars)"""
    page = re.sub(r"(?is)<(nav|header|footer|aside)\b.*?</\1>", " ", page)
    return plain(page)


def get(url, timeout=25):
    req = urllib.request.Request(url, headers=BROWSER)
    with net.urlopen(req, timeout=timeout) as r:
        return r.status, r.geturl(), r.read(600_000).decode("utf-8", "replace")


def shown_open(r, today):
    eps = r.get("epreuves") or []
    if r.get("complet") or r.get("clos") or (r.get("limite") and r["limite"] < today):
        return False
    if r.get("ouverture") and r["ouverture"][:10] > today:
        return False
    if r.get("avenir") and not r.get("ouverture"):   # registrations not open yet, date unknown
        return False
    return not eps or any(not e.get("complet") and not e.get("clos") and not (e.get("limite") and e["limite"] < today) for e in eps)


def statut(data, verif_src, today, fetch=get):
    """verification state of every visible upcoming race + alerts"""
    out, alerts = {}, []
    for r in data.get("races", []):
        if r.get("hidden") or (r.get("fin") or r.get("date") or "") < today:
            continue
        if r["id"] in verif_src:
            out[r["id"]] = "ok"
            continue
        url = r.get("inscription") or ""
        if not url.startswith("http") or ADAPTED.search(url):
            out[r["id"]] = "nv"
            continue
        try:
            code, final, page = fetch(url)
        except (urllib.error.URLError, OSError, ValueError):
            out[r["id"]] = "nv"
            continue
        t = main_text(page)
        if len(t) < 400:                     # page built in JavaScript: nothing readable
            out[r["id"]] = "nv"
            continue
        hit = CLOSED.search(t) or (FULL.search(t) and "inscri" in t.lower() and not re.search(r"(?i)s'inscrire|je m'inscris|inscrivez-vous", t))
        if hit and shown_open(r, today):
            out[r["id"]] = "alerte"
            ctx = t[max(0, hit.start() - 60):hit.end() + 60].strip()
            alerts.append(f"**{r['nom']}** ({r['date']}) : affichée ouverte, mais la page d'inscription indique « {ctx} » — {url}")
        else:
            out[r["id"]] = "nv"
    return out, alerts


def qualite(data, prev, today):
    pb = []
    races = [r for r in data.get("races", []) if not r.get("hidden")]
    seen = {}
    for r in races:
        n, rid = r.get("nom", "?"), r.get("id")
        if not r.get("date") or not re.fullmatch(r"\d{4}-\d\d-\d\d", r["date"]):
            pb.append(f"{n} : date manquante ou invalide")
            continue
        if r.get("fin") and r["fin"] < r["date"]:
            pb.append(f"{n} : fin ({r['fin']}) avant le début ({r['date']})")
        if r.get("commune") not in COMMUNES:
            pb.append(f"{n} : commune inconnue « {r.get('commune')} »")
        ll = r.get("ll")
        if not ll or not (-21.5 <= ll[0] <= -20.8 and 55.1 <= ll[1] <= 55.9):
            pb.append(f"{n} : point de départ absent ou hors de l'île")
        if (r.get("fin") or r["date"]) >= today and not (r.get("inscription") or "").startswith("https://") and not (r.get("inscription") or "").startswith("http://"):
            pb.append(f"{n} : pas de lien S'inscrire valide")
        if not r.get("epreuves"):
            pb.append(f"{n} : aucune épreuve")
        if r.get("complet") and any(not e.get("complet") for e in r.get("epreuves", []) if "complet" in e):
            pb.append(f"{n} : marquée complète alors qu'une épreuve est ouverte")
        key = (re.sub(r"[^a-z0-9]", "", n.lower()), r["date"][:7])
        if key in seen:
            pb.append(f"{n} : doublon possible avec la fiche {seen[key]}")
        seen[key] = rid
    if prev:
        cur = {r["id"]: r for r in data.get("races", [])}
        alias = data.get("alias") or {}
        for p in prev.get("races", []):
            if p.get("hidden"):
                continue
            c = cur.get(p["id"])
            if c is None:
                if (p.get("fin") or p.get("date") or "") >= today and p["id"] not in alias:
                    pb.append(f"{p.get('nom')} ({p.get('date')}) : fiche disparue sans être passée, annulée ni fusionnée")
                continue
            for f in ("fiche", "page"):
                if p.get(f) and not c.get(f):
                    pb.append(f"{c.get('nom')} : lien « {f} » supprimé (il était {p[f]})")
    return pb


def liens(data, today, fetch=get):
    pb, done = [], {}
    for r in data.get("races", []):
        if r.get("hidden") or (r.get("fin") or r.get("date") or "") < today:
            continue
        urls = {r.get("inscription"), r.get("fiche"), r.get("page")} | {e.get("url") for e in r.get("epreuves", [])}
        for u in sorted(x for x in urls if x and x.startswith("http")):
            if u not in done:
                try:
                    code, final, _ = fetch(u)
                    gone = re.sub(r"https?://(www\.)?", "", final).rstrip("/").count("/") == 0 and u.rstrip("/").count("/") > 2
                    done[u] = "redirigé vers l'accueil du site" if gone else None
                except urllib.error.HTTPError as e:
                    done[u] = f"erreur {e.code}" if e.code in (404, 410) else None   # 403 = robots refused, not a dead link
                except (urllib.error.URLError, OSError, ValueError) as e:
                    done[u] = "site injoignable" if "Name or service" in str(e) or "nodename" in str(e) else None
            if done[u]:
                pb.append(f"{r.get('nom')} : {done[u]} — {u}")
    return pb
