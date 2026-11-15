"""Post du lundi « Ce week-end » (carrousel Instagram / Facebook 4:5 et TikTok 9:16), dans le style des stories vidéo :
mer du site et relief de l'île, étiquette verte, panneaux crème, Saira Condensed + Inter.
1. Couverture : l'île entière, un point par course relié par un trait à son cadre (nom, jour et heure, commune, statut).
   Au-delà de 8 courses : points numérotés seulement, puis une page « programme ».
2. Une slide par course où l'on peut encore s'inscrire (les complètes sont seulement sur la couverture) : la carte zoomée sur le départ,
   puis la carte de la course (affiche, date, lieu, statut, une ligne par épreuve), comme la fin de « Nouveau dossard ».
3. Fin : dossardpei.re.
build(ref, data, races) -> (pages {fmt: [html]}, lignes de légende, hashtags), appelé par gen.py (build_lundi)."""
import re, datetime as D
from core import MAP, P_xy, _same, status, poster_path, art_path, fmt_km, upcoming, JOURS, JOURS_C, MOIS, MOIS_C, ROOT
from nouveau import island, bbox, rows, TLAB, TCOL, esc
import charte as CH

INK, TEAL, SURF, MUTED, SEA, LINE = '#1d2523', '#0d6b67', '#fffcf7', '#6b625a', '#083b5a', '#ece4d8'
OCEAN = (ROOT / 'ocean.webp').as_uri()
F = (ROOT / 'social' / 'fonts').as_uri()
LOGO = (ROOT / 'social' / 'assets' / 'logo-512.png').as_uri()
TAGS = ['#trail', '#run', '#iledelareunion', '#reunionisland']
STC = {'complet': '#c62828', 'clot': '#d2481e', 'bientot': TEAL, 'ouvert': '#2e7d32'}

