"""Dossard Péi – shared helpers for the social-media kits (data, dates, drawing, rendering)."""
import json, re, html, datetime as D, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent      # repository root (site files)
SOC = pathlib.Path(__file__).resolve().parent               # social/
FONTS = SOC / 'fonts'

# ---------------------------------------------------------------- colours / formats
# palette of the site (cream page, sky hero, warm dark text, teal buttons, orange alerts)
C = dict(bg='#f2f2f7', surface='#ffffff', fg='#111113', muted='#6e6e73', line='#e3e3e8',
         accent='#00968f', soft='#e0f2f1', hot='#e5502e', sea='#d9e6e6', red='#b42318', dark='#111113', mint='#00968f',
         sky1='#5fb0e6', sky2='#bfe0f3')
TYPE_COL = {'trail': '#2e7d32', 'route': '#5a6b7b', 'marche': '#9a8170', 'cross': '#a0782c', 'autre': '#9a6400',
            'jeunes': '#d6336c', 'multisport': '#0a76c2', 'relais': '#d9a000'}
TYPE_LAB = {'trail': 'Trail', 'route': 'Route', 'marche': 'Rando', 'cross': 'Cross', 'autre': 'Autre',
            'jeunes': 'Jeunes', 'multisport': 'Multisport', 'relais': 'Relais'}
TYPE_EMO = {'trail': '⛰️', 'route': '🏃', 'marche': '🥾', 'cross': '👟', 'autre': '🏅', 'jeunes': '🧒',
            'multisport': '🏊', 'relais': '🤝'}
# P = layout of a format: height, top/bottom safe margins, right margin (TikTok buttons column)
FMTS = {'instagram': dict(name='instagram', W=1080, H=1350, T=60, B=64, R=64),
        'tiktok': dict(name='tiktok', W=1080, H=1920, T=250, B=320, R=170)}

JOURS = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']
JOURS_C = ['lun.', 'mar.', 'mer.', 'jeu.', 'ven.', 'sam.', 'dim.']
MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
MOIS_C = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.']

REGIONS = {
    'nord': ('le Nord', ['Saint-Denis', 'Sainte-Marie', 'Sainte-Suzanne']),
    'ouest': ("l'Ouest", ['Le Port', 'La Possession', 'Saint-Paul', 'Trois-Bassins', 'Saint-Leu', 'Les Avirons']),
    'sud': ('le Sud', ["L'Étang-Salé", 'Saint-Louis', 'Saint-Pierre', 'Le Tampon', 'Entre-Deux', 'Petite-Île',
                       'Saint-Joseph', 'Saint-Philippe', 'Cilaos']),
    'est': ("l'Est", ['Sainte-Rose', 'Saint-Benoît', 'Bras-Panon', 'Saint-André', 'La Plaine-des-Palmistes', 'Salazie']),
}
REGION_ORDER = ['ouest', 'sud', 'est', 'nord']


def week_index(day):
    return day.isocalendar()[1] + day.isocalendar()[0] * 53


def esc(s): return html.escape(str(s))


def d(s): return D.date.fromisoformat(s[:10])


def fdate(x, short=False, year=False):
    s = f"{(JOURS_C if short else JOURS)[x.weekday()]} {x.day}{'er' if x.day == 1 else ''} {(MOIS_C if short else MOIS)[x.month - 1]}"
    return s + (f' {x.year}' if year else '')


# ---------------------------------------------------------------- data
def load():
    data = json.loads((ROOT / 'data.json').read_text())
    races = [r for r in data['races'] if not r.get('hidden') and not r.get('annule')]
    for r in races:
        r['_d'] = d(r['date'])
        ep = [e for e in r.get('epreuves', []) if e.get('km')]
        main = max(ep, key=lambda e: e['km']) if ep else (r['epreuves'][0] if r.get('epreuves') else {})
        r['_main'] = main
        types = [e.get('type') for e in r.get('epreuves', []) if e.get('type')]
        r['_type'] = main.get('type') or (types[0] if types else 'autre')
        r['_types'] = set(types)
        hs = [e['h'] for e in r.get('epreuves', []) if re.match(r'^\d{1,2}h\d{2}$', e.get('h', '') or '')]
        r['_h'] = min(hs, key=lambda h: int(h.replace('h', ''))) if hs else None
        g = data.get('gpx', {}).get(r['id'])
        r['_gpx'] = g
    return data, races


