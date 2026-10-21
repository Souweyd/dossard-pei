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
import re
import sys
import unicodedata
import urllib.request

sys.dont_write_bytecode = True  # no tools/__pycache__ in the repo
import health  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (DossardPei sync; +https://dossardpei.re)"}
TZ = dt.timezone(dt.timedelta(hours=4))  # La Réunion
NOW = dt.datetime.now(TZ)
TODAY = NOW.date().isoformat()


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
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


def can(r, field):
    return not r.get("manual") and field not in locked.get(r["id"], set())


def setf(obj, r, field, val, label):
    if val in (None, "") or obj.get(field) == val or not can(r, field):
        return
    obj[field] = val
    changes.append(f"{r['id']}:{label}")


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
        if it.get("slug"):  # S'inscrire opens this race, not the whole event
            setf(r, r, "inscription", f"https://utoi-inscriptions.com/courses/{it['slug']}", "lien course")
        if it.get("startAt"):
            st = dt.datetime.fromisoformat(it["startAt"].replace("Z", "+00:00")).astimezone(TZ)
            setf(r, r, "date", st.date().isoformat(), "date")
            setf(ep, r, "h", st.strftime("%Hh%M"), "heure")
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
            nm = "épreuve " + (ep.get("nom") or "")
            if it.get("startAt"):
                st = dt.datetime.fromisoformat(it["startAt"].replace("Z", "+00:00")).astimezone(TZ)
                if can(r, "epreuves"):
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
        # the event itself: first and last race days, latest deadline, full only when every race is full
        days = sorted(e["date"] for e in r["epreuves"] if e.get("date"))
        if days and can(r, "date"):
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
except Exception as e:  # source down: skip it this hour
    errors.append(f"utoi ({e.__class__.__name__})")
    run["utoi"] = {"metrics": {}, "error": f"{e.__class__.__name__}: {str(e)[:150]}"}

# 3. Top Chrono: "COMPLET"
try:
    pages, n = [], 1
    while n <= 4:
        batch = get_json(f"https://www.topchrono.run/wp-json/wp/v2/pages?inscription=133&per_page=100&page={n}&_fields=id,link")
        pages += batch
        if len(batch) < 100:
            break
        n += 1
    by_link = {p["link"].rstrip("/"): p["id"] for p in pages}
    run["topchrono"] = {"metrics": {"pages": len(pages)}}
    for r in data["races"]:
        link = (r.get("fiche") or r.get("inscription") or "").rstrip("/")
        if r.get("source") != "topchrono" or link not in by_link or r.get("complet"):
            continue
        c = get_json(f"https://www.topchrono.run/wp-json/wp/v2/pages/{by_link[link]}?_fields=content")["content"]["rendered"]
        txt = html.unescape(re.sub(r"<[^>]+>", " ", c))
        if re.search(r"\bCOMPLET\b", txt) and can(r, "complet"):
            r["complet"] = True
            changes.append(f"{r['id']}:complet")
except Exception as e:
    errors.append(f"topchrono ({e.__class__.__name__})")
    run["topchrono"] = {"metrics": {}, "error": f"{e.__class__.__name__}: {str(e)[:150]}"}

# Sportpro agenda: one card per event, one "epreuveFiche" per épreuve (button "S'inscrire" or "Complet").
def sp_agenda(page):
    out = {}
    for card in re.split(r'<li class="course-card">', page)[1:]:
        m = re.search(r'class="courseLink" href="courses/(\d{5})-[^"]+"', card)
        if not m: continue
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
                        "ouverture": f"{ouv.group(3)}-{ouv.group(2)}-{ouv.group(1)}T{int(ouv.group(4) or 0):02d}:{ouv.group(5) or '00'}" if ouv else None})
        out[m.group(1)] = eps
    return out

# Our épreuves are matched to the agenda ones by distance, then by the words of their names.
STOP = {"de", "du", "des", "la", "le", "les", "a", "au", "aux", "et", "l", "d", "en"}
def toks(s): return {t[:-1] if len(t) > 3 and t.endswith("s") else t for t in re.sub(r"(\d+) km\b", r"\1km", norm(s)).split() if t not in STOP}
def match(ours, theirs, event=""):
    """our épreuve -> agenda épreuve; None when unsure. Sportpro writes 0.1 km for an unknown distance."""
    common = set.intersection(*[toks(t["nom"]) for t in theirs]) if len(theirs) > 1 else set()
    common |= toks(event)
    res = {}
    for i, e in enumerate(ours):
        k = float(e["km"]) if e.get("km") else None
        def near(t):
            if t["km"] is None or t["km"] <= 0.1 or k is None: return True
            return abs(t["km"] - k) <= max(0.15, 0.03 * k)
        c = [t for t in theirs if near(t)]
        w = toks(e.get("nom")) - common
        def score(t):
            tw = toks(t["nom"]) - common
            sure = t["km"] is not None and t["km"] > 0.1 and k is not None
            return (2 * len(w & tw) - len(tw - w) + (3 if sure else 0))
        sc = sorted(((score(t), t) for t in c), key=lambda x: -x[0])
        if not sc or (len(sc) > 1 and sc[0][0] <= sc[1][0]): continue
        best = sc[0][1]; tw = toks(best["nom"]) - common
        sure = best["km"] is not None and best["km"] > 0.1 and k is not None
        if w & tw or sure or (not w and not tw):   # shared words, a matching distance, or both reduced to the event name
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
        out.append({"nom": j.get("title") or "", "km": None, "limite": lim, "complet": full})
    return out


