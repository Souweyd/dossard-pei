"""Charte graphique des posts Dossard Péi (validée le 28/10/2026) – gabarits HTML des posts du fil.

- Un seul décor (paysage du site : ciel, deux plans de montagnes, collines, sol crème) décliné en ambiances :
  matin (Ce week-end), couchant (thème), lagon (région), soir (le mois).
- Fil (4:5 et TikTok 9:16) : logo + compteur en haut, surtitre en capitales, grand titre Saira Condensed,
  dossardpei.re + flèche en bas ; dernière slide épurée dans l'ambiance de la couverture.
- Texte posé sur le décor : encre (blanc sur le ciel du soir), en gros ; gris et couleurs seulement sur blanc / crème.
- Listes, calendrier, captures : sur des cartes blanches. Pas d'emoji dans les visuels.
- L'étiquette bleu marine soulignée de jaune est réservée aux stories (nouveau.py, meteo.py).
"""
import html, calendar, pathlib
from core import ROOT, status, poster_path, art_path, island_svg, dist_label, TYPE_LAB, JOURS_C, MOIS, MOIS_C

FONTS = (ROOT / 'social' / 'fonts').as_uri()
LOGO = (ROOT / 'social' / 'assets' / 'logo-512.png').as_uri()
esc = lambda s: html.escape(str(s))

INK, CREAM = '#1d2523', '#f5efe6'
TEAL, ORANGE, RED = '#0d6b67', '#d2481e', '#c62828'
MUTED = '#5b6763'          # only on white / cream (6:1)
LINE = '#e6ded2'
TYPE_COL = {'trail': '#2e7d32', 'route': '#4f6475', 'marche': '#8a6f5c', 'cross': '#94702a', 'autre': '#8a5a00',
            'jeunes': '#c2255c', 'multisport': '#0a6fb5', 'relais': '#b07f00'}
MOODS = {
    'matin':    dict(s1='#5fb0e6', s2='#cfe8f6', m1='#a9c2d3', m2='#8eaabb', h='#9dbf93', light=False),
    'couchant': dict(s1='#f0a36f', s2='#fbe1c6', m1='#d3b0a6', m2='#b88f8a', h='#b5b183', light=False),
    'lagon':    dict(s1='#3fb3b0', s2='#cdeee9', m1='#9cc7c1', m2='#79aaa3', h='#8fbe8a', light=False),
    'soir':     dict(s1='#1b3766', s2='#557cb0', m1='#4a6390', m2='#3a5078', h='#6c8f6a', light=True),
}
# layouts : W, H, side margins, top / bottom safe zones (TikTok : buttons on the right, caption at the bottom)
LAYOUT = {'instagram': dict(W=1080, H=1350, L=72, R=72, T=60, B=60),
          'tiktok': dict(W=1080, H=1920, L=72, R=170, T=250, B=330)}

CSS = f'''
@font-face{{font-family:SC;font-weight:700;src:url('{FONTS}/SairaCondensed-700.woff2')}}
@font-face{{font-family:SC;font-weight:800;src:url('{FONTS}/SairaCondensed-800.woff2')}}
@font-face{{font-family:Saira;font-weight:800;src:url('{FONTS}/SairaCondensed-800.woff2')}}
@font-face{{font-family:IS;font-weight:400 700;src:url('{FONTS}/InstrumentSans.woff2')}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:IS,sans-serif;color:{INK};background:{CREAM};position:relative;overflow:hidden;-webkit-font-smoothing:antialiased}}
.decor{{position:absolute;left:0;top:0}}
.sc{{font-family:SC,sans-serif;font-weight:800;letter-spacing:-.005em}}
.abs{{position:absolute}}
.kick{{font-family:IS;font-weight:700;font-size:28px;letter-spacing:.14em;text-transform:uppercase}}
.card{{background:#fff;border-radius:28px;box-shadow:0 18px 44px rgba(29,37,35,.14),0 0 0 1px rgba(29,37,35,.05)}}
.chip{{display:inline-flex;align-items:center;font-family:IS;font-weight:700;font-size:24px;line-height:1;border-radius:999px;padding:9px 16px;white-space:nowrap}}
.st-complet{{background:{RED};color:#fff}} .st-clot{{background:{ORANGE};color:#fff}} .st-bientot{{background:#ece6dc;color:{INK}}} .st-ouvert{{background:#e1efec;color:{TEAL}}}
'''