def gpx_tracks(data, rid):
    """Return list of tracks [{nom, km, dp, pts:[[lat,lon,ele],...]}] for a race, or []."""
    g = data.get('gpx', {}).get(rid)
    if not g:
        return []
    if g.get('pts'):
        return [{'nom': '', 'km': None, 'dp': None, 'pts': g['pts']}]
    if g.get('file'):
        try:
            return [t for t in json.loads((ROOT / g['file']).read_text()).get('tracks', []) if t.get('pts')]
        except Exception:
            return []
    return []


def upcoming(races, start, end):
    return sorted([r for r in races if start <= r['_d'] <= end], key=lambda r: (r['_d'], r['_h'] or '99', r['nom']))


def dist_label(r, maxn=2):
    ep = sorted({e['km'] for e in r.get('epreuves', []) if e.get('km')}, reverse=True)
    if not ep:
        return ''
    m = r['_main']
    lab = ' · '.join(f"{fmt_km(k)} km" for k in ep[:maxn])
    if len(ep) == 1 and m.get('dp'):
        lab += f" · {m['dp']} D+"
    elif m.get('dp') and len(ep) > 1:
        lab = f"{fmt_km(ep[0])} km · {m['dp']} D+" + (f" · {fmt_km(ep[1])} km" if len(ep) > 1 else '')
    return lab


def fmt_km(k):
    return str(int(k)) if float(k).is_integer() else str(k).replace('.', ',')


def status(r, ref):
    """(code, label) of registrations at date ref: complet / clos / bientot / clotJ / ouvert."""
    eps = r.get('epreuves', [])
    if r.get('complet') or r.get('clos') or (eps and all(e.get('complet') or e.get('clos') for e in eps)):
        return 'complet', 'COMPLET'
    if r.get('ouverture'):
        o = d(r['ouverture'])
        if o > ref:
            return 'bientot', f"Inscriptions dès le {o.day} {MOIS_C[o.month - 1]}"
    elif r.get('avenir'):
        return 'bientot', 'Inscriptions à venir'   # not open yet, opening date unknown
    lim = r.get('limite')
    if lim:
        L = d(lim)
        if L < ref:
            return 'complet', 'COMPLET'      # closed registrations are shown as « complet » on the visuals
        n = (L - ref).days
        if n == 0:
            return 'clot', "Clôture aujourd'hui"
        if n == 1:
            return 'clot', 'Clôture demain'
        if n <= 6:
            return 'clot', f"Clôture {JOURS[L.weekday()]}"
        return 'ouvert', f"Inscriptions jusqu'au {L.day} {MOIS_C[L.month - 1]}"
    return 'ouvert', ''


def poster_path(r):
    for k in ('poster_lg', 'poster'):
        if r.get(k) and (ROOT / r[k]).exists():
            return ROOT / r[k]
    return None


def art_path(r):
    p = ROOT / 'tools' / f"art_{r['_type']}.png"
    return p if p.exists() else ROOT / 'tools' / 'art_autre.png'


# ---------------------------------------------------------------- map
_MAP = None


def MAP():
    global _MAP
    if _MAP is None:
        # the map used to be inline in index.html; since the site split (assets/app.<hash>.js) it lives in the app script
        s = (ROOT / 'index.html').read_text()
        m = re.search(r'MAP\s*=\s*\{', s)
        if not m:
            js = re.search(r'assets/app\.[0-9a-f]+\.js', s)
            s = (ROOT / js.group(0)).read_text() if js else ''
            m = re.search(r'MAP\s*=\s*\{', s)
        _MAP, _ = json.JSONDecoder().raw_decode(s[m.end() - 1:])
    return _MAP


def P_xy(lat, lon):
    M = MAP(); LON0, LON1, LAT0, LAT1 = M['bounds']
    return ((lon - LON0) / (LON1 - LON0) * M['W'], (LAT1 - lat) / (LAT1 - LAT0) * M['H'])


