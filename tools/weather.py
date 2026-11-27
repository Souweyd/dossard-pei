#!/usr/bin/env python3
"""Race-day weather for the races of the next 7 days (run by the hourly workflow, every 3 hours).

Main source (since 27/11/2026, with the agreement of its author): rundata.re, MCP service over HTTP
(tool prevision_meteo), 3-hour steps for the race day, temperatures brought back to the altitude of the point:
model AROME outre-mer of Météo-France (2.5 km) for ~48 h, then IFS HRES of ECMWF (9 km), with the
confidence of each day (agreement of the 51 ECMWF ensemble members); plus the official Météo-France
vigilance (tool vigilance_meteo) for races of today and tomorrow. Attribution: « rundata.re, d'après
Météo-France et l'ECMWF (Open-Meteo) ». ~1 call per race and run (+1 for a summit, +1 for the day before
of a trail), every 3 hours.
Backup, race by race (rundata unreachable or an answer that cannot be read): MET Norway locationforecast 2.0
(free, no key; identification by User-Agent, data under CC BY 4.0 « MET Norway »). Hourly steps for ~2.5 days,
then 6-hourly steps up to 10 days.
For each visible race whose race day is within 7 days, and for each race day of a multi-day event:
  - start: conditions at the start hour, at the start point (altitude of the track when known);
  - window: from the start to the estimated end of the longest épreuve of that day (max 14 h):
    min / max temperature, total rain, strongest wind, main sky;
  - top: for trails with a track, temperature at the highest point at mid-race;
  - veille: rain of the day before (trails only, shown only when it rained).
Writes weather.json = {"at", "src", "races": {id: [{date, h, j, src, conf?, vig?, start, window, top?, veille?}]}}
(src "rd" = rundata.re, "mn" = MET Norway; conf = forte / moyenne / faible; vig = {c: jaune|orange|rouge, p: [phénomènes]}).
Never fails the workflow: on error the previous file is kept.
"""
import datetime as dt
import json
import re
import sys
import urllib.request

import net  # one honest User-Agent, polite delay, size and time limits on every request

UA = {"User-Agent": "DossardPei/1.0 (+https://dossardpei.re; contact@dossardpei.re)"}
TZ = dt.timezone(dt.timedelta(hours=4))
DAYS = 7


def get(lat, lon, alt=None):
    u = f"https://api.met.no/weatherapi/locationforecast/2.0/complete?lat={lat:.4f}&lon={lon:.4f}" + (f"&altitude={int(alt)}" if alt is not None else "")
    with net.urlopen(urllib.request.Request(u, headers=UA), timeout=30) as r:
        ts = json.load(r)["properties"]["timeseries"]
    out = []
    for t in ts:
        at = dt.datetime.fromisoformat(t["time"].replace("Z", "+00:00")).astimezone(TZ)
        d = t["data"]
        inst = d["instant"]["details"]
        nxt = d.get("next_1_hours") or d.get("next_6_hours") or {}
        span = 1 if "next_1_hours" in d else 6
        out.append({"at": at, "span": span, "t": inst.get("air_temperature"), "w": inst.get("wind_speed"),
                    "g": inst.get("wind_speed_of_gust"), "rain": (nxt.get("details") or {}).get("precipitation_amount", 0.0) or 0.0,
                    "sym": ((nxt.get("summary") or {}).get("symbol_code") or "").split("_")[0]})
    return out


# ---------- rundata.re (main source) ----------
RD = "https://rundata.re/mcp"
RDH = {"content-type": "application/json", "accept": "application/json, text/event-stream"}


def rd_call(tool, args):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": args}}).encode()
    with net.urlopen(urllib.request.Request(RD, data=body, headers=RDH, method="POST"), timeout=40) as r:
        raw = r.read().decode("utf-8", "replace")
    if raw.lstrip().startswith("event:") or raw.lstrip().startswith("data:"):   # answer sent as an event stream
        raw = "".join(l[5:] for l in raw.splitlines() if l.startswith("data:"))
    res = json.loads(raw)["result"]
    if res.get("isError"):
        raise ValueError("rundata : " + res["content"][0]["text"][:120])
    return json.loads(res["content"][0]["text"])


def num(txt):
    m = re.search(r"(-?\d+(?:[.,]\d+)?)", (txt or "").replace("\u00a0", " "))
    return float(m.group(1).replace(",", ".")) if m else None


