#!/usr/bin/env python3
"""Posters for the races that have none (run by the hourly workflow, free): first on the race's own
pages (Sportpro « Affiches », chronometrage.com media.dag-system image, Top Chrono og:image,
Klikego « affiche » image), then on WeRun.

WeRun hosts the organisers' posters of many Réunion races ("Affiche-<name>.jpg"; its logos are
"Logo-..." files and are never taken). For each visible race to come without a poster (UTOI races keep
the UTOI logo; a poster set by the owner in the admin is never touched), the WeRun event of the same day
whose name shares a word is looked up; its image is used only if the file is named "affiche" and is a
portrait. Writes posters/<id>.webp (420 px) and posters/<id>_lg.webp (1100 px max) and sets affiche,
poster, poster_lg in data.json. A race without result is tried again after 24 h (state/posters.json).
"""
import datetime as dt
import html
import io
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request

import net  # one honest User-Agent, polite delay, size and time limits on every request

UA = {"User-Agent": "Mozilla/5.0 (DossardPei sync; +https://dossardpei.re)"}
STOP = {"de", "du", "des", "la", "le", "les", "l", "d", "et", "a", "au", "aux", "en", "sur", "trail", "course",
        "courses", "foulees", "foulee", "reunion", "edition", "run", "the", "of"}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def words(s):
    return {w for w in norm(s).split() if w not in STOP and not w.isdigit() and len(w) > 2}


def get(u, raw=False):
    for i in range(2):
        try:
            with net.urlopen(urllib.request.Request(u, headers=UA), timeout=30) as r:
                b = r.read()
            return b if raw else b.decode("utf-8", "replace")
        except Exception:
            if i:
                raise


def find(r):
    """WeRun poster URL for race r, or None"""
    ws = sorted(words(r["nom"]), key=len, reverse=True)
    if not ws:
        return None
    q = ws[0]   # one word: WordPress search is accent-sensitive and needs every word
    u = ("https://werun.world/wp-json/tribe/events/v1/events?" +
         urllib.parse.urlencode({"search": q, "start_date": r["date"], "end_date": r["date"] + " 23:59:59", "per_page": 20}))
    try:
        evs = json.loads(get(u)).get("events", [])
    except Exception:
        return None
    for e in evs:
        if (e.get("start_date") or "")[:10] != r["date"] or not (words(html.unescape(e.get("title", ""))) & words(r["nom"])):
            continue
        im = e.get("image") or {}
        url, w, h = im.get("url") or "", im.get("width") or 0, im.get("height") or 0
        if "affiche" in url.rsplit("/", 1)[-1].lower() and h >= 1.1 * w > 0:
            return url
    return None


ORG = [   # poster on the race's own pages (organiser or registration platform)
    (r"sportpro\.re/", r"""(?:https?://www\.sportpro\.re/|/)?res/images/Affiches/[^"'<>\s]+?\.(?:jpe?g|png|webp)"""),
    (r"chronometrage\.com/events/", r"""https://media\.dag-system\.com/[^"'<>\s]+?\.(?:jpe?g|png|webp)"""),
    (r"topchrono\.run/", r"""<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)"""),
    (r"klikego\.com/", r"""https?://[^"'<>\s]*affiche[^"'<>\s]*?\.(?:jpe?g|png|webp)"""),
]


def find_org(r):
    """poster URL found on the race's own pages, or None (ignores Sportpro's « _defaut » placeholder)"""
    for u in dict.fromkeys(x for x in (r.get("fiche"), r.get("inscription"), r.get("page")) if x):
        for site, pat in ORG:
            if not re.search(site, u):
                continue
            try:
                page = get(u)
            except Exception:
                continue
            for m in re.finditer(pat, page, re.I):
                img = html.unescape(m.group(1) if m.groups() else m.group(0))
                if "_defaut" in img.lower() or "logo" in img.rsplit("/", 1)[-1].lower():
                    continue
                return urllib.parse.urljoin(u, img)
    return None


def main(today, now):
    from PIL import Image
    data = json.load(open("data.json"))
    try:
        ov = json.load(open("state/overrides.json"))
        locked = {k: set(v.get("fields", [])) for k, v in ov.get("overrides", {}).items() if isinstance(v, dict)}
    except Exception:
        locked = {}
    try:
        tried = json.load(open("state/posters.json"))
    except Exception:
        tried = {}
    changed, added = False, []
    for r in data["races"]:
        if r.get("hidden") or (r.get("fin") or r["date"]) < today or r.get("poster") or r.get("source") == "utoi":
            continue
        if re.search(r"utoi", (r.get("inscription") or "") + (r.get("org") or ""), re.I):
            continue
        if {"poster", "poster_lg", "affiche"} & locked.get(r["id"], set()):
            continue
        if tried.get(r["id"], "") > (now - dt.timedelta(hours=24)).isoformat():
            continue
        tried[r["id"]] = now.isoformat(timespec="minutes")
        url, org = find_org(r), True
        if not url:
            url, org = find(r), False
        if not url:
            continue
        try:
            im = Image.open(io.BytesIO(get(url, raw=True)))
            im.load()
            if im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGBA")
                bg = Image.new("RGB", im.size, "white")
                bg.paste(im, mask=im.split()[-1])
                im = bg
            else:
                im = im.convert("RGB")
            if im.width > 4 * im.height or (org and min(im.size) < 300):   # banner, or icon-sized image
                continue
            for name, width, q in ((f"posters/{r['id']}.webp", 420, 78), (f"posters/{r['id']}_lg.webp", 1100, 82)):
                k = min(1, width / im.width)
                im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS).save(name, "WEBP", quality=q)
        except Exception as e:
            print(f"affiche {r['id']} : image illisible ({e.__class__.__name__})")
            continue
        r.update(affiche=url, poster=f"posters/{r['id']}.webp", poster_lg=f"posters/{r['id']}_lg.webp")
        tried.pop(r["id"], None)
        changed = True
        added.append(r["nom"])
    tried = {k: v for k, v in tried.items() if v > (now - dt.timedelta(days=7)).isoformat()}
    json.dump(tried, open("state/posters.json", "w"), ensure_ascii=False, indent=0, sort_keys=True)
    if changed:
        json.dump(data, open("data.json", "w"), ensure_ascii=False, separators=(",", ":"))
    print(f"affiches ajoutées : {', '.join(added) if added else 'aucune'}")


if __name__ == "__main__":
    try:
        n = dt.datetime.now(dt.timezone(dt.timedelta(hours=4)))
        main(n.date().isoformat(), n)
    except Exception as e:
        print(f"affiches non traitées ({e.__class__.__name__}: {e})")
    sys.exit(0)