def island_svg(width, pins=(), highlight=None, relief=False, contours=False, dim_others=True, labels=False, vb=None):
    """SVG of the island. pins: [{ll, color, n, r}], highlight: list of communes."""
    M = MAP()
    vb = vb or (-40, -20, M['W'] + 80, M['H'] + 40)
    out = [f'<svg viewBox="{vb[0]} {vb[1]} {vb[2]} {vb[3]}" width="{width}" xmlns="http://www.w3.org/2000/svg">',
           '<defs><clipPath id="isl">' + ''.join(f'<path d="{c["d"]}"/>' for c in M['communes']) + '</clipPath></defs>']
    if relief:
        out.append(f'<image href="{(ROOT / "relief_sm.webp").as_uri()}" x="0" y="0" width="{M["W"]}" height="{M["H"]}" clip-path="url(#isl)" preserveAspectRatio="none"/>')
    else:
        out.append('<g fill="#f8faf7">' + ''.join(f'<path d="{c["d"]}"/>' for c in M['communes']) + '</g>')
    if contours:
        try:
            cs = json.loads((ROOT / 'contours100.json').read_text())
            out.append('<g fill="none" stroke="#9fb8ad" stroke-width="1.2" opacity=".5">' + ''.join(f'<path d="{c["d"]}"/>' for c in cs if c['z'] % 500) + '</g>')
            out.append('<g fill="none" stroke="#7b9a8d" stroke-width="1.8" opacity=".65">' + ''.join(f'<path d="{c["d"]}"/>' for c in cs if c['z'] % 500 == 0) + '</g>')
        except Exception:
            pass
    if highlight is not None and dim_others:
        out.append('<g fill="#eef2ee" fill-opacity=".72">' + ''.join(f'<path d="{c["d"]}"/>' for c in M['communes'] if c['nom'] not in highlight and not _same(c['nom'], highlight)) + '</g>')
    out.append('<g fill="none" stroke="#ffffff" stroke-opacity=".9" stroke-width="2">' + ''.join(f'<path d="{c["d"]}"/>' for c in M['communes']) + '</g>')
    if highlight is not None:
        out.append(f'<g fill="none" stroke="{C["fg"]}" stroke-width="4" stroke-linejoin="round">' + ''.join(f'<path d="{c["d"]}"/>' for c in M['communes'] if _same(c['nom'], highlight)) + '</g>')
    s = vb[2] / (M['W'] + 80)                     # pins keep the same on-screen size whatever the zoom
    pos = [list(P_xy(*p['ll'])) for p in pins]
    rr = [p.get('r', 30) * s for p in pins]
    groups = []                                   # spread pins that overlap around their centre
    for k, (x, y) in enumerate(pos):
        for g in groups:
            gx, gy = g['c']
            if (x - gx) ** 2 + (y - gy) ** 2 < (2.1 * rr[k]) ** 2:
                g['m'].append(k); break
        else:
            groups.append({'c': (x, y), 'm': [k]})
    import math as _m
    for g in groups:
        if len(g['m']) > 1:
            R = rr[g['m'][0]] * (1.15 if len(g['m']) == 2 else 1.25 / _m.sin(_m.pi / len(g['m'])))
            for j, k in enumerate(g['m']):
                a = -_m.pi / 2 + 2 * _m.pi * j / len(g['m'])
                pos[k] = [g['c'][0] + R * _m.cos(a), g['c'][1] + R * _m.sin(a)]
    for p, (x, y), r in zip(pins, pos, rr):
        out.append(f'<g transform="translate({x:.1f},{y:.1f})"><circle r="{r + 9 * s:.1f}" fill="{p["color"]}" opacity=".2"/>'
                   f'<circle r="{r:.1f}" fill="{p["color"]}" stroke="#fff" stroke-width="{5 * s:.1f}"/>')
        if p.get('n') is not None:
            fs = int(r * 1.25)
            out.append(f'<text y="{fs * .35:.0f}" text-anchor="middle" font-family="Saira" font-weight="800" font-size="{fs}" fill="#fff">{p["n"]}</text>')
        out.append('</g>')
    out.append('</svg>')
    return ''.join(out)


def _norm(s):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn').replace("'", '').replace('-', ' ').replace('les ', '').replace('le ', '').replace('la ', '').replace('l', '', 0).strip()


def _same(nom, lst):
    n = _norm(nom)
    return any(_norm(x) == n or _norm(x).endswith(n) or n.endswith(_norm(x)) for x in lst)


# ---------------------------------------------------------------- html page / common blocks
LOGO = (ROOT / 'favicon.svg').read_text()


