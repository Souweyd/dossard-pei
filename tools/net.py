#!/usr/bin/env python3
"""Shared HTTP access for the hourly tools (sync_sources, controls, posters, tracks, triage, weather…).

Every request made through net.urlopen():
  - identifies itself honestly: one User-Agent naming the site and a contact (never a browser's);
  - waits GAP seconds between two requests to the same host (polite to small organiser sites);
  - is read in chunks with a size cap (CAP) and an overall time budget (DEADLINE), so a page that is
    huge or trickles one byte at a time can no longer hold the workflow for hours.
Returns a small response object (read(), status, geturl(), headers; usable with `with` and json.load).
"""
import time
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (compatible; DossardPei/1.0; +https://dossardpei.re; contact@dossardpei.re)"
CAP = 4_000_000      # bytes
DEADLINE = 45        # seconds for one whole request
GAP = 1.0            # seconds between two requests to the same host
_last = {}


class Resp:
    def __init__(self, r, body):
        self.status, self.headers, self._url, self._b, self._p = r.status, r.headers, r.geturl(), body, 0

    def read(self, n=-1):
        if n is None or n < 0:
            n = len(self._b) - self._p
        out = self._b[self._p:self._p + n]
        self._p += len(out)
        return out

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def urlopen(req, data=None, timeout=30):
    if isinstance(req, str):
        req = urllib.request.Request(req)
    req.add_header("User-Agent", UA)   # replaces any other User-Agent
    host = urllib.parse.urlsplit(req.full_url).hostname or ""
    wait = _last.get(host, 0) + GAP - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, data=data, timeout=min(timeout, 30)) as r:
            chunks, size = [], 0
            while True:
                b = r.read1(65536) if hasattr(r, "read1") else r.read(65536)   # returns as soon as some bytes arrive
                if not b:
                    break
                chunks.append(b)
                size += len(b)
                if size > CAP:
                    raise ValueError(f"page trop grande (> {CAP // 1_000_000} Mo)")
                if time.monotonic() - t0 > DEADLINE:
                    raise TimeoutError(f"lecture trop longue (> {DEADLINE} s)")
            return Resp(r, b"".join(chunks))
    finally:
        _last[host] = time.monotonic()
