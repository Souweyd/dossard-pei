#!/usr/bin/env python3
"""Tracks for the races that have none (run by the hourly workflow, free).

For each visible race to come without a track (data.json gpx), its own pages (fiche, page,
inscription and the épreuves' links) are searched for a public track:
  - Trace de Trail: tracedetrail.fr/fr/iframe/<n> (or /fr/trace/<n>): the iframe page holds the
    points as JSON objects {"lon":X,"lat":Y,…,"y":altitude} in Web Mercator (EPSG:3857);
  - Openrunner: openrunner.com/embed/<code> or embed.html?code=<code>: the embedded-routes API
    gives a Google polyline (precision 5) and the altitudes as a 1-D delta polyline every
    `interval` metres.
Points outside La Réunion are dropped; each track gets its measured km / D+ and the name of the
épreuve of the closest distance; at most 600 points per track. Writes gpx/<id>.json
{"src", "tracks": [{nom, km, dp, pts}]} (longest first) and data.json gpx[<id>].
A race is tried at most once every 24 h (state/tracks.json). Never fails the workflow.
"""
import datetime as dt
import json
import math
import re
import sys
import urllib.request

import net  # one honest User-Agent, polite delay, size and time limits on every request

UA = {"User-Agent": "Mozilla/5.0 (DossardPei sync; +https://dossardpei.re)", "Accept-Language": "fr-FR,fr;q=0.9"}
TZ = dt.timezone(dt.timedelta(hours=4))
TDT = re.compile(r"tracedetrail\.fr/(?:[a-z]{2}/)?(iframe|trace)/(\d+)")
ORN = re.compile(r"openrunner\.com/(?:route-embed/|embed/|embed\.html\?code=)([0-9a-zA-Z]+)")


