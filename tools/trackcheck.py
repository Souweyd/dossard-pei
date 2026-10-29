#!/usr/bin/env python3
"""Does a track fit the distances announced by the organiser? Used by tools/tracks.py (a track found on a race
page is published only when it fits; otherwise it waits in state/tracks_pending.json to be checked by hand) and
by tools/digest.py (morning summary: « Tracés à vérifier », also for the tracks already on the site).

A track fits when its measured length is close (± max(1.5 km, 15 %)) to one of:
  - the distance of an épreuve;
  - one leg or one loop written in an épreuve name (« Relais 5 × 3,7 km », « 2 boucles » of a 10 km);
  - the sum of all the tracks of the race (a long race given in several pieces).
Races whose épreuves have no distance are not checked.
"""
import re


def _num(s):
    return float(s.replace(",", "."))


def targets(eps):
    out = []
    for e in eps:
        if not e.get("km"):
            continue
        k = float(e["km"])
        out.append((k, e))
        nom = e.get("nom") or ""
        for m in re.finditer(r"[x×]\s*(\d+(?:[.,]\d+)?)\s*km", nom):   # « 5 × 3,7 km »: one leg
            out.append((_num(m.group(1)), e))
        n = re.search(r"(\d+)\s*(?:boucles?|tours?)", nom + " " + (e.get("note") or ""))   # « 10 km (2 boucles) »: one loop
        if n and int(n.group(1)) > 1:
            out.append((k / int(n.group(1)), e))
    return out


def fits(km, eps, total=None):
    """(True/False/None, closest épreuve); None when nothing can be compared"""
    tg = targets(eps)
    if not tg or not km:
        return None, None
    if total:
        tg = tg + [(k, e) for k, e in tg if abs(k - total) <= max(1.5, .15 * k)]
    best = min(tg, key=lambda x: abs(x[0] - km))
    if abs(best[0] - km) <= max(1.5, .15 * best[0]):
        return True, best[1]
    if total and any(abs(k - total) <= max(1.5, .15 * k) for k, e in tg):   # pieces of one long race
        return True, best[1]
    return False, best[1]


def problems(race, tracks):
    """list of (track, closest épreuve) that do not fit"""
    eps = race.get("epreuves", [])
    total = sum(t.get("km") or 0 for t in tracks) if len(tracks) > 1 else None
    out = []
    for t in tracks:
        ok, e = fits(t.get("km"), eps, total)
        if ok is False:
            out.append((t, e))
    return out
