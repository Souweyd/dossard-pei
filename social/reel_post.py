"""Reel motion design des posts du fil (1080x1920, bruitages, sans musique) : même sélection de courses que le carrousel du jour.
  python3 social/reel_post.py theme JOUR    → mercredi : le thème de la semaine
  python3 social/reel_post.py region JOUR   → vendredi : une région (zoom sur ses communes)
  python3 social/reel_post.py mois JOUR     → le 1er : les courses du mois (l'île s'allume course après course)
Déroulé : pastille + étiquette à la couleur du type + titre sur l'île floutée (image de couverture à 1,2 s), la carte se précise
(zoom sur la région pour « region »), un point par course dans l'ordre des dates avec sa fiche en bas, puis le total et le logo.
Sortie : social/out/reel/reel-<type>-<JOUR>.mp4 et …-couverture.jpg ; affiche « rien » s'il n'y a pas de quoi faire un reel."""
import sys, re, calendar, datetime as D
from core import load, upcoming, week_index, dist_label, MAP, P_xy, _same, REGIONS, REGION_ORDER, ROOT, SOC, JOURS_C, MOIS, MOIS_C
import nouveau as N
import rec, sfx, picto
from gen import THEMES

OUT = SOC / 'out' / 'reel'
W, H = 1080, 1920
INK, TEAL, SURF, MUTED = N.INK, N.TEAL, N.SURF, N.MUTED
from meteo import SEA
ICON = {'gros-dp': 'theme-mont', 'longues': 'theme-mont', 'rando': 'theme-mont', 'relais': 'theme-duo', 'marmailles': 'theme-duo'}


def select(kind, ref, races):
    """Même choix que gen.py (build_mardi / build_jeudi / build_mois). → dict(tag, title, sub, sel, icon, communes) ou None"""
    if kind == 'theme':
        horizon = upcoming(races, ref, ref + D.timedelta(days=70)); k0 = week_index(ref) % len(THEMES)
        for k in range(len(THEMES)):
            t = THEMES[(k0 + k) % len(THEMES)]; s = [r for r in horizon if t['pred'](r)]
            if len(s) >= 3:
                return dict(tag='Le thème de la semaine', title=t['short'], sub='ces 10 prochaines semaines', sel=s[:30], icon=ICON.get(t['id'], 'theme-shoe'), communes=None)
        return None
    if kind == 'region':
        k0 = week_index(ref) % len(REGION_ORDER)
        for weeks in (6, 10):
            for k in range(len(REGION_ORDER)):
                name, communes = REGIONS[REGION_ORDER[(k0 + k) % len(REGION_ORDER)]]
                s = [r for r in upcoming(races, ref + D.timedelta(days=1), ref + D.timedelta(days=7 * weeks)) if r['commune'] in communes]
                if len(s) >= 3:
                    return dict(tag='Près de chez toi', title=f"Courir dans {name}", sub=f'ces {weeks} prochaines semaines', sel=s[:30], icon='region', communes=communes)
        return None
    y, m = ref.year, ref.month
    s = upcoming(races, D.date(y, m, 1), D.date(y, m, calendar.monthrange(y, m)[1]))
    return dict(tag='Les courses du mois', title=f'{MOIS[m - 1].capitalize()} {y}', sub=f'en {MOIS[m - 1]}', sel=s[:40], icon='mois', communes=None) if s else None


def rtype(r):
    t = (r.get('_main') or {}).get('type')
    return t if t in N.TCOL else next((x for x in ('trail', 'route', 'relais', 'multisport', 'cross', 'marche', 'jeunes') if x in r['_types']), 'autre')


