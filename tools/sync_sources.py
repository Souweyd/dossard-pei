#!/usr/bin/env python3
"""Hourly, free, mechanical update of data.json (run by GitHub Actions).

- removes races whose date (or end date) is past, with their gpx entry;
- UTOI: updates date, start time, distance, D+, price, registration deadline and "complet"
  from the public API (https://api.utoi-inscriptions.com/api/races);
- Top Chrono: marks races "complet" when their page says so;
- Sportpro: hides races renamed "Course annulée : …" on the agenda, and copies each épreuve's own
  link, deadline, "Complet" and price from the agenda / épreuve pages (multi-épreuve S'inscrire then opens the event page).

Never touches a field the owner corrected in the admin (state/overrides.json, exported by the
Claude update) nor a manual race. New races, posters and tracks stay with the Claude update.
Prints a one-line summary; exits 0 even when a source is unreachable (it is simply skipped).
What each source read is recorded in state/health.json (tools/health.py); the workflow opens an
issue when a source fails 3 runs in a row (tools/health_alarm.py).
"""
import datetime as dt
import html
import json
import os
import re
import sys
import unicodedata
import urllib.request

sys.dont_write_bytecode = True  # no tools/__pycache__ in the repo
import health  # noqa: E402
import net  # noqa: E402  (one honest User-Agent, polite delay, size and time limits on every request)

UA = {"User-Agent": net.UA}
TZ = dt.timezone(dt.timedelta(hours=4))  # La Réunion
NOW = dt.datetime.now(TZ)
TODAY = NOW.date().isoformat()


def get_json(url):
    with net.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


data = json.load(open("data.json"))
try:
    ov = json.load(open("state/overrides.json"))
except (OSError, ValueError):
    ov = {}
locked = {k: set(v.get("fields", [])) if isinstance(v, dict) else set(v) for k, v in ov.get("overrides", ov).items()} if isinstance(ov, dict) else {}
changes, errors = [], []
run = {}  # source -> {"metrics": {name: count}, "error": ...}, for state/health.json
VERIF = {}  # race id -> platform that confirmed its registration state during this run
# race id -> {"source", "epreuves": [names]}: page read, but some of our épreuves not recognised among the
# platform's races. Such a race is NOT marked verified (its state may be wrong on the site) and is listed in
# state/partiels.json, reported by the daily summary until the names are matched (or fixed by hand).
PARTIAL = {}
FOUND = {}  # source -> [(key, label, url)] races listed by the platforms (new-race detector, tools/watch.py)
SP_DATES = {}  # Sportpro event id -> date of the event (agenda)
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def can(r, field):
    return not r.get("manual") and field not in locked.get(r["id"], set())


def setf(obj, r, field, val, label):
    if val in (None, "") or obj.get(field) == val or not can(r, field):
        return
    obj[field] = val
    changes.append(f"{r['id']}:{label}")


def sp_facts(page):
    """distance, climb and town of an épreuve page (« Distance : 12 km Dénivelé : 556 m … Ville : Salazie »)"""
    t = plain(page)
    km = re.search(r"Distance\s*:\s*(\d+(?:[.,]\d+)?)\s*km", t)
    dp = re.search(r"D[ée]nivel[ée]\s*:\s*(\d+)\s*m\b", t)
    ville = re.search(r"Ville\s*:\s*(.+?)\s+(?:Heure de d[ée]part|Lieu de d[ée]part|Ajouter)", t)
    lieu = re.search(r"Lieu de d[ée]part\s*:\s*(.+?)\s+(?:Lieu d.arriv[ée]e|Ajouter|S.inscrire)", t)
    return {"km": float(km.group(1).replace(",", ".")) if km else None, "dp": int(dp.group(1)) if dp else None,
            "ville": ville.group(1).strip() if ville else None, "lieu": lieu.group(1).strip()[:80] if lieu else None}


def geo_start(lieu, ville):
    """map position of a start: the start place written by the organiser (IGN geocoding: named places, then
    addresses), kept only when it lies in the right town of La Réunion with a good score; else the centre of
    the town. Returns (lat, lon, precise) or None."""
    import urllib.parse
    def ask(q, **kw):
        u = "https://data.geopf.fr/geocodage/search?" + urllib.parse.urlencode({"q": q, "limit": 5, **kw})
        for f in json.load(net.urlopen(urllib.request.Request(u, headers=UA), timeout=30)).get("features", []):
            lon, lat = f["geometry"]["coordinates"]
            city = f["properties"].get("city")
            city = city if isinstance(city, list) else [city]
            if -21.42 < lat < -20.85 and 55.2 < lon < 55.85 and any(norm(c or "") == norm(ville) for c in city) and f["properties"].get("score", 0) >= .6:
                return round(lat, 5), round(lon, 5)
        return None
    qs = []
    if lieu:
        l2 = re.sub(r"([a-zà-ÿ])([A-Z])", r"\1 \2", lieu)                      # « HellBourg » -> « Hell Bourg »
        qs = [l2] + [m for m in re.findall(r"(?:\bd[eu]s?\s+|\bd'|\bà\s+)([A-ZÉ][\w' -]+)$", l2)]   # « … de Hell Bourg » -> « Hell Bourg »
    try:
        for q in qs:
            for idx in ("poi", "address"):
                hit = ask(q, index=idx)
                if hit:
                    return hit + (True,)
        hit = ask(ville, index="address", type="municipality")
        return hit + (False,) if hit else None
    except Exception:
        return None


# differences found on the organisers' pages, state/ecarts.json (daily summary). One category per check
# ("lieu_sportpro", "lieu_utoi", "texte"…): a category is replaced only by a run where its check
# ran; "epingle" (pins put at the centre of a town) is kept 7 days.
ECARTS = {}
import controls as _cc  # noqa: E402
fmt_n = lambda v: (f"{v:g}").replace(".", ",")
ALIAS = [("hell bourg", "Salazie"), ("hellbourg", "Salazie"), ("grand ilet", "Salazie"), ("plaine des cafres", "Le Tampon"),
         ("bourg murat", "Le Tampon"), ("trois mares", "Le Tampon"), ("grand coude", "Saint-Joseph"), ("la saline", "Saint-Paul"),
         ("saint gilles", "Saint-Paul"), ("le gol", "Saint-Louis"), ("la riviere", "Saint-Louis"), ("makes", "Saint-Louis"),
         ("plaine des palmistes", "La Plaine-des-Palmistes"), ("etang sale", "L'Étang-Salé"), ("la nouvelle", "La Possession"),
         ("dos d ane", "La Possession"), ("le maido", "Saint-Paul"), ("tevelave", "Les Avirons"), ("bras panon", "Bras-Panon")]


def communes_in(text):
    """towns of La Réunion named in a text (« St-Pierre », « A LA POSSESSION », « Champ de foire de HellBourg »)"""
    t = " " + norm(re.sub(r"([a-z])([A-Z])", r"\1 \2", text or "")) + " "
    t = t.replace(" st ", " saint ").replace(" ste ", " sainte ")
    found = []
    for c in sorted(_cc.COMMUNES - {"Trois-Bassins"}):
        n = norm(c)
        pats = {n} | ({n.split(" ", 1)[1]} if n.split(" ")[0] in ("la", "le", "les", "l") and n not in ("le port",) else set())
        if any(f" {x} " in t for x in pats):
            found.append(c)
    found += [c for a, c in ALIAS if f" {a} " in t]
    return list(dict.fromkeys(found))


def move_town(r, top, lieu, cat):
    """the start moved to another town (organiser's data): town, start place and map pin follow"""
    if not top or norm(top) == norm(r.get("commune", "")) or not can(r, "commune"):
        return
    pos = geo_start(lieu, top)
    if not pos:   # no position found: nothing changed, reported
        ECARTS.setdefault(cat, {})[r["id"]] = {"site": r.get("commune"), "organisateur": top}
        return
    old = r.get("commune")
    r["commune"], r["lieu"], r["ll"] = top, lieu or top, [pos[0], pos[1]]
    changes.append(f"{r['id']}:lieu {old} -> {top}")
    if not pos[2]:
        ECARTS.setdefault("epingle", {})[r["id"]] = {"commune": top, "at": TODAY}


