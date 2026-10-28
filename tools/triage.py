#!/usr/bin/env python3
"""Hourly triage for the Claude update (run by the GitHub workflow, free).

The Claude update (3 times a day) used to fetch every source itself just to see whether anything
had changed. This script does that watch every hour instead:
  - every active source of data.json (auto != false, actif != false), plus the registration page
    of each race still « À venir » (avenir: true, no opening date);
  - the page text is reduced (no scripts, styles or tags, volatile bits such as clock times,
    « il y a … », counters removed) and fingerprinted;
  - state/watch.json keeps, per URL, the fingerprint and the time it last changed; a new content
    counts only once it is seen on two runs in a row (some pages shuffle or rotate items);
  - Sportpro, UTOI, Top Chrono and Chrono Run are not watched here: tools/sync_sources.py already
    reports their new races (issue n° 2).
state/ack.json ({"at": ...}) is written by the Claude update when it has processed the list.
state/todo.json lists what changed since that time:
  {"at", "since", "rien": bool, "sources": [{id, url, changed}], "avenir": [{id, url, changed}],
   "illisibles": [{id, url, erreur}]}
A page that cannot be read here is listed in « illisibles »: the Claude update reads only those
itself (with its own fingerprints, state/sources.json). « rien » ignores them.
Never fails the workflow.
"""
import datetime as dt
import hashlib
import html
import json
import re
import sys
import urllib.request

import net  # one honest User-Agent, polite delay, size and time limits on every request

UA = {"User-Agent": "Mozilla/5.0 (DossardPei sync; +https://dossardpei.re)", "Accept-Language": "fr-FR,fr;q=0.9"}
TZ = dt.timezone(dt.timedelta(hours=4))
# sources whose new races are already found by tools/sync_sources.py (issue n° 2 candidates): not watched here
BY_SYNC = {"sportpro", "utoi", "topchrono", "chronorun"}
NOISE = [
    r"\b\d{1,2}\s?[:h]\s?\d{2}(?::\d{2})?\b",                      # clock times
    r"(?i)il y a \d+\s*\w+|\b\d+\s*(?:min|minutes?|heures?|h|jours?|j)\s+(?:ago|restants?)\b",
    r"(?i)\b\d+\s*(?:inscrits?|participants?|places?\s+restantes?|vues?|views?|j'aime|likes?|commentaires?)\b",
    r"(?i)(?:copyright|©)\s*\d{4}", r"\b[0-9a-f]{16,}\b", r"(?i)nonce[^ ]*",
]


def text_of(page):
    """the page's text lines, without volatile bits, sorted: a list shown in a different order
    (several races on the same day are shuffled at each load on some sites) is not a change"""
    s = re.sub(r"<(script|style|noscript|svg|template)\b.*?</\1>|<!--.*?-->", " ", page, flags=re.S | re.I)
    s = re.sub(r"(?i)<(br|/p|/div|/li|/h\d|/tr|/td|/th|/a|/span|/article|/section)\b[^>]*>", "\n", s)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    for p in NOISE:
        s = re.sub(p, " ", s)
    lines = {re.sub(r"\s+", " ", x).strip() for x in s.split("\n")}
    return "\n".join(sorted(x for x in lines if len(x) > 1))


def fetch(u):
    with net.urlopen(urllib.request.Request(u, headers=UA), timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def load(p, default):
    try:
        return json.load(open(p))
    except Exception:
        return default


def main(now):
    data = json.load(open("data.json"))
    watch = load("state/watch.json", {})
    ack = load("state/ack.json", {}).get("at") or ""
    targets = []
    for s in data.get("sources", []):
        if s.get("id") in BY_SYNC:
            continue
        if s.get("auto") is False or s.get("actif") is False or s.get("deleted") or not s.get("url"):
            continue
        targets.append(("source", s.get("id") or s["url"], s["url"]))
    for r in data.get("races", []):
        if r.get("hidden") or not r.get("avenir") or r.get("ouverture"):
            continue
        u = r.get("inscription") or r.get("page")
        if u:
            targets.append(("avenir", r["id"], u))
    stamp = now.isoformat(timespec="minutes")
    out = {"sources": [], "avenir": [], "illisibles": []}
    seen = set()
    done = {}
    for kind, ident, u in targets:
        if u in done:   # same page as a source and as an « à venir » race: read once
            if done[u] and watch[u]["changed"] > ack and ack:
                out["sources" if kind == "source" else "avenir"].append({"id": ident, "url": u, "changed": watch[u]["changed"]})
            continue
        seen.add(u); done[u] = False
        try:
            t = text_of(fetch(u))
            if len(t) < 200:
                raise ValueError("page presque vide")
            h = hashlib.sha256(t.encode()).hexdigest()
        except Exception as e:
            err = e.__class__.__name__ + (f" {e.code}" if hasattr(e, "code") else "")
            out["illisibles"].append({"id": ident, "url": u, "erreur": err})
            continue
        w = watch.get(u)
        if not w:
            watch[u] = {"h": h, "at": stamp, "changed": ack or stamp}   # first sight: not a change
        elif w.get("h") == h:
            w.pop("pending", None); w.pop("since", None)
        elif w.get("pending") == h or (w.get("since") and now - dt.datetime.fromisoformat(w["since"]) >= dt.timedelta(hours=24)):
            # the new content is seen twice in a row (a real change, not a flicker), or the page has kept
            # changing for 24 h (some pages never show the same text twice): reported either way
            watch[u] = {"h": h, "at": stamp, "changed": stamp}
        else:
            w["pending"] = h
            w.setdefault("since", stamp)
        done[u] = True
        if watch[u]["changed"] > ack and ack:
            out["sources" if kind == "source" else "avenir"].append({"id": ident, "url": u, "changed": watch[u]["changed"]})
    watch = {u: v for u, v in watch.items() if u in seen}
    # « rien »: nothing changed among the pages read here (the unreadable ones are checked by the Claude update itself)
    todo = {"at": stamp, "since": ack, "rien": not (out["sources"] or out["avenir"]), **out}
    json.dump(watch, open("state/watch.json", "w"), ensure_ascii=False, indent=0, sort_keys=True)
    old = load("state/todo.json", {})
    if {k: v for k, v in old.items() if k != "at"} != {k: v for k, v in todo.items() if k != "at"}:   # no commit when nothing moved
        json.dump(todo, open("state/todo.json", "w"), ensure_ascii=False, indent=1)
    print(f"tri : {len(out['sources'])} source(s) changée(s), {len(out['avenir'])} « à venir » changée(s), {len(out['illisibles'])} illisible(s)")


if __name__ == "__main__":
    try:
        main(dt.datetime.now(TZ))
    except Exception as e:
        print(f"tri non fait ({e.__class__.__name__}: {e})")
    sys.exit(0)
