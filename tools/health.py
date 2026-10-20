"""Health of the sync sources (used by sync_sources.py and health_alarm.py).

state/health.json keeps, per source: etat ok/ko, consecutive failures (capped at SEUIL so a long
outage does not make one commit per hour), first failure date, last error, and the reference
(last healthy) counts. A source fails when it raises, reads 0 of something, or reads less than
EFFONDREMENT x its reference. The file is rewritten only when this content changes.
"""
import datetime as dt
import json

PATH = "state/health.json"
SEUIL = 3            # consecutive failures before the alarm
EFFONDREMENT = 0.5   # below 50 % of the reference count = failure
DERIVE = 0.25        # the reference follows a healthy count only when it moves by more than 25 %
ACCEPTE_APRES = dt.timedelta(hours=48)  # a lasting drop (no error, no zero) becomes the new reference


def load(path=PATH):
    try:
        d = json.load(open(path))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def evaluate(prev, run, now):
    """prev: content of health.json; run: {source: {"metrics": {name: int}, "error": str|None}};
    now: aware datetime. Returns the new content (sources absent from run are kept as they were)."""
    out = {k: dict(v) for k, v in prev.items() if isinstance(v, dict)}
    for src, r in run.items():
        st = dict(out.get(src, {}))
        ref = dict(st.get("ref", {}))
        m = r.get("metrics", {})
        why, drop = r.get("error"), False
        if not why:
            for k, v in m.items():
                if not v:
                    why = f"0 {k} lu(s)"
                    break
                if ref.get(k) and v < EFFONDREMENT * ref[k]:
                    why, drop = f"{k} effondré (< {EFFONDREMENT:.0%} des {ref[k]} habituels)", True
                    break
        if why and drop and st.get("depuis") and st.get("echecs", 0) >= SEUIL:
            try:  # the drop has lasted: accept it as the new normal level
                if now - dt.datetime.fromisoformat(st["depuis"]) > ACCEPTE_APRES:
                    why = None
            except ValueError:
                pass
        if why:
            st.update(etat="ko", echecs=min(st.get("echecs", 0) + 1, SEUIL), erreur=why)
            st.setdefault("depuis", now.isoformat(timespec="minutes"))
        else:
            for k, v in m.items():
                if not ref.get(k) or abs(v - ref[k]) > DERIVE * ref[k] or v < EFFONDREMENT * ref[k]:
                    ref[k] = v
            st = {"etat": "ok", "echecs": 0, "ref": ref, **({"alerte": st["alerte"]} if "alerte" in st else {})}
        if ref and "ref" not in st:
            st["ref"] = ref
        out[src] = st
    return out


def save(state, prev, path=PATH):
    """writes only when the content changed; returns True if written."""
    if state == prev:
        return False
    with open(path, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    return True


def summary(state):
    """short text for the one-line summary: only the failing sources."""
    ko = [f"{s} {v['echecs']}/{SEUIL}" for s, v in sorted(state.items()) if v.get("etat") == "ko"]
    return "santé : " + ", ".join(ko) + " en échec" if ko else ""
