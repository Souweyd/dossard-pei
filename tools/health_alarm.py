#!/usr/bin/env python3
"""Alarm on the sync sources (run by the hourly workflow, after tools/sync_sources.py).

When a source of state/health.json reaches health.SEUIL consecutive failures, opens ONE GitHub issue
"Alerte synchro : <source> ne répond plus" (GitHub e-mails it to the owner) and marks the source
"alerte" in health.json, so nothing is reopened while it stays down (even if the issue is closed by
hand). When the source is healthy again, comments and closes the issue. Never fails the job.
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


def bilan(src, st, report):
    r = (report.get("run") or {}).get(src, {})
    mets = ", ".join(f"{k} : {v} (habituel {st.get('ref', {}).get(k, '?')})" for k, v in r.get("metrics", {}).items())
    errs = [e for e in report.get("errors", []) if e.split(" (")[0].split()[0] == src.split("_")[0]]
    return "\n".join([
        f"La source **{NOMS.get(src, src)}** est en échec depuis le {st.get('depuis', '?')} "
        f"({health.SEUIL} passages horaires de la synchro consécutifs au moins).",
        "",
        f"- Dernière erreur : `{st.get('erreur', '?')}`",
        f"- Lu au dernier passage ({report.get('at', '?')}) : {mets or 'rien'}",
        f"- Erreurs du passage : {', '.join(errs) if errs else 'aucune exception (lecture vide ou effondrée)'}",
        "",
        "Les données de cette source ne sont plus mises à jour sur dossardpei.re (le reste continue). "
        "Causes probables : site ou API hors service, changement d'adresse ou de structure de la page. "
        "Script : `tools/sync_sources.py` ; état : `state/health.json`.",
        "",
        "Cette issue sera commentée et fermée automatiquement quand la source redeviendra saine.",
    ])


def run(state, report, api=github):
    """acts on the issues and returns the updated state (alerte flags)."""
    state = {k: dict(v) for k, v in state.items()}
    todo_open = [s for s, v in state.items() if v.get("echecs", 0) >= health.SEUIL and not v.get("alerte")]
    todo_close = [s for s, v in state.items() if v.get("etat") == "ok" and v.get("alerte")]
    if not todo_open and not todo_close:
        return state
    issues = {i["title"]: i for i in api("GET", "/issues?state=open&per_page=100") if "pull_request" not in i}
    for s in todo_open:
        try:
            num = (issues.get(titre(s)) or {}).get("number")  # an open one already exists: no duplicate
            if not num:
                num = api("POST", "/issues", {"title": titre(s), "body": bilan(s, state[s], report)})["number"]
                print(f"alarme : issue #{num} ouverte pour {s}")
            state[s]["alerte"] = num
        except Exception as e:
            print(f"alarme : impossible d'ouvrir l'issue pour {s} ({e.__class__.__name__}), nouvel essai dans une heure")
    for s in todo_close:
        try:
            i = issues.get(titre(s))
            if i:
                api("POST", f"/issues/{i['number']}/comments",
                    {"body": f"La source {NOMS.get(s, s)} est de nouveau saine (passage du {report.get('at', '?')}). "
                             "Fermeture automatique."})
                api("PATCH", f"/issues/{i['number']}", {"state": "closed", "state_reason": "completed"})
                print(f"alarme : issue #{i['number']} fermée, {s} rétablie")
            del state[s]["alerte"]
        except Exception as e:
            print(f"alarme : impossible de fermer l'issue de {s} ({e.__class__.__name__}), nouvel essai dans une heure")
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