# Polices : depuis la DA « épuré + running » du site, Inter remplace Instrument Sans (famille Inst)
# et Saira Condensed (la famille CSS « Saira » pointe désormais vers Inter, classe .saira conservée).
def css():
    f = FONTS.as_uri()
    return f"""
@font-face{{font-family:'Inst';font-weight:400;src:url('{f}/inter-latin-400-normal.woff2') format('woff2');}}
@font-face{{font-family:'Inst';font-weight:500;src:url('{f}/inter-latin-500-normal.woff2') format('woff2');}}
@font-face{{font-family:'Inst';font-weight:600;src:url('{f}/inter-latin-600-normal.woff2') format('woff2');}}
@font-face{{font-family:'Inst';font-weight:700;src:url('{f}/inter-latin-700-normal.woff2') format('woff2');}}
@font-face{{font-family:'Saira';font-weight:600;src:url('{f}/inter-latin-600-normal.woff2') format('woff2');}}
@font-face{{font-family:'Saira';font-weight:700;src:url('{f}/inter-latin-700-normal.woff2') format('woff2');}}
@font-face{{font-family:'Saira';font-weight:800;src:url('{f}/inter-latin-800-normal.woff2') format('woff2');}}
@font-face{{font-family:'Saira';font-weight:900;src:url('{f}/inter-latin-900-normal.woff2') format('woff2');}}

*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:1080px;overflow:hidden}}
body{{font-family:'Inst',sans-serif;color:{C['fg']};background:{C['bg']};position:relative}}
.saira{{font-family:'Saira',sans-serif;letter-spacing:-.035em}}
body{{letter-spacing:-.01em}}
.brand{{display:flex;align-items:center;gap:16px}}
.brand svg{{width:62px;height:62px}}
.brand b{{font-family:'Saira';font-weight:800;font-size:40px;letter-spacing:-.03em;line-height:1}}
.count{{font-weight:600;font-size:24px;color:{C['muted']};background:rgba(255,255,255,.75);border-radius:30px;padding:8px 18px}}
.chip{{display:inline-block;font-weight:700;font-size:26px;color:#fff;border-radius:10px;padding:6px 14px}}
"""


def scene(P, horizon=.62, fade=True):
    """Site-like background: sky gradient, blue mountains, green hills, cream page below."""
    W, H = P['W'], P['H']; y = H * horizon
    return f'''<svg style="position:absolute;left:0;top:0" width="{W}" height="{H}" viewBox="0 0 {W} {H}" preserveAspectRatio="none">
      <defs><linearGradient id="sk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C['sky1']}"/><stop offset="{horizon:.2f}" stop-color="{C['sky2']}"/></linearGradient>
      <linearGradient id="fd" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C['bg']}" stop-opacity="0"/><stop offset="1" stop-color="{C['bg']}"/></linearGradient></defs>
      <rect width="{W}" height="{H}" fill="url(#sk)"/>
      <ellipse cx="{W * .72:.0f}" cy="{H * .12:.0f}" rx="{W * .26:.0f}" ry="{H * .045:.0f}" fill="#fff" opacity=".35"/>
      <path d="M0 {y - H * .10:.0f} L{W * .22:.0f} {y - H * .17:.0f} L{W * .45:.0f} {y - H * .09:.0f} L{W * .7:.0f} {y - H * .2:.0f} L{W} {y - H * .12:.0f} L{W} {H} L0 {H}Z" fill="#a9c2d3"/>
      <path d="M0 {y - H * .02:.0f} L{W * .3:.0f} {y - H * .1:.0f} L{W * .62:.0f} {y - H * .03:.0f} L{W} {y - H * .08:.0f} L{W} {H} L0 {H}Z" fill="#8eaabb"/>
      <path d="M0 {y + H * .05:.0f} Q{W * .35:.0f} {y - H * .02:.0f} {W * .7:.0f} {y + H * .03:.0f} T{W} {y + H * .02:.0f} L{W} {H} L0 {H}Z" fill="#9dbf93"/>
      {f'<rect y="{y:.0f}" width="{W}" height="{H - y:.0f}" fill="url(#fd)"/>' if fade else ''}</svg>'''


def page(body, P, extra=''):
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{css()}html,body{{height:{P["H"]}px}}{extra}</style></head><body>{body}</body></html>'