CSS = f'''
@font-face{{font-family:S;font-weight:800;src:url('{F}/SairaCondensed-800.woff2')}}
@font-face{{font-family:S;font-weight:700;src:url('{F}/SairaCondensed-700.woff2')}}
@font-face{{font-family:I;font-weight:400;src:url('{F}/inter-latin-400-normal.woff2')}}
@font-face{{font-family:I;font-weight:600;src:url('{F}/inter-latin-600-normal.woff2')}}
@font-face{{font-family:I;font-weight:700;src:url('{F}/inter-latin-700-normal.woff2')}}
@font-face{{font-family:I;font-weight:800;src:url('{F}/inter-latin-800-normal.woff2')}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:I,sans-serif;color:{INK};background:{SEA};position:relative;overflow:hidden;-webkit-font-smoothing:antialiased}}
.s{{font-family:S,sans-serif;font-weight:800}} .abs{{position:absolute}}
.world{{position:absolute;left:0;top:0;transform-origin:0 0}} .world img,.world svg{{position:absolute;left:0;top:0;overflow:visible}}
.tag{{display:inline-block;background:{TEAL};color:#fff;font:800 64px/1 S,sans-serif;padding:8px 32px 12px;border-radius:18px;box-shadow:0 14px 30px rgba(0,0,0,.35)}}
.sub{{display:inline-block;background:{SURF};color:{INK};font:800 50px/1 S,sans-serif;padding:9px 28px 12px;border-radius:18px;box-shadow:0 14px 30px rgba(0,0,0,.3)}}
.cnt{{position:absolute;background:rgba(0,0,0,.35);color:#fff;font:700 24px/1 I,sans-serif;padding:9px 16px;border-radius:999px}}
.foot{{position:absolute;left:0;right:0;display:flex;justify-content:center}}
.foot>div{{display:flex;align-items:center;gap:12px;background:#fff;border:4px solid {INK};border-radius:999px;padding:6px 24px 6px 8px;box-shadow:0 10px 24px rgba(0,0,0,.35)}}
.foot img{{width:54px;display:block}} .foot b{{display:block;font:800 30px/.95 S,sans-serif}} .foot small{{display:block;font:700 19px/1.1 I,sans-serif;color:{TEAL};margin-top:2px}}
.st{{display:inline-block;color:#fff;font:700 21px/1 I,sans-serif;padding:7px 12px;border-radius:9px;white-space:nowrap}}
.pin{{position:absolute;width:48px;height:48px;margin:-24px 0 0 -24px;border-radius:50%;border:5px solid #fff;color:#fff;font:800 26px/38px S,sans-serif;text-align:center;box-shadow:0 4px 12px rgba(0,0,0,.5)}}
.co{{position:absolute;background:{SURF};border-radius:20px;padding:12px 14px 13px;box-shadow:0 12px 28px rgba(0,0,0,.4);display:flex;flex-direction:column;gap:5px}}
.co .h{{display:flex;gap:8px;align-items:flex-start}}
.co .n{{flex:none;width:34px;height:34px;border-radius:50%;color:#fff;font:800 22px/34px S,sans-serif;text-align:center}}
.co .nm{{font:800 27px/1 S,sans-serif;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}}
.co .d{{font:700 20px/1.2 I,sans-serif}} .co .c{{font:400 19px/1.2 I,sans-serif;color:{MUTED}}}
.card{{position:absolute;background:{SURF};border-radius:36px;box-shadow:0 -8px 40px rgba(0,0,0,.3);padding:34px 34px 22px}}
.top{{display:flex;gap:30px}}
.post{{flex:none;display:flex;align-items:flex-start;justify-content:center}}
.post img{{border-radius:16px;box-shadow:0 12px 26px rgba(29,37,35,.28);display:block}}
.info{{flex:1;min-width:0;display:flex;flex-direction:column;gap:18px;padding-top:2px}}
.ln{{display:flex;gap:12px;align-items:flex-start;font-size:28px;font-weight:600;line-height:1.2}}
.ln svg{{flex:0 0 30px;margin-top:2px}} .ln small{{display:block;font-size:23px;font-weight:400;color:{MUTED};margin-top:3px}}
.bd{{display:inline-flex;flex-direction:column;align-self:flex-start;color:#fff;border-radius:14px;padding:9px 18px 10px;font-weight:700;font-size:25px;line-height:1.15}}
.bd small{{font-weight:600;font-size:21px;opacity:.92}}
.ph{{font:700 26px/1 S,sans-serif;letter-spacing:2px;text-transform:uppercase;color:{MUTED};margin:24px 0 6px}}
.row{{display:grid;grid-template-columns:130px 1fr 74px 132px;align-items:center;gap:14px;min-height:64px;padding:6px 0;border-top:2px solid {LINE}}}
.chip{{color:#fff;font-weight:700;font-size:19px;text-transform:uppercase;letter-spacing:1px;text-align:center;border-radius:9px;padding:6px 0}}
.rn{{font-size:25px;font-weight:600;line-height:1.15;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
.rh{{font-size:23px;color:{MUTED};text-align:right}}
.rf{{font:800 38px/.9 S,sans-serif;text-align:right}} .rf small{{font-size:24px}}
.rf em{{display:block;font:600 19px I,sans-serif;font-style:normal;color:{MUTED};margin-top:4px}}
.more{{border-top:2px solid {LINE};padding:12px 0 2px;font-size:23px;font-weight:700;color:{MUTED}}}
.lrow{{display:grid;grid-template-columns:44px 96px 1fr auto;gap:16px;align-items:center;padding:14px 0;border-top:2px solid {LINE}}}
'''
CAL = '<svg viewBox="0 0 24 24" fill="none" stroke="#0d6b67" stroke-width="2.2"><rect x="3" y="5" width="18" height="16" rx="3"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>'
PINI = '<svg viewBox="0 0 24 24" fill="none" stroke="#0d6b67" stroke-width="2.2"><path d="M12 22s-7-7.5-7-13a7 7 0 0 1 14 0c0 5.5-7 13-7 13z"/><circle cx="12" cy="9" r="2.5"/></svg>'


def page(P, body):
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}html,body{{width:{P["W"]}px;height:{P["H"]}px}}</style></head><body>{body}</body></html>'