# 1. past races
keep = []
for r in data["races"]:
    end = r.get("fin") or r.get("date") or ""
    if end and end < TODAY:
        changes.append(f"{r['id']}:retirée")
        data.get("gpx", {}).pop(r["id"], None)
    else:
        keep.append(r)
data["races"] = keep

# 2. UTOI
try:
    items = []
    page = 1
    while True:
        d = get_json(f"https://api.utoi-inscriptions.com/api/races?page={page}")["data"]
        items += d["items"]
        if page * d.get("perPage", 30) >= d.get("total", 0) or not d["items"]:
            break
        page += 1
    run["utoi"] = {"metrics": {"courses": len(items)}}
    UPLACES = {}   # race id -> start places of its UTOI races (town of the start)
    FOUND["UTOI"] = [(it["slug"], f"{it.get('name', '')} ({(it.get('startAt') or '')[:10]})", f"https://utoi-inscriptions.com/courses/{it['slug']}") for it in items if it.get("slug")]
    for r in data["races"]:
        # link is either the event page (/evenements/<event>) or already the race page (/courses/<race>)
        m = re.search(r"utoi-inscriptions\.com/(evenements|courses)/([^/?#]+)", r.get("inscription", ""))
        if r.get("source") != "utoi" or not m or len(r.get("epreuves", [])) != 1:
            continue
        ep = r["epreuves"][0]
        relay = ep.get("type") == "relais" or bool(re.search(r"relai|duo|equipe", norm(r["nom"])))
        if m.group(1) == "courses":
            cands = [it for it in items if it.get("slug") == m.group(2)]
        else:
            cands = [it for it in items if it["event"]["slug"] == m.group(2)
                     and abs(float(it.get("distanceKm") or 0) - float(ep.get("km") or -1)) < 0.6
                     and (it.get("format") == "RELAY") == relay]
        if len(cands) > 1:  # e.g. relay of 5 vs relay of 10: use the leg count in the name
            n = re.search(r"\b(\d+)\b", norm(r["nom"]).replace(str(ep.get("km", "")), ""))
            cands = [c for c in cands if n and str(c.get("relayLegCount")) == n.group(1)] or cands
        if len(cands) != 1:
            continue
        it = cands[0]
        VERIF[r["id"]] = "utoi"
        if it.get("startPlace"):
            UPLACES.setdefault(r["id"], []).append(it["startPlace"])
        if it.get("slug"):  # S'inscrire opens this race, not the whole event
            setf(r, r, "inscription", f"https://utoi-inscriptions.com/courses/{it['slug']}", "lien course")
        if it.get("startAt"):
            st = dt.datetime.fromisoformat(it["startAt"].replace("Z", "+00:00")).astimezone(TZ)
            if st.date().isoformat() >= TODAY:   # a date already past from a source is never applied (it would delete the race)
                setf(r, r, "date", st.date().isoformat(), "date")
                setf(ep, r, "h", st.strftime("%Hh%M"), "heure")
            else:
                errors.append(f"utoi {r['id']} : date passée ignorée ({st.date().isoformat()})")
        km = float(it.get("distanceKm") or 0)
        setf(ep, r, "km", int(km) if km == int(km) else km, "km")
        setf(ep, r, "dp", it.get("elevationGainM"), "D+")
        if it.get("price") is not None:
            p = it["price"] / 100
            old = str(ep.get("prix") or "")
            mo = re.match(r"\s*(\d+(?:[.,]\d+)?)\s*€?(.*)", old)
            if not mo or float(mo.group(1).replace(",", ".")) != p:  # keep the wording, change only the amount
                suffix = mo.group(2) if mo and mo.group(2).strip() else (" / équipe" if it.get("format") == "RELAY" else "")
                setf(ep, r, "prix", f"{p:g} €{suffix}", "prix")
        cd = it.get("countdown") or {}
        if cd.get("kind") == "REGISTRATION_CLOSES" and cd.get("target"):
            lim = dt.datetime.fromisoformat(cd["target"].replace("Z", "+00:00")).astimezone(TZ).date().isoformat()
            setf(r, r, "limite", lim, "clôture")
        full = it.get("seatsLeft") == 0 or str(it.get("status", "")).upper() in ("FULL", "SOLD_OUT", "COMPLETE")
        if full and not r.get("complet") and can(r, "complet"):
            r["complet"] = True
            changes.append(f"{r['id']}:complet")
    # UTOI events with several races (one fiche per event, one épreuve per race): each épreuve links to its
    # race page /courses/<slug>; its own date, time, distance, D+, price, deadline and "complet" follow the API
    by_slug = {it.get("slug"): it for it in items if it.get("slug")}
    for r in data["races"]:
        if r.get("source") != "utoi" or len(r.get("epreuves", [])) < 2:
            continue
        hit = False
        for ep in r["epreuves"]:
            m = re.search(r"utoi-inscriptions\.com/courses/([^/?#]+)", ep.get("url") or "")
            it = by_slug.get(m.group(1)) if m else None
            if not it:
                continue
            hit = True
            if it.get("startPlace"):
                UPLACES.setdefault(r["id"], []).append(it["startPlace"])
            nm = "épreuve " + (ep.get("nom") or "")
            if it.get("startAt"):
                st = dt.datetime.fromisoformat(it["startAt"].replace("Z", "+00:00")).astimezone(TZ)
                if can(r, "epreuves") and st.date().isoformat() >= TODAY:   # never a past date from a source
                    for f, v in (("date", st.date().isoformat()), ("h", st.strftime("%Hh%M"))):
                        if ep.get(f) != v:
                            ep[f] = v; changes.append(f"{r['id']}:{nm} {f}")
            if not can(r, "epreuves"):
                continue
            km = float(it.get("distanceKm") or 0)
            for f, v in (("km", (int(km) if km == int(km) else km) if km else None), ("dp", it.get("elevationGainM"))):
                if v not in (None, "") and ep.get(f) != v:
                    ep[f] = v; changes.append(f"{r['id']}:{nm} {f}")
            if it.get("price") is not None:
                p = it["price"] / 100
                mo = re.match(r"\s*(\d+(?:[.,]\d+)?)\s*€?(.*)", str(ep.get("prix") or ""))
                if not mo or float(mo.group(1).replace(",", ".")) != p:
                    ep["prix"] = f"{p:g} €" + (mo.group(2) if mo and mo.group(2).strip() else (" / équipe" if it.get("format") == "RELAY" else ""))
                    changes.append(f"{r['id']}:{nm} prix")
            cd = it.get("countdown") or {}
            if cd.get("kind") == "REGISTRATION_CLOSES" and cd.get("target"):
                lim = dt.datetime.fromisoformat(cd["target"].replace("Z", "+00:00")).astimezone(TZ).date().isoformat()
                if ep.get("limite") != lim:
                    ep["limite"] = lim; changes.append(f"{r['id']}:{nm} clôture")
            full = it.get("seatsLeft") == 0 or str(it.get("status", "")).upper() in ("FULL", "SOLD_OUT", "COMPLETE")
            if bool(ep.get("complet")) != full:
                ep["complet"] = full; changes.append(f"{r['id']}:{nm} complet={full}")
        if not hit:
            continue
        VERIF[r["id"]] = "utoi"
        # the event itself: first and last race days, latest deadline, full only when every race is full
        days = sorted(e["date"] for e in r["epreuves"] if e.get("date"))
        if days and can(r, "date") and days[-1] >= TODAY:
            if r.get("date") != days[0]:
                r["date"] = days[0]; changes.append(f"{r['id']}:date")
            fin = days[-1] if days[-1] != days[0] else None
            if r.get("fin") != fin:
                if fin: r["fin"] = fin
                else: r.pop("fin", None)
                changes.append(f"{r['id']}:fin")
        lims = [e.get("limite") for e in r["epreuves"]]
        if all(lims) and can(r, "limite") and r.get("limite") != max(lims):
            r["limite"] = max(lims); changes.append(f"{r['id']}:clôture")
        full = all(e.get("complet") for e in r["epreuves"])
        if can(r, "complet") and bool(r.get("complet")) != full:
            r["complet"] = full; changes.append(f"{r['id']}:complet={full}")
    # town of the start (« PLACE FESTIVAL A LA POSSESSION »): the race follows when its UTOI races agree
    ECARTS.setdefault("lieu_utoi", {})
    for r in data["races"]:
        tw = [communes_in(pl) for pl in UPLACES.get(r["id"], [])]
        tw = [t[0] for t in tw if len(t) == 1]
        if tw and len(tw) * 2 > len(UPLACES[r["id"]]):
            top = max(set(tw), key=tw.count)
            if tw.count(top) * 2 > len(tw):
                move_town(r, top, next(pl for pl in UPLACES[r["id"]] if communes_in(pl) == [top]).title(), "lieu_utoi")