# sky of rundata (French words) -> MET Norway symbol codes used by the site (icons and words)
SKY = [("orage", "rainandthunder"), ("forte pluie", "heavyrain"), ("pluie forte", "heavyrain"), ("fortes averses", "heavyrainshowers"),
       ("averses faibles", "lightrainshowers"), ("faibles averses", "lightrainshowers"), ("averse", "rainshowers"),
       ("pluie faible", "lightrain"), ("bruine", "lightrain"), ("gouttes", "lightrain"), ("pluie", "rain"), ("brouillard", "fog"),
       ("dans les nuages", "fog"), ("couvert", "cloudy"), ("nuageux", "partlycloudy"), ("voilé", "fair"), ("plutôt dégagé", "fair"),
       ("dégagé", "clearsky"), ("ensoleillé", "clearsky")]


def sky(txt):
    t = (txt or "").lower()
    if "partiellement nuageux" in t or "éclaircies" in t:
        return "partlycloudy"
    for k, v in SKY:
        if k in t:
            return v
    return None


def rd_day(lat, lon, day, today):
    """3-hour steps of one day at a point: [{at, span, t, w, g, rain, sym}], confidence of the day"""
    j = (day - today).days
    quand = "aujourd'hui" if j == 0 else "demain" if j == 1 else f"dans {j} jours"
    p = rd_call("prevision_meteo", {"lieu": f"{lat:.4f}, {lon:.4f}", "quand": quand})
    dm = day.strftime("%d/%m")
    out = []
    for x in p.get("pas_de_3h") or []:
        m = re.search(r"(\d{2}/\d{2})\s+(\d{1,2})\s*h\s*[–-]\s*(\d{1,2})\s*h", (x.get("heures") or "").replace("\u00a0", " "))
        if not m or m.group(1) != dm:
            continue
        t = num(x.get("temperature"))
        rain = 0.0 if "pas de pluie" in (x.get("pluie") or "") else (num(x.get("pluie")) or 0.0)
        v = (x.get("vent") or "").replace("\u00a0", " ")
        g = num(v.split("rafales", 1)[1]) if "rafales" in v else None
        w = num(v.split("rafales", 1)[0]) if "rafales" in v and re.search(r"\d", v.split("rafales", 1)[0]) else None
        if t is None:
            continue
        at = dt.datetime.combine(day, dt.time(int(m.group(2)) % 24), TZ)
        # same units as MET Norway (m/s) so that the rest of the computation does not change
        out.append({"at": at, "span": 3, "t": t, "w": (w or 0) / 3.6, "g": (g / 3.6) if g is not None else None,
                    "rain": rain, "sym": sky(x.get("ciel"))})
    conf = next((d.get("confiance") for d in p.get("jours") or [] if dm in (d.get("jour") or "")), None)
    if len(out) < 4:
        raise ValueError(f"rundata : {len(out)} pas de 3 h pour le {dm}")
    return out, conf


def rd_vigilance():
    """official Météo-France vigilance for the whole island: None when everything is green"""
    v = rd_call("vigilance_meteo", {})
    txt = json.dumps(v, ensure_ascii=False).lower()
    if "tout est vert" in txt and "alerte cyclonique en cours" not in txt.replace("pas d'alerte cyclonique en cours", ""):
        return None
    return v


def rd_vig_at(commune):
    """vigilance of the zone of a commune: {c, p, cyclone?} or None"""
    v = rd_call("vigilance_meteo", {"lieu": commune})
    txt = json.dumps(v, ensure_ascii=False).lower()
    cols = [c for c in ("rouge", "orange", "jaune") if re.search(r"vigilance\s+" + c, txt) or re.search(r'"couleur"\s*:\s*"' + c, txt)]
    ph = [x.get("titre") for x in v.get("suivi_meteo_france") or [] if x.get("titre") and "pas de vigilance" not in (x.get("texte") or "").lower()]
    cyc = v.get("alerte_cyclonique") if v.get("alerte_cyclonique") and "pas d'alerte" not in v.get("alerte_cyclonique", "").lower() else None
    if not cols and not cyc:
        return None
    out = {"c": cols[0] if cols else None, "p": ph[:3]}
    if cyc:
        out["cyclone"] = cyc[:160]
    return out


