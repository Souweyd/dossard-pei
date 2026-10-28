#!/usr/bin/env python3
"""Safety net on data.json before anything is published (run by the hourly workflow right after the
tools that edit data.json, before the course pages are built and committed).

1. Clean-up, race by race:
   - km / dp written as text ("10 km", "10,5") become numbers; anything else unreadable is removed;
   - links (fiche, page, inscription, affiche, épreuve url) must be http(s): others are removed
     (a « javascript: » link would run in visitors' browsers);
   - a race without id, name or a valid date is put back as it was in the last published version
     (or dropped if it is new), so one bad entry can no longer stop every hourly run.
2. Mass-loss check: if, compared with the last published version (HEAD), more than LOST_MAX races to
   come disappear or become hidden without being cancelled, the whole data.json is put back as
   published, the run goes on with the published data, and an issue is opened (GitHub e-mails it).
Writes state/guard.json (last check). Never fails the workflow.
"""
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.request

TZ = dt.timezone(dt.timedelta(hours=4))
URL_FIELDS = ("fiche", "page", "inscription", "affiche")
LOST_MIN = 3        # races
LOST_SHARE = 0.10   # of the races to come


def num(v):
    if v is None or isinstance(v, (int, float)) and not isinstance(v, bool):
        return v, True
    m = re.fullmatch(r"\s*(\d+(?:[.,]\d+)?)\s*(?:km|m|d\+|m\s*d\+)?\s*", str(v), re.I)
    if not m:
        return None, False
    f = float(m.group(1).replace(",", "."))
    return (int(f) if f == int(f) else f), False


def iso(d):
    try:
        dt.date.fromisoformat(str(d)[:10])
        return len(str(d)) == 10
    except Exception:
        return False


def ok_url(u):
    return isinstance(u, str) and re.match(r"(?i)https?://", u.strip()) is not None


def clean(r, notes):
    rid = r.get("id")
    for f in URL_FIELDS:
        if f in r and r[f] and not ok_url(r[f]):
            notes.append(f"{rid} : lien {f} retiré ({str(r[f])[:40]})"); r.pop(f)
    for e in r.get("epreuves") or []:
        if not isinstance(e, dict):
            continue
        if e.get("url") and not ok_url(e["url"]):
            notes.append(f"{rid} : lien d'épreuve retiré ({str(e['url'])[:40]})"); e.pop("url")
        for f in ("km", "dp"):
            if f in e:
                v, same = num(e[f])
                if not same:
                    notes.append(f"{rid} : {f} « {e[f]} » → {v}")
                    if v is None:
                        e.pop(f)
                    else:
                        e[f] = v
        if e.get("date") and not iso(e["date"]):
            notes.append(f"{rid} : date d'épreuve invalide retirée ({e['date']})"); e.pop("date")
    if r.get("fin") and not iso(r["fin"]):
        notes.append(f"{rid} : date de fin invalide retirée ({r['fin']})"); r.pop("fin")


def valid(r):
    return isinstance(r, dict) and isinstance(r.get("id"), str) and r["id"] and isinstance(r.get("nom"), str) \
        and r["nom"].strip() and iso(r.get("date")) and isinstance(r.get("epreuves", []), list)


def upcoming(races, today):
    return {r["id"]: r for r in races if valid(r) and not r.get("hidden") and (r.get("fin") or r["date"]) >= today}


def issue(title, body):
    tok, repo = os.environ.get("GH_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    if not tok or not repo:
        return
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/issues", method="POST",
                                 data=json.dumps({"title": title, "body": body}).encode(),
                                 headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json",
                                          "User-Agent": "dossardpei-guard"})
    urllib.request.urlopen(req, timeout=30).read()


def save_report(report):
    """state/guard.json only when its content changes (no hourly commit for a timestamp)"""
    try:
        old = json.load(open("state/guard.json"))
    except Exception:
        old = {}
    if {k: v for k, v in old.items() if k != "at"} != {k: v for k, v in report.items() if k != "at"}:
        json.dump(report, open("state/guard.json", "w"), ensure_ascii=False, indent=1)


def main(now):
    today = now.date().isoformat()
    data = json.load(open("data.json", encoding="utf-8"))
    try:
        head = json.loads(subprocess.run(["git", "show", "HEAD:data.json"], capture_output=True, check=True).stdout)
    except Exception:
        head = None
    notes, report = [], {"at": now.isoformat(timespec="minutes")}
    before = {r.get("id"): r for r in (head or {}).get("races", []) if isinstance(r, dict)}
    races = []
    for r in data.get("races", []):
        if isinstance(r, dict):
            clean(r, notes)
        if valid(r):
            races.append(r)
        elif isinstance(r, dict) and r.get("id") in before and valid(before[r["id"]]):
            notes.append(f"{r.get('id')} : fiche invalide, version publiée remise"); races.append(before[r["id"]])
        else:
            notes.append(f"course invalide écartée : {str(r)[:80]}")
    data["races"] = races
    lost = []
    if head:
        was, now_up = upcoming(head.get("races", []), today), {r["id"]: r for r in races}
        for rid, r in was.items():
            n = now_up.get(rid)
            if n is None and rid not in (data.get("alias") or {}):
                lost.append(f"{r['nom']} ({r['date']}) : retirée")
            elif n is not None and n.get("hidden") and not n.get("annule"):
                lost.append(f"{r['nom']} ({r['date']}) : masquée")
        if len(lost) > max(LOST_MIN, LOST_SHARE * len(was)):
            report.update(restored=True, lost=lost)
            json.dump(head, open("data.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
            print(f"::error::garde-fou : {len(lost)} courses à venir perdues d'un coup, data.json remis tel que publié")
            try:
                issue("Garde-fou : data.json remis tel que publié",
                      f"La mise à jour automatique aurait retiré ou masqué **{len(lost)} courses à venir** d'un coup "
                      f"(seuil : plus de {max(LOST_MIN, round(LOST_SHARE * len(was)))}). Les données publiées ont été gardées.\n\n"
                      + "\n".join(f"- {x}" for x in lost[:40]) + "\n\nÀ vérifier : une source a peut-être changé de format.")
            except Exception as e:
                print(f"issue non créée ({e.__class__.__name__})")
            save_report(report)
            return
    report.update(restored=False, notes=notes[:50], lost=lost)
    if notes:
        json.dump(data, open("data.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    save_report(report)
    print(f"garde-fou : {len(notes)} correction(s), {len(lost)} course(s) à venir en moins")


if __name__ == "__main__":
    try:
        main(dt.datetime.now(TZ))
    except Exception as e:
        print(f"garde-fou non exécuté ({e.__class__.__name__}: {e})")
    sys.exit(0)
