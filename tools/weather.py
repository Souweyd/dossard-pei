#!/usr/bin/env python3
"""Race-day weather for the races of the next 7 days (run by the hourly workflow, every 3 hours).

Source: MET Norway locationforecast 2.0 (free, no key; identification by User-Agent, data under
CC BY 4.0 « MET Norway »). Hourly steps for ~2.5 days, then 6-hourly steps up to 10 days.
For each visible race whose race day is within 7 days, and for each race day of a multi-day event:
  - start: conditions at the start hour, at the start point (altitude of the track when known);
  - window: from the start to the estimated end of the longest épreuve of that day (max 14 h):
    min / max temperature, total rain, strongest wind, main sky;
  - top: for trails with a track, temperature at the highest point at mid-race;
  - veille: rain of the day before (trails only, shown only when it rained).
Writes weather.json = {"at", "src", "races": {id: [{date, h, j, start, window, top?, veille?}]}}.
Never fails the workflow: on error the previous file is kept.
"""
import datetime as dt
import json
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


def main(now):
    data = json.load(open("data.json"))
    if not due(now, data):
        print("météo : rien à faire à cette heure")
        return
    today = now.date()
    out, calls = {}, 0
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
        try:
            fc = get(lat, lon, alt); calls += 1
            fct = get(top[0], top[1], top[2]) if top and top[2] is not None and alt is not None and top[2] - alt >= 400 else None
            calls += fct is not None
        except Exception as e:
            print(f"météo {r['id']} : {e.__class__.__name__}")
            if r["id"] in prev:   # forecast unavailable this time: the previous one stays
                out[r["id"]] = prev[r["id"]]
            continue
        res = []
        try:
            for day in days:
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
                item = {"date": day, "h": f"{h:02d}h{m:02d}" if sh else None, "j": j, "precise": s0["span"] == 1,
                        "start": {"t": round(s0["t"]), "sym": s0["sym"], "w": round((s0["w"] or 0) * 3.6), "rain": round(s0["rain"], 1)},
                        "window": {"hours": round(dur, 1), "tmin": round(min(temps)), "tmax": round(max(temps)),
                                   "rain": round(sum(s["rain"] for s in win), 1),
                                   "w": round(max((s["g"] or s["w"] or 0) for s in win) * 3.6),
                                   "sym": max(set(syms), key=syms.count) if syms else s0["sym"]}}
                if fct:
                    st = near(fct, t0 + (t1 - t0) / 2)
                    item["top"] = {"alt": int(top[2]), "t": round(st["t"])}
                if any(e.get("type") == "trail" for e in r.get("epreuves", [])):
                    v0 = t0.replace(hour=0, minute=0) - dt.timedelta(days=1)
                    vr = sum(s["rain"] for s in fc if v0 <= s["at"] < v0 + dt.timedelta(days=1))
                    if vr >= 5:
                        item["veille"] = round(vr)
                res.append(item)
        except Exception as e:   # one race with incomplete data (a missing temperature…) never stops the others
            print(f"météo {r['id']} : {e.__class__.__name__}")
            continue
        out[r["id"]] = res
    if not calls and any(0 <= (dt.date.fromisoformat(r.get("fin") or r["date"]) - today).days <= DAYS for r in data["races"] if not r.get("hidden") and r.get("ll")):
        print("météo : aucune prévision obtenue, le fichier précédent est gardé")   # MET Norway down: never empty the site's weather
        return
    json.dump({"at": now.isoformat(timespec="minutes"), "src": "MET Norway", "races": out},
              open("weather.json", "w"), ensure_ascii=False, separators=(",", ":"))
    print(f"météo : {len(out)} course(s), {calls} appel(s)")


if __name__ == "__main__":
    try:
        main(dt.datetime.now(TZ))
    except Exception as e:
        print(f"météo non traitée ({e.__class__.__name__}: {e})")
    sys.exit(0)
