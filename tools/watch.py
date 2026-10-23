#!/usr/bin/env python3
"""Watch over the data, after each hourly sync (all free on GitHub Actions).

- nouveautes : races listed by the organisers' platforms that the site does not have yet
               (Sportpro agenda, UTOI API, Chrono Run list, Top Chrono pages). Each one is reported
               once (state/nouveautes.json); the Claude update adds it at its next run.
- annulations: "événement annulé / reporté" written on the registration or info page of a race
               still shown on the site (every 3 hours).
- journal    : what changed on the site since the previous version (races added / removed,
               closed, full, date or time moved), kept 60 days in state/journal.json.
- recap      : on Monday morning, the summary of the week, sent by e-mail.
"""
import datetime as dt
import html
import json
import re

CANCEL = re.compile(r"(?i)\b(?:[ée]v[ée]nement|course|[ée]preuve|manifestation|[ée]dition|trail|rando(?:nn[ée]e)?)\s+(?:est\s+|a\s+[ée]t[ée]\s+)?(annul[ée]e?s?|report[ée]e?s?)\b")
HEDGE = re.compile(r"(?i)droit|peut|pourr|en cas|si |sera\s+|serait|conditions|rembours|intemp|m[ée]t[ée]o")


def load(path, default):
    try:
        return json.load(open(path))
    except Exception:
        return default


def save_if_changed(path, obj):
    old = load(path, None)
    if old != obj:
        json.dump(obj, open(path, "w"), ensure_ascii=False, indent=0)


