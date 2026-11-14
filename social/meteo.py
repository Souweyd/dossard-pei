"""Story vidéo « Météo des courses » du week-end (1080×1920, MP4 avec bruitages), à partir de weather.json.
Modèle validé le 14/11/2026 : « Météo des courses » et les dates sur la carte floutée, puis vue d'ensemble de l'île ;
course après course (ordre chronologique), un point se pose sur le départ, un trait en part vers son cadre météo
(nom, temps et température pendant la course, jour et heure, commune, terrain glissant, pluie, vent).
Cadres au-dessus de l'île pour les courses du nord, en dessous pour celles du sud ; 8 courses au plus
(au-delà : 7 + « + N autres courses »). Une course sur deux jours n'a qu'un cadre (son premier jour).
Usage (depuis la racine du dépôt) : python3 social/meteo.py <date du vendredi>   ex. python3 social/meteo.py 2026-11-13
Sortie : social/out/meteo/story-meteo-<vendredi>.mp4 ; « rien » s'il n'y a pas de course avec météo samedi / dimanche."""
import sys, json, pathlib, datetime as D
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from core import load, MAP, P_xy, ROOT, JOURS, JOURS_C, MOIS
from nouveau import island, INK, TEAL, SURF, esc
import rec, sfx

OUT = ROOT / 'social' / 'out' / 'meteo'
F = (ROOT / 'social' / 'fonts').as_uri()
LOGO = (ROOT / 'social' / 'assets' / 'logo-512.png').as_uri()
OCEAN = (ROOT / 'ocean.webp').as_uri()        # same IGN sea picture as the site map
SEA = '#083b5a'
W, H = 1080, 1920
WXT = {'clearsky': 'Ensoleillé', 'fair': 'Plutôt beau', 'partlycloudy': 'Éclaircies', 'cloudy': 'Nuageux', 'fog': 'Brouillard',
       'lightrain': 'Faible pluie', 'rain': 'Pluie', 'heavyrain': 'Fortes pluies', 'lightrainshowers': 'Quelques averses',
       'rainshowers': 'Averses', 'heavyrainshowers': 'Fortes averses'}
# line icons of the site (same drawings as the weather block of a race page)
SUN = '<circle cx="12" cy="12" r="4.2"/><g class="rays"><path d="M12 2.5v2.2M12 19.3v2.2M2.5 12h2.2M19.3 12h2.2M5.3 5.3l1.6 1.6M17.1 17.1l1.6 1.6M5.3 18.7l1.6-1.6M17.1 6.9l1.6-1.6"/></g>'
CLOUD = '<path d="M7 18.5h10.2a3.8 3.8 0 0 0 .4-7.6 5.6 5.6 0 0 0-10.9 1.2A3.2 3.2 0 0 0 7 18.5Z"/>'
PART = '<g class="rays"><path d="M8.5 4.2v1.6M3.6 9.1h1.6M5 5.6l1.1 1.1M12 5.6l-1.1 1.1"/></g><path d="M5.9 11.6a3.2 3.2 0 0 1 5.6-3"/><g class="drift"><path d="M9 19.5h8.6a3.4 3.4 0 0 0 .3-6.8 5 5 0 0 0-9.7 1.1A2.9 2.9 0 0 0 9 19.5Z"/></g>'
RAIN = '<path d="M7 15h10.2a3.6 3.6 0 0 0 .4-7.2 5.4 5.4 0 0 0-10.5 1.1A3 3 0 0 0 7 15Z"/><g class="drops"><path d="M8.5 18l-1 2.5M12.5 18l-1 2.5M16.5 18l-1 2.5"/></g>'
STORM = '<path d="M7 14.5h10.2a3.6 3.6 0 0 0 .4-7.2 5.4 5.4 0 0 0-10.5 1.1A3 3 0 0 0 7 14.5Z"/><g class="flash"><path d="m12.5 15.5-2 3.5h3l-2 3.5"/></g>'
ICON = dict(sun=(SUN, '#fff4d6', '#e39a00'), part=(PART, '#fff1d9', '#d98a00'), cloud=(CLOUD, '#eef1f4', '#6b7a88'),
            fog=(CLOUD, '#eef1f4', '#6b7a88'), rain=(RAIN, '#e3f0fb', '#2b7bc0'), storm=(STORM, '#ece8f7', '#5b4bb0'))