except Exception as e:  # source down: skip it this hour
    errors.append(f"utoi ({e.__class__.__name__})")
    run["utoi"] = {"metrics": {}, "error": f"{e.__class__.__name__}: {str(e)[:150]}"}

# 3. Top Chrono: list of event pages (health check); formats and their state: step 3c
try:
    pages, n = [], 1
    while n <= 4:
        batch = get_json(f"https://www.topchrono.run/wp-json/wp/v2/pages?inscription=133&per_page=100&page={n}&_fields=id,link")
        pages += batch
        if len(batch) < 100:
            break
        n += 1
    by_link = {p["link"].rstrip("/"): p["id"] for p in pages}
    FOUND["Top Chrono"] = [(p["link"].rstrip("/"), p["link"].rstrip("/").split("/")[-1].replace("-", " "), p["link"]) for p in pages]
    run["topchrono"] = {"metrics": {"pages": len(pages)}}
    # the state of each format is read from the event page itself (step 3c, ad_topchrono)
except Exception as e:
    errors.append(f"topchrono ({e.__class__.__name__})")
    run["topchrono"] = {"metrics": {}, "error": f"{e.__class__.__name__}: {str(e)[:150]}"}

# Sportpro agenda: one card per event, one "epreuveFiche" per épreuve (button "S'inscrire" or "Complet").
def sp_agenda(page):
    out = {}
    for card in re.split(r'<li class="course-card">', page)[1:]:
        m = re.search(r'class="courseLink" href="courses/(\d{5})-[^"]+"', card)
        if not m: continue
        dm = re.search(r'dateCourseCtnr">\s*\w+\s+(\d{1,2})\s+(\w+)\s+(\d{4})', html.unescape(card))
        if dm and dm.group(2).lower() in MOIS:
            SP_DATES[m.group(1)] = f"{dm.group(3)}-{MOIS.index(dm.group(2).lower()) + 1:02d}-{int(dm.group(1)):02d}"
        eps = []
        fiches = re.split(r'<div class="epreuveFiche">', card)[1:]
        if not fiches and "lbl-distance" in card:
            # single-épreuve event: no épreuve card, the event card itself carries the épreuve
            t = re.search(r'class="courseLink" href="(courses/\d{5}-[^"]+)">([^<]+)</a>', card)
            fiches = [f'<a href="{t.group(1)}">{t.group(2)}</a>' + card] if t else []
        for f in fiches:
            a = re.search(r'<a href="(courses/(?:epreuves/)?\d{5}-[^"]+)">([^<]+)</a>', f)
            if not a: continue
            km = re.search(r'lbl-distance">[^<]*</span>\s*<span class="valCourse">\s*([\d.,]+)\s*km', f)
            lim = re.search(r"jusqu'au\s*(\d\d)/(\d\d)/(\d{4})", f)
            ouv = re.search(r"ouverture le\s*(\d\d)/(\d\d)/(\d{4})(?:\s*(?:à partir de|à|dès)\s*(\d{1,2})\s*h\s*(\d\d)?)?", f)
            full = bool(re.search(r'<input type="button" value="Complet"', f))
            ins = "S'inscrire" in f or "S&#039;inscrire" in f
            eps.append({"url": "https://www.sportpro.re/" + a.group(1), "nom": html.unescape(a.group(2)).strip(),
                        "km": float(km.group(1).replace(",", ".")) if km else None,
                        "limite": f"{lim.group(3)}-{lim.group(2)}-{lim.group(1)}" if lim else None,
                        "complet": full, "ouvert": ins and not full,
                        "ouverture": f"{ouv.group(3)}-{ouv.group(2)}-{ouv.group(1)}T{int(ouv.group(4) or 0):02d}:{ouv.group(5) or '00'}" if ouv else None,
                        "h": (lambda hh: f"{int(hh.group(1)):02d}h{hh.group(2)}" if hh else None)(re.search(r'heureInline">\s*(\d{1,2})h(\d\d)', f))})
        out[m.group(1)] = eps
    return out

# Our épreuves are matched to the agenda ones by distance, then by the words of their names.
STOP = {"de", "du", "des", "la", "le", "les", "a", "au", "aux", "et", "l", "d", "en"}
def toks(s): return {t[:-1] if len(t) > 3 and t.endswith("s") else t for t in re.sub(r"(\d+) km\b", r"\1km", norm(s)).split() if t not in STOP}
def acro(s, ours=False):
    """initials of a race name: « MAFATE TRAIL TOUR » -> mtt; on our side a word already written in capitals
    (an acronym) is kept whole: « Ultra MTT » -> umtt. Lets « MTT » meet « MAFATE TRAIL TOUR »."""
    out = ""
    for w in re.findall(r"[A-Za-zÀ-ÿ]+", s or ""):
        n = norm(w)
        if not n or n in STOP:
            continue
        out += n if ours and len(w) >= 2 and w.isupper() else n[0]
    return out if len(out) >= 2 else None


def match(ours, theirs, event=""):
    """our épreuve -> agenda épreuve; None when unsure. Sportpro writes 0.1 km for an unknown distance."""
    common = set.intersection(*[toks(t["nom"]) for t in theirs]) if len(theirs) > 1 else set()
    common |= toks(event)
    res = {}
    for i, e in enumerate(ours):
        same = [t for t in theirs if norm(t["nom"]) == norm(e.get("nom"))] or [t for t in theirs if toks(t["nom"]) == toks(e.get("nom"))]
        if len(same) == 1:   # the very same name on both sides (the distances may disagree a little)
            res[i] = same[0]; continue
        k = float(e["km"]) if e.get("km") else None
        def near(t):
            if t["km"] is None or t["km"] <= 0.1 or k is None: return True
            return abs(t["km"] - k) <= max(0.15, 0.03 * k)
        c = [t for t in theirs if near(t)]
        w = toks(e.get("nom")) - common
        ac = acro(e.get("nom"), True)
        same_ac = lambda t: ac is not None and ac == acro(t["nom"])   # « MT » = « MAFATE TRAIL »
        def score(t):
            tw = toks(t["nom"]) - common
            sure = t["km"] is not None and t["km"] > 0.1 and k is not None
            return (2 * len(w & tw) - len(tw - w) + (3 if sure else 0) + (4 if same_ac(t) else 0))
        sc = sorted(((score(t), t) for t in c), key=lambda x: -x[0])
        if not sc or (len(sc) > 1 and sc[0][0] <= sc[1][0]): continue
        best = sc[0][1]; tw = toks(best["nom"]) - common
        sure = best["km"] is not None and best["km"] > 0.1 and k is not None
        if w & tw or sure or same_ac(best) or (not w and not tw):   # shared words, a matching distance, or both reduced to the event name
            res[i] = best
    used = [id(t) for t in res.values()]
    return {} if len(used) != len(set(used)) else res


# 3b. chronometrage.com (DAG system): each event page embeds its registration data (__NEXT_DATA__):
#     one "jetcode" per race with its price periods (end_date = sales close) and stock (remaining_places).
#     Gives each épreuve its own deadline and "complet"; the event gets the latest deadline.
def dag_races(page):
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', page, re.S)
    poi = json.loads(m.group(1))["props"]["pageProps"].get("initialPoi") or {} if m else {}
    out = []
    for j in poi.get("jetcodes") or []:
        prices = j.get("prices") or []
        ends = [p["end_date"] for p in prices if p.get("end_date")]
        lim = max(dt.datetime.fromisoformat(e.replace("Z", "+00:00")).astimezone(TZ).date().isoformat() for e in ends) if ends else None
        stocked = [p for p in prices if (p.get("id_stock") or -1) > 0 and p.get("total_places")]
        full = bool(stocked) and len(stocked) == len(prices) and all((p.get("remaining_places") or 0) <= 0 for p in stocked)
        st = dt.datetime.fromisoformat(j["event_start_date"].replace("Z", "+00:00")).astimezone(TZ) if j.get("event_start_date") else None
        # price shown today: the period on sale now (else the next one); "/ équipe" for team entries
        now_z = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M")
        live = [p for p in prices if isinstance(p.get("price"), (int, float)) and p["price"] > 0 and (p.get("end_date") or "9")[:16] >= now_z]
        cur = [p for p in live if (p.get("start_date") or "")[:16] <= now_z] or live
        prix = (f"{min(p['price'] for p in cur):g} €" + (" / équipe" if any(p.get("is_teams") for p in cur) else "")) if cur else None
        out.append({"nom": j.get("title") or "", "km": None, "limite": lim, "complet": full, "prix": prix,
                    "h": st.strftime("%Hh%M") if st else None, "date": st.date().isoformat() if st else None})
    return out


