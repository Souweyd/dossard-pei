#!/usr/bin/env python3
"""Alerts of the checks (tools/controls.py, tools/site_check.py) as GitHub issues, e-mailed by GitHub.

One issue per kind of check. New problems -> the issue is opened (or commented if already open: one
e-mail per new problem list, never for problems already reported); no more problems -> commented and
closed. Never fails the job. Needs GH_TOKEN and GITHUB_REPOSITORY. Usage: alerts.py <report.json>
"""
import json
import os
import sys
import urllib.request

TITRES = {
    "statut": "Contrôle : statut d'inscription à vérifier",
    "qualite": "Contrôle : incohérence dans les données",
    "liens": "Contrôle : liens morts sur des fiches",
    "site": "Contrôle : dossardpei.re ne fonctionne pas correctement",
    "fraicheur": "Contrôle : la synchro ne tourne plus",
}
INTRO = {
    "statut": "Le site affiche ces courses ouvertes, mais leur page d'inscription indique une fermeture. "
              "Elles s'affichent « À vérifier » sur le site tant que ce n'est pas résolu (corrige dans l'admin si besoin).",
    "qualite": "Le contrôle des données (tools/controls.py) a trouvé :",
    "liens": "Ces liens ne répondent plus (vérification quotidienne) :",
    "site": "Le test du site publié (tools/site_check.py) a échoué :",
    "fraicheur": "La mise à jour automatique semble bloquée :",
}


def github(method, path, body=None):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}{path}", method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {os.environ['GH_TOKEN']}", "Accept": "application/vnd.github+json",
                 "User-Agent": "dossardpei-controls"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def corps(kind, pbs):
    return INTRO[kind] + "\n\n" + "\n".join(f"- {p}" for p in pbs) + \
        "\n\n_Cette issue est mise à jour automatiquement et sera fermée quand tout sera rentré dans l'ordre._"


def sync(report, api=github):
    open_ = {i["title"]: i for i in api("GET", "/issues?state=open&per_page=100") if "pull_request" not in i}
    for kind, pbs in report.items():
        if kind not in TITRES or pbs is None:
            continue
        issue = open_.get(TITRES[kind])
        try:
            if pbs and not issue:
                n = api("POST", "/issues", {"title": TITRES[kind], "body": corps(kind, pbs)})["number"]
                print(f"alerte {kind} : issue #{n} ouverte ({len(pbs)})")
            elif pbs and issue:
                old = issue.get("body") or ""
                new = [p for p in pbs if f"- {p}" not in old]
                if new:
                    api("POST", f"/issues/{issue['number']}/comments", {"body": "Nouveau :\n\n" + "\n".join(f"- {p}" for p in new)})
                if corps(kind, pbs) != old:
                    api("PATCH", f"/issues/{issue['number']}", {"body": corps(kind, pbs)})
            elif not pbs and issue:
                api("POST", f"/issues/{issue['number']}/comments", {"body": "Tout est rentré dans l'ordre. ✅"})
                api("PATCH", f"/issues/{issue['number']}", {"state": "closed"})
                print(f"alerte {kind} : issue #{issue['number']} fermée")
        except Exception as e:
            print(f"alerte {kind} : GitHub injoignable ({e.__class__.__name__}), nouvel essai au prochain passage")


if __name__ == "__main__":
    try:
        sync(json.load(open(sys.argv[1])))
    except FileNotFoundError:
        print("pas de rapport de contrôles")
    except Exception as e:
        print(f"alertes non envoyées ({e.__class__.__name__}: {e})")
    sys.exit(0)