def head(i, n, P, dark=False):
    col = '#fff' if dark else C['fg']
    cnt = 'background:rgba(255,255,255,.12);color:#cfe1e4' if dark else ''
    return f'''<div style="position:absolute;left:64px;right:64px;top:{P['T']}px;display:flex;justify-content:space-between;align-items:center;color:{col}">
      <div class="brand">{LOGO}<b>Dossard Péi</b></div><span class="count" style="{cnt}">{i}/{n}</span></div>'''


def crop_img(path, x0, y0, x1, y1, w, dpr=3, radius=26, extra=''):
    """Crop a css box of a capture (taken at dpr) and display it at width w. Returns (html, h, scale)."""
    from PIL import Image
    fw = Image.open(path).size[0] / dpr
    sc = w / (x1 - x0); h = (y1 - y0) * sc
    return (f'<div style="width:{w}px;height:{h:.0f}px;overflow:hidden;position:relative;border-radius:{radius}px;'
            f'box-shadow:0 26px 60px rgba(29,37,35,.28),0 0 0 1px rgba(29,37,35,.08);background:#fff">'
            f'<img src="{pathlib.Path(path).as_uri()}" style="position:absolute;left:{-x0 * sc:.1f}px;top:{-y0 * sc:.1f}px;width:{fw * sc:.1f}px">{extra}</div>'), h, sc


def cta_slide(i, n, P, title_html, sub, save_line):
    body = f'''
    {scene(P, .7)}
    {head(i, n, P)}
    <div style="position:absolute;left:64px;right:64px;top:{P['T'] + 150}px;color:{C['fg']}">
      <div class="saira" style="font-weight:800;font-size:116px;line-height:.92">{title_html}</div>
      <div style="font-size:40px;font-weight:600;margin-top:30px;line-height:1.3">{sub}</div>
    </div>
    <div style="position:absolute;left:64px;right:{P['R']}px;bottom:{P['B'] + 120}px;background:{C['fg']};border-radius:999px;padding:24px 26px 24px 44px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 18px 40px rgba(0,0,0,.18)">
      <div class="saira" style="font-weight:800;font-size:80px;line-height:1;color:#fff">dossardpei.re</div>
      <span style="width:84px;height:84px;border-radius:50%;background:{C['hot']};display:grid;place-items:center">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></span></div>
    <div style="position:absolute;left:64px;right:{P['R']}px;bottom:{P['B']}px;color:{C['fg']};display:flex;align-items:center;gap:16px;font-size:36px;font-weight:700">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="{C['accent']}"><path d="M6 2h12a1 1 0 0 1 1 1v19l-7-5-7 5V3a1 1 0 0 1 1-1z"/></svg>{save_line}</div>'''
    return page(body, P)


def how_slide(i, n, P, feature, title, steps, shot_html, shot_h):
    """'Sur le site' slide: feature name, steps, capture."""
    st = ''.join(f'''<div style="display:flex;gap:18px;align-items:flex-start;font-size:34px;font-weight:600;line-height:1.25">
        <span class="saira" style="flex:none;width:52px;height:52px;border-radius:50%;background:{C['hot']};color:#fff;display:grid;place-items:center;font-weight:800;font-size:34px">{k}</span>
        <span style="padding-top:6px">{s}</span></div>''' for k, s in enumerate(steps, 1))
    top_shot = P['T'] + 470
    return page(f'''
    {head(i, n, P)}
    <div style="position:absolute;left:64px;right:64px;top:{P['T'] + 112}px">
      <div class="saira" style="font-weight:700;font-size:40px;color:{C['hot']}">SUR LE SITE · {feature}</div>
      <div class="saira" style="font-weight:800;font-size:88px;line-height:.92;margin-top:4px">{title}</div>
    </div>
    <div style="position:absolute;left:64px;width:400px;top:{top_shot + 20}px;display:flex;flex-direction:column;gap:34px">{st}</div>
    <div style="position:absolute;right:{P['R']}px;top:{top_shot}px">{shot_html}</div>''', P)


def caption(lines, tags, fmt):
    t = list(tags)
    txt = '\n'.join(lines)
    if fmt == 'tiktok':
        txt = txt.replace(' (lien en bio)', '')
    return txt + '\n\n' + ' '.join(t[:4])