dag_targets = [r for r in data["races"] if not r.get("hidden") and re.search(r"chronometrage\.com/events/[A-Za-z0-9_-]+", (r.get("inscription") or "") + " " + (r.get("fiche") or ""))]
if dag_targets:
    lus, derr = 0, None
    for r in dag_targets:
        u = re.search(r"https?://(?:www\.)?chronometrage\.com/events/[A-Za-z0-9_-]+", (r.get("inscription") or "") + " " + (r.get("fiche") or "")).group(0)
        try:
            req = urllib.request.Request(u, headers=UA)
            theirs = dag_races(net.urlopen(req, timeout=30).read().decode("utf-8", "replace"))
        except Exception as e:
            derr = f"{e.__class__.__name__}: {str(e)[:150]}"
            errors.append(f"chronometrage {r['id']} ({e.__class__.__name__})")
            continue
        if not theirs:
            continue
        lus += 1
        # (the « city » of a chronometrage event is often the organiser's office, not the start: not used)
        if not can(r, "epreuves"):
            VERIF[r["id"]] = "chronometrage"
            continue
        eps = r.get("epreuves", [])
        res = {0: theirs[0]} if len(eps) == 1 and len(theirs) == 1 else match(eps, theirs, r.get("nom", ""))
        lo, lt = [k for k in range(len(eps)) if k not in res], [t for t in theirs if all(t is not v for v in res.values())]
        if len(lo) == 1 and len(lt) == 1:   # the last unmatched pair
            res[lo[0]] = lt[0]
        if len(res) < len(eps) and len(theirs) >= len(eps) and len({t["complet"] for t in theirs}) == 1 and theirs[0]["complet"]:
            res.update({k: {**theirs[0], "nom": "", "limite": max(t["limite"] or "" for t in theirs) or None, "prix": None, "h": None}
                        for k in range(len(eps)) if k not in res})   # every race of the page is full: so is each of ours
        if len(res) == len(eps):
            VERIF[r["id"]] = "chronometrage"
        else:
            PARTIAL[r["id"]] = {"source": "chronometrage", "epreuves": [eps[k].get("nom", "") for k in range(len(eps)) if k not in res],
                                "plateforme": [t["nom"] for t in theirs]}
        real_times = len({t.get("h") for t in theirs if t.get("h")}) >= 2
        for i, t in res.items():
            ep = eps[i]
            if real_times and t.get("h") and ep.get("h") != t["h"]:   # start time set by the organiser on the platform
                ep["h"] = t["h"]; changes.append(f"{r['id']}:{ep.get('nom', i)}:heure")
            if t["limite"] and ep.get("limite") != t["limite"]:
                ep["limite"] = t["limite"]
                changes.append(f"{r['id']}:{ep.get('nom', i)}:limite")
            setf(ep, r, "prix", t.get("prix"), f"{ep.get('nom', i)}:prix")
            # sold-out stock marks "complet"; never cleared here (organisers often close a nearly full race by hand)
            if t["complet"] and not ep.get("complet"):
                ep["complet"] = True
                changes.append(f"{r['id']}:{ep.get('nom', i)}:complet")
        dd = {t.get("date") for t in theirs if t.get("date")}
        if real_times and len(dd) == 1 and not r.get("fin") and not any(e.get("date") for e in eps) and can(r, "date"):
            nd = dd.pop()
            if nd != r.get("date") and nd >= TODAY:
                r["date"] = nd; changes.append(f"{r['id']}:date")
        if res and len(res) == len(eps):
            lims = [t["limite"] for t in res.values()]
            if all(lims) and can(r, "limite") and r.get("limite") != max(lims):
                r["limite"] = max(lims)
                changes.append(f"{r['id']}:clôture")
            if all(eps[i].get("complet") for i in res) and can(r, "complet") and not r.get("complet"):
                r["complet"] = True
                changes.append(f"{r['id']}:complet")
    run["chronometrage"] = {"metrics": {"pages": lus}, **({"error": derr} if not lus and derr else {})}


# 3c. Other registration platforms: each adapter reads a page and returns, per race of the page,
#     {"nom", "etat": "ouvert" | "clos" | "complet", "url"?}. The state shown on the site follows
#     the platform both ways (a reopened race loses "clos"/"complet"). Read pages are recorded in
#     VERIF (race id -> source), used by the "statut vérifié" check below.


def fetch(u):
    req = urllib.request.Request(u, headers={**UA, "Accept-Language": "fr-FR,fr;q=0.9"})
    return net.urlopen(req, timeout=30).read().decode("utf-8", "replace")