def world(k, cx, cy, sx, sy, extra=''):
    """the island (sea picture + relief + commune borders) with map point (cx, cy) at screen (sx, sy), zoom k"""
    M = MAP()
    allc = ''.join(f'<path vector-effect="non-scaling-stroke" d="{c["d"]}"/>' for c in M['communes'])
    return (f'<div class="world" style="width:{M["W"]}px;height:{M["H"]}px;transform:translate({sx - cx * k:.1f}px,{sy - cy * k:.1f}px) scale({k:.4f})">'
            f'<img src="{OCEAN}" style="width:{M["W"]}px;height:{M["H"]}px"><img src="{island()}" style="width:{M["W"]}px;height:{M["H"]}px">'
            f'<svg width="{M["W"]}" height="{M["H"]}" viewBox="0 0 {M["W"]} {M["H"]}"><g fill="none" stroke="#fff" stroke-opacity=".7" stroke-width="1.5">{allc}</g>{extra}</svg></div>')


def chrome(P, i, n, light=True):
    """counter (top right) and dossardpei.re (bottom left), inside the safe zones"""
    return (f'<div class="cnt" style="right:{P["R"] - 30}px;top:{P["T"] - 20}px">{i}/{n}</div>'
            f'<div class="foot" style="bottom:{P["B"] - 32}px"><div><img src="{LOGO}"><div><b>Dossard Péi</b><small>dossardpei.re</small></div></div></div>')


def stat(r, ref):
    code, lab = status(r, ref)
    if code == 'complet':
        return code, 'Complet'
    if code == 'ouvert':
        return code, 'Inscriptions ouvertes'
    return code, lab


def dh(r):
    d = r['_d']; h = (r.get('_h') or '').replace('h00', 'h').lstrip('0')
    return f"{JOURS_C[d.weekday()].capitalize()} {d.day} {MOIS_C[d.month - 1]}" + (f" · {h}" if h else '')