def hours_of(e):
    """estimated duration (h) of an épreuve"""
    km = float(e.get("km") or 0)
    if not km:
        return 2.0
    effort = km + (e.get("dp") or 0) / 100
    pace = 10 if e.get("type") in ("route", "cross", "jeunes") else 7 if e.get("type") in ("trail", "relais") else 6 if e.get("type") == "marche" else 9
    return max(1.0, min(14.0, effort / pace))


def start_h(r, day):
    hs = []
    for e in r.get("epreuves", []):
        if (e.get("date") or r["date"]) != day or not e.get("h"):
            continue
        try:
            h, m = e["h"].lower().replace("h", ":").split(":")[:2]
            hs.append((int(h), int(m or 0), e))
        except ValueError:
            pass
    if not hs:
        return None
    h, m, _ = min(hs, key=lambda x: (x[0], x[1]))
    longest = max((x[2] for x in hs), key=hours_of)
    return h, m, longest


def track(rid):
    try:
        g = json.load(open(f"gpx/{rid}.json"))
        pts = max(g.get("tracks", []), key=lambda t: len(t.get("pts", [])))["pts"]
        return pts[0], max(pts, key=lambda p: p[2] if len(p) > 2 and p[2] is not None else -1e9)
    except Exception:
        return None, None


def near(fc, when):
    """forecast step covering `when` (the closest earlier step)"""
    best = None
    for s in fc:
        if s["at"] <= when:
            best = s
        else:
            break
    return best or (fc[0] if fc else None)


def due(now, data):
    """when the last forecast is 3 hours old or more (a delayed or skipped run is caught up at the next
    one), or at once when a race of the next 7 days is missing from weather.json"""
    if "--all" in sys.argv:
        return True
    try:
        w = json.load(open("weather.json"))
        have = w.get("races", {})
        if now - dt.datetime.fromisoformat(w["at"]) >= dt.timedelta(hours=2, minutes=50):
            return True
    except Exception:
        return True
    for r in data["races"]:
        if not r.get("hidden") and 0 <= (dt.date.fromisoformat(r["date"]) - now.date()).days <= DAYS and r["id"] not in have:
            return True
    return False


VIG, VIGC = None, {}