def plain(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", s, flags=re.S)))


CLOSED = re.compile(r"(?i)inscriptions?\s+(?:sont\s+)?(?:closes?|ferm[ée]es?|termin[ée]es?|cl[ôo]tur[ée]es?)|inscription\s+termin[ée]e")


def ad_topchrono(page):
    out = []
    for row in re.split(r'<div class="tc-event-cta-row">', page)[1:]:
        lab = re.search(r'tc-event-cta-label">([^<]+)<', row)
        btn = re.search(r'<a href="([^"]+)"[^>]*class="tc-event-btn tc-event-btn-primary">\s*([^<]+?)\s*</a>', row)
        if not lab or not btn: continue
        t = btn.group(2).lower()
        etat = "complet" if "complet" in t else "clos" if re.search(r"clos|ferm|termin", t) else "ouvert" if "inscri" in t else None
        if etat: out.append({"nom": html.unescape(lab.group(1)).strip(), "km": None, "etat": etat, "url": btn.group(1)})
    return out


def ad_utoire(page):
    m = re.search(r"[ÉE]tat de l.inscription\s*:\s*Inscription\s+(\w+)", plain(page))
    if not m: return []
    w = m.group(1).lower()
    etat = "ouvert" if w.startswith("ouvert") else "complet" if w.startswith("complet") else "clos"
    return [{"nom": "", "km": None, "etat": etat}]


def ad_sportinnovation(page):
    out = []
    for blk in re.split(r'<div class="raceItem', page)[1:]:
        t = re.search(r"<h1>([^<]+)</h1>", blk)
        if not t: continue
        etat = "complet" if "raceItemSoldOut" in blk[:400] else "ouvert" if "btn-inscription" in blk[:200] else None
        if etat: out.append({"nom": html.unescape(t.group(1)).strip(), "km": None, "etat": etat})
    return out


def ad_klikego(page):
    t = plain(page)
    if CLOSED.search(t): return [{"nom": "", "km": None, "etat": "clos"}]
    if re.search(r"(?i)\bcomplet\b", t) and "S'inscrire" not in t: return [{"nom": "", "km": None, "etat": "complet"}]
    if "S'inscrire" in t or "S&#039;inscrire" in page: return [{"nom": "", "km": None, "etat": "ouvert"}]
    return []


def ad_njuko(u):
    """njuko registration pages are built in JavaScript; the page itself reads the public JSON of the
    edition (front-api.njuko.com, no login), which gives per competition the registration window,
    the price tiers and whether they are sold out. Takes the URL, not the page."""
    slug = re.sub(r"[?#].*", "", u).rstrip("/").rsplit("/", 1)[-1]
    req = urllib.request.Request(f"https://front-api.njuko.com/edition/url/{slug}", headers={**UA, "Accept": "application/json"})
    d = json.load(net.urlopen(req, timeout=30))
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M")
    out = []
    for c in d.get("competitions") or []:
        if c.get("hideOnFront"):
            continue
        nm = c.get("name")
        nom = next((x.get("translation") for x in nm if x.get("language") == "fr"), None) if isinstance(nm, list) else nm
        nom = nom or c.get("reportName") or ""
        deb, fin = (c.get("startDateRegistrations") or "")[:16], (c.get("endDateRegistrations") or "")[:16]
        prices = [x for x in c.get("prices") or [] if x.get("enabled") and (not x.get("end") or x["end"][:16] > now)]
        sold = bool(prices) and all(x.get("soldOutAt") or (x.get("participantLimit") and (x.get("reservedCount") or 0) >= x["participantLimit"]) for x in prices)
        if d.get("status") != "OPEN" or (fin and fin < now):
            etat = "clos"
        elif deb and deb > now:
            continue                       # not open yet: not decided here (stays "non vérifiable")
        elif sold:
            etat = "complet"
        elif prices:
            etat = "ouvert"
        else:
            continue
        live = [x.get("value") for x in prices if isinstance(x.get("value"), (int, float)) and x["value"] > 0]
        km = re.search(r"(\d+(?:[.,]\d+)?)\s*km", nom, re.I)
        out.append({"nom": nom.strip(), "km": float(km.group(1).replace(",", ".")) if km else None, "etat": etat,
                    **({"prix": f"{min(live):g} €"} if live and etat == "ouvert" else {})})
    return out


ad_njuko.by_url = True


def ad_supabase_counter(u):
    """small registration sites made with Supabase (Foulées Solidaires de l'Entre-Deux): the page shows
    "N inscrits sur Q" by calling the public function etat_public with the site's publishable key
    (public by design, written in the page). Same reading as a visitor; anything unexpected -> []"""
    page = fetch(u)
    base = next((b for b in re.findall(r"https://[a-z0-9]{12,}\.supabase\.co", page)), None)
    key = (re.findall(r"sb_publishable_[A-Za-z0-9_-]+", page) or re.findall(r"eyJ[\w-]+\.[\w-]+\.[\w-]+", page) or [None])[0]
    if not base or not key:
        return []
    req = urllib.request.Request(f"{base}/rest/v1/rpc/etat_public", data=b"{}", method="POST",
                                 headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json", **UA})
    d = json.load(net.urlopen(req, timeout=30))
    d = d[0] if isinstance(d, list) and d else d
    if not isinstance(d, dict) or not isinstance(d.get("quota"), int) or not isinstance(d.get("inscrits"), int):
        return []
    return [{"nom": "", "km": None, "etat": "complet" if d["inscrits"] >= d["quota"] > 0 else "ouvert"}]


ad_supabase_counter.by_url = True

ADAPTERS = [(r"topchrono\.run/evenements/", ad_topchrono), (r"utoi\.re/produit/", ad_utoire),
            (r"sportinnovation\.fr/Evenements/Inscriptions/", ad_sportinnovation), (r"klikego\.com/inscription/", ad_klikego),
            (r"in\.njuko\.com/[^/?#]+", ad_njuko), (r"foulee-solidaire-polio\.netlify\.app", ad_supabase_counter)]


def can_status(r):
    # registration state always follows the platform, unless the owner locked "complet" himself
    return not r.get("manual") and "complet" not in locked.get(r["id"], set())


def set_state(r, ep, etat, label):
    want_c, want_x = etat == "complet", etat == "clos"
    if etat == "ouvert" and (ep.get("limite") or "9999") < TODAY:   # the platform still takes entries: a past deadline is stale
        ep.pop("limite"); changes.append(f"{label}:clôture périmée retirée")
    if bool(ep.get("complet")) != want_c:
        ep["complet"] = want_c; changes.append(f"{label}:complet={want_c}")
    if bool(ep.get("clos")) != want_x:
        if want_x: ep["clos"] = True
        else: ep.pop("clos", None)
        changes.append(f"{label}:clos={want_x}")


def match_names(ours, theirs, event=""):
    """platform formats -> our épreuves by shared words (numbers alone never match), then the last
    unmatched pair; ambiguous cases stay unmatched"""
    common = (set.intersection(*[toks(t["nom"]) for t in theirs]) if len(theirs) > 1 else set()) | toks(event)
    words = lambda x: {w for w in toks(x) - common if not w.isdigit() and not re.fullmatch(r"\d+km", w)}
    res, used = {}, set()
    for i, e in enumerate(ours):
        ac = acro(e.get("nom"), True)
        kms = lambda x: {w for w in toks(x) if re.fullmatch(r"\d+(?:[.,]\d+)?km", w)}
        # shared words first; the same distance (« 21 km ») only decides when no word does
        sc = sorted((((len(words(e.get("nom")) & words(t["nom"])) + (2 if ac and ac == acro(t["nom"]) else 0)) * 10 + len(kms(e.get("nom")) & kms(t["nom"])), j)
                     for j, t in enumerate(theirs) if j not in used), reverse=True)
        if sc and sc[0][0] > 0 and (len(sc) == 1 or sc[0][0] > sc[1][0]):
            res[i] = theirs[sc[0][1]]; used.add(sc[0][1])
    left_o = [i for i in range(len(ours)) if i not in res]
    left_t = [j for j in range(len(theirs)) if j not in used]
    if len(left_o) == 1 and len(left_t) == 1:
        res[left_o[0]] = theirs[left_t[0]]
    return res


plat_read, plat_err = 0, None
for r in data["races"]:
    if r.get("hidden") or not can_status(r): continue
    eps = r.get("epreuves", [])
    # pages to read: the épreuves' own links when they point to a known platform, else the event link
    per_ep = [(i, e.get("url")) for i, e in enumerate(eps) if e.get("url") and any(re.search(p, e["url"]) for p, _ in ADAPTERS)]
    jobs = per_ep or [(None, u) for u in [r.get("inscription") or ""] if any(re.search(p, u) for p, _ in ADAPTERS)]
    if not jobs: continue
    ok = True
    for i, u in jobs:
        fn = next(f for p, f in ADAPTERS if re.search(p, u))
        try:
            theirs = fn(u) if getattr(fn, "by_url", False) else fn(fetch(u))
        except Exception as e:
            plat_err = f"{e.__class__.__name__}: {str(e)[:150]}"; errors.append(f"plateforme {r['id']} ({e.__class__.__name__})"); ok = False
            continue
        if not theirs:
            ok = False; continue
        plat_read += 1
        if i is not None:                        # one page per épreuve
            set_state(r, eps[i], theirs[0]["etat"], f"{r['id']}:{eps[i].get('nom', i)}")
            continue
        if len(theirs) == 1 and not theirs[0]["nom"]:   # one state for the whole page
            res = {k: theirs[0] for k in range(len(eps))}
        else:
            res = {0: theirs[0]} if len(eps) == 1 and len(theirs) == 1 else match_names(eps, theirs, r.get("nom", ""))
            if len(res) < len(eps) or len(theirs) != len(eps):
                states = {t["etat"] for t in theirs}
                if len(states) == 1:   # formats differ from our épreuves but the platform says the same everywhere
                    only = next(iter(states))
                    res = {k: {"etat": only} for k in range(len(eps))}
                else:
                    ok = False
                    PARTIAL[r["id"]] = {"source": "plateforme", "epreuves": [eps[k].get("nom", "") for k in range(len(eps)) if k not in res],
                                        "plateforme": [t["nom"] for t in theirs]}
        if any(t.get("prix") for t in theirs) and can(r, "epreuves"):   # price given by the platform (njuko)
            pm = {0: theirs[0]} if len(eps) == 1 and len(theirs) == 1 else match(eps, theirs, r.get("nom", ""))
            lo, lt = [k for k in range(len(eps)) if k not in pm], [t for t in theirs if all(t is not v for v in pm.values())]
            if len(lo) == 1 and len(lt) == 1:   # the last unmatched pair
                pm[lo[0]] = lt[0]
            for k, t in pm.items():
                setf(eps[k], r, "prix", t.get("prix"), f"{eps[k].get('nom', k)}:prix")
        for k, t in res.items():
            set_state(r, eps[k], t["etat"], f"{r['id']}:{eps[k].get('nom', k)}")
            if t.get("url") and eps[k].get("url") != t["url"]:   # closest page to the registration of this race
                eps[k]["url"] = t["url"]; changes.append(f"{r['id']}:{eps[k].get('nom', k)}:url")
    if ok and eps:
        VERIF[r["id"]] = "plateforme"
        if (r.get("limite") or "9999") < TODAY and any(not e.get("complet") and not e.get("clos") for e in eps):
            r.pop("limite"); changes.append(f"{r['id']}:clôture périmée retirée")
        full = all(e.get("complet") for e in eps)
        shut = not full and all(e.get("complet") or e.get("clos") for e in eps)
        if bool(r.get("complet")) != full:
            r["complet"] = full; changes.append(f"{r['id']}:complet={full}")
        if bool(r.get("clos")) != shut:
            if shut: r["clos"] = True
            else: r.pop("clos", None)
            changes.append(f"{r['id']}:clos={shut}")
if plat_read or plat_err:
    run["plateformes"] = {"metrics": {"pages": plat_read}, **({"error": plat_err} if not plat_read and plat_err else {})}


# 4. Sportpro: races renamed "Course annulée : …" on the agenda are hidden (not deleted, so the
#    Claude update does not add them back).
try:
    req = urllib.request.Request("https://www.sportpro.re/courses/", headers=UA)
    page = net.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    cancelled = {m.group(1) for m in re.finditer(r'courses/(\d{5})-([a-z0-9-]+)/', page) if "annul" in m.group(2)}
    for r in data["races"]:
        m = re.search(r"sportpro\.re/courses/(\d{5})-", r.get("page") or "")
        if m and m.group(1) in cancelled and not r.get("hidden") and can(r, "hidden"):
            r["hidden"] = True
            r["annule"] = True
            changes.append(f"{r['id']}:annulée")
    # 4b. per-épreuve status from the same agenda page: link, deadline and "Complet" of each épreuve
    ag = sp_agenda(page)
    # only events held in La Réunion (Sportpro also times races in Mayotte, Maurice…): the card's town must be a Réunion commune
    import controls as _c
    _reu = {norm(x) for x in _c.COMMUNES} | {"la plaine des cafres", "plaine des cafres", "hell bourg", "cilaos", "mafate"}
    FOUND["Sportpro"] = []
    for card in re.split(r'<li class="course-card">', page)[1:]:
        m = re.search(r'class="courseLink" href="courses/(\d{5})-([^"/]+)/?">([^<]+)</a>', card)
        if not m: continue
        ville = re.search(r'lbl-ville">[^<]*</span>\s*<span class="valCourse">\s*([^<]+?)\s*(?:<|$)', card)
        v = norm(html.unescape(ville.group(1))) if ville else ""
        if v and not any(v == c or v.startswith(c + " ") for c in _reu):
            continue
        FOUND["Sportpro"].append((f"courses/{m.group(1)}-", html.unescape(m.group(3)).strip() + (f" ({SP_DATES[m.group(1)]})" if m.group(1) in SP_DATES else "") + (f", {ville.group(1).strip()}" if ville else ""),
                                  f"https://www.sportpro.re/courses/{m.group(1)}-{m.group(2)}/"))
    associees = 0
    for r in data["races"]:
        m = re.search(r"sportpro\.re/courses/(\d{5})-", r.get("page") or "")
        if r.get("hidden") or not m or not ag.get(m.group(1)) or not can(r, "epreuves"):
            continue
        res = match(r.get("epreuves", []), ag[m.group(1)], r.get("nom", ""))
        if res and len(res) == len(r.get("epreuves", [])): VERIF[r["id"]] = "sportpro"
        elif r.get("epreuves"):
            PARTIAL[r["id"]] = {"source": "sportpro", "epreuves": [e.get("nom", "") for k, e in enumerate(r["epreuves"]) if k not in res],
                                "plateforme": [t["nom"] for t in ag[m.group(1)]]}
        # start time of each épreuve and date of a one-day event follow the agenda (organiser's data)
        if can(r, "epreuves"):
            for i, t in res.items():
                if t.get("h") and r["epreuves"][i].get("h") != t["h"]:
                    r["epreuves"][i]["h"] = t["h"]; changes.append(f"{r['id']}:{r['epreuves'][i].get('nom', i)}:heure")
        nd = SP_DATES.get(m.group(1))
        if nd and nd != r.get("date") and nd >= TODAY and not r.get("fin") and not any(e.get("date") for e in r.get("epreuves", [])) and can(r, "date"):
            r["date"] = nd; changes.append(f"{r['id']}:date")
        associees += len(res)
        for t in res.values():  # Sportpro also greys "Complet" once the deadline is past: that is "closed", not "full"
            if t["limite"] and t["limite"] < TODAY:
                t["complet"] = False
        for i, t in res.items():
            ep = r["epreuves"][i]
            for f, v in (("url", t["url"]), ("limite", t["limite"]), ("complet", t["complet"])):
                if v is not None and ep.get(f) != v:
                    ep[f] = v
                    changes.append(f"{r['id']}:{ep.get('nom', i)}:{f}")
        # registration opening date announced on the agenda ("ouverture le 23/10/2026 à partir de 12h00"):
        # follows the source when it moves, and disappears once registrations are open
        for i, t in res.items():
            ep = r["epreuves"][i]
            if ep.get("ouverture") != t["ouverture"]:
                if t["ouverture"]:
                    ep["ouverture"] = t["ouverture"]
                else:
                    ep.pop("ouverture", None)
                changes.append(f"{r['id']}:{ep.get('nom', i)}:ouverture")
        if res and len(res) == len(r.get("epreuves", [])) and can(r, "ouverture"):
            ouvs = [t["ouverture"] for t in res.values()]
            ro = min(ouvs) if all(ouvs) else None
            if r.get("ouverture") != ro:
                if ro:
                    r["ouverture"] = ro
                else:
                    r.pop("ouverture", None)
                changes.append(f"{r['id']}:ouverture={ro}")
        if len(r.get("epreuves", [])) > 1:
            # several épreuves: S'inscrire opens the event page, which lists them all with their own buttons
            if "/courses/epreuves/" in (r.get("inscription") or "") and can(r, "inscription"):
                r["inscription"] = r["page"]
                changes.append(f"{r['id']}:inscription événement")
            if len(res) == len(r["epreuves"]) and can(r, "complet"):
                full = all(t["complet"] for t in res.values())
                if bool(r.get("complet")) != full:
                    r["complet"] = full
                    changes.append(f"{r['id']}:complet={full}")
    run["sportpro"] = {"metrics": {"evenements": len(ag), "epreuves": sum(len(v) for v in ag.values()),
                                   "associees": associees}}
except Exception as e:
    errors.append(f"sportpro ({e.__class__.__name__})")
    run["sportpro"] = {"metrics": {}, "error": f"{e.__class__.__name__}: {str(e)[:150]}"}

# 5. Sportpro race pages (every 3 hours, to stay light on the site): a cancellation can also be
#    written only in the presentation ("Evénement annulé… Ne pas s'inscrire") without changing the title.
#    Only a cancellation in the page TITLE hides the race. One found in the presentation is reported
#    (issue « annulation ou report repéré ») and the race stays shown: conditional phrases such as
#    « ne pas s'inscrire si vous n'êtes pas licencié » or « en cas d'alerte cyclonique, toute course
#    annulée sera remboursée » must never hide a race.
CANCEL = re.compile(r"(?i)\b(?:[ée]v[ée]nement|course|[ée]preuve|manifestation)\s+annul[ée]e?s?\b|ne\s+pas\s+s[’']inscrire")
SP_ANNUL = []   # cancellations seen only in a Sportpro presentation: reported, not hidden
import watch  # noqa: E402  (HEDGE: conditional wording)
if NOW.hour % 3 == 0 or "--all" in sys.argv:
    lues, essais, derr = 0, 0, None
    for r in data["races"]:
        if r.get("hidden") or not can(r, "hidden"):
            continue
        urls = [u for u in (r.get("inscription"), r.get("page")) if u and "sportpro.re/courses/" in u]
        for u in urls[:1]:
            essais += 1
            try:
                req = urllib.request.Request(u, headers=UA)
                s = net.urlopen(req, timeout=30).read().decode("utf-8", "replace")
                lues += 1
                clean = lambda x: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x)))
                h1 = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S)
                txt = clean(s)
                i = txt.find(" Présentation ")
                pres = txt[i:i + 900] if i >= 0 else ""
                for stop in (" Parcours de l", " Modalités d", " Tarifs ", " À venir ", " A venir "):
                    j = pres.find(stop)
                    if j > 0:
                        pres = pres[:j]
                # only this race's own title and presentation (the sidebar lists other races)
                if CANCEL.search(clean(h1.group(1)) if h1 else ""):
                    r["hidden"] = True
                    r["annule"] = True
                    changes.append(f"{r['id']}:annulée")
                else:
                    for m in CANCEL.finditer(pres):
                        if watch.HEDGE.search(pres[max(0, m.start() - 45):m.start()] + pres[m.end():m.end() + 40]):
                            continue
                        SP_ANNUL.append(f"**{r['nom']}** ({r['date']}) : « {pres[max(0, m.start() - 70):m.end() + 50].strip()} » — {u}")
                        break
            except Exception as e:
                errors.append(f"sportpro {r['id']} ({e.__class__.__name__})")
                derr = f"{e.__class__.__name__} sur {u}"
    if essais:  # a failure only when no page could be read at all (or the count collapses)
        run["sportpro_pages"] = {"metrics": {"pages": lues}, **({"error": derr} if not lues and derr else {})}

