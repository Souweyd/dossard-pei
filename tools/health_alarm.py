#!/usr/bin/env python3
"""Alarm on the sync sources (run by the hourly workflow, after tools/sync_sources.py).

When a source of state/health.json reaches health.SEUIL consecutive failures, opens ONE GitHub issue
per platform "Alerte synchro : <plateforme> ne répond plus" (GitHub e-mails it to the owner; sources
sportpro, sportpro_pages, sportpro_prix share the sportpro issue, completed without new e-mail) and marks
the source "alerte" in health.json, so nothing is reopened while it stays down (even if the issue is
closed by hand). When all the alerted sources of the platform are healthy again, comments and closes. Never fails the job.
Needs GH_TOKEN and GITHUB_REPOSITORY (both set in the workflow).
"""
import json
import os
import sys
import tempfile
import urllib.request

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import health  # noqa: E402

NOMS = {"utoi": "UTOI (API des inscriptions)", "topchrono": "Top Chrono (API WordPress)",
        "sportpro": "Sportpro (agenda des courses)", "sportpro_pages": "Sportpro (pages des courses)",
        "sportpro_prix": "Sportpro (prix des épreuves)"}


def titre(src):
    return f"Alerte synchro : {src} ne répond plus"


def github(method, path, body=None):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}{path}", method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {os.environ['GH_TOKEN']}", "Accept": "application/vnd.github+json",
                 "User-Agent": "dossardpei-health"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def plateforme(src):
    return src.split("_")[0]


def bilan(p, srcs, state, report):
    """one issue per platform: every failing check of the platform in the same body."""
    out = [f"La plateforme **{p}** ne répond plus correctement ({health.SEUIL} passages horaires de la synchro "
           "consécutifs au moins) :", ""]
    for src in srcs:
        st = state[src]
        r = (report.get("run") or {}).get(src, {})
        mets = ", ".join(f"{k} : {v} (habituel {st.get('ref', {}).get(k, '?')})" for k, v in r.get("metrics", {}).items())
        out += [f"**{NOMS.get(src, src)}** : en échec depuis le {st.get('depuis', '?')}",
                f"- Dernière erreur : `{st.get('erreur', '?')}`",
                f"- Lu au dernier passage ({report.get('at', '?')}) : {mets or 'rien'}", ""]
    errs = [e for e in report.get("errors", []) if e.split(" (")[0].split()[0] == p]
    out += [f"Erreurs du passage : {', '.join(errs) if errs else 'aucune exception (lecture vide ou effondrée)'}", "",
            "Les données de cette plateforme ne sont plus mises à jour sur dossardpei.re (le reste continue) ; "
            "ses courses s'affichent « non vérifiable ». Causes probables : site en maintenance ou hors service, "
            "changement d'adresse ou de structure de la page. Script : `tools/sync_sources.py` ; état : `state/health.json`.", "",
            "Cette issue est mise à jour sans nouvel e-mail si un autre contrôle de la même plateforme tombe, "
            "et sera commentée et fermée automatiquement quand tout redeviendra sain."]
    return "\n".join(out)


def run(state, report, api=github):
    """acts on the issues (one per platform) and returns the updated state (alerte flags)."""
    state = {k: dict(v) for k, v in state.items()}
    groups = {}
    for s in state:
        groups.setdefault(plateforme(s), []).append(s)
    todo = {}
    for p, srcs in groups.items():
        new = [s for s in srcs if state[s].get("echecs", 0) >= health.SEUIL and not state[s].get("alerte")]
        alerted = [s for s in srcs if state[s].get("alerte")]
        close = bool(alerted) and not new and all(state[s].get("etat") == "ok" for s in alerted)
        if new or close:
            todo[p] = (srcs, new, alerted, close)
    if not todo:
        return state
    issues = {i["title"]: i for i in api("GET", "/issues?state=open&per_page=100") if "pull_request" not in i}
    for p, (srcs, new, alerted, close) in todo.items():
        i = issues.get(titre(p))
        try:
            if new:
                failing = [s for s in srcs if state[s].get("etat") == "ko" and (state[s].get("alerte") or s in new)]
                body = bilan(p, failing, state, report)
                if i:   # already reported for this platform: body updated, no new e-mail
                    api("PATCH", f"/issues/{i['number']}", {"body": body})
                    num = i["number"]
                    print(f"alarme : issue #{num} complétée ({', '.join(new)})")
                else:
                    num = api("POST", "/issues", {"title": titre(p), "body": body})["number"]
                    print(f"alarme : issue #{num} ouverte pour {p}")
                for s in new:
                    state[s]["alerte"] = num
            else:
                if i:
                    api("POST", f"/issues/{i['number']}/comments",
                        {"body": f"La plateforme {p} est de nouveau saine (passage du {report.get('at', '?')}). Fermeture automatique."})
                    api("PATCH", f"/issues/{i['number']}", {"state": "closed", "state_reason": "completed"})
                    print(f"alarme : issue #{i['number']} fermée, {p} rétablie")
                for s in alerted:
                    del state[s]["alerte"]
        except Exception as e:
            print(f"alarme : GitHub injoignable pour {p} ({e.__class__.__name__}), nouvel essai dans une heure")
    return state


if __name__ == "__main__":
    try:
        prev = health.load()
        try:
            report = json.load(open(os.path.join(os.environ.get("RUNNER_TEMP") or tempfile.gettempdir(), "health_run.json")))
        except (OSError, ValueError):
            report = {}
        health.save(run(prev, report), prev)
    except Exception as e:
        print(f"alarme non évaluée ({e.__class__.__name__}: {e})")
    sys.exit(0)