def is_tt(P): return P['H'] > 1500


def page(P, body):
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}html,body{{width:{P["W"]}px;height:{P["H"]}px}}</style></head><body>{body}</body></html>'


def decor(P, mood, horizon=.5, cream_from=None):
    W, H = P['W'], P['H']
    m = MOODS[mood]; y = H * horizon
    cf = cream_from if cream_from is not None else y
    return f'''<svg class="decor" width="{W}" height="{H}" viewBox="0 0 {W} {H}" preserveAspectRatio="none">
      <defs><linearGradient id="sk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{m['s1']}"/><stop offset="{horizon:.2f}" stop-color="{m['s2']}"/></linearGradient>
      <linearGradient id="fd" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{CREAM}" stop-opacity="0"/><stop offset=".55" stop-color="{CREAM}"/></linearGradient></defs>
      <rect width="{W}" height="{H}" fill="url(#sk)"/>
      <ellipse cx="{W * .74:.0f}" cy="{H * .11:.0f}" rx="{W * .24:.0f}" ry="{H * .04:.0f}" fill="#fff" opacity=".22"/>
      <path d="M0 {y - H * .10:.0f} L{W * .22:.0f} {y - H * .17:.0f} L{W * .45:.0f} {y - H * .09:.0f} L{W * .7:.0f} {y - H * .2:.0f} L{W} {y - H * .12:.0f} L{W} {H} L0 {H}Z" fill="{m['m1']}"/>
      <path d="M0 {y - H * .02:.0f} L{W * .3:.0f} {y - H * .1:.0f} L{W * .62:.0f} {y - H * .03:.0f} L{W} {y - H * .08:.0f} L{W} {H} L0 {H}Z" fill="{m['m2']}"/>
      <path d="M0 {y + H * .05:.0f} Q{W * .35:.0f} {y - H * .02:.0f} {W * .7:.0f} {y + H * .03:.0f} T{W} {y + H * .02:.0f} L{W} {H} L0 {H}Z" fill="{m['h']}"/>
      <rect y="{cf:.0f}" width="{W}" height="{H - cf:.0f}" fill="url(#fd)"/></svg>'''


def header(P, i, n, light=False):
    col = '#fff' if light else INK
    cnt_bg = 'rgba(255,255,255,.18)' if light else 'rgba(255,255,255,.7)'
    return f'''<div class="abs" style="left:{P['L']}px;right:{P['R']}px;top:{P['T']}px;display:flex;align-items:center;justify-content:space-between">
      <div style="display:flex;align-items:center;gap:14px"><img src="{LOGO}" style="width:58px;display:block">
        <span class="sc" style="font-size:34px;color:{col}">Dossard Péi</span></div>
      <span style="font-weight:700;font-size:24px;color:{col};background:{cnt_bg};border-radius:999px;padding:8px 18px">{i}/{n}</span></div>'''


def footer(P):
    return f'''<div class="abs" style="left:{P['L']}px;right:{P['R']}px;bottom:{P['B']}px;display:flex;align-items:center;justify-content:space-between">
      <span style="font-weight:700;font-size:28px;color:{INK}">dossardpei.re</span>
      <span style="width:76px;height:76px;border-radius:50%;background:{INK};display:grid;place-items:center">
      <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></span></div>'''


def title_block(P, kicker, title, sub, top, size=150, light=False, right=None):
    col = '#fff' if light else INK
    return f'''<div class="abs" style="left:{P['L']}px;right:{right if right is not None else P['R']}px;top:{top}px;color:{col}">
      <div class="kick">{kicker}</div>
      <div class="sc" style="font-size:{size}px;line-height:.88;margin-top:14px">{title}</div>
      {f'<div style="font-weight:600;font-size:40px;line-height:1.25;margin-top:20px">{sub}</div>' if sub else ''}</div>'''


def stchip(r, ref):
    code, lab = status(r, ref)
    lab = {'complet': 'Complet'}.get(code, lab) or 'Inscriptions ouvertes'
    return f'<span class="chip st-{code}">{esc(lab)}</span>'