TEMP = '<path d="M10 14.5V5a2 2 0 0 1 4 0v9.5a4 4 0 1 1-4 0Z"/><path d="M12 9v7.5"/>'
SMALL = {'drop': '<path d="M12 3.5s-5.5 6.2-5.5 10a5.5 5.5 0 0 0 11 0c0-3.8-5.5-10-5.5-10Z"/>',
         'wind': '<path d="M3 9h11a2.5 2.5 0 1 0-2.5-2.5M3 13h15a2.5 2.5 0 1 1-2.5 2.5M3 17h7"/>',
         'peak': '<path d="m3 19 6.5-11 3.5 6 2-3.2L21 19Z"/><path d="m8 10.4 1.5 1.3 1.5-1.3"/>',
         'wet': '<path d="M4 18c2 0 2-1.5 4-1.5s2 1.5 4 1.5 2-1.5 4-1.5 2 1.5 4 1.5"/><path d="M12 4s-3 3.4-3 5.5a3 3 0 0 0 6 0C15 7.4 12 4 12 4Z"/>'}


def kind(s):
    s = s or ''
    if 'thunder' in s: return 'storm'
    if any(k in s for k in ('rain', 'sleet', 'snow')): return 'rain'
    if s == 'fog': return 'fog'
    if s == 'cloudy': return 'cloud'
    if s in ('partlycloudy', 'fair'): return 'part'
    return 'sun'


def svg(p, s, col, sw=1.8): return f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{col}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round" style="overflow:visible">{p}</svg>'


def mm(x): return '0 mm' if x < 1 else (f'{round(x)} mm' if x >= 10 else f'{x:.1f} mm'.replace('.', ','))


GRAD = dict(sun=('#f6b73c', '#e3762a'), part=('#5fb3ec', '#2f7fc9'), cloud=('#8597a8', '#536576'), fog=('#8597a8', '#536576'),
            rain=('#4f86b8', '#2a4f7a'), storm=('#5b5891', '#2e2b57'))
CW, CH, GAP, SIDE = 246, 270, 14, 24          # weather card size, gap, side margin
KF, CY = 760 / 1100, 940                     # final zoom (island 800 px wide) and centre
TOP_Y, BOT_Y = 290, 1318                     # rows of cards above / under the island
STEP = .5                                    # one race every half second


def races(friday):
    wx = json.loads((ROOT / 'weather.json').read_text())
    data, rs = load(); by = {r['id']: r for r in rs}
    days = {friday + D.timedelta(days=1), friday + D.timedelta(days=2)}
    out, seen = [], set()
    for rid, lst in wx['races'].items():
        for x in sorted(lst, key=lambda x: x['date']):
            if rid in by and rid not in seen and D.date.fromisoformat(x['date']) in days:
                seen.add(rid); out.append((x['date'], x.get('h') or '99', by[rid], x))
    return wx, out


def spread(xs):
    """card centres near their pins, in the same order, without overlap"""
    lo, hi, d = SIDE + CW / 2, W - SIDE - CW / 2, CW + GAP
    c = [min(max(x, lo), hi) for x in xs]
    for _ in range(50):
        for i in range(1, len(c)):
            if c[i] - c[i - 1] < d:
                m = (c[i] + c[i - 1]) / 2; c[i - 1], c[i] = m - d / 2, m + d / 2
        c = [min(max(x, lo + i * 0), hi) for i, x in enumerate(c)]
        if c and c[0] < lo:
            c = [x + lo - c[0] for x in c]
        if c and c[-1] > hi:
            c = [x - (c[-1] - hi) for x in c]
    return c


