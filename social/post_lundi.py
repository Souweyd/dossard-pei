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
SITE = __import__('os').environ.get('POST_SITE') == '1'   # proposition du 15/11 (en attente de validation): the site's drawn landscape (sky, mountains, cream ground) behind the slides, as on the site
V2 = __import__('os').environ.get('POST_V2', '1') == '1'   # nouvelle DA validée le 15/11/2026 (POST_V2=0 : ancienne version)
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


def world(k, cx, cy, sx, sy, extra='', sea=True):
    """the island (sea picture + relief + commune borders) with map point (cx, cy) at screen (sx, sy), zoom k"""
    M = MAP()
    allc = ''.join(f'<path vector-effect="non-scaling-stroke" d="{c["d"]}"/>' for c in M['communes'])
    return (f'<div class="world" style="width:{M["W"]}px;height:{M["H"]}px;transform:translate({sx - cx * k:.1f}px,{sy - cy * k:.1f}px) scale({k:.4f})">'
            + (f'<img src="{OCEAN}" style="width:{M["W"]}px;height:{M["H"]}px">' if sea else '') + f'<img src="{island()}" style="width:{M["W"]}px;height:{M["H"]}px">'
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
    d = r['_d']; h = re.sub(r'^0(?=\d)', '', (r.get('_h') or '').replace('h00', 'h'))   # 00h01 -> 0h01, 06h -> 6h
    return f"{JOURS_C[d.weekday()].capitalize()} {d.day} {MOIS_C[d.month - 1]}" + (f" · {h}" if h else '')


# ------------------------------------------------------------------ 1. cover: island + callouts
def teaser(P, n, rs, ref, title, lab, sea=False, mood='matin'):
    """cover that makes people swipe (site style): big title, the island and numbered points only;
    the races are told on the next slides"""
    M = MAP(); W, H = P['W'], P['H']; tt = H > 1500
    top = P['T'] + (70 if not tt else 40)
    kf = (820 if tt else 740) / M['W']
    cy = top + (360 if tt else 330) + M['H'] * kf / 2
    pts = []
    for r in rs:
        mx, my = P_xy(*r['ll']); pts.append([W / 2 + (mx - M['W'] / 2) * kf, cy + (my - M['H'] / 2) * kf])
    for i in range(len(pts)):          # same place: put the point beside the others (left, right, then below)
        x0, y0, k = pts[i][0], pts[i][1], 0
        while any((pts[i][0] - pts[j][0]) ** 2 + (pts[i][1] - pts[j][1]) ** 2 < 66 ** 2 for j in range(i)) and k < 12:
            k += 1; pts[i] = [x0 + (-1) ** k * 68 * ((k + 1) // 2), y0] if k <= 4 else [x0 + (k - 6) * 34, y0 + 68]
    col = (lambda r: TCOL.get(r['_type'], TEAL)) if sea else (lambda r: STC[status(r, ref)[0]] if status(r, ref)[0] in ('complet', 'clot') else TCOL.get(r['_type'], TEAL))
    pins = ''.join(f'<div class="pin" style="left:{x:.0f}px;top:{y:.0f}px;background:{col(r)};width:64px;height:64px;margin:-32px 0 0 -32px;font-size:36px;line-height:54px">{k}</div>'
                   for k, (r, (x, y)) in enumerate(zip(rs, pts), 1))
    tc = '#fff' if sea else INK
    head = (f'<div class="abs" style="left:{P["L"]}px;right:{P["R"]}px;top:{top}px;color:{tc}">'
            f'<div style="font:700 28px/1 I,sans-serif;letter-spacing:.14em;text-transform:uppercase">{esc(lab)}</div>'
            + (titlefill(title, mood, 172 if not tt else 178) if sea else f'<div class="s" style="font-size:{150 if not tt else 160}px;line-height:.88;margin-top:16px">{esc(title)}</div>') +
            f''
            f'<div style="font:600 40px/1.25 I,sans-serif;margin-top:20px">{len(rs)} course{"s" if len(rs) > 1 else ""} à La Réunion</div></div>')
    ab, af = ('#fff', INK) if sea else (INK, '#fff')
    arrow = (f'<div class="abs" style="right:{P["R"] - 6}px;bottom:{P["B"] - 20}px;width:76px;height:76px;border-radius:50%;background:{ab};display:grid;place-items:center">'
             f'<svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="{af}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></div>')
    bg = world(kf, M['W'] / 2, M['H'] / 2, W / 2, cy) if sea else CH.decor(P, 'matin', .5) + world(kf, M['W'] / 2, M['H'] / 2, W / 2, cy, sea=False)
    return page(P, bg + pins + head + chrome(P, 1, n) + arrow)


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
    bg = CH.decor(P, 'matin', .42) + world(kf, M['W'] / 2, M['H'] / 2, W / 2, cy, sea=False) if SITE else world(kf, M['W'] / 2, M['H'] / 2, W / 2, cy)
    return page(P, bg + svg + pins + cards + head + chrome(P, 1, n))


# ------------------------------------------------------------------ programme (more than 8 races)
TYPE_ORDER = ['trail', 'route', 'cross', 'relais', 'multisport', 'marche', 'jeunes', 'autre']
TPLUR = {'trail': 'Trail', 'route': 'Route', 'cross': 'Cross', 'relais': 'Relais', 'multisport': 'Multisport', 'marche': 'Rando', 'jeunes': 'Jeunes', 'autre': 'Autres courses'}
by_type = lambda rs: sorted(rs, key=lambda r: (TYPE_ORDER.index(r['_type']) if r['_type'] in TYPE_ORDER else 99, r['_d'], r['_h'] or '99'))


def programme_types(P, i, n, rs, ref):
    """the programme grouped by discipline (rs already in that order: same numbers as the cover)"""
    W = P['W']; top = P['T'] + 40; tt = P['H'] > 1500
    small = len(rs) > 8
    fs, sub, rp = (28, 19, 8) if small else (34, 22, 12)
    out, cur = '', None
    for k, r in enumerate(rs, 1):
        t = r['_type']
        if t != cur:
            cur = t; cnt = sum(1 for x in rs if x['_type'] == t)
            out += (f'<div style="display:flex;align-items:center;gap:12px;margin:{18 if out else 6}px 0 4px"><span class="chip" style="background:{TCOL.get(t, TEAL)};padding:7px 14px;border-radius:9px">{esc(TPLUR.get(t, "Courses"))}</span>'
                    f'<span style="font:700 20px I,sans-serif;color:{MUTED}">{cnt} course{"s" if cnt > 1 else ""}</span></div>')
        code, sl = stat(r, ref)
        h = re.sub(r'^0(?=\d)', '', (r.get('_h') or '').replace('h00', 'h'))
        out += (f'<div class="lrow" style="grid-template-columns:48px 1fr auto;padding:{rp}px 0"><b class="s" style="width:48px;height:48px;border-radius:50%;background:{TCOL.get(t, TEAL)};color:#fff;font-size:28px;line-height:48px;text-align:center">{k}</b>'
                f'<div style="min-width:0"><div class="s" style="font-size:{fs}px;line-height:1">{esc(r["nom"])}</div>'
                f'<div style="font-size:{sub}px;color:{MUTED};margin-top:4px">{esc(JOURS_C[r["_d"].weekday()].capitalize())} {r["_d"].day} {MOIS_C[r["_d"].month - 1]}{" · " + esc(h) if h else ""} · {esc(r["commune"])}</div></div>'
                f'<span class="st" style="background:{STC[code]}">{esc(sl if code != "ouvert" else "Ouvert")}</span></div>')
    out = out.replace('<div class="lrow"', '<div class="lrow" data-first', 0)
    right = (P['R'] - 40) if tt else 36
    bg = f'<div class="abs" style="inset:0;filter:blur(12px) saturate(.85);opacity:.55">{world(900 / MAP()["W"], MAP()["W"] / 2, MAP()["H"] / 2, W / 2, P["H"] / 2)}</div>'
    body = (bg + f'<div class="abs" style="left:{P["L"] - 30}px;top:{P["T"] - 22}px"><div class="tag" style="font-size:40px;padding:6px 20px 9px;border-radius:13px">Le programme</div></div>'
            f'<div class="card" style="left:36px;right:{right}px;top:{top + 70}px;padding:12px 30px 12px">{out}</div>')
    return page(P, body + chrome(P, i, n))


def programme_site(P, i, n, rs, ref, sea=False):
    """the list of the week-end (numbers of the cover), on the site landscape"""
    W = P['W']; top = P['T'] + 40; tt = P['H'] > 1500
    col = lambda r: STC[status(r, ref)[0]] if status(r, ref)[0] in ('complet', 'clot') else TCOL.get(r['_type'], TEAL)
    rws = ''
    for k, r in enumerate(rs, 1):
        code, sl = stat(r, ref)
        h = re.sub(r'^0(?=\d)', '', (r.get('_h') or '').replace('h00', 'h'))
        rws += (f'<div class="lrow" style="grid-template-columns:52px 1fr auto"><b class="s" style="width:52px;height:52px;border-radius:50%;background:{col(r)};color:#fff;font-size:30px;line-height:52px;text-align:center">{k}</b>'
                f'<div style="min-width:0"><div class="s" style="font-size:34px;line-height:1">{esc(r["nom"])}</div>'
                f'<div style="font-size:22px;color:{MUTED};margin-top:5px">{esc(JOURS_C[r["_d"].weekday()].capitalize())} {r["_d"].day} {MOIS_C[r["_d"].month - 1]}{" · " + esc(h) if h else ""} · {esc(r["commune"])}</div></div>'
                f'<span class="st" style="background:{STC[code]}">{esc(sl if code != "ouvert" else "Ouvert")}</span></div>')
    right = (P['R'] - 40) if tt else 36
    bg = (f'<div class="abs" style="inset:0;filter:blur(12px) saturate(.85);opacity:.55">{world(900 / MAP()["W"], MAP()["W"] / 2, MAP()["H"] / 2, W / 2, P["H"] / 2)}</div>') if sea else CH.decor(P, 'matin', .3)
    body = (bg + f'<div class="abs" style="left:{P["L"] - 30}px;top:{P["T"] - 22}px"><div class="tag" style="font-size:40px;padding:6px 20px 9px;border-radius:13px">Le programme</div></div>'
            f'<div class="card" style="left:36px;right:{right}px;top:{top + 70}px;padding:14px 30px 10px">{rws.replace("border-top:2px solid", "border-top:2px solid", 1)}</div>')
    return page(P, body + chrome(P, i, n))


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
def race(P, i, n, r, ref, num=None):
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
    hh = re.sub(r'^0(?=\d)', '', (r.get('_h') or '').replace('h00', 'h'))
    right = (P['R'] - 40) if tt else 36
    pin = (f'<div class="abs" style="left:{W / 2}px;top:{pin_y}px"><svg class="abs" style="left:-26px;top:-72px" width="52" height="72" viewBox="0 0 60 82">'
           f'<path d="M30 80C30 80 4 48 4 28a26 26 0 0 1 52 0c0 20-26 52-26 52z" fill="{TEAL}" stroke="#fff" stroke-width="5"/><circle cx="30" cy="28" r="10" fill="#fff"/></svg>'
           f'<div class="abs" style="top:16px;left:0;transform:translateX(-50%);white-space:nowrap;text-align:center"><b class="s" style="display:inline-block;background:{INK};color:#fff;font-size:42px;padding:3px 22px 5px;border-radius:12px">{esc(r["commune"])}</b>'
           + (f'<i style="display:block;font:700 24px I,sans-serif;font-style:normal;color:#fff;margin-top:5px;text-shadow:0 1px 3px rgba(0,0,0,.8),0 0 10px rgba(0,0,0,.55)">{esc(lieu)}</i>' if lieu else '') + '</div></div>')
    tag = f'<div class="abs" style="left:{P["L"] - 30}px;top:{P["T"] - 22}px"><div class="tag" style="font-size:40px;padding:6px 20px 9px;border-radius:13px">Ce week-end</div></div>'
    card = f'''<div class="card" style="left:36px;right:{right}px;bottom:{card_bottom}px">
 <div class="top" style="min-height:{ph}px"><div class="post" style="width:{pw}px"><img src="{img}" style="max-width:{pw}px;max-height:{ph}px"></div>
  <div class="info"><div class="s" style="font-size:{fs}px;line-height:.98">{f'<b style="display:inline-block;vertical-align:.12em;width:{fs * .8:.0f}px;height:{fs * .8:.0f}px;margin-right:12px;border-radius:50%;background:{TCOL.get(r["_type"], TEAL)};color:#fff;font-size:{fs * .55:.0f}px;line-height:{fs * .8:.0f}px;text-align:center">{num}</b>' if num else ''}{esc(nm)}</div>
   <div class="ln">{CAL}<span>{esc(date)}{f'<small>Départ {esc(hh)}</small>' if hh else ''}</span></div>
   <div class="ln">{PINI}<span>{esc(r['commune'])}{f'<small>{esc(lieu)}</small>' if lieu else ''}</span></div>
   <div class="bd" style="background:{STC[code]}">{esc(bl[0])}{f'<small>{esc(bl[1])}</small>' if bl[1] else ''}</div></div></div>
 <div class="ph">{esc(head)}</div>{rows_html}</div>'''
    if SITE:   # the site's drawn landscape, the map in a rounded window at the top, the card under it
        wt, wh = P['T'] + 40, (430 if tt else 330)
        win = (f'<div class="abs" style="left:36px;right:{right}px;top:{wt}px;height:{wh}px;border-radius:30px;overflow:hidden;border:6px solid #fff;box-shadow:0 16px 36px rgba(29,37,35,.25)">'
               f'<div class="abs" style="inset:0;background:{SEA}">{world(k, px, py, (W - 36 - right) / 2 - 6, wh * .58)}</div>'
               + pin.replace(f'left:{W / 2}px;top:{pin_y}px', f'left:{(W - 36 - right) / 2 - 6:.0f}px;top:{wh * .58:.0f}px') + '</div>')
        card = card.replace(f'bottom:{card_bottom}px', f'top:{wt + wh + 26}px')
        return page(P, CH.decor(P, 'matin', .3) + win + tag + card + chrome(P, i, n))
    shade = '<div class="abs" style="left:0;right:0;bottom:0;height:45%;background:linear-gradient(180deg,rgba(8,59,90,0),rgba(8,59,90,.85) 50%)"></div>'
    return page(P, world(k, px, py, W / 2, pin_y) + shade + pin + tag + card + chrome(P, i, n))


# ------------------------------------------------------------------ 3. end
def fin(P, n):
    if SITE:
        return CH.fin(P, 'matin').replace('</body>', f'<div class="cnt" style="position:absolute;right:{P["R"] - 30}px;top:{P["T"] - 20}px;background:rgba(29,37,35,.55);color:#fff;font:700 24px/1 sans-serif;padding:9px 16px;border-radius:999px">{n}/{n}</div></body>')
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



def titlefill(title, mood, size):
    """big title whose letters show the site's drawn landscape (sky, mountains, hills) in the post's mood"""
    import base64
    svg = CH.decor({'W': 860, 'H': 190}, mood, .58).replace('class="decor" ', 'xmlns="http://www.w3.org/2000/svg" ')
    url = 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode()
    return (f'<div class="s" style="display:inline-block;font-size:{size}px;line-height:.92;white-space:nowrap;margin-top:14px;padding:0 6px 8px 0;'
            f'background:url({url}) 0 0/100% 100%;-webkit-background-clip:text;background-clip:text;color:transparent;filter:{"brightness(2.1) saturate(1.2) " if mood == "soir" else ""}drop-shadow(0 6px 18px rgba(0,0,0,.35))">{esc(title)}</div>')   # evening sky is too dark on the sea: lit up


# ------------------------------------------------------------------ ambiance (validée le 16/11/2026)
# one sky per post type, drawn from the site's own landscape, sharp at the top and fading into the sea and the island :
# matin = ce week-end, couchant = thèmes, lagon = région, soir = mois. Titles in a plain colour chosen for contrast.
AMB_TXT = {'matin': INK, 'couchant': INK, 'lagon': INK, 'soir': '#ffffff'}
AMB_MASK = 'linear-gradient(180deg,#000 0,#000 56%,rgba(0,0,0,.75) 70%,rgba(0,0,0,.35) 84%,transparent 100%)'


def ambiance(P, mood, h=None):
    """the site's drawn landscape (sky, mountains, hills) in the post's mood, across the top of a cover, fading out downwards"""
    h = h or (1020 if P['H'] > 1500 else 760)
    svg = CH.decor({'W': P['W'], 'H': h}, mood, .70, cream_from=h * 3)
    return (f'<div class="abs" style="left:0;right:0;top:0;height:{h}px;-webkit-mask-image:{AMB_MASK};mask-image:{AMB_MASK}">{svg}</div>')


def titlesolid(title, mood, size):
    """big title in one plain colour (ink on the light skies, white on the evening sky)"""
    col = AMB_TXT.get(mood, '#fff')
    sh = '0 4px 14px rgba(0,0,0,.35)' if col == '#ffffff' else '0 2px 10px rgba(255,255,255,.25)'
    return (f'<div class="s" style="display:inline-block;font-size:{size}px;line-height:.92;white-space:nowrap;margin-top:14px;padding:0 6px 8px 0;color:{col};text-shadow:{sh}">{esc(title)}</div>')


PERSO = ROOT / 'social' / 'assets' / 'perso'      # drawings of the game « Une histoire de dossard » (Sam, Ana)


def perso(ref, pose, who=None):
    """Sam one week, Ana the next one (who forces one of them)"""
    who = who or ('jeremi' if ref.isocalendar()[1] % 2 == 0 else 'nadia')
    return (PERSO / f'{who}{pose}.svg').read_text()


def bubble(text, side='left'):
    tail = 'left:46px' if side == 'left' else 'right:46px'
    return (f'<div style="position:relative;display:inline-block;background:#fff;color:{INK};font:800 34px/1.1 S,sans-serif;padding:14px 22px 16px;border-radius:22px;box-shadow:0 10px 24px rgba(0,0,0,.3)">{esc(text)}'
            f'<span style="position:absolute;{tail};bottom:-16px;width:0;height:0;border:16px solid transparent;border-top-color:#fff;border-bottom:0"></span></div>')


def derniere(P, i, n, rs, ref):
    """the races whose registrations close before the week-end (only when there are some)"""
    W, H = P['W'], P['H']; tt = H > 1500; top = P['T'] + 40
    right = (P['R'] - 40) if tt else 36
    rws = ''
    for r in rs:
        code, sl = stat(r, ref)
        rws += (f'<div class="lrow" style="grid-template-columns:1fr auto"><div style="min-width:0"><div class="s" style="font-size:36px;line-height:1">{esc(r["nom"])}</div>'
                f'<div style="font-size:22px;color:{MUTED};margin-top:5px">{esc(dh(r))} · {esc(r["commune"])}</div></div>'
                f'<span class="st" style="background:{STC["clot"]};font-size:24px;padding:9px 14px">{esc(sl)}</span></div>')
    ph = 420 if tt else 380
    body = (f'<div class="abs" style="inset:0;filter:blur(12px) saturate(.85);opacity:.55">{world(900 / MAP()["W"], MAP()["W"] / 2, MAP()["H"] / 2, W / 2, H / 2)}</div>'
            f'<div class="abs" style="left:{P["L"] - 30}px;top:{P["T"] - 22}px"><div class="tag" style="background:{STC["clot"]}">Dernière chance</div></div>'
            f'<div class="abs" style="left:{P["L"] - 30}px;right:{right}px;top:{top + 100}px;color:#fff;font:600 30px/1.3 I,sans-serif">Les inscriptions ferment avant le week-end :</div>'
            f'<div class="card" style="left:36px;right:{right}px;top:{top + 160}px;padding:10px 30px 8px">{rws}</div>'
            )
    return page(P, body + chrome(P, i, n))


def fin_sea(P, n, ref, duo=False):
    """end: the address, and Sam or Ana of the game celebrating (both of them for the team themes)"""
    M = MAP(); W, H = P['W'], P['H']; tt = H > 1500
    ph = 560 if tt else 500
    body = (f'<div class="abs" style="inset:0;filter:blur(14px) saturate(.85)">{world(1000 / M["W"], M["W"] / 2, M["H"] / 2, W / 2, H / 2)}</div>'
            '<div class="abs" style="inset:0;background:rgba(8,59,90,.35)"></div>'
            f'<div class="abs" style="left:0;right:0;top:{P["T"] + 60}px;display:flex;flex-direction:column;align-items:center;gap:22px;text-align:center">'
            f'<div style="display:flex;align-items:center;gap:20px;background:#fff;border:6px solid {INK};border-radius:999px;padding:12px 40px 12px 16px;box-shadow:0 18px 40px rgba(0,0,0,.4)">'
            f'<img src="{LOGO}" style="width:100px"><div><div class="s" style="font-size:62px;line-height:.95">Dossard Péi</div>'
            f'<div style="font:700 30px I,sans-serif;color:{TEAL};margin-top:4px">dossardpei.re</div></div></div>'
            f'<div class="sub" style="font-size:42px">Toutes les courses de La Réunion</div></div>'
            f'<div class="abs" style="left:0;right:0;bottom:{P["B"] + 70}px;display:flex;justify-content:center;align-items:flex-end;gap:10px">'
            + (f'<div style="width:{ph * .74:.0f}px;height:{ph}px">{perso(ref, 3)}</div>'
               f'<div style="margin-bottom:{ph * .55:.0f}px">{bubble("Lé pa loin ! On se retrouve sur la ligne ?")}</div></div>' if not duo else
               f'<div style="width:{ph * .74:.0f}px;height:{ph}px">{perso(ref, 3, "jeremi")}</div>'
               f'<div style="width:{ph * .74:.0f}px;height:{ph}px;margin-left:-20px">{perso(ref, 3, "nadia")}</div></div>'
               f'<div class="abs" style="left:0;right:0;bottom:{P["B"] + 70 + ph * .98:.0f}px;text-align:center">{bubble("On fait équipe ? Lé pa loin !")}</div>')
            + f'<div class="abs" style="left:0;right:0;bottom:{P["B"] + 6}px;text-align:center;color:#fff;font:700 26px I,sans-serif;opacity:.95">Joue aussi à « Une histoire de dossard » sur dossardpei.re/jeu</div>')
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
        if SITE:   # teaser cover, then the programme, then one slide per open race
            n = 2 + len(shown) + 1
            sl = [teaser(P, n, rs, ref, 'Ce week-end', lab.upper()), programme_site(P, 2, n, rs, ref)]
        elif not V2:   # version in use until the new one is validated
            extra = 0 if len(rs) <= 8 else 1
            n = 1 + extra + len(shown) + 1
            sl = [cover(P, n, rs, ref, 'Ce week-end', lab)]
            if extra:
                sl.append(programme(P, 2, n, rs, ref))
        else:      # sea, title filled with the landscape (morning, as the Monday posts before)
            last = [r for r in rs if status(r, ref)[0] == 'clot']
            n = 2 + (1 if last else 0) + len(shown) + 1
            rt = by_type(rs)
            sl = [cover_weekend_v2(P, n, rt, ref, lab.upper()), programme_types(P, 2, n, rt, ref)]   # couverture resserrée sur les courses (16/11/2026)
            if last:
                sl.append(derniere(P, 3, n, last, ref))
            # one slide per open race, in the order of the programme, with its number
            shown = [r for r in rt if status(r, ref)[0] != 'complet'][:15]
            for r in shown:
                sl.append(race(P, len(sl) + 1, n, r, ref, num=rt.index(r) + 1))
            shown = []
        for r in shown:
            sl.append(race(P, len(sl) + 1, n, r, ref))
        sl.append(fin_sea(P, n, ref) if V2 and not SITE else fin(P, n))
        pages[fmt] = sl
    clot = [r for r in rs if status(r, ref)[0] == 'clot']
    lines = [f"Ce week-end, {len(rs)} course{'s' if len(rs) > 1 else ''} à La Réunion 🏃⛰️", '']
    for dd in sorted({r['_d'] for r in rs}):
        lines.append(f"📅 {JOURS_C[dd.weekday()].capitalize()} {dd.day} : " + ' · '.join(f"{r['nom']} ({r['commune']})" for r in rs if r['_d'] == dd))
    if clot:
        lines += ['', '⏳ Dernières inscriptions : ' + ' · '.join(f"{r['nom']} ({status(r, ref)[1].replace('Clôture ', '').lower()})" for r in clot)]
    lines += ['', 'Infos et inscriptions 👉 dossardpei.re (lien en bio)']
    return pages, lines, TAGS


# ------------------------------------------------------------------ same style for the other posts (Wednesday theme, Friday region)
def cover_v2(P, n, kicker, title, sub, mood, rs, ref, communes=None, numbered=False):
    """sea cover: kicker, title whose letters show the landscape in the post's mood, the island (or the region) with the races"""
    M = MAP(); W, H = P['W'], P['H']; tt = H > 1500
    top = P['T'] + (70 if not tt else 40)
    lines = title.split('<br>')
    size = int(min(172 if not tt else 178, (W - 2 * P['L']) / (0.44 * max(len(l) for l in lines))))
    th = 20 + sum(size * .92 + 8 for _ in lines)
    head = (f'<div class="abs" style="left:{P["L"]}px;right:{P["R"]}px;top:{top}px;color:{AMB_TXT.get(mood, "#fff")}">'
            f'<div style="font:700 28px/1 I,sans-serif;letter-spacing:.14em;text-transform:uppercase">{esc(kicker)}</div>'
            + ''.join(f'<div style="margin-top:{-size * .2 if i else 0:.0f}px">{titlesolid(l, mood, size)}</div>' for i, l in enumerate(lines)) +
            f'<div style="font:600 36px/1.25 I,sans-serif;margin-top:24px">{esc(sub)}</div></div>')
    y0 = top + 60 + th + 60 + 36
    y1 = H - P['B'] - 120
    if communes:
        xs, ys = [], []
        for c in M['communes']:
            if c['nom'] in communes:
                v = [float(t) for t in re.findall(r'-?\d+\.?\d*', c['d'])]; xs += v[0::2]; ys += v[1::2]
        cx, cy0, bw, bh = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, max(xs) - min(xs), max(ys) - min(ys)
        kf = min((W - 120) / bw, (y1 - y0) / bh, 3)
    else:
        cx, cy0 = M['W'] / 2, M['H'] / 2; kf = min((W - 300) / M['W'], (y1 - y0) / M['H'])
    sy = (y0 + y1) / 2
    pts = []
    for r in rs:
        mx, my = P_xy(*r['ll']); pts.append([W / 2 + (mx - cx) * kf, sy + (my - cy0) * kf])
    big = 58 if numbered else 30
    for i in range(len(pts)):
        x0, yy, k = pts[i][0], pts[i][1], 0
        while any((pts[i][0] - pts[j][0]) ** 2 + (pts[i][1] - pts[j][1]) ** 2 < (big + 4) ** 2 for j in range(i)) and k < 12:
            k += 1; pts[i] = [x0 + (-1) ** k * (big + 6) * ((k + 1) // 2), yy] if k <= 4 else [x0 + (k - 6) * big / 2, yy + big + 6]
    pins = ''.join(f'<div class="pin" style="left:{x:.0f}px;top:{y:.0f}px;background:{TCOL.get(r["_type"], TEAL)};width:{big}px;height:{big}px;margin:-{big / 2:.0f}px 0 0 -{big / 2:.0f}px;font-size:{big * .55:.0f}px;line-height:{big - 10}px;border-width:{5 if numbered else 4}px">{k if numbered else ""}</div>'
                   for k, (r, (x, y)) in enumerate(zip(rs, pts), 1))
    arrow = (f'<div class="abs" style="right:{P["R"] - 6}px;bottom:{P["B"] - 20}px;width:76px;height:76px;border-radius:50%;background:#fff;display:grid;place-items:center">'
             f'<svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="{INK}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></div>')
    fade = ambiance(P, mood)   # the post's sky, fading into the sea and the island
    return page(P, world(kf, cx, cy0, W / 2, sy) + fade + pins + head + chrome(P, 1, n) + arrow)


def list_v2(P, i0, n, tag, rs, ref, numbered=False, grouped=True):
    """the races as rows on cards (several slides when there are many)"""
    W = P['W']; tt = P['H'] > 1500; top = P['T'] + 40
    right = (P['R'] - 40) if tt else 36
    out = []
    for p0, p1 in _pages(P, rs, grouped):
        rws, cur = '', None
        for k, r in enumerate(rs[p0:p1], p0 + 1):
            if grouped and r['_type'] != cur:     # discipline header (repeated at the top of a following slide)
                cur = r['_type']; cnt = sum(1 for x in rs if x['_type'] == cur)
                rws += (f'<div style="display:flex;align-items:center;gap:12px;margin:{14 if rws else 6}px 0 2px"><span class="chip" style="background:{TCOL.get(cur, TEAL)};padding:7px 14px;border-radius:9px">{esc(TPLUR.get(cur, "Courses"))}</span>'
                        f'<span style="font:700 20px I,sans-serif;color:{MUTED}">{cnt} course{"s" if cnt > 1 else ""}</span></div>')
            code, sl = stat(r, ref)
            h = re.sub(r'^0(?=\d)', '', (r.get('_h') or '').replace('h00', 'h'))
            num = (f'<b class="s" style="width:46px;height:46px;border-radius:50%;background:{TCOL.get(r["_type"], TEAL)};color:#fff;font-size:27px;line-height:46px;text-align:center">{k}</b>' if numbered
                   else f'<span style="width:16px;height:16px;border-radius:50%;background:{TCOL.get(r["_type"], TEAL)};margin:0 15px"></span>')
            rws += (f'<div class="lrow" style="grid-template-columns:46px 1fr auto;padding:10px 0">{num}'
                    f'<div style="min-width:0"><div class="s" style="font-size:31px;line-height:1">{esc(r["nom"])}</div>'
                    f'<div style="font-size:21px;color:{MUTED};margin-top:4px">{esc(JOURS_C[r["_d"].weekday()].capitalize())} {r["_d"].day} {MOIS_C[r["_d"].month - 1]}{" · " + esc(h) if h else ""} · {esc(r["commune"])}</div></div>'
                    f'<span class="st" style="background:{STC[code]}">{esc(sl if code != "ouvert" else "Ouvert")}</span></div>')
        bg = f'<div class="abs" style="inset:0;filter:blur(12px) saturate(.85);opacity:.55">{world(900 / MAP()["W"], MAP()["W"] / 2, MAP()["H"] / 2, W / 2, P["H"] / 2)}</div>'
        out.append(page(P, bg + f'<div class="abs" style="left:{P["L"] - 30}px;top:{P["T"] - 22}px"><div class="tag" style="font-size:40px;padding:6px 20px 9px;border-radius:13px">{esc(tag)}</div></div>'
                        f'<div class="card" style="left:36px;right:{right}px;top:{top + 70}px;padding:8px 30px 8px">{rws}</div>' + chrome(P, i0 + len(out), n)))
    return out


ROW_H, HEAD_H = 84, 58      # rendered height of a race row and of a discipline header (px)


def _pages(P, rs, grouped=True):
    """cuts the list into slides filled down to the brand pill (headers counted), never one race alone on the last one"""
    room = (P['H'] - P['B'] - 130) - (P['T'] + 110) - 20
    out, p0, used, cur = [], 0, 0, None
    for k, r in enumerate(rs):
        h = ROW_H + (HEAD_H if grouped and (r['_type'] != cur or k == p0) else 0)
        if used + h > room and k > p0:
            out.append([p0, k]); p0, used = k, ROW_H + (HEAD_H if grouped else 0)
        else:
            used += h
        cur = r['_type']
    out.append([p0, len(rs)])
    if len(out) > 1 and out[-1][1] - out[-1][0] == 1:     # a lone race: take one more from the previous slide
        out[-2][1] -= 1; out[-1][0] -= 1
    return [tuple(x) for x in out]


def n_list_v2(P, rs, grouped=True):
    return len(_pages(P, rs, grouped))


def how_v2(P, i, n, feature, title, steps, shot):
    """« Sur le site » : the steps, and a capture of the site in a white frame"""
    W, H = P['W'], P['H']; tt = H > 1500
    right = (P['R'] - 40) if tt else 36
    st = ''.join(f'<div style="display:flex;gap:16px;align-items:center;font:600 30px/1.2 I,sans-serif;padding:7px 0"><span class="s" style="flex:none;width:46px;height:46px;border-radius:50%;background:{TEAL};color:#fff;display:grid;place-items:center;font-size:27px">{k}</span><span>{s}</span></div>'
                 for k, s in enumerate(steps, 1))
    top = P['T'] + 40
    stop = top + 90 + 80
    vtop = stop + 30 + 64 * len(steps) + 40
    maxw, maxh = W - 36 - right - 40, H - P['B'] - 120 - vtop
    res = shot(maxw, maxh) if shot else None
    vis = ''
    if res:
        h_, w_, hh = res
        vis = f'<div class="abs" style="left:{36 + (W - 36 - right - w_) / 2:.0f}px;top:{vtop}px;border:6px solid #fff;border-radius:18px;overflow:hidden;box-shadow:0 16px 36px rgba(0,0,0,.4);background:#fff">{h_}</div>'
    bg = f'<div class="abs" style="inset:0;filter:blur(12px) saturate(.85);opacity:.55">{world(900 / MAP()["W"], MAP()["W"] / 2, MAP()["H"] / 2, W / 2, H / 2)}</div>'
    return page(P, bg + f'<div class="abs" style="left:{P["L"] - 30}px;top:{P["T"] - 22}px"><div class="tag" style="font-size:40px;padding:6px 20px 9px;border-radius:13px">Sur le site · {esc(feature)}</div></div>'
                f'<div class="abs s" style="left:{P["L"] - 30}px;right:{right}px;top:{top + 80}px;color:#fff;font-size:64px;line-height:1">{esc(title)}</div>'
                f'<div class="card" style="left:36px;right:{right}px;top:{stop + 20}px;padding:12px 28px">{st}</div>' + vis + chrome(P, i, n))


def cover_cal_v2(P, n, y, m, rs, ref):
    """sea cover for the month (validée le 15/11/2026) : the month grid on a cream panel ; race days filled in teal with a white band holding one dot per race (colour of its discipline)"""
    import calendar
    M = MAP(); W, H = P['W'], P['H']; tt = H > 1500
    top = P['T'] + (56 if not tt else 40)
    title = f'{MOIS[m - 1].capitalize()} {y}'
    size = int(min(150 if not tt else 160, (W - 2 * P['L']) / (0.44 * len(title))))
    head = (f'<div class="abs" style="left:{P["L"]}px;right:{P["R"]}px;top:{top}px;color:{AMB_TXT.get("soir", "#fff")}">'
            f'<div style="font:700 28px/1 I,sans-serif;letter-spacing:.14em;text-transform:uppercase">Le programme du mois</div>'
            f'<div>{titlesolid(title, "soir", size)}</div>'
            f'<div style="font:600 36px/1.25 I,sans-serif;margin-top:10px">{len(rs)} courses à La Réunion</div></div>')
    w = W - P['L'] - (P['R'] if not tt else P['L'])
    gap = 10; pad = 26
    cw = (w - 2 * pad - 6 * gap) / 7
    weeks = calendar.Calendar(0).monthdatescalendar(y, m)
    ch = cw * (.86 if not tt else 1.16)
    hdr = ''.join(f'<div style="text-align:center;font:700 21px/1 I,sans-serif;letter-spacing:.08em;color:{TEAL if k >= 5 else MUTED}">{j.upper().rstrip(".")}</div>' for k, j in enumerate(JOURS_C))
    cells = ''
    for wk in weeks:
        for k, dd in enumerate(wk):
            out = dd.month != m
            day = [r for r in rs if r['_d'] <= dd <= (D.date.fromisoformat(r['fin']) if r.get('fin') else r['_d'])] if not out else []
            dz = 18 if not tt else 20
            dots = ''.join(f'<i style="display:block;width:{dz}px;height:{dz}px;border-radius:50%;background:{TCOL.get(r["_type"], MUTED)}"></i>' for r in day[:4])
            if len(day) > 4:
                dots += f'<b style="font:800 22px/1 S,sans-serif;color:{INK}">+{len(day) - 4}</b>'
            num = f'<div class="s" style="font-size:{30 if not tt else 34}px;line-height:1;color:{"#fff" if day else "#b7aea2"};padding:8px 9px 0">{dd.day}</div>'
            if out:
                cells += f'<div style="height:{ch:.0f}px"></div>'
            elif day:   # race day : teal cell, white number, white band with one dot per race
                cells += (f'<div style="height:{ch:.0f}px;border-radius:14px;background:{TEAL};box-shadow:0 6px 14px rgba(13,107,103,.4);display:flex;flex-direction:column;justify-content:space-between;overflow:hidden">'
                          f'{num}<div style="background:#fff;margin:0 5px 5px;border-radius:9px;padding:5px 6px;display:flex;flex-wrap:wrap;gap:4px;align-items:center;min-height:{dz + 10}px">{dots}</div></div>')
            else:
                cells += f'<div style="height:{ch:.0f}px;border-radius:14px;background:{"#efe8dc" if k >= 5 else "transparent"}">{num}</div>'
    used = [t for t in TYPE_ORDER if any(r['_type'] == t for r in rs)]
    legend = ''.join(f'<span style="display:inline-flex;align-items:center;gap:8px;font:600 22px I,sans-serif;color:{INK}"><i style="width:16px;height:16px;border-radius:50%;background:{TCOL.get(t, MUTED)}"></i>{TPLUR.get(t, t)} · {sum(r["_type"] == t for r in rs)}</span>' for t in used)
    cal_h = pad * 2 + 21 + 14 + len(weeks) * (ch + gap) + 54
    y0 = top + 28 + size * .92 + 22 + 46 + (34 if not tt else 60)
    panel = (f'<div class="abs" style="left:{P["L"]}px;top:{y0:.0f}px;width:{w}px;background:{SURF};border-radius:32px;padding:{pad}px;box-shadow:0 24px 60px rgba(0,0,0,.4)">'
             f'<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:{gap}px;margin-bottom:14px">{hdr}</div>'
             f'<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:{gap}px">{cells}</div>'
             f'<div style="display:flex;flex-wrap:wrap;gap:10px 24px;margin-top:18px;padding-top:16px;border-top:2px solid {LINE}">{legend}</div></div>')
    bg = (f'<div class="abs" style="inset:0;filter:blur(14px) saturate(.85)">{world(1000 / M["W"], M["W"] / 2, M["H"] / 2, W / 2, H * .62)}</div>'
          '<div class="abs" style="inset:0;background:rgba(8,59,90,.45)"></div>'
          + ambiance(P, "soir"))   # the post's sky over the blurred island
    arrow = (f'<div class="abs" style="right:{P["R"] - 6}px;bottom:{P["B"] - 20}px;width:76px;height:76px;border-radius:50%;background:#fff;display:grid;place-items:center">'
             f'<svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="{INK}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></div>')
    return page(P, bg + head + panel + chrome(P, 1, n) + arrow)


def cover_region_v2(P, n, name, sub, rs, communes):
    """lagoon cover for a region (validée le 15/11/2026) : tight zoom on the region's races, the rest of the island dimmed,
    the region's communes outlined in white, big numbered pins (numbers of the list), commune names under the pins"""
    M = MAP(); W, H = P['W'], P['H']; tt = H > 1500
    top = P['T'] + (56 if not tt else 40)
    lines = ['Courir dans', name]
    size = int(min(150 if not tt else 160, (W - 2 * P['L']) / (0.44 * max(len(l) for l in lines))))
    head = (f'<div class="abs" style="left:{P["L"]}px;right:{P["R"]}px;top:{top}px;color:{AMB_TXT.get("lagon", "#fff")}">'
            f'<div style="font:700 28px/1 I,sans-serif;letter-spacing:.14em;text-transform:uppercase">Près de chez toi</div>'
            + ''.join(f'<div style="margin-top:{-size * .2 if i else 0:.0f}px">{titlesolid(l, "lagon", size)}</div>' for i, l in enumerate(lines)) +
            f'<div style="font:600 36px/1.25 I,sans-serif;margin-top:24px">{esc(sub)}</div></div>')
    y0 = top + 28 + 2 * (size * .92 + 8) + 70 + 40
    y1 = H - P['B'] - 130
    # frame : the races (and their communes' centres), with a margin
    pts = [P_xy(*r['ll']) for r in rs]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    mx, my = (max(xs) - min(xs)) * .22 + 40, (max(ys) - min(ys)) * .22 + 40
    bx0, bx1, by0, by1 = min(xs) - mx, max(xs) + mx, min(ys) - my, max(ys) + my
    kf = min((W - (2 * P['L'] if not tt else 40)) / (bx1 - bx0), (y1 - y0) / (by1 - by0), 1000 / M['W'] * 3.2)
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    sy = (y0 + y1) / 2
    inreg = lambda c: _same(c['nom'], communes)        # map names differ (« Tampon », « Étang-Salé »)
    others = ''.join(f'<path d="{c["d"]}"/>' for c in M['communes'] if not inreg(c))
    mine = ''.join(f'<path vector-effect="non-scaling-stroke" d="{c["d"]}"/>' for c in M['communes'] if inreg(c))
    extra = (f'<g fill="#083b5a" fill-opacity=".55">{others}</g>'
             f'<g fill="none" stroke="#fff" stroke-width="4" stroke-linejoin="round">{mine}</g>')
    scr = [[W / 2 + (x - cx) * kf, sy + (y - cy) * kf] for x, y in pts]
    big = 64
    for i in range(len(scr)):
        x0, yy, k = scr[i][0], scr[i][1], 0
        while any((scr[i][0] - scr[j][0]) ** 2 + (scr[i][1] - scr[j][1]) ** 2 < (big + 6) ** 2 for j in range(i)) and k < 14:
            k += 1; scr[i] = [x0 + (-1) ** k * (big + 8) * ((k + 1) // 2), yy] if k <= 4 else [x0 + (k - 6) * big / 2, yy + big + 8]
    pins = ''.join(f'<div class="pin" style="left:{x:.0f}px;top:{y:.0f}px;background:{TCOL.get(r["_type"], TEAL)};width:{big}px;height:{big}px;margin:-{big / 2:.0f}px 0 0 -{big / 2:.0f}px;font-size:{big * .55:.0f}px;line-height:{big - 12}px;border-width:6px">{k}</div>'
                   for k, (r, (x, y)) in enumerate(zip(rs, scr), 1))
    icx, icy = W / 2 + (M['W'] / 2 - cx) * kf, sy + (M['H'] / 2 - cy) * kf
    leaders, labs = place_labels(rs, scr, big, W, y0 - 10, H - P['B'] - 100, (icx, icy), land=land_fn(kf, cx, cy, W, sy))
    arrow = (f'<div class="abs" style="right:{P["R"] - 6}px;bottom:{P["B"] - 20}px;width:76px;height:76px;border-radius:50%;background:#fff;display:grid;place-items:center">'
             f'<svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="{INK}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></div>')
    fade = ambiance(P, "lagon", 690 if P['H'] <= 1500 else 950)   # the post's sky, fading into the sea and the island
    return page(P, world(kf, cx, cy, W / 2, sy, extra) + fade + leaders + pins + labs + head + chrome(P, 1, n) + arrow)


# ------------------------------------------------------------------ theme covers (16/11/2026)
def _team(r):
    """team size of a relay race, read in the name / note of its relay formats (None if not said)"""
    for e in r.get('epreuves', []):
        if e.get('type') != 'relais':
            continue
        t = f"{e.get('nom', '')} {e.get('note', '')}".lower()
        for pat in (r'équipes? de (\d+)(?: ou (\d+))?', r'relais à (\d+)', r'\bà (\d+)\b', r'(\d+) relayeurs'):
            m = re.search(pat, t)
            if m:
                return (int(m.group(1)), int(m.group(2)) if m.lastindex and m.lastindex > 1 and m.group(2) else None)
        if 'duo' in t or 'binôme' in t:
            return (2, None)
    return None


def _d(r):
    return f"{['lun.', 'mar.', 'mer.', 'jeu.', 'ven.', 'sam.', 'dim.'][r['_d'].weekday()]} {r['_d'].day} {MOIS_C[r['_d'].month - 1]}"


def _big(txt, small='', size=150):
    return f'<div class="s" style="font-size:{size}px;line-height:.9;color:{INK}">{txt}<small style="font-size:{size * .4:.0f}px"> {small}</small></div>'


def hero_relais(rs, nmax=None):
    """the team sizes on offer, nothing else (the races are on the next slides)"""
    kms = [e['km'] for r in rs for e in r['epreuves'] if e.get('type') == 'relais' and e.get('km')]
    sizes = sorted({t[0] for t in map(_team, rs) if t} | {t[1] for t in map(_team, rs) if t and t[1]})
    chips = ''.join(
        f'<div style="display:flex;flex-direction:column;align-items:center;gap:12px;background:{TEAL};color:#fff;border-radius:22px;padding:24px 0 20px;flex:1">'
        f'<div style="display:flex;padding-left:10px">' + ''.join(f'<i style="display:block;width:34px;height:34px;border-radius:50%;background:#fff;border:3px solid {TEAL};margin-left:-12px"></i>' for _ in range(n)) + '</div>'
        f'<div class="s" style="font-size:80px;line-height:.9">à {n}</div></div>' for n in sizes)
    return (f'<div class="s" style="font-size:30px;letter-spacing:2px;text-transform:uppercase;color:{MUTED}">Il y en a pour toutes les équipes</div>'
            f'<div style="display:flex;gap:14px;margin:20px 0 22px">{chips}</div>'
            f'<div style="font:700 34px/1.2 I,sans-serif">{len(rs)} relais, de {fmt_km(min(kms))} à {fmt_km(max(kms))} km</div>')


def hero_bars(rs, key, unit, lab):
    """one big number (the record) and the bars as a silhouette, without the names"""
    vals = list((max(e[key] for e in es), r) for r in rs if (es := [e for e in r['epreuves'] if (e.get(key) or 0) > 0 and e.get('type') in ('trail', 'route', 'marche')]))
    vals.sort(key=lambda v: -v[0])
    vmax, vmin = vals[0][0], vals[-1][0]
    fmt = (lambda v: f"{v:,.0f}".replace(',', ' ')) if key == 'dp' else fmt_km
    bars = ''.join(f'<div style="flex:1;height:{max(10, 100 * v / vmax):.0f}%;border-radius:10px 10px 0 0;background:{TCOL.get(r["_type"], TEAL)}"></div>' for v, r in vals)
    return (f'<div class="s" style="font-size:30px;letter-spacing:2px;text-transform:uppercase;color:{MUTED}">{lab}</div>'
            f'<div style="display:grid;grid-template-columns:auto 1fr;gap:26px;align-items:end">{_big(fmt(vmax), unit, 120)}'
            f'<div style="display:flex;align-items:flex-end;gap:8px;height:120px;border-bottom:4px solid {INK}">{bars}</div></div>'
            f'<div style="font:700 32px/1.2 I,sans-serif;margin-top:16px">{len(vals)} courses, de {fmt(vmin)} à {fmt(vmax)} {unit}</div>')


def hero_premiere(rs, nmax=None):
    kms = sorted(e['km'] for r in rs for e in r['epreuves'] if e.get('km') and e['km'] < 15 and (e.get('dp') or 0) < 500 and e.get('type') in ('route', 'trail', 'cross'))
    five = [k for k in kms if k >= 5]
    return (f'<div class="s" style="font-size:30px;letter-spacing:2px;text-transform:uppercase;color:{MUTED}">Pour se lancer</div>'
            f'{_big("dès " + fmt_km(five[0] if five else kms[0]), "km")}'
            f'<div style="font:700 34px/1.25 I,sans-serif;margin-top:14px">{len(rs)} courses accessibles,<br>sans gros dénivelé</div>')


PERSO_TH = {'relais': (3, 'On fait équipe ?'), 'gros-dp': (1, 'Ayo, i monte !'), 'longues': (1, 'Lé pa loin… ou pas !'), 'premiere': (3, 'Allez, lance-toi !')}


HEROES = {'relais': hero_relais, 'premiere': hero_premiere,
          'gros-dp': lambda rs: hero_bars(rs, 'dp', 'm D+', 'Jusqu\'à'),
          'longues': lambda rs: hero_bars(rs, 'km', 'km', 'Jusqu\'à')}


def cover_theme_v2(P, n, th, rs, ref):
    """sunset cover for a theme (validée le 16/11/2026) : one strong fact on a cream panel (team sizes, record D+ or distance,
    shortest distance) and Sam / Ana under it with a word in a bubble ; the other themes keep the island"""
    if th['id'] not in HEROES:
        return cover_v2(P, n, 'Ces 10 prochaines semaines', th['title'], th['sub'], 'couchant', by_type(rs), ref)
    M = MAP(); W, H = P['W'], P['H']; tt = H > 1500
    top = P['T'] + (56 if not tt else 40)
    lines = th['title'].split('<br>')
    size = int(min(140 if not tt else 150, (W - 2 * P['L']) / (0.44 * max(len(l) for l in lines))))
    head = (f'<div class="abs" style="left:{P["L"]}px;right:{P["R"]}px;top:{top}px;color:{AMB_TXT.get("couchant", "#fff")}">'
            f'<div style="font:700 28px/1 I,sans-serif;letter-spacing:.14em;text-transform:uppercase">Ces 10 prochaines semaines</div>'
            + ''.join(f'<div style="margin-top:{-size * .2 if i else 0:.0f}px">{titlesolid(l, "couchant", size)}</div>' for i, l in enumerate(lines)) +
            f'<div style="font:600 34px/1.22 I,sans-serif;margin-top:24px">{esc(th["sub"])}</div></div>')
    import math
    w = W - P['L'] - (P['R'] if not tt else P['L'])
    sub_lines = math.ceil(len(th['sub']) * .52 * 34 / (W - P['L'] - P['R']))
    y0 = top + 28 + len(lines) * (size * .92 + 8) - (len(lines) - 1) * size * .2 + 24 + sub_lines * 42 + (34 if not tt else 50)
    fn = HEROES[th['id']]
    z = 1.2 if tt else 1      # TikTok : bigger panel
    panel = (f'<div class="abs" style="left:{P["L"]}px;width:{w}px;top:{y0:.0f}px">'
             f'<div style="width:{w / z:.0f}px;zoom:{z};background:{SURF};border-radius:32px;padding:30px 34px 32px;box-shadow:0 24px 60px rgba(0,0,0,.4)">'
             f'{fn(rs)}</div></div>')
    # the game's runners (Sam, Ana) under the panel, with a word in their bubble
    pose, text = PERSO_TH[th['id']]
    ph = 360 if not tt else 380
    duo = th.get('duo')
    figs = (f'<div style="width:{ph * .74:.0f}px;height:{ph}px">{perso(ref, pose, "jeremi")}</div>'
            f'<div style="width:{ph * .74:.0f}px;height:{ph}px;margin-left:-30px">{perso(ref, pose, "nadia")}</div>') if duo else \
           f'<div style="width:{ph * .74:.0f}px;height:{ph}px">{perso(ref, pose)}</div>'
    runners = (f'<div class="abs" style="left:{P["L"] - 10}px;bottom:{P["B"] + 70}px;display:flex;align-items:flex-end;gap:6px">{figs}'
               f'<div style="margin-bottom:{ph * .62:.0f}px;margin-left:-6px">{bubble(text)}</div></div>')
    panel += runners
    bg = (f'<div class="abs" style="inset:0;filter:blur(14px) saturate(.85)">{world(1000 / M["W"], M["W"] / 2, M["H"] / 2, W / 2, H * .62)}</div>'
          '<div class="abs" style="inset:0;background:rgba(8,59,90,.45)"></div>'
          + ambiance(P, "couchant"))   # the post's sky over the blurred island
    arrow = (f'<div class="abs" style="right:{P["R"] - 6}px;bottom:{P["B"] - 20}px;width:76px;height:76px;border-radius:50%;background:#fff;display:grid;place-items:center">'
             f'<svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="{INK}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></div>')
    return page(P, bg + head + panel + chrome(P, 1, n) + arrow)

# ------------------------------------------------------------------ Monday cover (16/11/2026)
def cover_weekend_v2(P, n, rs, ref, lab):
    """morning cover for the weekend : the island framed on the races (not the whole island when they are close),
    numbered pins (numbers of the programme and of the race slides), commune and day under each group of pins"""
    M = MAP(); W, H = P['W'], P['H']; tt = H > 1500
    top = P['T'] + (56 if not tt else 40)
    size = int(min(170 if not tt else 178, (W - 2 * P['L']) / (0.44 * len('Ce week-end'))))
    head = (f'<div class="abs" style="left:{P["L"]}px;right:{P["R"]}px;top:{top}px;color:{AMB_TXT.get("matin", "#fff")}">'
            f'<div style="font:700 28px/1 I,sans-serif;letter-spacing:.14em;text-transform:uppercase">{esc(lab)}</div>'
            f'<div>{titlesolid("Ce week-end", "matin", size)}</div>'
            f'<div style="font:600 36px/1.25 I,sans-serif;margin-top:24px">{len(rs)} course{"s" if len(rs) > 1 else ""} à La Réunion</div></div>')
    y0 = top + 28 + size * .92 + 8 + 24 + 46 + 50
    y1 = H - P['B'] - 130
    pts = [P_xy(*r['ll']) for r in rs]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    # frame : the races with a margin, never smaller than a third of the island (a lone race keeps its surroundings)
    minw, minh = M['W'] * .34, M['H'] * .30
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    bw = max(minw, (max(xs) - min(xs)) * 1.45 + 80); bh = max(minh, (max(ys) - min(ys)) * 1.45 + 80)
    kf = min((W - (2 * P['L'] if not tt else 40)) / bw, (y1 - y0) / bh, (W - 300) / M['W'] * 3.4)
    kf = max(kf, min((W - 300) / M['W'], (y1 - y0) / M['H']))          # never smaller than the whole island
    sy = (y0 + y1) / 2
    scr = [[W / 2 + (x - cx) * kf, sy + (y - cy) * kf] for x, y in pts]
    big = 64
    for i in range(len(scr)):
        x0, yy, k = scr[i][0], scr[i][1], 0
        while any((scr[i][0] - scr[j][0]) ** 2 + (scr[i][1] - scr[j][1]) ** 2 < (big + 6) ** 2 for j in range(i)) and k < 14:
            k += 1; scr[i] = [x0 + (-1) ** k * (big + 8) * ((k + 1) // 2), yy] if k <= 4 else [x0 + (k - 6) * big / 2, yy + big + 8]
    pins = ''.join(f'<div class="pin" style="left:{x:.0f}px;top:{y:.0f}px;background:{TCOL.get(r["_type"], TEAL)};width:{big}px;height:{big}px;margin:-{big / 2:.0f}px 0 0 -{big / 2:.0f}px;font-size:{big * .55:.0f}px;line-height:{big - 12}px;border-width:6px">{k}</div>'
                   for k, (r, (x, y)) in enumerate(zip(rs, scr), 1))
    icx, icy = W / 2 + (M['W'] / 2 - cx) * kf, sy + (M['H'] / 2 - cy) * kf
    dsub = lambda com, ii: ' · '.join(f"{JOURS_C[d.weekday()]} {d.day}" for d in sorted({rs[i]['_d'] for i in ii}))
    leaders, labs = place_labels(rs, scr, big, W, y0 - 10, H - P['B'] - 100, (icx, icy), dsub, land_fn(kf, cx, cy, W, sy))
    arrow = (f'<div class="abs" style="right:{P["R"] - 6}px;bottom:{P["B"] - 20}px;width:76px;height:76px;border-radius:50%;background:#fff;display:grid;place-items:center">'
             f'<svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="{INK}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></div>')
    fade = ambiance(P, "matin")   # the post's sky, fading into the sea and the island
    return page(P, world(kf, cx, cy, W / 2, sy) + fade + leaders + pins + labs + head + chrome(P, 1, n) + arrow)

_LAND = {}


def land_fn(kf, cx, cy, W, sy):
    """screen point -> True if it is on the island (alpha of the relief picture)"""
    from PIL import Image
    M = MAP()
    if 'img' not in _LAND:
        im = Image.open(island().replace('file://', '')).convert('RGBA')
        _LAND['img'] = im.getchannel('A').resize((800, round(800 * im.height / im.width)))
    a = _LAND['img']; k = a.width / M['W']
    def land(x, y):
        mx, my = (cx + (x - W / 2) / kf) * k, (cy + (y - sy) / kf) * k
        return 0 <= mx < a.width and 0 <= my < a.height and a.getpixel((int(mx), int(my))) > 128
    return land


def place_labels(rs, scr, big, W, ymin, ymax, center, sub=None, land=None):
    """commune labels glued to their pins : for each commune, the free spot closest to its pins (outwards first),
    with a short white leader line when the label could not touch the pin. Returns (svg leader lines, label html)."""
    placed, lines, labs, segs = [], '', '', []
    pins = [(x, y) for x, y in scr]
    icx, icy = center
    for com in dict.fromkeys(r['commune'] for r in rs):
        ii = [i for i, r in enumerate(rs) if r['commune'] == com]
        sub_txt = sub(com, ii) if sub else ''
        lw = max(len(com) * 15, len(sub_txt) * 10) + 32; lh = 62 if sub_txt else 42
        gx0 = min(scr[i][0] for i in ii) - big / 2; gx1 = max(scr[i][0] for i in ii) + big / 2
        gy0 = min(scr[i][1] for i in ii) - big / 2; gy1 = max(scr[i][1] for i in ii) + big / 2
        gx, gy = (gx0 + gx1) / 2, (gy0 + gy1) / 2
        out = (gx - icx, gy - icy); on = (out[0] ** 2 + out[1] ** 2) ** .5 or 1
        import math
        coast = land is not None and any(not land(gx + 110 * math.cos(t / 8 * math.pi), gy + 110 * math.sin(t / 8 * math.pi)) for t in range(16))
        cands = []
        for gap in (8, 50, 95, 140):
            for cx_, cy_ in ((gx1 + gap + lw / 2, gy), (gx0 - gap - lw / 2, gy), (gx, gy1 + gap + lh / 2), (gx, gy0 - gap - lh / 2),
                             (gx1 + gap + lw / 2, gy1 + gap / 2 + lh / 2), (gx0 - gap - lw / 2, gy1 + gap / 2 + lh / 2),
                             (gx1 + gap + lw / 2, gy0 - gap / 2 - lh / 2), (gx0 - gap - lw / 2, gy0 - gap / 2 - lh / 2)):
                cands.append((cx_, cy_, gap))
        def score(c):
            x, y, gap = c
            bx0, bx1, by0, by1 = x - lw / 2, x + lw / 2, y - lh / 2, y + lh / 2
            sc = sum(12 for a0, a1, b0, b1 in placed if bx0 < a1 + 8 and bx1 > a0 - 8 and by0 < b1 + 8 and by1 > b0 - 8)
            sc += sum(2 for px, py in pins if bx0 - big / 2 < px < bx1 + big / 2 and by0 - big / 2 < py < by1 + big / 2)
            sc += 9 * (bx0 < 16 or bx1 > W - 16 or by0 < ymin or by1 > ymax)
            d = ((x - gx) * out[0] + (y - gy) * out[1]) / on                 # > 0 : towards the sea
            if coast:      # coastal race : the label goes on the sea, not on the island
                f = sum(land(bx0 + (bx1 - bx0) * u / 4, by0 + (by1 - by0) * v / 2) for u in range(5) for v in range(3)) / 15
                sc += 6 * f
            # the leader (nearest pin -> label) must not pass by another pin, nor cross another leader
            px, py = min(((scr[i][0], scr[i][1]) for i in ii), key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2)
            qx, qy = min(max(px, bx0), bx1), min(max(py, by0), by1)
            def segd(ax, ay):
                vx, vy = qx - px, qy - py; L = vx * vx + vy * vy or 1
                t = max(0, min(1, ((ax - px) * vx + (ay - py) * vy) / L)); return ((px + t * vx - ax) ** 2 + (py + t * vy - ay) ** 2) ** .5
            sc += 4 * sum(1 for j, (ax, ay) in enumerate(pins) if j not in ii and segd(ax, ay) < big / 2 + 4)
            def cross(a, b):
                (x1, y1, x2, y2), (x3, y3, x4, y4) = a, b
                d1 = (x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1); d2 = (x2 - x1) * (y4 - y1) - (y2 - y1) * (x4 - x1)
                d3 = (x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3); d4 = (x4 - x3) * (y2 - y3) - (y4 - y3) * (x2 - x3)
                return d1 * d2 < 0 and d3 * d4 < 0
            sc += 6 * sum(cross((px, py, qx, qy), l) for l in segs)
            sc += 4 * sum(1 for a0, a1, b0, b1 in placed for (lx1, ly1, lx2, ly2) in [(px, py, qx, qy)] if min(lx1, lx2) < a1 and max(lx1, lx2) > a0 and min(ly1, ly2) < b1 and max(ly1, ly2) > b0 and ((qx - px) ** 2 + (qy - py) ** 2) > (big / 2 + 12) ** 2)
            return sc + gap / 25 + (0 if d > 0 else .6)
        x, y, gap = min(cands, key=score)
        placed.append((x - lw / 2, x + lw / 2, y - lh / 2, y + lh / 2))
        # leader : from the nearest pin to the nearest point of the label
        px, py = min(((scr[i][0], scr[i][1]) for i in ii), key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2)
        qx, qy = min(max(px, x - lw / 2), x + lw / 2), min(max(py, y - lh / 2), y + lh / 2)
        segs.append((px, py, qx, qy))
        if ((qx - px) ** 2 + (qy - py) ** 2) ** .5 > big / 2 + 12:
            lines += (f'<line x1="{px:.0f}" y1="{py:.0f}" x2="{qx:.0f}" y2="{qy:.0f}" stroke="{INK}" stroke-width="8" stroke-linecap="round"/>'
                      f'<line x1="{px:.0f}" y1="{py:.0f}" x2="{qx:.0f}" y2="{qy:.0f}" stroke="#fff" stroke-width="4" stroke-linecap="round"/>')
        labs += (f'<div class="abs" style="left:{x - lw / 2:.0f}px;top:{y - lh / 2:.0f}px;width:{lw:.0f}px;height:{lh}px;white-space:nowrap;text-align:center;background:{INK};color:#fff;'
                 f'border-radius:12px;box-shadow:0 6px 14px rgba(0,0,0,.35);display:flex;flex-direction:column;justify-content:center">'
                 f'<div style="font:800 28px/1 S,sans-serif">{esc(com)}</div>'
                 + (f'<div style="font:700 19px/1.1 I,sans-serif;color:#ffd400;margin-top:3px">{esc(sub_txt)}</div>' if sub_txt else '') + '</div>')
    svg = f'<svg class="abs" style="left:0;top:0;overflow:visible" width="{W}" height="{ymax}">{lines}</svg>'
    return svg, labs