def page(kind, ref, races):
    S = select(kind, ref, races)
    if not S:
        return None, 0
    sel = S['sel']; n = len(sel); M = MAP(); E = N.esc; F = N.F
    bg, fg = picto.TAG[kind]
    # ---- final framing : whole island, or the region's communes
    AX, AY, AW, AH = 540, 850, 940, 860                      # centre and size of the map area on screen
    if S['communes']:
        bb = [N.bbox(c) for c in S['communes']]; x0, y0, x1, y1 = min(b[0] for b in bb), min(b[1] for b in bb), max(b[2] for b in bb), max(b[3] for b in bb)
        KF = min(AW / (x1 - x0), AH / (y1 - y0), 3.2 * 1000 / M['W']); cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    else:
        KF = 980 / M['W']; cx, cy = M['W'] / 2, M['H'] / 2
    k0 = 1000 / M['W']
    cam = lambda k, wx, wy, sx, sy: f'translate({sx - wx * k:.1f}px,{sy - wy * k:.1f}px) scale({k:.4f})'
    # ---- pins (screen position at the final framing) ; several races at the same place are spread on a small circle
    import math
    P, seen = [], {}
    for r in sel:
        mx, my = P_xy(*r['ll']); px, py = AX + (mx - cx) * KF, AY + (my - cy) * KF
        key = (round(px / 26), round(py / 26)); j = seen.get(key, 0); seen[key] = j + 1
        if j:
            a = j * 2.4; px += 30 * math.sqrt(j) * math.cos(a); py += 30 * math.sqrt(j) * math.sin(a)
        P.append((min(W - 40, max(40, px)), min(AY + AH / 2 + 40, max(AY - AH / 2 - 40, py))))
    T0 = 3.3; STEP = min(.55, 8.5 / n); TS = T0 + n * STEP + .35; DUR = TS + 4.0
    p = lambda t: f'{t / DUR * 100:.2f}%'
    d = lambda t: f'animation-delay:{t:.2f}s'
    pins, cards = [], []
    for i, r in enumerate(sel):
        t = T0 + i * STEP; col = N.TCOL.get(rtype(r), N.TCOL['autre']); dt = r['_d']
        pins.append(f'<div class="pin one" style="left:{P[i][0]:.0f}px;top:{P[i][1]:.0f}px;--c:{col};{d(t)}"></div><div class="ring one" style="left:{P[i][0]:.0f}px;top:{P[i][1]:.0f}px;--c:{col};{d(t)}"></div>')
        km = dist_label(r); info = f"{E(r['commune'])}{' · ' + E(km) if km else ''}"
        t1 = T0 + (i + 1) * STEP if i < n - 1 else TS
        cards.append(f'''<div class="cd one" style="{d(t)}"><div class="cdo one" style="{d(t1)}"><i style="background:{col}"></i>
 <div class="tx"><div class="dt">{JOURS_C[dt.weekday()].capitalize()} {dt.day} {MOIS_C[dt.month - 1] if n > 1 else ''} · {E(N.TLAB.get(rtype(r), 'Course'))}</div><div class="nm s">{E(r['nom'])}</div><div class="in">{info}</div></div>
 <div class="ct s">{i + 1}<small>/{n}</small></div></div></div>''')
    if S['communes']:
        dim = ''.join(f'<path d="{c["d"]}"/>' for c in M['communes'] if not _same(c['nom'], S['communes']))
        hl = ''.join(f'<path vector-effect="non-scaling-stroke" d="{c["d"]}"/>' for c in M['communes'] if _same(c['nom'], S['communes']))
        over = f'<g class="dim anim" fill="#06202e">{dim}</g><g fill="none" stroke="#fff" stroke-width="3.5" stroke-linejoin="round">{hl}</g>'
    else:
        over = '<g fill="none" stroke="#fff" stroke-opacity=".6" stroke-width="1.5">' + ''.join(f'<path vector-effect="non-scaling-stroke" d="{c["d"]}"/>' for c in M['communes']) + '</g>'
    nfs = 92 if len(S['title']) <= 18 else (78 if len(S['title']) <= 26 else 64)
    html = f'''<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:S;font-weight:800;src:url('{F}/SairaCondensed-800.woff2')}}
@font-face{{font-family:I;font-weight:400;src:url('{F}/inter-latin-400-normal.woff2')}}
@font-face{{font-family:I;font-weight:600;src:url('{F}/inter-latin-600-normal.woff2')}}
@font-face{{font-family:I;font-weight:700;src:url('{F}/inter-latin-700-normal.woff2')}}
*{{box-sizing:border-box;margin:0;padding:0}} html,body{{width:{W}px;height:{H}px;overflow:hidden;background:#083b5a}}
body{{font-family:I,sans-serif;color:{INK};position:relative}} .s{{font-family:S,sans-serif;font-weight:800}}
.anim{{animation-duration:{DUR}s;animation-fill-mode:both;animation-timing-function:linear}}
.one{{animation-fill-mode:both;animation-timing-function:linear}}
#lens{{position:absolute;inset:0;background:{SEA};animation-name:lens}}
@keyframes lens{{0%,{p(1.4)}{{filter:blur(22px) saturate(.8)}} {p(1.4)}{{animation-timing-function:ease-out}} {p(2.6)},100%{{filter:blur(0) saturate(1)}}}}
#world{{position:absolute;left:0;top:0;width:{M['W']}px;height:{M['H']}px;transform-origin:0 0;animation-name:cam}}
@keyframes cam{{0%{{transform:{cam(k0 * .96, M['W'] / 2, M['H'] / 2, 540, 900)}}} {p(1.5)}{{transform:{cam(k0, M['W'] / 2, M['H'] / 2, 540, 900)};animation-timing-function:cubic-bezier(.6,0,.25,1)}} {p(3.0)},100%{{transform:{cam(KF, cx, cy, AX, AY)}}}}}
#world img{{position:absolute;left:0;top:0;width:{M['W']}px;height:{M['H']}px}} #world svg{{position:absolute;left:0;top:0;overflow:visible}}
.dim{{animation-name:dim}} @keyframes dim{{0%,{p(1.6)}{{opacity:0}} {p(2.8)},100%{{opacity:.6}}}}
#tag{{position:absolute;left:0;right:0;top:0;display:flex;flex-direction:column;align-items:center;transform-origin:50% 0;animation-name:tag}}
#tag .t{{background:{bg};color:{fg};font-size:84px;letter-spacing:1px;padding:10px 44px 14px;border-radius:22px;box-shadow:0 18px 40px rgba(0,0,0,.35);line-height:1}}
#tag .n{{margin-top:22px;max-width:980px;background:{SURF};color:{INK};font-size:{nfs}px;line-height:1;text-align:center;padding:12px 40px 16px;border-radius:22px;box-shadow:0 18px 40px rgba(0,0,0,.3);animation-name:nm}}
@keyframes tag{{0%,{p(.25)}{{transform:translateY(700px) scale(.5);opacity:0}} {p(.25)}{{animation-timing-function:cubic-bezier(.3,1.6,.5,1)}}
  {p(.8)},{p(1.5)}{{transform:translateY(700px) scale(1);opacity:1}} {p(1.5)}{{animation-timing-function:cubic-bezier(.6,0,.2,1)}} {p(2.5)},100%{{transform:translateY(150px) scale(.66);opacity:1}}}}
@keyframes nm{{0%,{p(.55)}{{opacity:0;transform:translateY(30px)}} {p(.55)}{{animation-timing-function:cubic-bezier(.2,.9,.3,1)}} {p(1.0)},100%{{opacity:1;transform:none}}}}
{picto.badge_css(p)}
.pin{{position:absolute;width:46px;height:46px;margin:-23px 0 0 -23px;border-radius:50%;background:var(--c);border:7px solid #fff;box-shadow:0 4px 12px rgba(0,0,0,.55);animation:pop .45s both}}
@keyframes pop{{0%{{opacity:0;transform:scale(.1)}} 55%{{opacity:1;transform:scale(1.5)}} 100%{{opacity:1;transform:scale(1)}}}}
.ring{{position:absolute;width:38px;height:38px;margin:-19px 0 0 -19px;border-radius:50%;border:6px solid #fff;animation:ring .8s both}}
@keyframes ring{{0%{{opacity:0;transform:scale(.6)}} 15%{{opacity:.9}} 100%{{opacity:0;transform:scale(4.2)}}}}
.cd{{position:absolute;left:50px;right:50px;top:1370px;height:216px;animation:cin .22s both}} @keyframes cin{{0%{{opacity:0;transform:translateY(40px) scale(.96)}} 100%{{opacity:1;transform:none}}}}
.cdo{{position:absolute;inset:0;background:{SURF};border-radius:30px;box-shadow:0 22px 46px rgba(4,20,30,.45);display:flex;align-items:center;overflow:hidden;animation:cout .12s both}} @keyframes cout{{0%{{opacity:1}} 100%{{opacity:0}}}}
.cdo i{{width:22px;align-self:stretch;flex:none}} .cdo .tx{{flex:1;min-width:0;padding:0 26px 4px 30px}}
.dt{{font-weight:700;font-size:34px;color:{TEAL}}} .nm{{font-size:66px;line-height:1.06;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}} .in{{font-weight:600;font-size:34px;color:{MUTED};white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.ct{{flex:none;padding:0 34px 0 0;font-size:84px;line-height:1;color:{INK}}} .ct small{{font-size:42px;color:{MUTED}}}
#sum{{position:absolute;left:0;right:0;top:1350px;display:flex;flex-direction:column;align-items:center;gap:18px;animation-name:sum}}
@keyframes sum{{0%,{p(TS + .1)}{{opacity:0;transform:scale(.5)}} {p(TS + .1)}{{animation-timing-function:cubic-bezier(.3,1.6,.5,1)}} {p(TS + .6)},100%{{opacity:1;transform:none}}}}
#sum .b{{background:{bg};color:{fg};font-size:120px;line-height:1;padding:10px 50px 18px;border-radius:28px;box-shadow:0 20px 44px rgba(0,0,0,.4)}}
#sum .l{{background:{SURF};font-weight:700;font-size:36px;white-space:nowrap;padding:10px 30px 12px;border-radius:18px;box-shadow:0 14px 30px rgba(0,0,0,.3)}}
#foot{{position:absolute;left:0;right:0;top:1650px;display:flex;justify-content:center;animation-name:foot}}
@keyframes foot{{0%,{p(TS + .8)}{{opacity:0;transform:translateY(30px)}} {p(TS + 1.3)},100%{{opacity:1;transform:none}}}}
#foot .b{{display:flex;align-items:center;gap:18px;background:#fff;border:5px solid {INK};border-radius:999px;padding:10px 36px 10px 14px;box-shadow:0 16px 30px rgba(4,20,30,.3)}}
#foot .b img{{width:84px;display:block}} #foot .b div{{font:800 46px/1 S,sans-serif}} #foot .b small{{display:block;font:700 26px I,sans-serif;color:{TEAL};margin-top:3px}}
</style></head><body>
<div id="lens" class="anim"><div id="world" class="anim"><img src="{N.OCEAN}"><img src="{N.island()}">
 <svg width="{M['W']}" height="{M['H']}" viewBox="0 0 {M['W']} {M['H']}">{over}</svg></div></div>
{''.join(pins)}{''.join(cards)}
<div id="tag" class="anim">{picto.badge(S['icon'])}<div class="s t">{E(S['tag'])}</div><div class="s n anim">{E(S['title'])}</div></div>
<div id="sum" class="anim"><div class="s b">{n} course{'s' if n > 1 else ''}</div><div class="l">{E(S['sub'])} · détail dans le carrousel</div></div>
<div id="foot" class="anim"><div class="b"><img src="{N.LOGO}"><div>Dossard Péi<small>dossardpei.re</small></div></div></div>
</body></html>'''
    page.n = n; page.title = S['title']
    page.ev = [(.25, 'pop', 520), (.5, 'pop', 420), (.6, 'pop', 700), (1.45, 'whoosh', 1.5)] + \
              [e for i in range(n) for e in ((T0 + i * STEP, 'pop', 520 + 380 * i / max(1, n - 1), .1, .38), (T0 + i * STEP + .08, 'tick', 1500, .04, .12))] + \
              [(TS + .1, 'thud'), (TS + .2, 'pop', 900, .12, .35), (TS + .85, 'chime')]
    return html, DUR


if __name__ == '__main__':
    kind, ref = sys.argv[1], D.date.fromisoformat(sys.argv[2])
    data, races = load()
    html, dur = page(kind, ref, races)
    if not html:
        print('rien : pas assez de courses pour ce reel'); sys.exit(0)
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / f'_{kind}.html'; f.write_text(html)
    mp4 = OUT / f'reel-{kind}-{ref}.mp4'; cover = OUT / f'reel-{kind}-{ref}-couverture.jpg'; tmp = OUT / f'_{kind}.mp4'
    rec.record(f, tmp, dur, stills=[(1.2, cover)])
    wav = OUT / f'_{kind}.wav'; sfx.track(page.ev, dur, wav); sfx.mux(tmp, wav); wav.unlink()
    tmp.replace(mp4); f.unlink()
    print(f'ok {page.n} course(s) · {page.title} · {dur:.1f} s\n{mp4}\n{cover}')
