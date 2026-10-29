#!/usr/bin/env python3
"""Daily summary of the small problems (run by the hourly workflow; sends at most once a day).

The big failures already open their own issue (a platform down, mass loss of races, cancellation
spotted). The small ones used to stay in the logs; once a day (first run after 7:00 Réunion time)
they are gathered here and posted as ONE comment on the issue « Résumé quotidien » (GitHub e-mails it
to the owner). Nothing is posted on a day without problem.
Checked:
  - source pages unreadable for 24 h or more (state/todo.json « illisibles », first failure kept here);
  - weather older than 6 h while a race is within 7 days;
  - « Infos manquantes »: races of the next 90 days with a missing price, start time, distance, climb,
    registration link, poster / track (30 days) or a registration state no platform confirms;
  - corrections made by the data guard (state/guard.json) since the last summary;
  - races whose épreuves were not all recognised on their registration page (state/partiels.json);
  - tracks whose length does not fit the announced distances (held back, or already on the site).
State: state/digest.json {"sent": date, "seen": {url: first failure}}. Never fails the workflow.
"""
import datetime as dt
import json
import os
import sys
import urllib.request

TZ = dt.timezone(dt.timedelta(hours=4))
TITLE = "Résumé quotidien Dossard Péi"


def load(p, d):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


def github(method, path, body=None):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}{path}", method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {os.environ['GH_TOKEN']}", "Accept": "application/vnd.github+json",
                 "User-Agent": "dossardpei-digest"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def problems(now, st):
    today = now.date()
    out = []
    data = load("data.json", {"races": []})
    races = {r["id"]: r for r in data["races"]}
    todo = load("state/todo.json", {})
    seen = st.setdefault("seen", {})
    bad = {x["url"]: x for x in todo.get("illisibles", [])}
    for u in list(seen):
        if u not in bad:
            seen.pop(u)
    for u, x in bad.items():
        first = seen.setdefault(u, now.isoformat(timespec="minutes"))
        h = (now - dt.datetime.fromisoformat(first)).total_seconds() / 3600
        if h >= 24:
            out.append(f"Page illisible depuis {int(h // 24)} j : {x.get('id')} ({x.get('erreur')}) — {u}")
    soon = [r for r in data["races"] if not r.get("hidden") and r.get("date") and 0 <= (dt.date.fromisoformat(r["date"]) - today).days]
    try:
        w = load("weather.json", {})
        age = (now - dt.datetime.fromisoformat(w["at"])).total_seconds() / 3600
        if age > 6 and any((dt.date.fromisoformat(r["date"]) - today).days <= 7 for r in soon):
            out.append(f"Météo pas mise à jour depuis {int(age)} h (MET Norway)")
    except Exception:
        out.append("Météo : fichier weather.json illisible")
    for rid, v in load("state/partiels.json", {}).items():   # page read but épreuves not recognised: state not checked
        if rid in races and not races[rid].get("hidden"):
            out.append(f"Épreuves non reconnues sur {v.get('source')} : {races[rid]['nom']} — {', '.join(v.get('epreuves') or [])}"
                       f" (la plateforme dit : {', '.join(v.get('plateforme') or [])}). Statut d'inscription non vérifié.")
    ec = load("state/ecarts.json", {})
    for cat, items in ec.items():   # differences with the organisers' pages (tools/sync_sources.py)
        if not isinstance(items, dict):
            continue
        for rid, v in items.items():
            if rid not in races or races[rid].get("hidden"):
                continue
            nom = races[rid]["nom"]
            if cat == "epingle":
                out.append(f"Lieu modifié : {nom} — départ à {v.get('commune')}, épingle placée au centre de la commune (lieu exact non trouvé, à ajuster si besoin)")
            elif cat.startswith("lieu_"):
                out.append(f"Lieu différent : {nom} — le site dit {v.get('site')}, la plateforme dit {v.get('organisateur')} (position non trouvée, à corriger à la main)")
            elif cat == "texte":
                out.append(f"À vérifier sur la page de l'organisateur : {nom} — " + " ; ".join(v))
    # tracks: found but held back because their length does not fit the announced distances, or already on the
    # site and no longer fitting (the organiser changed a distance, or the track is not the right one)
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import trackcheck
        for rid, v in load("state/tracks_pending.json", {}).items():
            if rid in races and not races[rid].get("hidden"):
                out.append(f"Tracé trouvé mais pas publié : {races[rid]['nom']} — " + " ; ".join(v.get("ecarts", [])) + f" — {v.get('src')} (dis à Claude de le publier s'il est bon)")
        for rid, gg in data.get("gpx", {}).items():
            r = races.get(rid)
            if not r or r.get("hidden") or (r.get("fin") or r.get("date") or "") < today.isoformat():
                continue
            for t, e in trackcheck.problems(r, gg.get("tracks", [])):
                out.append(f"Tracé à vérifier : {r['nom']} — {t.get('nom')} mesure {str(t.get('km')).replace('.', ',')} km, {e.get('nom')} est annoncé à {str(e.get('km')).replace('.', ',')} km — {gg.get('src', '')}")
    except Exception as e:
        out.append(f"Contrôle des tracés non fait ({e.__class__.__name__})")
    g = load("state/guard.json", {})
    if g.get("at", "") > st.get("sent_at", "") and (g.get("notes") or g.get("restored")):
        out += [f"Garde-fou : {n}" for n in (g.get("notes") or [])[:10]]
        if g.get("restored"):
            out.append("Garde-fou : data.json a été remis tel que publié (voir l'issue dédiée)")
    return out


MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
HORIZON = 90   # days: races further away are left out (their details are rarely out yet)


def manquants(now):
    """infos missing on the sheets of the races of the next HORIZON days, one line per race with the link to
    look at: price, start time, distance, climb (trails), registration link, poster (30 days), track (trails,
    30 days), registration state that no platform confirms. Full / closed races: only what still matters."""
    today = now.date()
    data = load("data.json", {"races": []})
    verif = load("verif.json", {}).get("races", {})
    out = []
    for r in sorted(data["races"], key=lambda r: r.get("date") or ""):
        if r.get("hidden") or not r.get("date"):
            continue
        dd = dt.date.fromisoformat(r["date"])
        d = (dd - today).days
        if d < 0 or d > HORIZON:
            continue
        eps = r.get("epreuves", [])
        shut = r.get("complet") or r.get("clos") or (eps and all(e.get("complet") or e.get("clos") for e in eps))
        miss = []
        def eps_without(cond):
            names = [e.get("nom", "?") for e in eps if cond(e)]
            return names if len(names) < len(eps) or len(eps) == 1 else ["toutes"]
        if not shut:
            n = eps_without(lambda e: not e.get("prix") and not (e.get("complet") or e.get("clos")))
            if n: miss.append("tarif (" + ", ".join(n) + ")")
        n = eps_without(lambda e: not e.get("h"))
        if n: miss.append("heure de départ (" + ", ".join(n) + ")")
        n = eps_without(lambda e: not e.get("km") and e.get("type") not in ("jeunes",) and not e.get("sans_km"))   # sans_km: no distance given by the organiser (by category…)
        if n: miss.append("distance (" + ", ".join(n) + ")")
        n = eps_without(lambda e: not e.get("dp") and e.get("type") == "trail")
        if n: miss.append("D+ (" + ", ".join(n) + ")")
        if not r.get("inscription") and not shut:
            miss.append("lien d'inscription")
        if d <= 30 and not r.get("poster"):
            miss.append("affiche")
        if d <= 30 and r["id"] not in data.get("gpx", {}) and any(e.get("type") == "trail" for e in eps):
            miss.append("tracé")
        recent = (r.get("verifie_le") or "") >= (today - dt.timedelta(days=7)).isoformat()   # state checked by hand in the last 7 days
        if not shut and verif.get(r["id"]) == "nv" and not recent:
            miss.append("état des inscriptions (aucune plateforme lisible : ouvert ? complet ?)")
        if miss:
            # where the details are: the Chrono Run technical sheet (and its règlement) rather than the chronometrage registration page
            link = r.get("page") if "chronorun974" in (r.get("page") or "") else (r.get("inscription") or r.get("fiche") or r.get("page") or "")
            out.append(f"{dd.day} {MOIS[dd.month - 1]} — **{r['nom']}** : " + " · ".join(miss) + (f" — {link}" if link else ""))
    return out


def main(now):
    st = load("state/digest.json", {})
    pbs = problems(now, st)
    mq = manquants(now)
    due = now.hour >= 7 and st.get("sent") != now.date().isoformat()
    if due:
        st["sent"], st["sent_at"] = now.date().isoformat(), now.isoformat(timespec="minutes")
        if (pbs or mq) and os.environ.get("GH_TOKEN") and os.environ.get("GITHUB_REPOSITORY"):
            owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "")
            body = (f"@{owner} " if owner else "") + f"**{now.strftime('%d/%m/%Y')}**"
            if pbs:
                body += f" : {len(pbs)} point(s) à regarder.\n\n" + "\n".join(f"- {p}" for p in pbs)
            if mq:
                body += f"\n\n### Infos manquantes ({len(mq)} course{'s' if len(mq) > 1 else ''} des {HORIZON} prochains jours)\n" \
                        "_À compléter si tu trouves l'info : envoie-la (ou une capture) à Claude._\n\n" + "\n".join(f"- {m}" for m in mq)
            body += "\n\n_Résumé envoyé une fois par jour, seulement quand il y a quelque chose._"
            try:
                found = [i for i in github("GET", "/issues?state=open&per_page=100") if i.get("title") == TITLE]
                num = found[0]["number"] if found else github("POST", "/issues", {"title": TITLE, "body": "Les petits problèmes du jour, réunis en un message (un commentaire par jour)."})["number"]
                github("POST", f"/issues/{num}/comments", {"body": body})
            except Exception as e:
                print(f"résumé non envoyé ({e.__class__.__name__})")
                st.pop("sent", None)
    old = load("state/digest.json", None)
    if old != st:
        json.dump(st, open("state/digest.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
    print(f"résumé : {len(pbs)} point(s), {len(mq)} course(s) avec infos manquantes{' — envoyé' if st.get('sent') == now.date().isoformat() and due and (pbs or mq) else ''}")
    for p in pbs + mq:
        print("  -", p)


if __name__ == "__main__":
    try:
        main(dt.datetime.now(TZ))
    except Exception as e:
        print(f"résumé non fait ({e.__class__.__name__}: {e})")
    sys.exit(0)