def plain(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", s, flags=re.S)))


# ---------- new races ----------
def known_keys(data):
    txt = json.dumps(data.get("races", []), ensure_ascii=False) + json.dumps(data.get("alias", {}))
    return txt


def nouveautes(data, found, state_path="state/nouveautes.json", check=None):
    """found: {source: [(key, label, url)]} as listed by the platforms during this run.
    Returns the lines to report (each key once). A source seen for the first time with more than
    15 unknown entries is taken as the starting point (old pages), without report."""
    st = load(state_path, {})
    known = known_keys(data)
    out = []
    for src, items in found.items():
        seen = set(st.get(src, []))
        new = [(k, lab, u) for k, lab, u in items if k not in seen and k not in known and (u or "") not in known]
        if src not in st and len(new) > 15:
            st[src] = sorted({k for k, _, _ in items})
            continue
        for k, lab, u in new:
            if check and src in check and not check[src](u):   # not a race to come in La Réunion: remembered, not reported
                continue
            out.append(f"**{lab}** — {src} : {u}")
        st[src] = sorted(seen | {k for k, _, _ in items})
    save_if_changed(state_path, st)
    return out


# ---------- cancellations ----------
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def _shown_date(r, txt):
    """the text gives the (new) date the site already shows for this race"""
    try:
        y, mo, d = (int(x) for x in r["date"].split("-"))
    except Exception:
        return False
    low = txt.lower()
    return MOIS[mo - 1] in low and str(y) in low and re.search(rf"(?<!\d){d}(?:er)?(?!\d)", low) is not None


def annulations(data, today, fetch):
    out = []
    for r in data.get("races", []):
        if r.get("hidden") or (r.get("fin") or r.get("date") or "") < today:
            continue
        for u in [x for x in dict.fromkeys([r.get("inscription"), r.get("fiche")]) if x and x.startswith("http")]:
            if "sportpro.re/courses/" in u:      # Sportpro pages: handled by the sync itself (title / presentation)
                continue
            try:
                t = plain(fetch(u)[2])
            except Exception:
                continue
            for m in CANCEL.finditer(t):
                before = t[max(0, m.start() - 45):m.start()]
                if HEDGE.search(before + t[m.end():m.end() + 25]):
                    continue
                if m.group(1).lower().startswith("report") and _shown_date(r, t[m.start():m.end() + 200]):
                    continue   # postponed to the date already shown on the site: nothing to do
                ctx = t[max(0, m.start() - 70):m.end() + 50].strip()
                out.append(f"**{r['nom']}** ({r['date']}) : « {ctx} » — {u}")
                break
            else:
                continue
            break
    return out


# ---------- journal ----------
def _state(r, today):
    if r.get("complet"):
        return "complet"
    if r.get("clos") or (r.get("limite") and r["limite"] < today):
        return "clos"
    return "ouvert"


def diff(prev, cur, today, now):
    if not prev:
        return []
    ev, P = [], {r["id"]: r for r in prev.get("races", []) if not r.get("hidden")}
    C = {r["id"]: r for r in cur.get("races", []) if not r.get("hidden")}
    alias = cur.get("alias") or {}
    at = now.isoformat(timespec="minutes")
    for i, r in C.items():
        if i not in P:
            if not any(a in P for a, b in alias.items() if b == i):   # not just the result of a merge
                ev.append({"at": at, "t": "ajout", "id": i, "nom": r["nom"], "date": r["date"]})
            continue
        p = P[i]
        if p.get("date") != r.get("date"):
            ev.append({"at": at, "t": "date", "id": i, "nom": r["nom"], "de": p.get("date"), "a": r.get("date")})
        hp = {e.get("nom"): e.get("h") for e in p.get("epreuves", [])}
        for e in r.get("epreuves", []):
            if e.get("nom") in hp and hp[e["nom"]] and e.get("h") and hp[e["nom"]] != e["h"]:
                ev.append({"at": at, "t": "heure", "id": i, "nom": f"{r['nom']} – {e['nom']}", "de": hp[e["nom"]], "a": e["h"]})
        sp, sc = _state(p, today), _state(r, today)
        if sp != sc and sc != "ouvert":
            ev.append({"at": at, "t": sc, "id": i, "nom": r["nom"], "date": r["date"]})
        elif sp != sc:
            ev.append({"at": at, "t": "réouvert", "id": i, "nom": r["nom"], "date": r["date"]})
    for i, p in P.items():
        if i not in C and i not in alias and (p.get("fin") or p.get("date") or "") >= today:
            ev.append({"at": at, "t": "retrait", "id": i, "nom": p["nom"], "date": p.get("date")})
    return ev


def journal_add(events, now, path="state/journal.json"):
    j = load(path, [])
    limit = (now - dt.timedelta(days=60)).isoformat()
    j = [e for e in j if e.get("at", "") >= limit] + events
    save_if_changed(path, j)
    return j


LIB = {"ajout": "Nouvelle course", "retrait": "Course retirée", "date": "Date modifiée", "heure": "Heure modifiée",
       "complet": "Complète", "clos": "Inscriptions closes", "réouvert": "Inscriptions rouvertes"}


def line(e):
    if e["t"] in ("date", "heure"):
        return f"{LIB[e['t']]} : **{e['nom']}** ({e['de']} → {e['a']})"
    return f"{LIB.get(e['t'], e['t'])} : **{e['nom']}** ({e.get('date', '')})"


# ---------- weekly recap ----------
def recap(data, journal, today, now, open_alerts=0):
    since = (now - dt.timedelta(days=7)).isoformat()
    week = [e for e in journal if e.get("at", "") >= since]
    races = [r for r in data.get("races", []) if not r.get("hidden") and (r.get("fin") or r["date"]) >= today]
    end = (dt.date.fromisoformat(today) + dt.timedelta(days=7)).isoformat()
    closing = sorted((r["limite"], r["nom"]) for r in races if r.get("limite") and today <= r["limite"] <= end and not r.get("complet") and not r.get("clos"))
    soon = sorted((r["date"], r["nom"], r["commune"]) for r in races if r["date"] <= end)
    incompl = [r["nom"] for r in races if not r.get("poster")]
    notrk = [r["nom"] for r in races if r["id"] not in (data.get("gpx") or {})]
    noh = [r["nom"] for r in races if not any(e.get("h") for e in r.get("epreuves", []))]
    sec = lambda t, xs: f"### {t}\n" + ("\n".join(f"- {x}" for x in xs) if xs else "_rien_") + "\n"
    by = lambda t: [line(e) for e in week if e["t"] == t]
    body = "\n".join([
        f"**{len(races)} courses à venir** sur dossardpei.re.\n",
        sec("Ajoutées cette semaine", by("ajout")),
        sec("Retirées", by("retrait")),
        sec("Devenues complètes ou closes", by("complet") + by("clos")),
        sec("Dates ou heures modifiées", by("date") + by("heure")),
        sec("Courses des 7 prochains jours", [f"{d[8:]}/{d[5:7]} · {n} ({c})" for d, n, c in soon]),
        sec("Clôtures des inscriptions dans les 7 jours", [f"{d[8:]}/{d[5:7]} · {n}" for d, n in closing]),
        sec("Fiches sans affiche", incompl[:15]),
        sec("Fiches sans tracé", notrk[:15]),
        sec("Fiches sans horaire", noh[:15]),
        f"Alertes ouvertes : {open_alerts}.",
    ])
    return {"titre": f"Récapitulatif de la semaine du {dt.date.fromisoformat(today):%d/%m/%Y}", "corps": body}