def dlabel(dd): return f"{JOURS_C[dd.weekday()]} {dd.day} {MOIS_C[dd.month - 1]}"


def hfmt(h): return (h or '').replace('h00', 'h').lstrip('0')


def pin_col(r, ref): return RED if status(r, ref)[0] == 'complet' else TYPE_COL.get(r['_type'], MUTED)


def pins_for(rs, ref, r=44):
    return [dict(ll=x['ll'], color=pin_col(x, ref), n=k, r=r) for k, x in enumerate(rs, 1)]


def list_rows(rs, ref, w, rowh=112, name_fs=42, numbers=False, start=1):
    rows = []
    small = rowh < 96
    for k, r in enumerate(rs, start):
        dd = r['_d']
        num = (f'<span style="flex:none;width:46px;height:46px;border-radius:50%;background:{pin_col(r, ref)};'
               f'color:#fff;display:grid;place-items:center;font-family:SC;font-weight:800;font-size:28px">{k}</span>') if numbers else ''
        date = (f'<div style="flex:none;width:{70 if small else 86}px;text-align:center;line-height:1"><div style="font-weight:700;font-size:{17 if small else 20}px;letter-spacing:.08em;color:{MUTED}">{JOURS_C[dd.weekday()].upper().rstrip(".")}</div>'
                f'<div class="sc" style="font-size:{40 if small else 52}px;margin-top:2px">{dd.day}</div>'
                + ('' if small else f'<div style="font-weight:600;font-size:20px;color:{MUTED}">{MOIS_C[dd.month - 1]}</div>') + '</div>')
        meta = ' · '.join(x for x in [r['commune'], dist_label(r)] if x)
        rows.append(f'''<div style="display:flex;align-items:center;gap:{16 if small else 20}px;height:{rowh}px;padding:0 {20 if small else 26}px;{'border-top:2px solid ' + LINE if k > start else ''}">
          {num}{date}<div style="flex:1;min-width:0"><div class="sc" style="font-size:{name_fs}px;line-height:1.02;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{esc(r['nom'])}</div>
          <div style="font-weight:500;font-size:{22 if small else 25}px;color:{MUTED};margin-top:{3 if small else 6}px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{esc(meta)}</div></div>{stchip(r, ref)}</div>''')
    return f'<div class="card" style="width:{w}px;overflow:hidden">{"".join(rows)}</div>'


# ---------------------------------------------------------------- slides
def cover_island(P, i, n, mood, kicker, title, sub, rs, ref, size=168):
    """Cover with the whole island and numbered pins (Ce week-end)."""
    tt = is_tt(P)
    mapw = 800 if not tt else 900
    maptop = P['T'] + (420 if not tt else 520)
    return page(P, f'''{decor(P, mood, .5)}{header(P, i, n)}
      {title_block(P, kicker, title, sub, P['T'] + (130 if not tt else 150), size)}
      <div class="abs" style="left:{(P['W'] - mapw) // 2}px;top:{maptop}px;width:{mapw}px">{island_svg(mapw, pins_for(rs, ref), relief=True)}</div>
      {footer(P)}''')


def cover_region(P, i, n, kicker, title, sub, rs, ref, communes, vb):
    tt = is_tt(P)
    mapw = 640 if not tt else 700
    return page(P, f'''{decor(P, 'lagon', .5)}{header(P, i, n)}
      {title_block(P, kicker, title, sub, P['T'] + (130 if not tt else 150), 140)}
      <div class="abs" style="left:{P['W'] - P['R'] - mapw + (20 if not tt else 40)}px;top:{P['T'] + (500 if not tt else 560)}px;width:{mapw}px;height:{mapw}px;border-radius:50%;overflow:hidden;
           background:#e9f1ec;border:10px solid #fff;box-shadow:0 26px 50px rgba(29,37,35,.25)">{island_svg(mapw, pins_for(rs, ref, 40), highlight=communes, relief=True, vb=vb)}</div>
      {footer(P)}''')


