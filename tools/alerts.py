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
    "annulation": "Contrôle : annulation ou report repéré",
}
JOURNAL = "Journal : changements chez les organisateurs"
INTRO = {
    "statut": "Le site affiche ces courses ouvertes, mais leur page d'inscription indique une fermeture. "
              "Elles s'affichent « À vérifier » sur le site tant que ce n'est pas résolu (corrige dans l'admin si besoin).",
    "qualite": "Le contrôle des données (tools/controls.py) a trouvé :",
    "liens": "Ces liens ne répondent plus (vérification quotidienne) :",
    "site": "Le test du site publié (tools/site_check.py) a échoué :",
    "fraicheur": "La mise à jour automatique semble bloquée :",
    "annulation": "Ces courses sont encore affichées sur le site, mais leur page mentionne une annulation ou un report. "
                  "À vérifier : si c'est confirmé, la mise à jour Claude la masquera (ou corrige dans l'admin).",
}


def github(method, path, body=None):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}{path}", method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {os.environ['GH_TOKEN']}", "Accept": "application/vnd.github+json",
                 "User-Agent": "dossardpei-controls"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def who():   # mentioning the owner makes GitHub e-mail him (participating notification), whatever his watch settings
    o = os.environ.get("GITHUB_REPOSITORY_OWNER") or os.environ.get("GITHUB_REPOSITORY", "/").split("/")[0]
    return f"@{o} " if o else ""


def corps(kind, pbs):
    return who() + INTRO[kind] + "\n\n" + "\n".join(f"- {p}" for p in pbs) + \
        "\n\n_Cette issue est mise à jour automatiquement et sera fermée quand tout sera rentré dans l'ordre._"


def info(report, open_, api):
    """journal of changes and new races: one comment on a permanent issue (one e-mail), weekly recap: own issue"""
    parts = []
    if report.get("nouveautes"):
        parts.append("**Nouvelles courses repérées chez les organisateurs** (elles seront ajoutées au prochain passage de la mise à jour Claude, 8h57 / 13h57 / 18h57) :\n" + "\n".join(f"- {x}" for x in report["nouveautes"]))
    if report.get("journal"):
        parts.append("**Changements sur le site** :\n" + "\n".join(f"- {x}" for x in report["journal"]))
    try:
        if parts:
            issue = open_.get(JOURNAL)
            num = issue["number"] if issue else api("POST", "/issues", {"title": JOURNAL, "body": "Fil des changements repérés automatiquement (un commentaire par passage qui a trouvé quelque chose). Laisse cette issue ouverte."})["number"]
            api("POST", f"/issues/{num}/comments", {"body": who() + "\n\n" + "\n\n".join(parts)})
        rc = report.get("recap")
        if rc:
            n = api("POST", "/issues", {"title": rc["titre"], "body": who() + "\n\n" + rc["corps"]})["number"]
            api("PATCH", f"/issues/{n}", {"state": "closed"})
            print(f"récapitulatif envoyé (#{n})")
    except Exception as e:
        print(f"journal non envoyé ({e.__class__.__name__})")


def sync(report, api=github):
    open_ = {i["title"]: i for i in api("GET", "/issues?state=open&per_page=100") if "pull_request" not in i}
    info(report, open_, api)
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
                    api("POST", f"/issues/{issue['number']}/comments", {"body": who() + "Nouveau :\n\n" + "\n".join(f"- {p}" for p in new)})
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
