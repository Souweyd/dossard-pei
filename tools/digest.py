#!/usr/bin/env python3
"""Daily summary of the small problems (run by the hourly workflow; sends at most once a day).

The big failures already open their own issue (a platform down, mass loss of races, cancellation
spotted). The small ones used to stay in the logs; once a day (first run after 7:00 Réunion time)
they are gathered here and posted as ONE comment on the issue « Résumé quotidien » (GitHub e-mails it
to the owner). Nothing is posted on a day without problem.
Checked:
  - source pages unreadable for 24 h or more (state/todo.json « illisibles », first failure kept here);
  - weather older than 6 h while a race is within 7 days;
  - races of the next 30 days without poster, races (trail) of the next 14 days without track;
  - corrections made by the data guard (state/guard.json) since the last summary;
  - races whose épreuves were not all recognised on their registration page (state/partiels.json).
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
    for r in soon:
        d = (dt.date.fromisoformat(r["date"]) - today).days
        if d <= 30 and not r.get("poster"):
            out.append(f"Sans affiche, dans {d} j : {r['nom']} ({r['date']})")
        if d <= 14 and r["id"] not in data.get("gpx", {}) and any(e.get("type") == "trail" for e in r.get("epreuves", [])):
            out.append(f"Trail sans tracé, dans {d} j : {r['nom']} ({r['date']})")
    for rid, v in load("state/partiels.json", {}).items():   # page read but épreuves not recognised: state not checked
        if rid in races and not races[rid].get("hidden"):
            out.append(f"Épreuves non reconnues sur {v.get('source')} : {races[rid]['nom']} — {', '.join(v.get('epreuves') or [])}"
                       f" (la plateforme dit : {', '.join(v.get('plateforme') or [])}). Statut d'inscription non vérifié.")
    for rid, v in load("state/ecarts.json", {}).items():   # start town different on the organiser's page
        if rid in races and v.get("lieu", {}).get("epingle"):
            out.append(f"Lieu modifié : {races[rid]['nom']} — départ à {v['lieu']['organisateur']}, épingle placée au centre de la commune (lieu exact non trouvé, à ajuster si besoin)")
        elif rid in races and v.get("lieu"):
            out.append(f"Lieu différent : {races[rid]['nom']} — le site dit {v['lieu'].get('site')}, la page de l'organisateur dit {v['lieu'].get('organisateur')} (lieu et épingle à corriger à la main)")
    g = load("state/guard.json", {})
    if g.get("at", "") > st.get("sent_at", "") and (g.get("notes") or g.get("restored")):
        out += [f"Garde-fou : {n}" for n in (g.get("notes") or [])[:10]]
        if g.get("restored"):
            out.append("Garde-fou : data.json a été remis tel que publié (voir l'issue dédiée)")
    return out


def main(now):
    st = load("state/digest.json", {})
    pbs = problems(now, st)
    due = now.hour >= 7 and st.get("sent") != now.date().isoformat()
    if due:
        st["sent"], st["sent_at"] = now.date().isoformat(), now.isoformat(timespec="minutes")
        if pbs and os.environ.get("GH_TOKEN") and os.environ.get("GITHUB_REPOSITORY"):
            owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "")
            body = (f"@{owner} " if owner else "") + f"**{now.strftime('%d/%m/%Y')}** : {len(pbs)} point(s) à regarder.\n\n" + \
                "\n".join(f"- {p}" for p in pbs) + "\n\n_Résumé envoyé une fois par jour, seulement quand il y a quelque chose._"
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
    print(f"résumé : {len(pbs)} point(s){' — envoyé' if st.get('sent') == now.date().isoformat() and due and pbs else ''}")
    for p in pbs:
        print("  -", p)


if __name__ == "__main__":
    try:
        main(dt.datetime.now(TZ))
    except Exception as e:
        print(f"résumé non fait ({e.__class__.__name__}: {e})")
    sys.exit(0)