ICONS = {   # line pictograms (no emoji in the visuals)
    'longues': '<path d="M3 20h18"/><path d="m4 20 5-9 3 4 3-6 5 11"/><circle cx="17" cy="5" r="1.6"/>',
    'gros-dp': '<path d="m3 20 6-11 4 6 3-4 5 9Z"/><path d="M8.2 10.5 9 9l1.6 2.4"/>',
    'premiere': '<circle cx="13" cy="4.5" r="2"/><path d="m8 21 3-6 3 2v5"/><path d="M6 12l3-4 4 1 3 4 3 1"/>',
    'relais': '<path d="M7 7h10l-3-3M17 17H7l3 3"/>',
    'marmailles': '<circle cx="9" cy="6" r="2.2"/><circle cx="16" cy="9" r="1.7"/><path d="M5.5 20l1.5-6 2-2 2 2 1 6M13.5 20l1-5 1.5-1.5 1.5 1.5.5 5"/>',
    'route': '<path d="M8 21 10 3M16 21 14 3M12 6v2M12 11v2M12 16v2"/>',
    'rando': '<path d="M7 21l3-9 2 2v7M10 12l-1-4 3-2 2 4 3 1"/><circle cx="12.5" cy="3.8" r="1.8"/><path d="M18 11v10"/>',
    'multisport': '<path d="M3 17c2 0 2-1.5 4-1.5S9 17 11 17s2-1.5 4-1.5 2 1.5 4 1.5"/><circle cx="15" cy="6" r="2"/><path d="m6 13 4-4 3 2 3-1"/>',
}


def cover_theme(P, i, n, th, rs, ref):
    tt = is_tt(P)
    w = P['W'] - P['L'] - P['R']
    top = P['T'] + (130 if not tt else 150)
    cardtop = P['T'] + (620 if not tt else 700)
    K = min(len(rs), 3 if not tt else 4)
    more = len(rs) - K
    ic = ICONS.get(th['id'], ICONS['longues'])
    return page(P, f'''{decor(P, 'couchant', .52)}{header(P, i, n)}
      <div class="abs" style="right:{P['R']}px;top:{top + 4}px;width:150px;height:150px;border-radius:40px;background:#fff;display:grid;place-items:center;box-shadow:0 14px 30px rgba(29,37,35,.18)">
        <svg width="96" height="96" viewBox="0 0 24 24" fill="none" stroke="{ORANGE}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{ic}</svg></div>
      {title_block(P, 'Le thème de la semaine', th['title'], th['sub'].replace(' : ', ' :<br>'), top, 150, right=P['R'] + 180)}
      <div class="abs" style="left:{P['L']}px;top:{cardtop}px">{list_rows(rs[:K], ref, w, 112, 40)}</div>
      {f'<div class="abs" style="left:{P["L"]}px;top:{cardtop + K * 112 + 22}px;font-weight:700;font-size:30px">+ {more} autre{"s" if more > 1 else ""} dans le carrousel</div>' if more > 0 else ''}
      {footer(P)}''')


def cover_month(P, i, n, y, m, rs, ref):
    tt = is_tt(P)
    w = P['W'] - P['L'] - P['R']
    cal = calendar.Calendar(0).monthdatescalendar(y, m)
    cell = (w - 48 - 6 * 10) / 7
    CH = .66 if not tt else .8
    hdr = ''.join(f'<div style="text-align:center;font-weight:700;font-size:20px;letter-spacing:.08em;color:{MUTED}">{j.upper().rstrip(".")}</div>' for j in JOURS_C)
    cells = ''
    for wk in cal:
        for dd in wk:
            day = [r for r in rs if r['_d'] == dd]
            dots = ''.join(f'<i style="width:13px;height:13px;border-radius:50%;background:{TYPE_COL.get(r["_type"], MUTED)}"></i>' for r in day[:6])
            out = dd.month != m
            cells += (f'<div style="height:{cell * CH:.0f}px;border-radius:14px;padding:8px 9px;background:{"transparent" if out else (CREAM if day else "#fff")};'
                      f'{"" if out or day else "box-shadow:inset 0 0 0 2px " + LINE + ";"}opacity:{.3 if out else 1}">'
                      f'<div class="sc" style="font-size:28px;line-height:1">{dd.day}</div><div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:6px">{"" if out else dots}</div></div>')
    used = sorted({r['_type'] for r in rs})
    legend = ''.join(f'<span style="display:inline-flex;align-items:center;gap:8px;font-size:21px;font-weight:600;color:{MUTED}"><i style="width:14px;height:14px;border-radius:50%;background:{TYPE_COL.get(t, MUTED)}"></i>{TYPE_LAB.get(t, t)}</span>' for t in used)
    grid = (f'<div class="card" style="width:{w}px;padding:24px"><div style="display:grid;grid-template-columns:repeat(7,1fr);gap:10px;margin-bottom:12px">{hdr}</div>'
            f'<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:10px">{cells}</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:8px 20px;margin-top:16px">{legend}</div></div>')
    return page(P, f'''{decor(P, 'soir', .46, cream_from=P['H'] * .5)}{header(P, i, n, light=True)}
      {title_block(P, 'Le mois en un coup d\'œil', MOIS[m - 1].capitalize(), f'{len(rs)} courses à La Réunion', P['T'] + (130 if not tt else 150), 150, light=True)}
      <div class="abs" style="left:{P['L']}px;top:{P['T'] + (410 if not tt else 560)}px">{grid}</div>
      {footer(P)}''')