def get(u, ref=None):
    h = dict(UA, **({"Referer": ref} if ref else {}))
    with net.urlopen(urllib.request.Request(u, headers=h), timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def merc(x, y):
    return math.degrees(2 * math.atan(math.exp(y / 6378137.0)) - math.pi / 2), math.degrees(x / 6378137.0)


def tracedetrail(kind, n):
    """kind = "iframe" or "trace" (the two pages carry the points; their numbers differ)"""
    h = get(f"https://tracedetrail.fr/fr/{kind}/{n}").replace('\\"', '"')
    pts = []
    for m in re.finditer(r'\{[^{}]*?"lon":(-?[\d.]+),"lat":(-?[\d.]+)[^{}]*?\}', h):
        y = re.search(r'"y":(-?[\d.]+)', m.group(0))
        lat, lon = merc(float(m.group(1)), float(m.group(2)))
        pts.append([lat, lon, float(y.group(1)) if y else 0.0])
    t = re.search(r"<title>([^<]+)</title>", h)
    return [{"nom": t.group(1).split("|")[0].strip() if t else "", "pts": pts, "src": f"https://tracedetrail.fr/fr/{kind}/{n}"}] if len(pts) > 10 else []


def dec(s, dims):
    idx, cur, out = 0, [0] * dims, []
    while idx < len(s):
        for k in range(dims):
            res = shift = 0
            while True:
                b = ord(s[idx]) - 63; idx += 1; res |= (b & 0x1f) << shift; shift += 5
                if b < 0x20:
                    break
            cur[k] += ~(res >> 1) if res & 1 else res >> 1
        out.append(tuple(cur))
    return out


def openrunner(code, ref):
    d = json.loads(get(f"https://api.openrunner.com/api/v2/embedded-routes/{code}", ref))["data"]
    ll = [(a / 1e5, b / 1e5) for a, b in dec(d["shape"]["full_encoded"], 2)]
    el = [v[0] for v in dec(d["elevation"]["full_encoded"], 1)] if d.get("elevation", {}).get("full_encoded") else []
    step = (d.get("elevation") or {}).get("interval") or 100
    pts, dist = [], 0.0
    for i, (la, lo) in enumerate(ll):
        if i:
            a = ll[i - 1]
            dist += math.hypot(math.radians(lo - a[1]) * math.cos(math.radians(la)), math.radians(la - a[0])) * 6371000
        pts.append([la, lo, float(el[min(len(el) - 1, int(dist / step))]) if el else 0.0])
    return [{"nom": d.get("name") or "", "pts": pts, "src": f"https://www.openrunner.com/route-details/{code}"}] if len(pts) > 10 else []


def stats(pts):
    d = 0.0
    for a, b in zip(pts, pts[1:]):
        d += math.hypot(math.radians(b[1] - a[1]) * math.cos(math.radians((a[0] + b[0]) / 2)), math.radians(b[0] - a[0])) * 6371.0
    el = [p[2] for p in pts]
    sm = [sum(el[max(0, i - 2):i + 3]) / len(el[max(0, i - 2):i + 3]) for i in range(len(el))]
    return round(d, 1), round(sum(max(0, b - a) for a, b in zip(sm, sm[1:])))


def thin(pts, n=600):
    if len(pts) <= n:
        return pts
    k = (len(pts) - 1) / (n - 1)
    return [pts[round(i * k)] for i in range(n)]


def main(now):
    data = json.load(open("data.json"))
    today = now.date().isoformat()
    try:
        tried = json.load(open("state/tracks.json"))
    except Exception:
        tried = {}
    try:
        ov = json.load(open("state/overrides.json"))
        manual = set(ov.get("manual", []))
    except Exception:
        manual = set()
    gpx = data.setdefault("gpx", {})
    added = []
    for r in data["races"]:
        rid = r["id"]
        if r.get("hidden") or (r.get("fin") or r["date"]) < today or rid in gpx or rid in manual or r.get("manual"):
            continue
        if tried.get(rid, "") > (now - dt.timedelta(hours=24)).isoformat():
            continue
        tried[rid] = now.isoformat(timespec="minutes")
        pages = list(dict.fromkeys(u for u in [r.get("fiche"), r.get("page"), r.get("inscription")] + [e.get("url") for e in r.get("epreuves", [])] if u))
        found = []
        for u in pages[:6]:
            try:
                h = get(u)
            except Exception:
                continue
            for kind, n in dict.fromkeys(TDT.findall(h)):
                try:
                    found += tracedetrail(kind, n)
                except Exception as e:
                    print(f"tracé {rid} tracedetrail {n} : {e.__class__.__name__}")
            for c in dict.fromkeys(ORN.findall(h)):
                try:
                    found += openrunner(c, u)
                except Exception as e:
                    print(f"tracé {rid} openrunner : {e.__class__.__name__}")
        tracks, seen = [], set()
        for t in found:
            pts = [[round(p[0], 5), round(p[1], 5), round(p[2])] for p in t["pts"] if -21.5 < p[0] < -20.8 and 55.1 < p[1] < 55.9]
            if len(pts) < 20:
                continue
            km, dp = stats(pts)
            if km < 0.5 or (km, dp) in seen:
                continue
            seen.add((km, dp))
            eps = [e for e in r.get("epreuves", []) if e.get("km")]
            best = min(eps, key=lambda e: abs(float(e["km"]) - km)) if eps else None
            nom = best["nom"] if best and abs(float(best["km"]) - km) <= max(2, 0.15 * km) else (t["nom"] or f"{km:g} km")
            tracks.append({"nom": nom, "km": km, "dp": dp, "pts": thin(pts), "src": t["src"]})
        if not tracks:
            continue
        tracks.sort(key=lambda t: -t["km"])
        src = tracks[0]["src"]
        json.dump({"src": src, "tracks": [{k: t[k] for k in ("nom", "km", "dp", "pts")} for t in tracks]},
                  open(f"gpx/{rid}.json", "w"), ensure_ascii=False, separators=(",", ":"))
        gpx[rid] = {"file": f"gpx/{rid}.json", "src": src, "tracks": [{k: t[k] for k in ("nom", "km", "dp")} for t in tracks]}
        tried.pop(rid, None)
        added.append(f"{r['nom']} ({len(tracks)})")
    tried = {k: v for k, v in tried.items() if v > (now - dt.timedelta(days=7)).isoformat()}
    json.dump(tried, open("state/tracks.json", "w"), ensure_ascii=False, indent=0, sort_keys=True)
    if added:
        json.dump(data, open("data.json", "w"), ensure_ascii=False, separators=(",", ":"))
    print(f"tracés ajoutés : {', '.join(added) if added else 'aucun'}")


if __name__ == "__main__":
    try:
        main(dt.datetime.now(TZ))
    except Exception as e:
        print(f"tracés non traités ({e.__class__.__name__}: {e})")
    sys.exit(0)