# ------------------------------------------------------------------ 1. cover: island + callouts
def cover(P, n, rs, ref, title, lab):
    M = MAP(); W, H = P['W'], P['H']
    tt = H > 1500
    callouts = len(rs) <= 8
    TOP_T = P['T'] - 10
    head_h = 175
    if callouts:
        ch = 196 if not tt else 236
        top_y = TOP_T + head_h
        if tt:
            kf = 640 / M['W']
        else:
            kf = 520 / M['W']
        isl_h = M['H'] * kf
        cy = top_y + ch + 30 + isl_h / 2
        bot_y = cy + isl_h / 2 + 30
    else:
        kf = (900 if tt else 760) / M['W']; cy = TOP_T + head_h + 40 + M['H'] * kf / 2
    pts = []
    for r in rs:
        mx, my = P_xy(*r['ll'])
        pts.append([W / 2 + (mx - M['W'] / 2) * kf, cy + (my - M['H'] / 2) * kf])
    for i in range(len(pts)):                      # same place: spread the pins
        for j in range(i):
            if (pts[i][0] - pts[j][0]) ** 2 + (pts[i][1] - pts[j][1]) ** 2 < 46 ** 2:
                pts[i][0] += 48
    col = lambda r: STC[status(r, ref)[0]] if status(r, ref)[0] in ('complet', 'clot') else TCOL.get(r['_type'], TEAL)
    pins = ''.join(f'<div class="pin" style="left:{x:.0f}px;top:{y:.0f}px;background:{col(r)}">{k}</div>' for k, (r, (x, y)) in enumerate(zip(rs, pts), 1))
    lines = cards = ''
    if callouts:
        order = sorted(range(len(rs)), key=lambda i: pts[i][1])
        ntop = min(4, max(len(rs) - 4, (len(rs) + 1) // 2))
        rowsets = [(sorted(order[:ntop], key=lambda i: pts[i][0]), top_y), (sorted(order[ntop:], key=lambda i: pts[i][0]), bot_y)]
        side = 34 if not tt else 40
        right = W - (P['R'] - 30 if tt else side)
        avail = right - side
        cw = (avail - 3 * 14) / 4
        for row, y in rowsets:
            if not row:
                continue
            lo, hi, dd = side + cw / 2, right - cw / 2, cw + 14
            c = [min(max(pts[i][0], lo), hi) for i in row]
            for _ in range(60):
                for a in range(1, len(c)):
                    if c[a] - c[a - 1] < dd:
                        m = (c[a] + c[a - 1]) / 2; c[a - 1], c[a] = m - dd / 2, m + dd / 2
                if c[0] < lo:
                    c = [x + lo - c[0] for x in c]
                if c[-1] > hi:
                    c = [x - (c[-1] - hi) for x in c]
            for i, cx in zip(row, c):
                r = rs[i]; code, sl = stat(r, ref)
                ey = y + ch if y == top_y else y
                lines += f'<line x1="{pts[i][0]:.0f}" y1="{pts[i][1]:.0f}" x2="{cx:.0f}" y2="{ey:.0f}"/>'
                stb = f'<span class="st" style="background:{STC[code]}">{esc(sl)}</span>' if code in ('complet', 'clot', 'bientot') else ''
                cards += (f'<div class="co" style="left:{cx - cw / 2:.0f}px;top:{y:.0f}px;width:{cw:.0f}px;height:{ch}px">'
                          f'<div class="h"><span class="n" style="background:{col(r)}">{i + 1}</span><div class="nm">{esc(r["nom"])}</div></div>'
                          f'<div class="d">{esc(dh(r))}</div><div class="c">{esc(r["commune"])}</div><div style="margin-top:auto">{stb}</div></div>')
    svg = f'<svg class="abs" style="left:0;top:0" width="{W}" height="{H}"><g stroke="#fff" stroke-width="4" stroke-linecap="round" style="filter:drop-shadow(0 2px 3px rgba(0,0,0,.5))">{lines}</g></svg>'
    head = (f'<div class="abs" style="left:0;right:0;top:{TOP_T}px;display:flex;flex-direction:column;align-items:center;gap:14px">'
            f'<div class="tag">{esc(title)}</div><div class="sub">{esc(lab)}</div></div>')
    return page(P, world(kf, M['W'] / 2, M['H'] / 2, W / 2, cy) + svg + pins + cards + head + chrome(P, 1, n))


# ------------------------------------------------------------------ programme (more than 8 races)
def programme(P, i, n, rs, ref):
    W = P['W']; top = P['T'] + 40
    rws = ''
    for k, r in enumerate(rs, 1):
        code, sl = stat(r, ref)
        rws += (f'<div class="lrow"><b class="s" style="width:44px;height:44px;border-radius:50%;background:{TCOL.get(r["_type"], TEAL)};color:#fff;font-size:26px;line-height:44px;text-align:center">{k}</b>'
                f'<div style="font:700 22px/1.2 I,sans-serif">{esc(dh(r).split(" · ")[0])}</div>'
                f'<div><div class="s" style="font-size:32px;line-height:1">{esc(r["nom"])}</div><div style="font-size:21px;color:{MUTED};margin-top:4px">{esc(r["commune"])}</div></div>'
                f'<span class="st" style="background:{STC[code]}">{esc(sl if code != "ouvert" else "Ouvert")}</span></div>')
    body = (world(560 / MAP()['W'], MAP()['W'] / 2, MAP()['H'] / 2, W / 2, P['H'] / 2) + '<div class="abs" style="inset:0;background:rgba(8,59,90,.55)"></div>'
            f'<div class="abs" style="left:{P["L"] - 30}px;right:{P["R"] - 30}px;top:{top}px;text-align:center"><div class="tag">Le programme</div></div>'
            f'<div class="card" style="left:{P["L"] - 36}px;right:{P["R"] - 36}px;top:{top + 120}px">{rws}</div>')
    return page(P, body + chrome(P, i, n))


# ------------------------------------------------------------------ 2. one race: zoomed map + race card
def race(P, i, n, r, ref):
    M = MAP(); W, H = P['W'], P['H']; tt = H > 1500
    x0, y0, x1, y1 = bbox(r['commune'])
    px, py = P_xy(*r['ll'])
    k = min(820 / (x1 - x0), 700 / (y1 - y0), 4.2)
    pin_y = (P['T'] + 120) if tt else 205
    card_bottom = (P['B'] + 50) if tt else 110            # the card sits at the bottom, the map fills the rest
    poster = poster_path(r)
    if poster and 'utoi-logo' in str(poster):
        poster = None
    img = (poster or art_path(r)).as_uri()
    code, sl = stat(r, ref)
    bl = {'complet': ('Complet', ''), 'clot': ('Inscriptions ouvertes', sl.replace('Clôture ', 'clôture ')), 'bientot': (sl, ''),
          'ouvert': ('Inscriptions ouvertes', status(r, ref)[1].replace('Inscriptions ', ''))}[code]
    lieu = r.get('lieu') or ''
    lieu = '' if _same(lieu, [r['commune']]) else lieu
    rw = rows(r); more = 0
    maxr = 5 if tt else 4
    if len(rw) > maxr:
        more = len(rw) - (maxr - 1); rw = rw[:maxr - 1]
    rows_html = ''.join(f'''<div class="row"><span class="chip" style="background:{TCOL.get(t, '#666')}">{esc(TLAB.get(t, 'Course'))}</span>
      <span class="rn">{esc(nm)}</span><span class="rh">{esc(h)}</span><span class="rf">{f}{f'<em>{esc(dp)}</em>' if dp else ''}</span></div>''' for t, nm, h, f, dp in rw)
    if more:
        rows_html += f'<div class="more">+ {more} autres formats</div>'
    ne = len(r.get('epreuves', []))
    head = f"{ne} courses au programme" if ne > 1 else 'Au programme'
    nm = r['nom']; fs = 58 if len(nm) <= 20 else (50 if len(nm) <= 30 else 42)
    ph = 470 if tt else 400
    pw = 330 if tt else 290
    d = r['_d']
    date = f"{JOURS[d.weekday()].capitalize()} {d.day} {MOIS[d.month - 1]}"
    hh = (r.get('_h') or '').replace('h00', 'h').lstrip('0')
    right = (P['R'] - 40) if tt else 36
    pin = (f'<div class="abs" style="left:{W / 2}px;top:{pin_y}px"><svg class="abs" style="left:-26px;top:-72px" width="52" height="72" viewBox="0 0 60 82">'
           f'<path d="M30 80C30 80 4 48 4 28a26 26 0 0 1 52 0c0 20-26 52-26 52z" fill="{TEAL}" stroke="#fff" stroke-width="5"/><circle cx="30" cy="28" r="10" fill="#fff"/></svg>'
           f'<div class="abs" style="top:16px;left:0;transform:translateX(-50%);white-space:nowrap;text-align:center"><b class="s" style="display:inline-block;background:{INK};color:#fff;font-size:42px;padding:3px 22px 5px;border-radius:12px">{esc(r["commune"])}</b>'
           + (f'<i style="display:block;font:700 24px I,sans-serif;font-style:normal;color:#fff;margin-top:5px;text-shadow:0 1px 3px rgba(0,0,0,.8),0 0 10px rgba(0,0,0,.55)">{esc(lieu)}</i>' if lieu else '') + '</div></div>')
    tag = f'<div class="abs" style="left:{P["L"] - 30}px;top:{P["T"] - 22}px"><div class="tag" style="font-size:40px;padding:6px 20px 9px;border-radius:13px">Ce week-end</div></div>'
    card = f'''<div class="card" style="left:36px;right:{right}px;bottom:{card_bottom}px">
 <div class="top" style="min-height:{ph}px"><div class="post" style="width:{pw}px"><img src="{img}" style="max-width:{pw}px;max-height:{ph}px"></div>
  <div class="info"><div class="s" style="font-size:{fs}px;line-height:.98">{esc(nm)}</div>
   <div class="ln">{CAL}<span>{esc(date)}{f'<small>Départ {esc(hh)}</small>' if hh else ''}</span></div>
   <div class="ln">{PINI}<span>{esc(r['commune'])}{f'<small>{esc(lieu)}</small>' if lieu else ''}</span></div>
   <div class="bd" style="background:{STC[code]}">{esc(bl[0])}{f'<small>{esc(bl[1])}</small>' if bl[1] else ''}</div></div></div>
 <div class="ph">{esc(head)}</div>{rows_html}</div>'''
    shade = '<div class="abs" style="left:0;right:0;bottom:0;height:45%;background:linear-gradient(180deg,rgba(8,59,90,0),rgba(8,59,90,.85) 50%)"></div>'
    return page(P, world(k, px, py, W / 2, pin_y) + shade + pin + tag + card + chrome(P, i, n))


# ------------------------------------------------------------------ 3. end
def fin(P, n):
    M = MAP(); W, H = P['W'], P['H']
    body = (f'<div class="abs" style="inset:0;filter:blur(14px) saturate(.85)">{world(1000 / M["W"], M["W"] / 2, M["H"] / 2, W / 2, H / 2)}</div>'
            '<div class="abs" style="inset:0;background:rgba(8,59,90,.35)"></div>'
            f'<div class="abs" style="left:0;right:0;top:{H / 2 - 210}px;display:flex;flex-direction:column;align-items:center;gap:26px;text-align:center">'
            f'<div style="display:flex;align-items:center;gap:20px;background:#fff;border:6px solid {INK};border-radius:999px;padding:12px 40px 12px 16px;box-shadow:0 18px 40px rgba(0,0,0,.4)">'
            f'<img src="{LOGO}" style="width:100px"><div><div class="s" style="font-size:62px;line-height:.95">Dossard Péi</div>'
            f'<div style="font:700 30px I,sans-serif;color:{TEAL};margin-top:4px">dossardpei.re</div></div></div>'
            f'<div class="sub" style="font-size:44px">Toutes les courses de La Réunion</div>'
            f'<div style="color:#fff;font:700 30px I,sans-serif;margin-top:20px;opacity:.95">Parcours, infos et inscriptions</div></div>'
            f'<div class="abs" style="left:0;right:0;bottom:{P["B"] + 10}px;text-align:center;color:#fff;font:700 28px I,sans-serif">Enregistre ce post pour le retrouver</div>')
    return page(P, body + f'<div class="cnt" style="right:{P["R"] - 30}px;top:{P["T"] - 20}px">{n}/{n}</div>')


def build(ref, data, races):
    days = [ref + D.timedelta(days=k) for k in (4, 5, 6)]
    rs = upcoming(races, days[0], days[-1])
    rs = [r for r in rs if r['_d'] != days[0] or (r['_h'] and int(r['_h'][:2]) >= 16)]   # Friday only if evening
    if not rs:
        return None
    rs = sorted(rs, key=lambda r: (r['_d'], r['_h'] or '99'))
    first = rs[0]['_d']; last = rs[-1]['_d']
    fmt_d = lambda dd: f"{JOURS_C[dd.weekday()].capitalize()} {dd.day}"
    lab = (f"{fmt_d(first)} {MOIS[first.month - 1]}" if first == last
           else f"{fmt_d(first)}{'' if first.month == last.month else ' ' + MOIS[first.month - 1]} – {JOURS_C[last.weekday()]} {last.day} {MOIS[last.month - 1]}")
    shown = [r for r in rs if status(r, ref)[0] != 'complet'][:15]   # one slide per race still open (validé le 15/11/2026)
    pages = {}
    for fmt, P in CH.LAYOUT.items():
        extra = 0 if len(rs) <= 8 else 1
        n = 1 + extra + len(shown) + 1
        sl = [cover(P, n, rs, ref, 'Ce week-end', lab)]
        if extra:
            sl.append(programme(P, 2, n, rs, ref))
        for r in shown:
            sl.append(race(P, len(sl) + 1, n, r, ref))
        sl.append(fin(P, n))
        pages[fmt] = sl
    clot = [r for r in rs if status(r, ref)[0] == 'clot']
    lines = [f"Ce week-end, {len(rs)} course{'s' if len(rs) > 1 else ''} à La Réunion 🏃⛰️", '']
    for dd in sorted({r['_d'] for r in rs}):
        lines.append(f"📅 {JOURS_C[dd.weekday()].capitalize()} {dd.day} : " + ' · '.join(f"{r['nom']} ({r['commune']})" for r in rs if r['_d'] == dd))
    if clot:
        lines += ['', '⏳ Dernières inscriptions : ' + ' · '.join(f"{r['nom']} ({status(r, ref)[1].replace('Clôture ', '').lower()})" for r in clot)]
    lines += ['', 'Infos et inscriptions 👉 dossardpei.re (lien en bio)']
    return pages, lines, TAGS