def main(now):
    data = json.load(open("data.json"))
    if not due(now, data):
        print("météo : rien à faire à cette heure")
        return
    today = now.date()
    out, calls, rd_calls = {}, 0, 0
    global VIG, VIGC
    VIGC = {}
    try:
        VIG = rd_vigilance(); rd_calls += 1   # one call: is anything not green on the island?
    except Exception as e:
        VIG = None
        print(f"vigilance : indisponible ({e.__class__.__name__})")
    try:
        prev = json.load(open("weather.json")).get("races", {})
    except Exception:
        prev = {}
    for r in data["races"]:
        if r.get("hidden") or not r.get("ll"):
            continue
        days = sorted({e.get("date") or r["date"] for e in r.get("epreuves", [])} | {r["date"]})
        days = [d for d in days if 0 <= (dt.date.fromisoformat(d) - today).days <= DAYS and d <= (r.get("fin") or r["date"]) and d >= r["date"]]
        if not days:
            continue
        p0, top = track(r["id"])
        lat, lon = (p0[0], p0[1]) if p0 and abs(p0[0] - r["ll"][0]) < 0.05 and abs(p0[1] - r["ll"][1]) < 0.05 else r["ll"]
        alt = p0[2] if p0 and len(p0) > 2 and p0[2] is not None and (lat, lon) == (p0[0], p0[1]) else None
        ftop = top and top[2] is not None and alt is not None and top[2] - alt >= 400
        trail = any(e.get("type") == "trail" for e in r.get("epreuves", []))
        # main source: rundata.re, day by day (3-hour steps); any failure -> MET Norway for this race
        RDD = {}
        try:
            for day in days:
                d = dt.date.fromisoformat(day)
                fcd, conf = rd_day(lat, lon, d, today); rd_calls += 1
                ft = rd_day(top[0], top[1], d, today)[0] if ftop else None; rd_calls += ft is not None
                fv = None
                if trail and (d - today).days >= 1:
                    try:
                        fv = rd_day(lat, lon, d - dt.timedelta(days=1), today)[0]; rd_calls += 1
                    except Exception:
                        fv = None
                RDD[day] = (fcd, conf, ft, fv)
        except Exception as e:
            print(f"météo {r['id']} : rundata indisponible ({e.__class__.__name__}), MET Norway en secours")
            RDD = None
        fc = fct = None
        if RDD is None:
            try:
                fc = get(lat, lon, alt); calls += 1
                fct = get(top[0], top[1], top[2]) if ftop else None
                calls += fct is not None
            except Exception as e:
                print(f"météo {r['id']} : {e.__class__.__name__}")
                if r["id"] in prev:   # forecast unavailable this time: the previous one stays
                    out[r["id"]] = prev[r["id"]]
                continue
        res = []
        try:
            for day in days:
                conf = None
                if RDD is not None:
                    fc, conf, fct, fv = RDD[day]
                    if fv:
                        fc = fv + fc   # the day before too (rain of the eve, for trails)
                sh = start_h(r, day)
                h, m, lg = sh if sh else (8, 0, None)
                t0 = dt.datetime.combine(dt.date.fromisoformat(day), dt.time(h, m), TZ)
                dur = hours_of(lg) if lg else 3.0
                t1 = t0 + dt.timedelta(hours=dur)
                s0 = near(fc, t0)
                win = [s for s in fc if t0 - dt.timedelta(hours=s["span"]) < s["at"] <= t1] or [s0]
                temps = [s["t"] for s in win if s["t"] is not None]
                syms = [s["sym"] for s in win if s["sym"]]
                j = (dt.date.fromisoformat(day) - today).days
                item = {"date": day, "h": f"{h:02d}h{m:02d}" if sh else None, "j": j, "src": "rd" if RDD is not None else "mn",
                        "precise": (j <= 2) if RDD is not None else s0["span"] == 1,
                        "start": {"t": round(s0["t"]), "sym": s0["sym"], "w": round((s0["w"] or 0) * 3.6), "rain": round(s0["rain"], 1)},
                        "window": {"hours": round(dur, 1), "tmin": round(min(temps)), "tmax": round(max(temps)),
                                   "rain": round(sum(s["rain"] for s in win), 1),
                                   "w": round(max((s["g"] or s["w"] or 0) for s in win) * 3.6),
                                   "sym": max(set(syms), key=syms.count) if syms else s0["sym"]}}
                if conf:
                    item["conf"] = conf
                if VIG is not None and j <= 1 and r.get("commune"):
                    if r["commune"] not in VIGC:
                        try:
                            VIGC[r["commune"]] = rd_vig_at(r["commune"])
                        except Exception:
                            VIGC[r["commune"]] = None
                    if VIGC[r["commune"]]:
                        item["vig"] = VIGC[r["commune"]]
                if fct:
                    st = near(fct, t0 + (t1 - t0) / 2)
                    item["top"] = {"alt": int(top[2]), "t": round(st["t"])}
                if trail:
                    v0 = t0.replace(hour=0, minute=0) - dt.timedelta(days=1)
                    vr = sum(s["rain"] for s in fc if v0 <= s["at"] < v0 + dt.timedelta(days=1))
                    if vr >= 5:
                        item["veille"] = round(vr)
                res.append(item)
        except Exception as e:   # one race with incomplete data (a missing temperature…) never stops the others
            print(f"météo {r['id']} : {e.__class__.__name__}")
            continue
        out[r["id"]] = res
    if not calls and not rd_calls and any(0 <= (dt.date.fromisoformat(r.get("fin") or r["date"]) - today).days <= DAYS for r in data["races"] if not r.get("hidden") and r.get("ll")):
        print("météo : aucune prévision obtenue, le fichier précédent est gardé")   # MET Norway down: never empty the site's weather
        return
    json.dump({"at": now.isoformat(timespec="minutes"), "src": "rundata.re (Météo-France AROME, ECMWF) ; MET Norway en secours", "races": out},
              open("weather.json", "w"), ensure_ascii=False, separators=(",", ":"))
    print(f"météo : {len(out)} course(s), {rd_calls} appel(s) rundata, {calls} appel(s) MET Norway")


if __name__ == "__main__":
    try:
        main(dt.datetime.now(TZ))
    except Exception as e:
        print(f"météo non traitée ({e.__class__.__name__}: {e})")
    sys.exit(0)
