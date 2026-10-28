#!/usr/bin/env python3
"""Cuts the detailed map layers used by the race sheets' mini maps into square tiles.

contours100.json (100 m contour lines, ~570 KB) and labels.json (trails, trail names, place names,
~710 KB) cover the whole island. A race sheet shows a small area only, so its mini map now loads
just the tiles it overlaps: mm/<i>_<j>.json, TILE map units wide (map: 1100 x 1013 units).
Each tile: {"c": minor contours path, "t": trails path, "p": places, "n": trail names}.
Lines are cut into short pieces, each written in every tile its box touches (a line crossing a
tile border is drawn whole on both sides). The main map keeps using the full files.
Run again only when contours100.json or labels.json change.
"""
import json
import os
import re
import shutil

TILE = 125
CHUNK = 24   # points per piece


def pieces(d):
    for sub in re.split(r"(?=M)", d):
        pts = re.findall(r"(-?[\d.]+),(-?[\d.]+)", sub)
        if len(pts) < 2:
            continue
        for i in range(0, len(pts) - 1, CHUNK - 1):
            yield pts[i:i + CHUNK]


def tiles_of(pts):
    xs = [float(p[0]) for p in pts]; ys = [float(p[1]) for p in pts]
    for i in range(int(min(xs) // TILE), int(max(xs) // TILE) + 1):
        for j in range(int(min(ys) // TILE), int(max(ys) // TILE) + 1):
            yield f"{i}_{j}"


def main():
    out = {}
    get = lambda k: out.setdefault(k, {"c": [], "t": [], "p": [], "n": []})
    for c in json.load(open("contours100.json")):
        for pts in pieces(c["d"]):
            s = "M" + "L".join(f"{x},{y}" for x, y in pts)
            for k in tiles_of(pts):
                get(k)["c"].append(s)
    lab = json.load(open("labels.json"))
    for pts in pieces(lab["trails"]):
        s = "M" + "L".join(f"{x},{y}" for x, y in pts)
        for k in tiles_of(pts):
            get(k)["t"].append(s)
    # names keep their rank in the whole-island list as last item (the mini map places the most important first)
    for i, p in enumerate(lab["places"]):
        get(f"{int(p[0] // TILE)}_{int(p[1] // TILE)}")["p"].append(p + [i])
    for i, n in enumerate(lab["tnames"]):
        get(f"{int(n[0] // TILE)}_{int(n[1] // TILE)}")["n"].append(n + [i])
    for i in range(1100 // TILE + 1):   # every tile of the map exists, even empty (sea): no « not found » in the browser
        for j in range(1013 // TILE + 1):
            get(f"{i}_{j}")
    shutil.rmtree("mm", ignore_errors=True)
    os.makedirs("mm")
    total = 0
    for k, v in out.items():
        js = json.dumps({"c": "".join(v["c"]), "t": "".join(v["t"]), "p": v["p"], "n": v["n"]}, ensure_ascii=False, separators=(",", ":"))
        open(f"mm/{k}.json", "w", encoding="utf-8").write(js)
        total += len(js)
    print(f"{len(out)} tuiles, {total // 1024} Ko au total, {total // len(out) // 1024} Ko en moyenne")


if __name__ == "__main__":
    main()
