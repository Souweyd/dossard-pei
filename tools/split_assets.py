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
import hashlib
import os
import re
import sys

MIN = 20_000   # bytes: smaller blocks stay inline
KEEP = 3       # builds whose files are kept


def main():
    page = open("index.html", encoding="utf-8").read()
    os.makedirs("assets", exist_ok=True)
    used = set()

    def out(kind, body):
        h = hashlib.sha1(body.encode()).hexdigest()[:10]
        name = f"assets/app.{h}.{kind}"
        if not os.path.exists(name):
            open(name, "w", encoding="utf-8").write(body)
        used.add(os.path.basename(name))
        return name

    def style(m):
        if len(m.group(2)) < MIN:
            return m.group(0)
        # url(...) in a stylesheet is relative to the stylesheet (assets/), not to the page: made absolute
        css = re.sub(r"url\((['\"]?)(?![a-z]+:|/|#)", r"url(\1/", m.group(2))
        return f'<link rel="stylesheet" href="{out("css", css)}">'

    def script(m):
        attrs, body = m.group(1) or "", m.group(2)
        if len(body) < MIN or re.search(r'\b(type|src)\s*=', attrs):
            return m.group(0)
        return f'<script src="{out("js", body)}"></script>'

    page = re.sub(r"<style(\s[^>]*)?>(.*?)</style>", style, page, flags=re.S)
    page = re.sub(r"<script(\s[^>]*)?>(.*?)</script>", script, page, flags=re.S)
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
        if f.startswith("app.") and f not in keep:
            os.remove(f"assets/{f}")
    print(f"index.html : {len(page) // 1024} Ko ; fichiers : {', '.join(sorted(used))}")


if __name__ == "__main__":
    sys.exit(main())
