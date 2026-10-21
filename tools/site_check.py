#!/usr/bin/env python3
"""Tests the published site like a visitor, and checks that the automatic updates still run.

site      : opens https://dossardpei.re in a headless browser (Playwright): the page loads without
            script error, shows the right number of races, the map is drawn, data.json is readable.
fraicheur : the hourly sync has succeeded in the last 3 hours, and the published data.json is the
            one of the repository (GitHub Pages not stuck).
Writes a report for tools/alerts.py. Usage: site_check.py <report.json>
"""
import datetime as dt
import json
import os
import sys
import urllib.request

SITE = "https://dossardpei.re/"


def site_problems():
    from playwright.sync_api import sync_playwright
    pb = []
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=4))).date().isoformat()
    data = json.load(open("data.json"))
    want = sum(1 for r in data["races"] if not r.get("hidden") and (r.get("fin") or r["date"]) >= today)
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1366, "height": 900})
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)[:200]))
        try:
            resp = page.goto(SITE + f"?check={int(dt.datetime.now().timestamp())}", wait_until="networkidle", timeout=60000)
            if not resp or resp.status != 200:
                pb.append(f"la page d'accueil répond {resp.status if resp else 'rien'}")
            page.wait_for_timeout(3000)
            n = page.evaluate("() => typeof filtered === 'function' ? filtered().length : -1")
            if n == -1:
                pb.append("le script du site ne s'est pas exécuté")
            elif abs(n - want) > 1:
                pb.append(f"le site affiche {n} courses à venir au lieu de {want}")
            if not page.evaluate("() => !!document.querySelector('#map') && document.querySelectorAll('#map *').length > 50"):
                pb.append("la carte ne s'affiche pas")
            d = page.evaluate("() => fetch('data.json?c=' + Date.now()).then(r => r.ok ? r.json() : null).then(j => j && j.races ? j.races.length : 0).catch(() => 0)")
            if not d:
                pb.append("data.json illisible sur le site")
        except Exception as e:
            pb.append(f"la page ne se charge pas ({e.__class__.__name__})")
        for e in errs[:3]:
            pb.append(f"erreur de script : {e}")
        b.close()
    return pb


def fraicheur_problems():
    pb = []
    repo = os.environ.get("GITHUB_REPOSITORY")
    tok = os.environ.get("GH_TOKEN")
    if repo and tok:
        req = urllib.request.Request(f"https://api.github.com/repos/{repo}/actions/workflows/sync-sources.yml/runs?status=success&per_page=1",
                                     headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"})
        runs = json.load(urllib.request.urlopen(req, timeout=30)).get("workflow_runs", [])
        if runs:
            last = dt.datetime.fromisoformat(runs[0]["updated_at"].replace("Z", "+00:00"))
            age = (dt.datetime.now(dt.timezone.utc) - last).total_seconds() / 3600
            if age > 3:
                pb.append(f"dernière synchro réussie il y a {age:.0f} h ({last:%d/%m %H:%M} UTC)")
        else:
            pb.append("aucune synchro réussie trouvée")
    local = json.load(open("data.json"))
    try:
        live = json.load(urllib.request.urlopen(SITE + f"data.json?c={int(dt.datetime.now().timestamp())}", timeout=30))
        if live.get("updatedAt") != local.get("updatedAt"):
            mt = dt.datetime.fromisoformat(local["updatedAt"])
            if (dt.datetime.now(mt.tzinfo) - mt).total_seconds() > 45 * 60:
                pb.append(f"le site publie encore les données du {live.get('updatedAt')} alors que le dépôt a celles du {local['updatedAt']} (GitHub Pages bloqué ?)")
    except Exception as e:
        pb.append(f"data.json du site injoignable ({e.__class__.__name__})")
    return pb


if __name__ == "__main__":
    rep = {}
    for k, f in (("site", site_problems), ("fraicheur", fraicheur_problems)):
        try:
            rep[k] = f()
        except Exception as e:
            rep[k] = None if k == "site" else [f"contrôle impossible ({e.__class__.__name__})"]
            print(f"{k} : contrôle non fait ({e.__class__.__name__}: {e})")
    print(json.dumps(rep, ensure_ascii=False))
    json.dump(rep, open(sys.argv[1] if len(sys.argv) > 1 else "site_check.json", "w"), ensure_ascii=False)
