#!/usr/bin/env python3
"""Moves the site's big inline style and script out of index.html into cacheable files.

index.html is built as one self-contained page (the Claude artifact needs it that way). For the public
site, the large <style> block and the large application <script> are written to
assets/app.<hash>.css / assets/app.<hash>.js and referenced from the page. Every course page
(/course/<id>/, built from index.html by gen_pages.py) then points to the same files, so a visitor who
opens a shared race link and then the home page downloads the application only once.
The file name changes with the content (hash), so a new version is never hidden by the cache.
Small inline blocks, JSON data (snapshot, structured data) and analytics stay in the page.
Run on the repository root after index.html is written (gh_sync), before gen_pages.py.
"""
import base64
import hashlib
import os
import re
import shutil
import subprocess
import sys

MIN = 20_000   # bytes: smaller blocks stay inline
KEEP = 3       # builds whose files are kept
# esbuild (minifier): $ESBUILD, else on the PATH; without it the files are written unminified
ESBUILD = os.environ.get("ESBUILD") or shutil.which("esbuild")
# fonts hosted by the site (/fonts/, SIL Open Font License) instead of Google Fonts: their @font-face rules
# (fonts/fonts.css) open the style sheet; a font file is only downloaded by a page that uses it
FONTS = open("fonts/fonts.css", encoding="utf-8").read() if os.path.exists("fonts/fonts.css") else ""
# Content-Security-Policy of the public pages (meta tag): what the site loads and where it sends data.
# GoatCounter (visits), Web3Forms (contact form), jsDelivr (three.js for the 3D view), IGN Géoplateforme (3D imagery);
# images may come from the organisers' sites. The inline sky script is allowed by its hash (added below).
CSP = ("default-src 'self'; script-src 'self' https://gc.zgo.at https://cdn.jsdelivr.net{hashes}; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data: blob: https:; font-src 'self'; "
       "connect-src 'self' https://dossardpei.goatcounter.com https://api.web3forms.com https://cdn.jsdelivr.net https://data.geopf.fr; "
       "frame-src https://api.web3forms.com; form-action https://api.web3forms.com; worker-src 'self' blob:; "
       "object-src 'none'; base-uri 'self'; upgrade-insecure-requests")


def minify(body, kind):
    if not ESBUILD:
        return body
    try:
        r = subprocess.run([ESBUILD, f"--loader={kind}", "--minify", "--charset=utf8", "--log-level=error"] + (["--target=es2020"] if kind == "js" else []),
                           input=body.encode(), capture_output=True, timeout=120)
        if r.returncode == 0 and r.stdout:
            return r.stdout.decode()
        print(f"esbuild ({kind}) : {r.stderr.decode()[:300]}", file=sys.stderr)
    except Exception as e:
        print(f"esbuild ({kind}) : {e}", file=sys.stderr)
    return body


def main():
    page = open("index.html", encoding="utf-8").read()
    # entrées vers le jeu « Une histoire de dossard » (pastille, carte du Scroll, pied de page) : jeu/promo.js
    if "/jeu/promo.js" not in page:
        page = page.rstrip("\n") + '\n<script src="/jeu/promo.js" defer></script>\n'
    os.makedirs("assets", exist_ok=True)
    used = set()

    def out(kind, body, prefix="app"):
        h = hashlib.sha1(body.encode()).hexdigest()[:10]
        name = f"assets/{prefix}.{h}.{kind}"
        if not os.path.exists(name):
            open(name, "w", encoding="utf-8").write(body)
        used.add(os.path.basename(name))
        return name

    def style(m):
        if len(m.group(2)) < MIN:
            return m.group(0)
        # url(...) in a stylesheet is relative to the stylesheet (assets/), not to the page: made absolute
        css = re.sub(r"url\(\s*(['\"]?)([^'\")]*)", lambda u: u.group(0) if re.match(r"[a-z]+:|/|#", u.group(2), re.I) or not u.group(2)
                     else f"url({u.group(1)}/{u.group(2)}", m.group(2))
        return f'<link rel="stylesheet" href="{out("css", minify(FONTS + css, "css"))}">'

    def script(m):
        attrs, body = m.group(1) or "", m.group(2)
        if len(body) < MIN or re.search(r'\b(type|src)\s*=', attrs):
            return m.group(0)
        # the contour lines of the map (DEM, ~160 KB) become a separate file, fetched only when a map is shown
        def dem(d):
            return 'const DEM = {"contours":[],"src":"/' + out("json", d.group(1), "dem") + '"};'
        body = re.sub(r'^const DEM = (\{"contours":.*?\});$', dem, body, count=1, flags=re.M)
        # the commune outlines (MAP) stay in the script, and are also written as plain JSON for the
        # social-media scripts (social/core.py), which cannot read them once the script is minified
        mm = re.search(r'^const MAP = (\{"W":.*?\});$', body, flags=re.M)
        if mm:
            open("assets/map.json", "w", encoding="utf-8").write(mm.group(1))
        return f'<script src="{out("js", minify(body, "js"))}"></script>'

    page = re.sub(r"<style(\s[^>]*)?>(.*?)</style>", style, page, flags=re.S)
    page = re.sub(r"<script(\s[^>]*)?>(.*?)</script>", script, page, flags=re.S)
    # no call to Google Fonts (the fonts are in the style sheet, served by the site)
    page = re.sub(r'<link rel="(preconnect|stylesheet)" href="https://fonts\.(googleapis|gstatic)\.com[^"]*"[^>]*>\n?', "", page)
    # Content-Security-Policy: inline scripts that run (not JSON data) are allowed by their hash
    hashes = ""
    for m in re.finditer(r"<script(\s[^>]*)?>(.*?)</script>", page, re.S):
        attrs = m.group(1) or ""
        if m.group(2).strip() and not re.search(r'\b(src|type)\s*=', attrs):
            hashes += " 'sha256-" + base64.b64encode(hashlib.sha256(m.group(2).encode()).digest()).decode() + "'"
    page = re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]*>\n?', "", page)
    page = page.replace("<base href=\"/\">", f'<meta http-equiv="Content-Security-Policy" content="{CSP.format(hashes=hashes)}">\n<base href="/">', 1)
    open("index.html", "w", encoding="utf-8").write(page)
    # older versions are kept a little (pages cached by browsers for a few minutes still point to them):
    # the files of the last KEEP builds stay, older ones are removed
    hist = [l.split() for l in open("assets/versions.txt").read().splitlines() if l.strip()] if os.path.exists("assets/versions.txt") else []
    cur = sorted(used)
    if not hist or hist[-1] != cur:
        hist.append(cur)
    hist = hist[-KEEP:]
    open("assets/versions.txt", "w").write("".join(" ".join(v) + "\n" for v in hist))
    keep = {f for v in hist for f in v}
    for f in os.listdir("assets"):
        if (f.startswith("app.") or f.startswith("dem.")) and f not in keep:
            os.remove(f"assets/{f}")
    print(f"index.html : {len(page) // 1024} Ko ; fichiers : {', '.join(sorted(used))}")


if __name__ == "__main__":
    sys.exit(main())