# 6. Sportpro épreuve prices (every 3 hours): each épreuve page has its own price grid
#    ("Dossard jetable" column; licensed / non-licensed rows for triathlons).
def sp_price(page):
    m = re.search(r'<table class="tabTarifs">(.*?)</table>', page, re.S)
    if not m:
        return None
    rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", m.group(1), re.S):
        cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", c))).strip() for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S)]
        euros = [c for c in cells[1:] if re.fullmatch(r"\d+(?:[.,]\d+)?\s*€", c)]
        if euros:
            label = re.sub(r"(?i)^tarif\s*|\(.*?\)", "", cells[0]).strip()
            rows.append((euros[0].replace(" €", " €"), label))
    if not rows:
        return None
    if len({p for p, _ in rows}) == 1:
        return rows[0][0]
    return " / ".join(f"{p} {l}".strip() for p, l in rows)


FULL_PRIX = NOW.hour % 3 == 0 or "--all" in sys.argv   # every 3 hours all prices; each hour the épreuves still without one (new races)
if True:
    prix_lus, essais, derr = 0, 0, None
    for r in data["races"]:
        if r.get("hidden") or not can(r, "epreuves"):
            continue
        villes, lieux = [], []
        for ep in r.get("epreuves", []):
            if "sportpro.re/courses/epreuves/" not in (ep.get("url") or "") or (not FULL_PRIX and ep.get("prix")):
                continue
            essais += 1
            try:
                pg = net.urlopen(urllib.request.Request(ep["url"], headers=UA), timeout=30).read().decode("utf-8", "replace")
                pr = sp_price(pg)
                prix_lus += pr is not None
                setf(ep, r, "prix", pr, "prix " + ep.get("nom", ""))
                # distance and climb follow the organiser's page (an event can be reworked after it was listed);
                # Sportpro writes 0.1 km for an unknown distance
                f = sp_facts(pg)
                if f["km"] and f["km"] > 0.1 and abs(f["km"] - float(ep.get("km") or 0)) >= 0.05:
                    setf(ep, r, "km", int(f["km"]) if f["km"] == int(f["km"]) else f["km"], "distance " + ep.get("nom", ""))
                if f["dp"] and f["dp"] != ep.get("dp"):
                    setf(ep, r, "dp", f["dp"], "D+ " + ep.get("nom", ""))
                if f["ville"]:
                    villes.append(f["ville"]); lieux.append((f["ville"], f["lieu"]))
            except Exception as e:
                errors.append(f"sportpro prix {r['id']} ({e.__class__.__name__})")
                derr = f"{e.__class__.__name__} sur {ep['url']}"
        # town: the start can move (Maloya Trail: Sainte-Rose -> Hell-Bourg): when most épreuve pages agree on
        # another town of La Réunion, the race follows (town, start place, map pin)
        if villes:
            top = max(set(villes), key=villes.count)
            if villes.count(top) * 2 > len(villes) and top in _cc.COMMUNES:
                lt = [l for v, l in lieux if v == top and l]
                move_town(r, top, max(set(lt), key=lt.count) if lt else None, "lieu_sportpro")
    if essais and FULL_PRIX:
        ECARTS.setdefault("lieu_sportpro", {})
        run["sportpro_prix"] = {"metrics": {"prix": prix_lus}, **({"error": derr} if not prix_lus and derr else {})}