def page(friday):
    wx, items = races(friday)
    if not items:
        return None, 0
    M = MAP()
    more = 0
    if len(items) > 8:
        more = len(items) - 7; items = sorted(items, key=lambda t: (t[0], t[1]))[:7]
    # pins on screen (final framing)
    P = []
    for it in items:
        mx, my = P_xy(*it[2]['ll'])
        P.append((W / 2 + (mx - M['W'] / 2) * KF, CY + (my - M['H'] / 2) * KF))
    order = sorted(range(len(items)), key=lambda i: P[i][1])           # north first
    ntop = min(4, max(len(items) - 4, (len(items) + 1) // 2))
    top, bot = sorted(order[:ntop], key=lambda i: P[i][0]), sorted(order[ntop:], key=lambda i: P[i][0])
    slot = {}
    for row, y in ((top, TOP_Y), (bot, BOT_Y)):
        for i, cx in zip(row, spread([P[i][0] for i in row])):
            slot[i] = (cx, y)
    # appearance order: by date and hour
    seq = sorted(range(len(items)), key=lambda i: (items[i][0], items[i][1]))
    T0 = 3.0
    DUR = T0 + len(items) * STEP + 5.5
    p = lambda t: f'{t / DUR * 100:.2f}%'
    k0 = 1000 / M['W']
    cam = lambda k, sy: f"translate({W / 2 - M['W'] / 2 * k:.1f}px,{sy - M['H'] / 2 * k:.1f}px) scale({k:.4f})"
    dset = sorted({D.date.fromisoformat(i[0]) for i in items})
    title = (f"{JOURS[dset[0].weekday()]} {dset[0].day} {MOIS[dset[0].month - 1]}" if len(dset) == 1
             else f"{JOURS_C[dset[0].weekday()]} {dset[0].day} et {JOURS_C[dset[1].weekday()]} {dset[1].day} {MOIS[dset[1].month - 1]}")
    title = title[0].upper() + title[1:]
    lines, pins, cards = [], [], []
    for k, i in enumerate(seq):
        ds, h, r, x = items[i]; t = T0 + k * STEP
        px, py = P[i]; cx, cy = slot[i]
        ey = cy + CH if cy == TOP_Y else cy                       # attach to the card edge facing the island
        kd = kind(x['start']['sym']); g = GRAD[kd]; w = x['window']
        lines.append(f'<line class="ln anim" style="animation-delay:{t + .15:.2f}s" x1="{px:.0f}" y1="{py:.0f}" x2="{cx:.0f}" y2="{ey:.0f}" pathLength="1"/>')
        pins.append(f'<div class="pin anim" style="left:{px:.0f}px;top:{py:.0f}px;animation-delay:{t:.2f}s;--c:{g[1]}"></div>')
        d = D.date.fromisoformat(ds)
        hh = (x.get('h') or '').replace('h00', 'h').lstrip('0')
        temp = f"{w['tmin']}–{w['tmax']}°" if w['tmin'] != w['tmax'] else f"{w['tmin']}°"
        txt = WXT.get(x['start']['sym'].replace('andthunder', ''), 'Orages' if kd == 'storm' else '')
        extra = f'<div class="wet">{svg(SMALL["wet"], 18, "#fff", 2)}Terrain glissant</div>' if x.get('veille') else ''
        cards.append(f'''<div class="card anim" style="left:{cx - CW / 2:.0f}px;top:{cy}px;animation-delay:{t + .35:.2f}s;background:linear-gradient(150deg,{g[0]},{g[1]})">
      <div class="cn s">{esc(r['nom'])}</div>
      <div class="ct">{svg(ICON[kd][0], 44, '#fff', 1.7)}<b>{temp}</b></div>
      <div class="cs"><b>{JOURS_C[d.weekday()].capitalize()} {hh}</b></div><div class="cs cc">{esc(r['commune'])}</div>
      {extra}
      <div class="cw"><span>{svg(SMALL['drop'], 18, '#fff', 2)}{mm(w['rain'])}</span><span>{svg(SMALL['wind'], 18, '#fff', 2)}{w['w']} km/h</span></div></div>''')
    at = D.datetime.fromisoformat(wx['at'])
    tf = T0 + len(items) * STEP + .2
    allc = ''.join(f'<path vector-effect="non-scaling-stroke" d="{c["d"]}"/>' for c in M['communes'])
    html = f'''<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:S;font-weight:800;src:url('{F}/SairaCondensed-800.woff2')}}
@font-face{{font-family:I;font-weight:400;src:url('{F}/inter-latin-400-normal.woff2')}}
@font-face{{font-family:I;font-weight:600;src:url('{F}/inter-latin-600-normal.woff2')}}
@font-face{{font-family:I;font-weight:700;src:url('{F}/inter-latin-700-normal.woff2')}}
*{{box-sizing:border-box;margin:0;padding:0}} html,body{{width:{W}px;height:{H}px;overflow:hidden;background:{SEA}}}
body{{font-family:I,sans-serif;color:{INK};position:relative}} .s{{font-family:S,sans-serif}}
.anim{{animation-duration:{DUR}s;animation-fill-mode:both;animation-timing-function:linear}}
#lens{{position:absolute;inset:0;background:{SEA};animation-name:lens}}
@keyframes lens{{0%,{p(1.3)}{{filter:blur(22px) saturate(.8)}} {p(1.3)}{{animation-timing-function:ease-out}} {p(2.4)},100%{{filter:blur(0) saturate(1)}}}}
#world{{position:absolute;left:0;top:0;width:{M['W']}px;height:{M['H']}px;transform-origin:0 0;animation-name:cam}}
@keyframes cam{{0%{{transform:{cam(k0 * .96, 900)}}} {p(1.4)}{{transform:{cam(k0, 900)};animation-timing-function:cubic-bezier(.6,0,.25,1)}} {p(2.7)},100%{{transform:{cam(KF, CY)}}}}}
#world img{{position:absolute;left:0;top:0;width:{M['W']}px;height:{M['H']}px}} #world svg{{position:absolute;left:0;top:0;overflow:visible}}
#tag{{position:absolute;left:0;right:0;top:0;display:flex;flex-direction:column;align-items:center;transform-origin:50% 0;animation-name:tag}}
#tag .t{{background:{TEAL};color:#fff;font-weight:800;font-size:92px;letter-spacing:1px;padding:10px 44px 14px;border-radius:22px;box-shadow:0 18px 40px rgba(0,0,0,.35);line-height:1}}
#tag .n{{margin-top:22px;background:{SURF};color:{INK};font-weight:800;font-size:84px;line-height:1;padding:12px 40px 16px;border-radius:22px;box-shadow:0 18px 40px rgba(0,0,0,.3);animation-name:nm}}
@keyframes tag{{0%,{p(.25)}{{transform:translateY(700px) scale(.5);opacity:0}} {p(.25)}{{animation-timing-function:cubic-bezier(.3,1.6,.5,1)}}
  {p(.8)},{p(1.5)}{{transform:translateY(700px) scale(1);opacity:1}} {p(1.5)}{{animation-timing-function:cubic-bezier(.6,0,.2,1)}} {p(2.5)},100%{{transform:translateY(120px) scale(.6);opacity:1}}}}
@keyframes nm{{0%,{p(.55)}{{opacity:0;transform:translateY(30px)}} {p(.55)}{{animation-timing-function:cubic-bezier(.2,.9,.3,1)}} {p(1.0)},100%{{opacity:1;transform:none}}}}
#lines{{position:absolute;left:0;top:0}}
.ln{{stroke:#fff;stroke-width:4;stroke-linecap:round;stroke-dasharray:1;filter:drop-shadow(0 2px 3px rgba(0,0,0,.5));animation-name:draw}}
@keyframes draw{{0%{{stroke-dashoffset:1}} {.3 / DUR * 100:.2f}%,100%{{stroke-dashoffset:0}}}}
.pin{{position:absolute;width:30px;height:30px;margin:-15px 0 0 -15px;border-radius:50%;background:var(--c);border:6px solid #fff;box-shadow:0 3px 10px rgba(0,0,0,.5);animation-name:pop}}
@keyframes pop{{0%{{opacity:0;transform:scale(.2)}} {.18 / DUR * 100:.2f}%{{opacity:1;transform:scale(1.25)}} {.3 / DUR * 100:.2f}%,100%{{opacity:1;transform:scale(1)}}}}
.card{{position:absolute;width:{CW}px;height:{CH}px;border-radius:22px;border:4px solid #fff;color:#fff;padding:12px 14px;box-shadow:0 14px 30px rgba(0,0,0,.4);display:flex;flex-direction:column;gap:3px;animation-name:pop}}
.ct{{display:flex;align-items:center;gap:8px;margin:4px 0 2px}} .ct b{{font:800 46px/1 S,sans-serif}}
.cn{{font-weight:800;font-size:28px;line-height:1;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}}
.cs{{font-size:19px;font-weight:600;line-height:1.2;opacity:.95;display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;overflow:hidden}} .cs b{{font-weight:800}} .cs.cc{{-webkit-line-clamp:2}}
.cnd{{font-size:19px;opacity:.9}}
.wet{{display:flex;align-items:center;gap:5px;font-size:18px;font-weight:700;background:rgba(0,0,0,.22);border-radius:8px;padding:1px 7px;align-self:flex-start}}
.cw{{margin-top:auto;display:flex;gap:14px;font-size:20px;font-weight:700}} .cw span{{display:flex;align-items:center;gap:4px}}
#foot{{position:absolute;left:0;right:0;top:1612px;display:flex;flex-direction:column;align-items:center;gap:10px;animation-name:foot}}
@keyframes foot{{0%,{p(tf)}{{opacity:0;transform:translateY(20px)}} {p(tf + .5)},100%{{opacity:1;transform:none}}}}
#foot .b{{display:flex;align-items:center;gap:16px;background:#fff;border:5px solid {INK};border-radius:999px;padding:8px 30px 8px 12px}}
#foot .b img{{width:70px;display:block}} #foot .b div{{font:800 40px/1 S,sans-serif}} #foot .b small{{display:block;font:700 22px I,sans-serif;color:{TEAL};margin-top:2px}}
#foot .src{{font-size:21px;font-weight:600;color:#fff;opacity:.85}}
</style></head><body>
<div id="lens" class="anim"><div id="world" class="anim"><img src="{OCEAN}"><img src="{island()}">
 <svg width="{M['W']}" height="{M['H']}" viewBox="0 0 {M['W']} {M['H']}"><g fill="none" stroke="#fff" stroke-opacity=".7" stroke-width="1.5">{allc}</g></svg></div></div>
<svg id="lines" width="{W}" height="{H}">{''.join(lines)}</svg>
{''.join(pins)}{''.join(cards)}
<div id="tag" class="anim"><div class="s t">Météo des courses</div><div class="s n anim">{esc(title)}</div></div>
<div id="foot" class="anim"><div class="b"><img src="{LOGO}"><div>Dossard Péi<small>dossardpei.re</small></div></div>
 <div class="src">{f"+ {more} autres courses sur dossardpei.re · " if more else ""}Prévisions MET Norway du {at.day:02d}/{at.month:02d} à {at.hour}h</div></div>
</body></html>'''
    page.n = len(items) + more
    page.ev = [(.25, 'pop', 520), (.6, 'pop', 700), (1.45, 'whoosh', 1.4)] + [e for k in range(len(items)) for e in ((T0 + k * STEP, 'pop', 620, .1, .4), (T0 + k * STEP + .15, 'tick', 1400, .05, .15), (T0 + k * STEP + .35, 'pop', 900, .1, .3))] + [(tf, 'chime')]
    return html, DUR


if __name__ == '__main__':
    fri = D.date.fromisoformat(sys.argv[1])
    html, dur = page(fri)
    if not html:
        print('rien : aucune course avec météo samedi / dimanche'); sys.exit(0)
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / '_meteo.html'; f.write_text(html)
    mp4 = OUT / f'story-meteo-{fri}.mp4'; tmp = OUT / '_meteo.mp4'
    rec.record(f, tmp, dur)
    wav = OUT / '_meteo.wav'; sfx.track(page.ev, dur, wav); sfx.mux(tmp, wav); wav.unlink()
    tmp.replace(mp4); f.unlink()
    wx_at = json.loads((ROOT / 'weather.json').read_text())['at']
    print(f'ok {page.n} course(s) · météo du {wx_at}\n{mp4}')