def fit_size(text, width, base):
    """Font size (px) so a one-line Saira Condensed title fits the width."""
    import re as _re
    t = _re.sub('<[^>]+>', '', text)
    return int(min(base, width / (0.47 * max(1, len(t)))))


def _list_plan(P, nr):
    """(row height, [rows per slide]) : one slide with rows from 132/118 px down to 80 px, else several balanced slides."""
    tt = is_tt(P)
    top = P['T'] + (300 if not tt else 330)
    avail = P['H'] - P['B'] - 120 - top
    full = 118 if not tt else 132
    if nr * full <= avail:
        return min(150 if not tt else 170, int(avail / max(1, nr))), [nr]
    if nr * 80 <= avail:
        return int(avail / nr), [nr]
    per = int(avail // 86)
    k = -(-nr // per)
    base, extra = divmod(nr, k)
    sizes = [base + (1 if j < extra else 0) for j in range(k)]
    return min(full, int(avail / max(sizes))), sizes


def n_list_pages(P, rs):
    return len(_list_plan(P, len(rs))[1])


def list_pages(P, n0, n, kicker, title, rs, ref, numbers=False):
    """Plain cream slides with the races in a white card; balanced over several slides when needed. Returns [html]."""
    tt = is_tt(P)
    w = P['W'] - P['L'] - P['R']
    top = P['T'] + (300 if not tt else 330)
    rowh, sizes = _list_plan(P, len(rs))
    out, k0 = [], 0
    for c, sz in enumerate(sizes):
        ch = rs[k0:k0 + sz]
        t = title if c == 0 else f'{title} (suite)'
        out.append(page(P, f'''{header(P, n0 + c, n)}
          {title_block(P, kicker, t, '', P['T'] + 110, fit_size(t, w, 112))}
          <div class="abs" style="left:{P['L']}px;top:{top}px">{list_rows(ch, ref, w, rowh, 44 if rowh >= 104 else (38 if rowh >= 90 else 34), numbers, start=1 + k0)}</div>
          {footer(P)}'''))
        k0 += sz
    return out


def race_slide(P, i, n, r, ref):
    tt = is_tt(P)
    pth = poster_path(r) or art_path(r)
    ph = 760 if not tt else 900
    code = status(r, ref)[0]
    meta = ' · '.join(x for x in [r['commune'], dist_label(r)] if x)
    when = dlabel(r['_d']) + (f" · départ {hfmt(r['_h'])}" if r['_h'] else '')
    stamp = (f'<div class="sc" style="position:absolute;right:-26px;top:46px;transform:rotate(10deg);font-size:64px;letter-spacing:.06em;color:{RED};'
             f'border:8px solid {RED};border-radius:14px;padding:2px 20px;background:rgba(255,255,255,.92)">COMPLET</div>') if code == 'complet' else ''
    nm = r['nom']
    return page(P, f'''
      <div class="abs" style="inset:-80px;background:url('{pth.as_uri()}') center/cover;filter:blur(60px) saturate(1.1);opacity:.55"></div>
      <div class="abs" style="inset:0;background:linear-gradient(180deg,rgba(245,239,230,.35),rgba(245,239,230,.75) 45%,{CREAM} 70%)"></div>
      {header(P, i, n)}
      <div class="abs" style="left:0;right:0;top:{P['T'] + 100}px;display:flex;justify-content:center">
        <div style="position:relative"><img src="{pth.as_uri()}" style="height:{ph}px;max-width:{P['W'] - 2 * P['L']}px;object-fit:contain;display:block;border-radius:22px;border:10px solid #fff;box-shadow:0 26px 60px rgba(29,37,35,.3)">{stamp}</div></div>
      <div class="abs" style="left:{P['L']}px;right:{P['R']}px;top:{P['T'] + 110 + ph + 40}px">
        <div style="display:flex;align-items:center;gap:12px"><span class="chip" style="background:{TYPE_COL.get(r['_type'], MUTED)};color:#fff">{TYPE_LAB.get(r['_type'], 'Course')}</span>{stchip(r, ref)}</div>
        <div class="sc" style="font-size:{72 if len(nm) < 26 else 60}px;line-height:.95;margin-top:16px">{esc(nm)}</div>
        <div style="font-weight:600;font-size:32px;margin-top:10px">{esc(when)}</div>
        <div style="font-weight:500;font-size:28px;color:{MUTED};margin-top:4px">{esc(meta)}</div></div>
      {footer(P)}''')


def how_slide(P, i, n, feature, title, steps, shot):
    """'Sur le site' slide on cream : title, numbered steps, capture of the site in a card. shot(maxw, maxh) -> (html, w, h) or None."""
    tt = is_tt(P)
    st = ''.join(f'''<div style="display:flex;gap:16px;align-items:center;font-size:32px;font-weight:600;line-height:1.2">
        <span class="sc" style="flex:none;width:48px;height:48px;border-radius:50%;background:{INK};color:#fff;display:grid;place-items:center;font-size:28px">{k}</span>
        <span>{s}</span></div>''' for k, s in enumerate(steps, 1))
    top_steps = P['T'] + (300 if not tt else 330)
    top = top_steps + 62 * len(steps) + 40
    maxw, maxh = P['W'] - P['L'] - P['R'], P['H'] - P['B'] - 120 - top
    res = shot(maxw, maxh) if shot else None
    vis = ''
    if res:
        h_, w_, hh = res
        vis = f'<div class="abs" style="left:{P["L"] + (maxw - w_) // 2}px;top:{top}px">{h_}</div>'
    return page(P, f'''{header(P, i, n)}
      {title_block(P, f'Sur le site · {feature}', title, '', P['T'] + 110, fit_size(title, P['W'] - P['L'] - P['R'], 100))}
      <div class="abs" style="left:{P['L']}px;right:{P['R']}px;top:{top_steps}px;display:flex;flex-direction:column;gap:14px">{st}</div>
      {vis}{footer(P)}''')


def fin(P, mood, save='Enregistre ce post'):
    """Last slide, minimal : same mood as the cover, logo + address + one line."""
    light = MOODS[mood]['light']
    col = '#fff' if light else INK
    mid = P['T'] + (150 if not is_tt(P) else 170)
    return page(P, f'''{decor(P, mood, .5 if mood != 'soir' else .46, cream_from=None if mood != 'soir' else P['H'] * .5)}
      <div class="abs" style="left:{P['L']}px;right:{P['R']}px;top:{mid:.0f}px;display:flex;flex-direction:column;align-items:center;text-align:center;color:{col}">
        <img src="{LOGO}" style="width:190px;display:block;filter:drop-shadow(0 14px 24px rgba(29,37,35,.25))">
        <div class="sc" style="font-size:112px;line-height:.9;margin-top:30px">dossardpei.re</div>
        <div style="font-weight:600;font-size:38px;margin-top:18px">Toutes les courses de La Réunion</div></div>
      <div class="abs" style="left:{P['L']}px;right:{P['R']}px;bottom:{P['B'] + 6}px;display:flex;justify-content:center;align-items:center;gap:12px;font-weight:700;font-size:30px;color:{INK}">
        <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="{INK}" stroke-width="2.2" stroke-linejoin="round"><path d="M6 3h12v18l-6-4.5L6 21z"/></svg>{save}</div>''')
