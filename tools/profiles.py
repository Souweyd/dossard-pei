#!/usr/bin/env python3
"""Mini elevation profiles shown on the race cards: profiles.json = {race id: [48 altitudes]} from the
longest track of each race (gpx/<id>.json, or the points imported in the admin). Run by the hourly
workflow; rewritten only when its content changes."""
import json
import math
import sys


def hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


def main():
    d = json.load(open("data.json"))
    live = {r["id"] for r in d["races"] if not r.get("hidden")}
    out = {}
    for rid, g in sorted((d.get("gpx") or {}).items()):
        if rid not in live:
            continue
        try:
            tracks = json.load(open(g["file"]))["tracks"] if g.get("file") else [{"pts": g["pts"]}]
        except Exception:
            continue
        pts = [p for p in max(tracks, key=lambda t: len(t.get("pts") or []))["pts"] if len(p) > 2]
        if len(pts) < 5:
            continue
        cum = [0.0]
        for a, b in zip(pts, pts[1:]):
            cum.append(cum[-1] + hav(a, b))
        n, j, res = 48, 0, []
        for k in range(n):
            x = cum[-1] * k / (n - 1)
            while j < len(cum) - 2 and cum[j + 1] < x:
                j += 1
            res.append(round(pts[j][2]))
        if max(res) - min(res) >= 3:
            out[rid] = res
    txt = json.dumps(out, separators=(",", ":"))
    try:
        if open("profiles.json").read() == txt:
            return
    except OSError:
        pass
    open("profiles.json", "w").write(txt)
    print(f"profils : {len(out)} courses")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"profils non calculés ({e.__class__.__name__}: {e})")
    sys.exit(0)