dag_targets = [r for r in data["races"] if not r.get("hidden") and re.search(r"chronometrage\.com/events/[A-Za-z0-9_-]+", (r.get("inscription") or "") + " " + (r.get("fiche") or ""))]
if dag_targets:
    lus, derr = 0, None
    for r in dag_targets:
        u = re.search(r"https?://(?:www\.)?chronometrage\.com/events/[A-Za-z0-9_-]+", (r.get("inscription") or "") + " " + (r.get("fiche") or "")).group(0)
        try:
            req = urllib.request.Request(u, headers=UA)
            theirs = dag_races(urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace"))
        except Exception as e:
            derr = f"{e.__class__.__name__}: {str(e)[:150]}"
            errors.append(f"chronometrage {r['id']} ({e.__class__.__name__})")
            continue
        if not theirs:
            continue
        lus += 1
        if not can(r, "epreuves"):
            continue
        eps = r.get("epreuves", [])
        res = {0: theirs[0]} if len(eps) == 1 and len(theirs) == 1 else match(eps, theirs, r.get("nom", ""))
        for i, t in res.items():
            ep = eps[i]
            if t["limite"] and ep.get("limite") != t["limite"]:
                ep["limite"] = t["limite"]
                changes.append(f"{r['id']}:{ep.get('nom', i)}:limite")
            # sold-out stock marks "complet"; never cleared here (organisers often close a nearly full race by hand)
            if t["complet"] and not ep.get("complet"):
                ep["complet"] = True
                changes.append(f"{r['id']}:{ep.get('nom', i)}:complet")
        if res and len(res) == len(eps):
            lims = [t["limite"] for t in res.values()]
            if all(lims) and can(r, "limite") and r.get("limite") != max(lims):
                r["limite"] = max(lims)
                changes.append(f"{r['id']}:clôture")
            if all(eps[i].get("complet") for i in res) and can(r, "complet") and not r.get("complet"):
                r["complet"] = True
                changes.append(f"{r['id']}:complet")
    run["chronometrage"] = {"metrics": {"pages": lus}, **({"error": derr} if not lus and derr else {})}


# 4. Sportpro: races renamed "Course annulée : …" on the agenda are hidden (not deleted, so the
#    Claude update does not add them back).
try:
    req = urllib.request.Request("https://www.sportpro.re/courses/", headers=UA)
    page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    cancelled = {m.group(1) for m in re.finditer(r'courses/(\d{5})-([a-z0-9-]+)/', page) if "annul" in m.group(2)}
    for r in data["races"]:
        m = re.search(r"sportpro\.re/courses/(\d{5})-", r.get("page") or "")
        if m and m.group(1) in cancelled and not r.get("hidden") and can(r, "hidden"):
            r["hidden"] = True
            r["annule"] = True
            changes.append(f"{r['id']}:annulée")
    # 4b. per-épreuve status from the same agenda page: link, deadline and "Complet" of each épreuve
    ag = sp_agenda(page)
    associees = 0
    for r in data["races"]:
        m = re.search(r"sportpro\.re/courses/(\d{5})-", r.get("page") or "")
        if r.get("hidden") or not m or not ag.get(m.group(1)) or not can(r, "epreuves"):
            continue
        res = match(r.get("epreuves", []), ag[m.group(1)], r.get("nom", ""))
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
CANCEL = re.compile(r"(?i)\b(?:[ée]v[ée]nement|course|[ée]preuve|manifestation)\s+annul[ée]e?s?\b|ne\s+pas\s+s[’']inscrire")
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
                s = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
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
                if CANCEL.search((clean(h1.group(1)) if h1 else "") + " " + pres):
                    r["hidden"] = True
                    r["annule"] = True
                    changes.append(f"{r['id']}:annulée")
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


if NOW.hour % 3 == 0 or "--all" in sys.argv:
    prix_lus, essais, derr = 0, 0, None
    for r in data["races"]:
        if r.get("hidden") or not can(r, "epreuves"):
            continue
        for ep in r.get("epreuves", []):
            if "sportpro.re/courses/epreuves/" not in (ep.get("url") or ""):
                continue
            essais += 1
            try:
                pg = urllib.request.urlopen(urllib.request.Request(ep["url"], headers=UA), timeout=30).read().decode("utf-8", "replace")
                pr = sp_price(pg)
                prix_lus += pr is not None
                setf(ep, r, "prix", pr, "prix " + ep.get("nom", ""))
            except Exception as e:
                errors.append(f"sportpro prix {r['id']} ({e.__class__.__name__})")
                derr = f"{e.__class__.__name__} sur {ep['url']}"
    if essais:
        run["sportpro_prix"] = {"metrics": {"prix": prix_lus}, **({"error": derr} if not prix_lus and derr else {})}

if changes:
    data["updatedAt"] = NOW.isoformat(timespec="seconds")
    json.dump(data, open("data.json", "w"), ensure_ascii=False, separators=(",", ":"))
# health of each source: state/health.json (rewritten only when its content changes) + this run's counts
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
print(f"{len(changes)} changement(s)" + (": " + ", ".join(changes) if changes else "")
      + (" · sources en erreur : " + ", ".join(errors) if errors else "") + (" · " + sante if sante else ""))
sys.exit(0)
