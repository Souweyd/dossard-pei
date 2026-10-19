#!/usr/bin/env python3
"""Hourly, free, mechanical update of data.json (run by GitHub Actions).

- removes races whose date (or end date) is past, with their gpx entry;
- UTOI: updates date, start time, distance, D+, price, registration deadline and "complet"
  from the public API (https://api.utoi-inscriptions.com/api/races);
- Top Chrono: marks races "complet" when their page says so;
- Sportpro: hides races renamed "Course annulée : …" on the agenda.

Never touches a field the owner corrected in the admin (state/overrides.json, exported by the
Claude update) nor a manual race. New races, posters and tracks stay with the Claude update.
Prints a one-line summary; exits 0 even when a source is unreachable (it is simply skipped).
"""
import datetime as dt
import html
import json
import re
import sys
import unicodedata
import urllib.request

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
    for r in data["races"]:
        m = re.search(r"utoi-inscriptions\.com/evenements/([^/?#]+)", r.get("inscription", ""))
        if r.get("source") != "utoi" or not m or len(r.get("epreuves", [])) != 1:
            continue
        ep = r["epreuves"][0]
        relay = ep.get("type") == "relais" or bool(re.search(r"relai|duo|equipe", norm(r["nom"])))
        cands = [it for it in items if it["event"]["slug"] == m.group(1)
                 and abs(float(it.get("distanceKm") or 0) - float(ep.get("km") or -1)) < 0.6
                 and (it.get("format") == "RELAY") == relay]
        if len(cands) > 1:  # e.g. relay of 5 vs relay of 10: use the leg count in the name
            n = re.search(r"\b(\d+)\b", norm(r["nom"]).replace(str(ep.get("km", "")), ""))
            cands = [c for c in cands if n and str(c.get("relayLegCount")) == n.group(1)] or cands
        if len(cands) != 1:
            continue
        it = cands[0]
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
except Exception as e:  # source down: skip it this hour
    errors.append(f"utoi ({e.__class__.__name__})")

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
except Exception as e:
    errors.append(f"sportpro ({e.__class__.__name__})")

if changes:
    data["updatedAt"] = NOW.isoformat(timespec="seconds")
    json.dump(data, open("data.json", "w"), ensure_ascii=False, separators=(",", ":"))
print(f"{len(changes)} changement(s)" + (": " + ", ".join(changes) if changes else "")
      + (" · sources en erreur : " + ", ".join(errors) if errors else ""))
sys.exit(0)