# 7. Other sources (organisers' sites, HelloAsso, Top Chrono, chronometrage, njuko…): their pages are free text,
#    so nothing is changed from them. Every 6 hours each race's own pages are read and compared with the sheet:
#    a distance or a climb of an épreuve that appears nowhere on the page, or a start town not named on the
#    page while another one is. Reported by the daily summary (« À vérifier sur la page de l'organisateur »).
#    Sportpro and UTOI races are left out (checked field by field above).
KMRE = re.compile(r"(?<![\d.,])(\d{1,3}(?:[.,]\d{1,2})?)\s?(?:km|kms|kilom[eè]tres?)\b", re.I)
DPRE = re.compile(r"(?:(\d[\d  .]{0,5}\d|\d)\s?m(?:[eè]tres?)?\s?(?:de\s)?(?:D\+|d[ée]nivel[ée]\s?(?:positif)?|de d[ée]nivel)|(?:D\+|d[ée]nivel[ée]\s?(?:positif)?)\s?:?\s?(\d[\d  .]{0,5}\d))", re.I)
if NOW.hour % 6 == 2 or "--all" in sys.argv or "--textes" in sys.argv:
    ECARTS["texte"] = {}
    for r in data["races"]:
        if r.get("hidden") or (r.get("fin") or r.get("date") or "") < TODAY:
            continue
        urls = [r.get(k) for k in ("fiche", "inscription", "page")] + [e.get("url") for e in r.get("epreuves", [])]
        if any("sportpro.re" in (u or "") or "utoi" in (u or "") for u in urls):
            continue
        urls = list(dict.fromkeys(u for u in urls if u and re.match(r"https?://[^/]+/.+", u)))   # pages of the race, not a site's home page
        txt, main_ok = "", False
        mains = {r.get(k) for k in ("fiche", "inscription", "page")}
        for u in urls[:4]:
            try:
                if re.search(r"in\.njuko\.com/", u):
                    txt += " " + " ".join(t["nom"] for t in ad_njuko(u))
                else:
                    txt += " " + plain(fetch(u))
                main_ok |= u in mains
            except Exception:
                pass
        # the race's own page must have been read (a registration site alone lists other events too)
        if not main_ok or (len(txt) < 200 and not re.search(r"\bkm\b", txt)):
            continue
        kms = [float(x.replace(",", ".")) for x in KMRE.findall(txt)]
        dps = [int(re.sub(r"\D", "", a or b)) for a, b in DPRE.findall(txt) if re.sub(r"\D", "", a or b)]
        msgs = []
        for e in (r.get("epreuves", []) if can(r, "epreuves") else []):   # épreuves set by hand (locked): not compared
            k = float(e["km"]) if e.get("km") else None
            leg = re.search(r"[x×]\s*(\d+(?:[.,]\d+)?)\s*km", e.get("nom") or "")   # relay « 5 × 3,7 km »: a leg is enough
            ok_v = [k] + ([float(leg.group(1).replace(",", "."))] if leg else [])
            if k and kms and not any(abs(v - w) <= max(.3, .05 * w) for v in kms for w in ok_v):
                msgs.append(f"{e.get('nom')} : {fmt_n(k)} km introuvable (la page cite {', '.join(fmt_n(v) + ' km' for v in sorted(set(kms))[:6])})")
            if e.get("dp") and dps and not any(abs(v - e["dp"]) <= max(30, .08 * e["dp"]) for v in dps):
                msgs.append(f"{e.get('nom')} : {e['dp']} m D+ introuvable (la page cite {', '.join(str(v) + ' m' for v in sorted(set(dps))[:6])})")
        tw = communes_in(re.sub(r"\b974\d\d\s+[A-Za-zÀ-ÿ'’ -]{2,25}", " ", txt))   # postal addresses (organiser's office) left out
        if tw and r.get("commune") not in tw and not any(norm(r.get("commune", "")) in norm(x) for x in tw):
            msgs.append(f"ville : la fiche dit {r.get('commune')}, la page cite {', '.join(tw[:4])}")
        if msgs:
            ECARTS["texte"][r["id"]] = msgs

# differences: each category written by this run replaces the stored one; pins at a town centre kept 7 days
try:
    old_e = json.load(open("state/ecarts.json")) if os.path.exists("state/ecarts.json") else {}
    old_e = old_e if all(isinstance(v, dict) for v in old_e.values()) else {}
    new_e = dict(old_e)
    for cat, v in ECARTS.items():
        new_e[cat] = v if cat != "epingle" else {**old_e.get("epingle", {}), **v}
    lim7 = (NOW - dt.timedelta(days=7)).date().isoformat()
    new_e["epingle"] = {k: v for k, v in new_e.get("epingle", {}).items() if v.get("at", "") >= lim7}
    if new_e != old_e:
        json.dump(new_e, open("state/ecarts.json", "w"), ensure_ascii=False, indent=1, sort_keys=True)
except Exception as e:
    errors.append(f"écarts ({e.__class__.__name__})")

if changes:
    data["updatedAt"] = NOW.isoformat(timespec="seconds")
    json.dump(data, open("data.json", "w"), ensure_ascii=False, separators=(",", ":"))
# health of each source: state/health.json (rewritten only when its content changes) + this run's counts
try:   # races whose épreuves were not all recognised (daily summary)
    old_p = json.load(open("state/partiels.json")) if os.path.exists("state/partiels.json") else None
    new_p = {k: v for k, v in sorted(PARTIAL.items())}
    if old_p != new_p:
        json.dump(new_p, open("state/partiels.json", "w"), ensure_ascii=False, indent=1)
except Exception:
    pass
sante = ""
try:
    prev = health.load()
    state = health.evaluate(prev, run, NOW)
    health.save(state, prev)
    sante = health.summary(state)
    import os, tempfile
    with open(os.path.join(os.environ.get("RUNNER_TEMP") or tempfile.gettempdir(), "health_run.json"), "w") as f:
        json.dump({"at": NOW.isoformat(timespec="minutes"), "run": run, "errors": errors}, f, ensure_ascii=False)
except Exception as e:
    sante = f"santé non évaluée ({e.__class__.__name__})"
# checks (tools/controls.py): verification state of each race (verif.json, read by the site),
# consistency of the data, dead links once a day; problems go to tools/alerts.py through a report file
controle = ""
try:
    import os, subprocess, tempfile
    import controls
    verif, alertes = controls.statut(data, VERIF, TODAY)
    try:
        old_vf = json.load(open("verif.json"))
        stale = (NOW - dt.datetime.fromisoformat(old_vf["at"])).total_seconds() > 1.8 * 3600
    except Exception:
        old_vf, stale = {}, True
    if stale or old_vf.get("races") != verif:   # no commit every hour just for the time stamp
        json.dump({"at": NOW.isoformat(timespec="minutes"), "races": verif}, open("verif.json", "w"), ensure_ascii=False, separators=(",", ":"))
    # reference version: before the push that started this run (Claude update), else the last commit
    ref = "HEAD~1" if os.environ.get("GITHUB_EVENT_NAME") == "push" else "HEAD"
    try:
        prev_data = json.loads(subprocess.run(["git", "show", f"{ref}:data.json"], capture_output=True, text=True, check=True).stdout)
    except Exception:
        prev_data = None
    rep = {"statut": alertes, "qualite": controls.qualite(data, prev_data, TODAY)}
    import watch
    try:   # Chrono Run: its list of races (new-race detector)
        crp = fetch("https://chronorun974.re/courses-2/")
        nav = {"a-propos", "courses-2", "feed", "meteo", "news", "resultats-courses", "suivi-live", "wp-json", "contact", "mentions-legales", "politique-de-confidentialite"}
        FOUND["Chrono Run"] = [(u, u.rstrip("/").split("/")[-1].replace("-", " "), u) for u in dict.fromkeys(re.findall(r'href="(https://chronorun974\.re/([a-z0-9-]+)/)"', crp))
                               for u in [u[0]] if u.rstrip("/").split("/")[-1] not in nav]
    except Exception:
        pass
    def _future_race(u):   # a candidate page must announce a date to come (not a past edition, a challenge or a news item)
        try:
            t = watch.plain(fetch(u))[:20000]
        except Exception:
            return False
        if re.search(r"(?i)\bchallenge\b|classement g[ée]n[ée]ral", t[:600]):
            return False
        for d, mo, y in re.findall(r"(\d{1,2})(?:er)?\s+(janvier|f[ée]vrier|mars|avril|mai|juin|juillet|ao[ûu]t|septembre|octobre|novembre|d[ée]cembre)\s+(20\d\d)", t, re.I):
            k = [norm(x) for x in MOIS].index(norm(mo))
            if f"{y}-{k + 1:02d}-{int(d):02d}" >= TODAY:
                return True
        return False
    if NOW.hour % 3 == 0 or "--all" in sys.argv:
        try:   # WeRun (directory, discovery only): the events it added most recently, all countries
            wr = json.loads(fetch("https://werun.world/wp-json/wp/v2/tribe_events?orderby=date&order=desc&per_page=50&_fields=id,link,title"))
            FOUND["WeRun"] = [(f"werun:{e['id']}", html.unescape(e["title"]["rendered"]), e["link"]) for e in wr if e.get("link")]
        except Exception:
            pass

    def _werun_reunion(u):
        """a WeRun page counts only if its event is in La Réunion, to come, and not already on the site
        (same day and a shared name word); the Claude update adds it from the organiser's link"""
        try:
            pg = fetch(u)
        except Exception:
            return False
        ld = re.search(r'"addressRegion":"([^"]*)"', pg)
        day = re.search(r'"startDate":"(\d{4}-\d\d-\d\d)', pg)
        if not ld or "union" not in ld.group(1) or not day or day.group(1) < TODAY:
            return False
        title = re.search(r"<title>([^<|]+)", pg)
        words = {w for w in toks(html.unescape(title.group(1)) if title else "") if len(w) > 3 and not w.isdigit()} - {"trail", "course", "foulee", "reunion"}
        d0 = dt.date.fromisoformat(day.group(1))
        for r in data["races"]:
            try:
                near = abs((dt.date.fromisoformat(r["date"]) - d0).days) <= 1
            except Exception:
                continue
            if near and (words & toks(r.get("nom", "")) or not words):
                return False
        return True

    rep["nouveautes"] = watch.nouveautes(data, FOUND, check={"Chrono Run": _future_race, "Top Chrono": _future_race, "WeRun": _werun_reunion})
    if NOW.hour % 3 == 0 or "--all" in sys.argv:
        rep["annulation"] = watch.annulations(data, TODAY, controls.get) + SP_ANNUL
    evts = watch.diff(prev_data, data, TODAY, NOW)
    jr = watch.journal_add(evts, NOW)
    rep["journal"] = [watch.line(e) for e in evts]
    if NOW.weekday() == 0 and NOW.hour == 7 or "--recap" in sys.argv:
        rep["recap"] = watch.recap(data, jr, TODAY, NOW)
    if NOW.hour == 6 or "--liens" in sys.argv:
        rep["liens"] = controls.liens(data, TODAY)
    with open(os.path.join(os.environ.get("RUNNER_TEMP") or tempfile.gettempdir(), "controls.json"), "w") as f:
        json.dump(rep, f, ensure_ascii=False)
    n = {k: len(v) for k, v in rep.items()}
    controle = f"vérifiées {sum(v == 'ok' for v in verif.values())}/{len(verif)}, à vérifier {sum(v == 'alerte' for v in verif.values())}, " \
               + ", ".join(f"{k} {v}" for k, v in n.items())
except Exception as e:
    controle = f"contrôles non faits ({e.__class__.__name__}: {e})"
print(f"{len(changes)} changement(s)" + (": " + ", ".join(changes) if changes else "")
      + (" · sources en erreur : " + ", ".join(errors) if errors else "") + (" · " + sante if sante else "")
      + (" · " + controle if controle else ""))
sys.exit(0)
