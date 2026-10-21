"""Dossard Péi – generator of the weekly social-media kits (Instagram/Facebook 4:5 + TikTok 9:16).

Usage (from the repository root):
  python social/gen.py semaine 2026-10-26      # Monday's date -> Monday, Tuesday, Thursday, Friday (+ the 1st of the month if it falls in that week)
  python social/gen.py lundi 2026-10-26        # one post: lundi | mardi | jeudi | vendredi | mois
Output: social/out/<date>-<kind>/{instagram,tiktok}/*.jpg, reel .mp4 for Friday, legende-*.txt
"""
import sys, asyncio, pathlib, datetime as D, json, shutil, math
from core import *
from core import _norm, _same
import capture

OUT = SOC / 'out'
TMP = SOC / 'out' / '_tmp'

# ------------------------------------------------------------------ themes (Tuesday) – rotate weekly
def _has(r, f): return any(f(e) for e in r.get('epreuves', []))

THEMES = [
    dict(id='premiere', emo='🎽', title='TA PREMIÈRE<br>COURSE', short='Ta première course',
         sub='Moins de 15 km, moins de 500 m de D+ : idéal pour se lancer.',
         pred=lambda r: _has(r, lambda e: e.get('km') and e['km'] < 15 and (e.get('dp') or 0) < 500 and e.get('type') in ('route', 'trail', 'cross')),
         filt={'f-dist': 'court', 'f-dp': 'dp1'}, cta='Tague quelqu\'un qui devrait se lancer 👇', flab='Distance « < 15 km » et Dénivelé « < 500 m »', tag='#premierecourse'),
    dict(id='relais', emo='🤝', title='À FAIRE<br>EN ÉQUIPE', short='Les relais',
         sub='Relais entre potes, collègues ou en famille.', pred=lambda r: 'relais' in r['_types'], cta='Tague ton équipe de relais 👇',
         filt={'f-disc': 'relais'}, flab='Discipline « Relais »', tag='#relais'),
    dict(id='gros-dp', emo='⛰️', title='LES GROS<br>DÉNIVELÉS', short='Les gros D+',
         sub='Plus de 1 500 m de D+ : pour les grimpeurs.', pred=lambda r: _has(r, lambda e: (e.get('dp') or 0) >= 1500 and e.get('type') in ('trail', 'marche')), cta='Tu es plutôt montée ou descente ? 👇',
         filt={'f-dp': 'dp3'}, flab='Dénivelé « 1 500 – 3 000 m »', tag='#trailrunning'),
    dict(id='marmailles', emo='🧒', title='AVEC LES<br>MARMAILLES', short='Les courses jeunes',
         sub='Des courses pour les enfants, le même jour que les grands.', pred=lambda r: 'jeunes' in r['_types'], cta='Tague les parents de futurs champions 👇',
         filt={'f-disc': 'jeunes'}, flab='Discipline « Jeunes »', tag='#marmailles'),
    dict(id='route', emo='🏃', title='SUR LA<br>ROUTE', short='Les courses sur route',
         sub='10 km, semi, foulées : pour aller vite.', pred=lambda r: 'route' in r['_types'], cta='Ton record sur 10 km ? Dis-le en commentaire 👇',
         filt={'f-disc': 'route'}, flab='Discipline « Route »', tag='#running'),
    dict(id='rando', emo='🥾', title='RANDO<br>ET MARCHE', short='Rando et marche',
         sub='Pas besoin de courir pour prendre un dossard.', pred=lambda r: 'marche' in r['_types'], cta='Tague ton binôme de rando 👇',
         filt={'f-disc': 'marche'}, flab='Discipline « Rando / marche »', tag='#randonnee'),
    dict(id='longues', emo='🔥', title='LES LONGUES<br>DISTANCES', short='Les longues distances',
         sub='Plus de 30 km : les grosses sorties de la saison.', pred=lambda r: _has(r, lambda e: (e.get('km') or 0) > 30 and e.get('type') in ('trail', 'route', 'marche')), cta='Ta plus longue course, c\'était combien ? 👇',
         filt={'f-dist': 'long'}, flab='Distance « > 30 km »', tag='#ultratrail'),
    dict(id='multisport', emo='🏊', title='TRIATHLON,<br>SWIMRUN…', short='Le multisport',
         sub='Nager, pédaler, courir : les épreuves multisport.', pred=lambda r: 'multisport' in r['_types'], cta='Nage, vélo ou course : ton point fort ? 👇',
         filt={'f-disc': 'multisport'}, flab='Discipline « Multisport »', tag='#triathlon'),
]

TAGS = ['#trailreunion', '#run974', '#lareunion', '#974', '#courseapied']


# ------------------------------------------------------------------ shared slide parts
def row(r, ref, num=None):
    col = TYPE_COL.get(r['_type'], C['muted'])
    code, lab = status(r, ref)
    badge = ''
    if code == 'complet':
        badge = f'<span class="saira" style="font-weight:800;font-size:22px;color:#fff;background:{C["red"]};border-radius:7px;padding:1px 9px;margin-left:10px">COMPLET</span>'
    elif code == 'clot':
        badge = f'<span style="font-weight:700;font-size:20px;color:#fff;background:{C["hot"]};border-radius:7px;padding:2px 9px;margin-left:10px">{lab}</span>'
    left = (f'<span class="saira" style="flex:none;width:56px;height:56px;border-radius:50%;background:{col};color:#fff;display:grid;place-items:center;font-weight:800;font-size:34px">{num}</span>'
            if num is not None else '')
    dt = r['_d']
    return f'''<div style="display:flex;gap:18px;align-items:center;background:#fff;border-radius:18px;padding:14px 18px;border-left:8px solid {col}">
      {left}<div style="flex:none;width:84px;text-align:center;line-height:1">
        <div style="font-size:20px;font-weight:700;color:{C['muted']};text-transform:uppercase">{JOURS_C[dt.weekday()]}</div>
        <div class="saira" style="font-size:46px;font-weight:800">{dt.day}</div>
        <div style="font-size:18px;font-weight:600;color:{C['muted']}">{MOIS_C[dt.month - 1]}</div></div>
      <div style="min-width:0;flex:1"><div class="saira" style="font-weight:700;font-size:36px;line-height:1.02;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{esc(r['nom'])}</div>
        <div style="font-size:24px;font-weight:600;color:{C['muted']};margin-top:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{esc(r['commune'])}{' · ' + esc(dist_label(r)) if dist_label(r) else ''}{badge}</div></div></div>'''


ROW_H = 118


def list_slides(title_fn, races, ref, P, start_i, n_total, numbers=False, kicker=''):
    """Paginated list of races. Returns list of html pages."""
    top = P['T'] + 300
    per = max(3, int((P['H'] - P['B'] - top) // (ROW_H + 14)))
    npg = max(1, math.ceil(len(races) / per)); per = math.ceil(len(races) / npg)
    pages = []
    for k in range(0, len(races), per):
        chunk = races[k:k + per]
        rows = ''.join(row(r, ref, (k + j + 1) if numbers else None) for j, r in enumerate(chunk))
        i = start_i + len(pages)
        pages.append(page(f'''
        {head(i, n_total, P)}
        <div style="position:absolute;left:64px;right:64px;top:{P['T'] + 112}px">
          <div class="saira" style="font-weight:700;font-size:40px;color:{C['hot']}">{kicker}</div>
          <div class="saira" style="font-weight:800;font-size:84px;line-height:.92;margin-top:4px">{title_fn(k // per)}</div></div>
        <div style="position:absolute;left:64px;right:{P['R']}px;top:{top}px;display:flex;flex-direction:column;gap:14px">{rows}</div>''', P))
    return pages


def n_list_pages(n, P):
    top = P['T'] + 300
    per = max(3, int((P['H'] - P['B'] - top) // (ROW_H + 14)))
    return max(1, math.ceil(n / per))


def how(i, n, P, feature, title, steps, shot):
    """'Sur le site' slide. shot(maxw, maxh) -> (html, w, h) or None."""
    st = ''.join(f'''<div style="display:flex;gap:16px;align-items:center;font-size:32px;font-weight:600;line-height:1.2">
        <span class="saira" style="flex:none;width:48px;height:48px;border-radius:50%;background:{C['hot']};color:#fff;display:grid;place-items:center;font-weight:800;font-size:30px">{k}</span>
        <span>{s}</span></div>''' for k, s in enumerate(steps, 1))
    top = P['T'] + 400 + 70 * len(steps)
    maxw, maxh = P['W'] - 64 - P['R'], P['H'] - P['B'] - top
    res = shot(maxw, maxh) if shot else None
    vis = ''
    if res:
        h_, w_, hh = res
        x = 64 + (maxw - w_) // 2
        vis = f'<div style="position:absolute;left:{x}px;top:{top}px">{h_}</div>'
    return page(f'''
    {head(i, n, P)}
    <div style="position:absolute;left:64px;right:64px;top:{P['T'] + 112}px">
      <div class="saira" style="font-weight:700;font-size:40px;color:{C['hot']}">SUR LE SITE · {feature}</div>
      <div class="saira" style="font-weight:800;font-size:84px;line-height:.92;margin-top:4px">{title}</div></div>
    <div style="position:absolute;left:64px;right:{P['R']}px;top:{P['T'] + 370}px;display:flex;flex-direction:column;gap:20px">{st}</div>
    {vis}''', P)


def fit_crop(path, box, maxw, maxh, extra_fn=None):
    x0, y0, x1, y1 = box
    w = min(maxw, int(maxh * (x1 - x0) / (y1 - y0)))
    _, _, sc = crop_img(path, x0, y0, x1, y1, w)
    extra = extra_fn(sc) if extra_fn else ''
    h_, hh, _ = crop_img(path, x0, y0, x1, y1, w, extra=extra)
    return h_, w, hh


MASK = '-webkit-mask-image:radial-gradient(closest-side,#000 72%,transparent 100%);mask-image:radial-gradient(closest-side,#000 72%,transparent 100%)'


def region_vb(communes, races):
    import re as _re
    xs, ys = [], []
    for c in MAP()['communes']:
        if _same(c['nom'], communes):
            nums = [float(v) for v in _re.findall(r'-?\d+\.?\d*', c['d'])]
            xs += nums[0::2]; ys += nums[1::2]
    for r in races:
        x, y = P_xy(*r['ll']); xs.append(x); ys.append(y)
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    w, h = x1 - x0, y1 - y0
    side = max(w, h * 1.05) * 1.18
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return (cx - side / 2, cy - side * .5, side, side)


def hfmt(h):
    h = h.replace('h00', 'h')
    return h[1:] if h.startswith('0') else h


def dnum(x):
    return f"{x.day}{'ER' if x.day == 1 else ''}"


# ------------------------------------------------------------------ MONDAY : the coming week-end
def race_slide(i, n, P, r, ref):
    pth = poster_path(r) or art_path(r)
    poster = pth.as_uri()
    code, lab = status(r, ref)
    col = TYPE_COL.get(r['_type'], C['muted'])
    top_poster = P['T'] + 140
    hp = P['H'] - P['B'] - 140 - P['T'] - 390
    sash = ''
    if code == 'complet':
        sash = f'''<div style="position:absolute;top:0;right:0;width:330px;height:330px;overflow:hidden;border-top-right-radius:24px">
          <div class="saira" style="position:absolute;top:78px;right:-96px;width:460px;transform:rotate(45deg);background:{C['red']};color:#fff;
          text-align:center;font-weight:800;font-size:60px;letter-spacing:4px;line-height:1;padding:16px 0;box-shadow:0 8px 24px rgba(0,0,0,.35);
          border-top:4px solid rgba(255,255,255,.85);border-bottom:4px solid rgba(255,255,255,.85)">COMPLET</div></div>'''
    if code == 'complet':
        st = f'<span class="saira" style="font-weight:800;font-size:30px;letter-spacing:1.5px;color:#fff;background:{C["red"]};border-radius:10px;padding:4px 14px">COMPLET</span>'
    elif code == 'clot':
        st = f'<span style="font-weight:700;font-size:28px;color:#fff;background:{C["hot"]};border-radius:10px;padding:6px 14px">⏳ {lab}</span>'
    elif code in ('clos', 'bientot'):
        st = f'<span style="font-weight:700;font-size:26px;color:{C["muted"]};background:#e1e6e2;border-radius:10px;padding:6px 14px">{lab}</span>'
    else:
        st = f'<span style="font-weight:700;font-size:26px;color:{C["accent"]};background:{C["soft"]};border-radius:10px;padding:6px 14px">{lab or "Inscriptions ouvertes"}</span>'
    mini = island_svg(170, [dict(ll=r['ll'], color=C['red'] if code == 'complet' else col, r=80)])
    nm = r['nom']; ns = 74 if len(nm) < 26 else (62 if len(nm) < 36 else 52)
    dt = r['_d']
    when = f"{JOURS[dt.weekday()].upper()} {dt.day} {MOIS_C[dt.month - 1].upper().rstrip('.')}"
    right = '' if P['R'] > 64 else ('Viens encourager les coureurs !' if code in ('complet', 'clos') else 'Infos sur le site')
    other = [e for e in r.get('epreuves', []) if e is not r['_main'] and e.get('type')]
    extra = ''
    if other:
        kinds = sorted({TYPE_LAB.get(e['type'], '') for e in other} - {''})
        if kinds:
            extra = f'<div style="font-size:30px;font-weight:500;color:{C["muted"]};margin-top:6px">Aussi : {", ".join(k.lower() for k in kinds)}</div>'
    body = f'''
    <div style="position:absolute;inset:-60px;background:url('{poster}') center/cover;filter:blur(46px) saturate(1.1)"></div>
    <div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(238,242,238,.62) 0%,rgba(238,242,238,.80) 45%,{C['bg']} 64%)"></div>
    <div style="position:absolute;left:64px;top:{P['T'] - 4}px;right:64px;display:flex;justify-content:space-between;align-items:flex-start">
      <div><div class="saira" style="font-weight:800;font-size:58px;line-height:1;color:{C['hot']}">{when}</div>
        <div class="saira" style="font-weight:700;font-size:40px;line-height:1.1;margin-top:4px">{'Départ ' + hfmt(r['_h']) if r['_h'] else esc(r['commune'])}</div></div>
      <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px"><span class="count">{i}/{n}</span><div style="margin-top:-6px;margin-right:-14px">{mini}</div></div></div>
    <div style="position:absolute;left:0;right:0;top:{top_poster}px;height:{hp}px;display:flex;justify-content:center">
      <div style="position:relative;height:{hp}px"><img src="{poster}" style="height:{hp}px;max-width:900px;object-fit:contain;display:block;border-radius:24px;box-shadow:0 24px 60px rgba(29,37,35,.32)">{sash}</div></div>
    <div style="position:absolute;left:64px;right:{P['R']}px;top:{top_poster + hp + 30}px">
      <div style="display:flex;gap:12px;align-items:center;margin-bottom:12px;flex-wrap:wrap">
        <span class="chip" style="background:{col}">{TYPE_LAB.get(r['_type'], 'Course')}</span>{st}</div>
      <div class="saira" style="font-weight:800;font-size:{ns}px;line-height:.98">{esc(nm)}</div>
      <div style="display:flex;align-items:center;gap:10px;font-size:34px;font-weight:600;margin-top:12px;flex-wrap:wrap">
        <svg width="30" height="30" viewBox="0 0 24 24" fill="{C['hot']}"><path d="M12 2a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z"/></svg>
        {esc(r['commune'])}{f'<span style="color:{C["line"]}">|</span><span>{esc(dist_label(r))}</span>' if dist_label(r) else ''}</div>{extra}</div>
    <div style="position:absolute;left:64px;right:64px;bottom:{P['B'] - 8}px;display:flex;align-items:center;justify-content:space-between">
      <div class="brand">{LOGO}<div><b>DOSSARD PÉI</b><div style="font-weight:700;color:{C['accent']};font-size:28px">dossardpei.re</div></div></div>
      <div style="text-align:right;font-weight:600;font-size:26px;color:{C['muted']}">{right}</div></div>'''
    return page(body, P)


def cover_map(i, n, P, kicker, big, sub, races, ref, highlight=None, relief=False):
    vb = region_vb(highlight, races) if highlight else None
    pins = [dict(ll=r['ll'], color=C['red'] if status(r, ref)[0] == 'complet' else TYPE_COL.get(r['_type'], C['muted']), n=k, r=40)
            for k, r in enumerate(races, 1)]
    tt = P['R'] > 64
    lst_items = races[:8]
    lst = ''.join(f'''<div style="display:flex;gap:14px;align-items:flex-start">
        <span class="saira" style="flex:none;width:48px;height:48px;border-radius:50%;background:{C['red'] if status(r, ref)[0] == 'complet' else TYPE_COL.get(r['_type'], C['muted'])};color:#fff;display:grid;place-items:center;font-weight:800;font-size:30px">{k}</span>
        <div style="min-width:0"><div class="saira" style="font-weight:700;font-size:{34 if len(races) <= 5 else 30}px;line-height:1">{esc(r['nom'])}</div>
        <div style="font-size:22px;font-weight:600;color:{C['muted']};margin-top:5px">{JOURS_C[r['_d'].weekday()].capitalize()} {r['_d'].day} · {esc(r['commune'])}
        {'<span class="saira" style="font-weight:800;font-size:20px;color:#fff;background:' + C['red'] + ';border-radius:6px;padding:0 8px;margin-left:4px">COMPLET</span>' if status(r, ref)[0] == 'complet' else ''}</div></div></div>'''
                  for k, r in enumerate(lst_items, 1))
    more = f'<div style="font-size:26px;font-weight:700;color:{C["accent"]}">+ {len(races) - 8} autre{"s" if len(races) > 9 else ""} sur le site</div>' if len(races) > 8 else ''
    ylist = P['T'] + 480
    if not tt:
        mapw = 640
        visual = f'''<div style="position:absolute;left:24px;top:{ylist}px;{MASK if vb else ''}">{island_svg(mapw, pins, highlight=highlight, relief=relief, contours=not relief, vb=vb)}</div>
        <div style="position:absolute;left:{mapw + 14}px;right:52px;top:{ylist + 10}px;display:flex;flex-direction:column;gap:{24 if len(races) <= 5 else 16}px">{lst}{more}</div>'''
    else:
        ratio = (vb[3] / vb[2]) if vb else (MAP()['H'] + 40) / (MAP()['W'] + 80)
        mapw = int(min(P['W'] - 64 - P['R'] + 60, (P['H'] - P['B'] - ylist) / ratio))
        visual = f'''<div style="position:absolute;left:{(P['W'] - P['R'] + 64 - mapw) // 2}px;top:{ylist}px;{MASK if vb else ''}">{island_svg(mapw, pins, highlight=highlight, relief=relief, contours=not relief, vb=vb)}</div>'''
    body = f'''
    <div style="position:absolute;inset:0;background:radial-gradient(circle at 60% 45%, {C['sea']} 0%, {C['bg']} 62%)"></div>
    {head(i, n, P)}
    <div style="position:absolute;left:64px;right:64px;top:{P['T'] + 110}px">
      <div class="saira" style="font-weight:700;font-size:40px;color:{C['hot']}">{kicker}</div>
      <div class="saira" style="font-weight:800;font-size:{150 if len(big) < 14 else 112}px;line-height:.86;letter-spacing:-1px">{big}</div>
      <div style="font-size:34px;font-weight:600;color:{C['muted']};margin-top:12px">{sub}</div></div>
    {visual}'''
    return page(body, P)


def build_lundi(ref, data, races):
    sat = ref + D.timedelta(days=5)
    days = [ref + D.timedelta(days=k) for k in (4, 5, 6)]
    rs = upcoming(races, days[0], days[-1])
    rs = [r for r in rs if r['_d'] != days[0] or (r['_h'] and int(r['_h'][:2]) >= 16)]   # Friday only if evening
    if not rs:
        return None
    shown = rs[:8]
    sun = sat + D.timedelta(days=1)
    lab = (f"SAM. {dnum(sat)} & DIM. {dnum(sun)} {MOIS[sun.month - 1].upper()}" if sat.month == sun.month
           else f"SAM. {dnum(sat)} {MOIS_C[sat.month - 1].upper()} & DIM. {dnum(sun)} {MOIS_C[sun.month - 1].upper()}")
    shot_p, info = capture.run(capture.cal_weekend(TMP / 'cal_we.png', sat.isoformat()))
    pages = {}
    for fmt, P in FMTS.items():
        n = 1 + len(shown) + (1 if shot_p else 0) + 1
        sl = [cover_map(1, n, P, lab, 'CE WEEK-END', f"{len(rs)} course{'s' if len(rs) > 1 else ''} à La Réunion", rs, ref, relief=True)]
        sl += [race_slide(k, n, P, r, ref) for k, r in enumerate(shown, 2)]
        if shot_p:
            def shot(mw, mh, info=info):
                g = info['grid']
                ring = lambda sc: (f'<div style="position:absolute;left:{(info["cell"][0] - g[0]) * sc - 8:.0f}px;top:{(info["cell"][1] - g[1]) * sc - 8:.0f}px;'
                                   f'width:{info["cell"][2] * sc + 16:.0f}px;height:{info["cell"][3] * sc + 16:.0f}px;border:6px solid {C["hot"]};border-radius:14px"></div>')
                return fit_crop(shot_p, g, mw, mh, ring)
            sl.append(how(len(sl) + 1, n, P, 'CALENDRIER', 'TON WEEK-END<br>EN UN COUP D\'ŒIL',
                          ['Ouvre <b>dossardpei.re</b>', 'Touche <b>« Ce week-end »</b> ou <b>Calendrier</b>', 'Touche un jour : <b>la liste s\'affiche</b>'], shot))
        sl.append(cta_slide(len(sl) + 1, n, P, 'TOUTES LES COURSES<br><span style="color:#5cc4bc">DE LA RÉUNION</span>',
                            'Calendrier, carte, tracés<br>et liens d\'inscription.', 'Enregistre pour ce week-end'))
        pages[fmt] = sl
    clot = [r for r in rs if status(r, ref)[0] == 'clot']
    lines = [f"Ce week-end, {len(rs)} course{'s' if len(rs) > 1 else ''} à La Réunion 🏃⛰️", '']
    for dd in sorted({r['_d'] for r in rs}):
        lines.append(f"📅 {JOURS_C[dd.weekday()].capitalize()} {dd.day} : " + ' · '.join(f"{r['nom']} ({r['commune']})" for r in rs if r['_d'] == dd))
    if clot:
        lines += ['', '⏳ Dernières inscriptions : ' + ' · '.join(f"{r['nom']} ({status(r, ref)[1].replace('Clôture ', '').lower()})" for r in clot)]
    lines += ['', 'Infos et inscriptions 👉 dossardpei.re (lien en bio)', '', 'Tu cours ou tu vas encourager ? Dis-le en commentaire 👇']
    return pages, lines, TAGS


# ------------------------------------------------------------------ TUESDAY : a theme (filters)
def build_mardi(ref, data, races):
    horizon = upcoming(races, ref, ref + D.timedelta(days=70))
    k0 = week_index(ref) % len(THEMES)
    th = sel = None
    for k in range(len(THEMES)):
        t = THEMES[(k0 + k) % len(THEMES)]
        s = [r for r in horizon if t['pred'](r)]
        if len(s) >= 3:
            th, sel = t, s; break
    if not th:
        return None
    sel = sel[:16]
    shot_p, info = capture.run(capture.filters(TMP / 'filters.png', th['filt']))
    pages = {}
    for fmt, P in FMTS.items():
        nl = n_list_pages(len(sel), P)
        n = 1 + nl + (1 if shot_p else 0) + 1
        cover = page(f'''
        <div style="position:absolute;inset:0;background:radial-gradient(circle at 75% 75%, {C['sea']} 0%, {C['bg']} 60%)"></div>
        <div style="position:absolute;right:-60px;bottom:{P['B'] - 40}px;font-size:520px;line-height:1;opacity:.9">{th['emo']}</div>
        {head(1, n, P)}
        <div style="position:absolute;left:64px;right:64px;top:{P['T'] + 150}px">
          <div class="saira" style="font-weight:700;font-size:44px;color:{C['hot']}">LE THÈME DE LA SEMAINE</div>
          <div class="saira" style="font-weight:800;font-size:160px;line-height:.86;letter-spacing:-1px;margin-top:10px">{th['title']}</div>
          <div style="font-size:40px;font-weight:600;color:{C['muted']};margin-top:30px;max-width:780px;line-height:1.25">{th['sub']}</div>
          <div class="saira" style="display:inline-block;font-weight:800;font-size:48px;color:#fff;background:{C['fg']};border-radius:16px;padding:8px 24px;margin-top:40px">{len(sel)} courses d'ici {MOIS[(ref + D.timedelta(days=70)).month - 1]} →</div></div>''', P)
        sl = [cover] + list_slides(lambda p: th['title'].replace('<br>', ' '), sel, ref, P, 2, n, kicker=th['short'].upper())
        if shot_p:
            def shot(mw, mh, info=info):
                b = info['box']
                return fit_crop(shot_p, [b[0], b[1], b[2], b[3]], mw, mh)
            sl.append(how(len(sl) + 1, n, P, 'FILTRES', 'TROUVE-LES<br>EN 2 SECONDES',
                          ['Touche <b>Filtres</b>', th['flab'], 'Touche <b>Voir les courses</b>'], shot))
        sl.append(cta_slide(len(sl) + 1, n, P, 'TA COURSE<br><span style="color:#5cc4bc">EST SUR</span><br><span style="color:#d2481e">DOSSARD PÉI</span>',
                            'Toutes les courses de La Réunion,<br>avec les filtres qui vont bien.', 'Enregistre pour plus tard'))
        pages[fmt] = sl
    lines = [f"{th['emo']} {th['short']} : {len(sel)} courses à La Réunion d'ici {MOIS[(ref + D.timedelta(days=70)).month - 1]}", '',
             th['sub'], '']
    lines += [f"• {fdate(r['_d'], short=True).capitalize()} : {r['nom']} ({r['commune']})" for r in sel[:6]]
    if len(sel) > 6:
        lines.append(f"… et {len(sel) - 6} autre{'s' if len(sel) > 7 else ''}")
    lines += ['', f"Sur dossardpei.re : Filtres → {th['flab']} (lien en bio)", '', th.get('cta', 'Tague quelqu\'un que ça intéresse 👇')]
    return pages, lines, TAGS[:4] + [th['tag']]


# ------------------------------------------------------------------ THURSDAY : a region (map)
def build_jeudi(ref, data, races):
    k0 = week_index(ref) % len(REGION_ORDER)
    for weeks in (6, 10):
        for k in range(len(REGION_ORDER)):
            reg = REGION_ORDER[(k0 + k) % len(REGION_ORDER)]
            name, communes = REGIONS[reg]
            end = ref + D.timedelta(days=7 * weeks)
            sel = [r for r in upcoming(races, ref + D.timedelta(days=1), end) if r['commune'] in communes]
            if len(sel) >= 3:
                break
        if len(sel) >= 3:
            break
    else:
        return None
    sel = sel[:16]
    top_commune = max(communes, key=lambda c: sum(r['commune'] == c for r in sel))
    shot_p, info = capture.run(capture.map_commune(TMP / 'map.png', top_commune))
    endlab = f"d'ici le {end.day} {MOIS[end.month - 1]}"
    pages = {}
    for fmt, P in FMTS.items():
        nl = n_list_pages(len(sel), P)
        n = 1 + nl + (1 if shot_p else 0) + 1
        sl = [cover_map(1, n, P, 'PRÈS DE CHEZ TOI', f'COURIR DANS<br>{name}', f"{len(sel)} courses {endlab}", sel, ref, highlight=communes, relief=True)]
        sl += list_slides(lambda p: f'{name}', sel, ref, P, 2, n, numbers=True, kicker=endlab.upper())
        if shot_p:
            def shot(mw, mh, info=info):
                ile = info['ile']; pop = info['pop']
                # island (css 0..470 x 128..565) + popup card overlaid at bottom-left
                mw2 = min(mw, int(mh * 470 / 437 * .95))
                m, mh2, _ = crop_img(ile, 0, 128, 470, 565, mw2)
                pw = int(mw2 * .58)
                pp, ph, _ = crop_img(shot_p, pop[0], pop[1], pop[2], pop[3], pw)
                tot = max(mh2, mh2 * .55 + ph)
                if tot > mh:
                    return None
                return (f'<div style="position:relative;width:{mw2}px;height:{tot:.0f}px">{m}'
                        f'<div style="position:absolute;left:-10px;top:{mh2 * .55:.0f}px">{pp}</div></div>', mw2, tot)
            sl.append(how(len(sl) + 1, n, P, 'CARTE', 'LES COURSES<br>AUTOUR DE TOI',
                          ['Touche <b>Carte</b>', 'Agrandis la carte en plein écran', 'Touche ta commune : <b>ses courses s\'affichent</b>'], shot))
        sl.append(cta_slide(len(sl) + 1, n, P, 'TON WEEK-END<br><span style="color:#5cc4bc">+ TON COIN</span><br><span style="color:#d2481e">= TA COURSE</span>',
                            'Toute l\'île sur la carte,<br>commune par commune.', 'Enregistre et tague tes dalons'))
        pages[fmt] = sl
    nm_ = {'nord': 'le Nord', 'sud': 'le Sud', 'est': 'l’Est', 'ouest': 'l’Ouest'}[reg]
    lines = [f"📍 Courir dans {nm_} : {len(sel)} courses {endlab}", '']
    lines += [f"{k}. {fdate(r['_d'], short=True).capitalize()} : {r['nom']} ({r['commune']})" for k, r in enumerate(sel[:8], 1)]
    if len(sel) > 8:
        lines.append(f"… et {len(sel) - 8} autre{'s' if len(sel) > 9 else ''}")
    lines += ['', 'Toutes les courses sur la carte 👉 dossardpei.re (lien en bio)', '', 'Tague tes dalons du coin 👇']
    return pages, lines, TAGS[:4] + ['#' + _norm(top_commune).replace(' ', '')]


# ------------------------------------------------------------------ 1st of the month (calendar)
def month_grid(y, m, races, w):
    import calendar
    cal = calendar.Calendar(0).monthdatescalendar(y, m)
    cell = w / 7
    hdr = ''.join(f'<div style="text-align:center;font-weight:700;font-size:{cell * .2:.0f}px;color:{C["muted"]}">{j.upper()}</div>' for j in JOURS_C)
    cells = ''
    for wk in cal:
        for dd in wk:
            rs = [r for r in races if r['_d'] == dd]
            dots = ''.join(f'<span style="width:{cell * .16:.0f}px;height:{cell * .16:.0f}px;border-radius:50%;background:{TYPE_COL.get(r["_type"], C["muted"])}"></span>' for r in rs[:6])
            out = dd.month != m
            we = dd.weekday() >= 5
            cells += f'''<div style="height:{cell:.0f}px;border-radius:{cell * .16:.0f}px;background:{'transparent' if out else ('#fff' if not we else '#fff7f2')};
                {'' if out else 'box-shadow:0 0 0 1px ' + C['line'] + ';'}padding:{cell * .1:.0f}px;opacity:{.25 if out else 1}">
                <div class="saira" style="font-weight:800;font-size:{cell * .3:.0f}px;line-height:1">{dd.day}</div>
                <div style="display:flex;flex-wrap:wrap;gap:{cell * .05:.0f}px;margin-top:{cell * .07:.0f}px">{'' if out else dots}</div></div>'''
    return f'''<div style="width:{w}px"><div style="display:grid;grid-template-columns:repeat(7,1fr);gap:8px;margin-bottom:10px">{hdr}</div>
      <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:8px">{cells}</div></div>'''


def build_mois(ref, data, races):
    y, m = ref.year, ref.month
    import calendar
    last = D.date(y, m, calendar.monthrange(y, m)[1])
    sel = upcoming(races, D.date(y, m, 1), last)
    if not sel:
        return None
    shot_p, info = capture.run(capture.cal_month(TMP / 'cal_m.png', f'{y}-{m:02d}'))
    pages = {}
    used = sorted({r['_type'] for r in sel})
    legend = ''.join(f'<span style="display:inline-flex;align-items:center;gap:8px;font-size:24px;font-weight:600;color:{C["muted"]};margin-right:20px"><span style="width:18px;height:18px;border-radius:50%;background:{TYPE_COL[t]}"></span>{TYPE_LAB[t]}</span>' for t in used)
    for fmt, P in FMTS.items():
        nl = n_list_pages(len(sel), P)
        n = 1 + nl + (1 if shot_p else 0) + 1
        gw = P['W'] - 64 - P['R'] if P['R'] > 64 else 820
        cover = page(f'''
        {head(1, n, P)}
        <div style="position:absolute;left:64px;right:64px;top:{P['T'] + 100}px">
          <div class="saira" style="font-weight:700;font-size:40px;color:{C['hot']}">LE MOIS EN UN COUP D'ŒIL</div>
          <div class="saira" style="font-weight:800;font-size:150px;line-height:.86;letter-spacing:-1px">{MOIS[m - 1].upper()} {y}</div>
          <div style="font-size:36px;font-weight:600;color:{C['muted']};margin-top:10px">{len(sel)} courses à La Réunion</div></div>
        <div style="position:absolute;left:64px;top:{P['T'] + 370}px">{month_grid(y, m, sel, gw)}<div style="margin-top:22px">{legend}</div></div>''', P)
        sl = [cover] + list_slides(lambda p: f'{MOIS[m - 1].upper()}' + (f' ({p + 1}/{nl})' if nl > 1 else ''), sel, ref, P, 2, n, kicker='TOUTES LES COURSES DU MOIS')
        if shot_p:
            sl.append(how(len(sl) + 1, n, P, 'CALENDRIER', 'TOUT LE MOIS<br>SUR UN ÉCRAN',
                          ['Touche <b>Calendrier</b>', 'Une pastille = une course', 'Touche un jour pour voir ses courses'],
                          lambda mw, mh: fit_crop(shot_p, info, mw, mh)))
        sl.append(cta_slide(len(sl) + 1, n, P, f'{MOIS[m - 1].upper()}<br><span style="color:#5cc4bc">C\'EST PARTI</span>',
                            'Toutes les courses du mois,<br>dans le calendrier du site.', 'Enregistre pour tout le mois'))
        pages[fmt] = sl
    lines = [f"📅 {MOIS[m - 1].capitalize()} à La Réunion : {len(sel)} courses", '']
    import itertools
    for wk, grp in itertools.groupby(sel, key=lambda r: r['_d'].isocalendar()[1]):
        g = list(grp)
        lines.append(f"• Semaine du {g[0]['_d'].day} : " + ' · '.join(r['nom'] for r in g[:5]) + (f" (+{len(g) - 5})" if len(g) > 5 else ''))
    lines += ['', 'Le calendrier complet 👉 dossardpei.re (lien en bio)', '', 'Enregistre pour tout le mois 🔖']
    return pages, lines, TAGS


# ------------------------------------------------------------------ render
async def _render(pages, outdir):
    from playwright.async_api import async_playwright
    from PIL import Image
    files = {}
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for fmt, sl in pages.items():
            P = FMTS[fmt]
            d_ = outdir / fmt; d_.mkdir(parents=True, exist_ok=True)
            pg = await b.new_page(viewport={'width': 1080, 'height': P['H']})
            files[fmt] = []
            for k, h in enumerate(sl, 1):
                f = TMP / f'_{fmt}_{k}.html'; f.write_text(h)
                await pg.goto(f.as_uri()); await pg.evaluate('document.fonts.ready'); await pg.wait_for_timeout(250)
                png = d_ / f'{k}.png'
                await pg.screenshot(path=str(png))
                jp = d_ / f'{outdir.name}-{fmt}-{k:02d}.jpg'
                Image.open(png).convert('RGB').save(jp, quality=92); png.unlink()
                files[fmt].append(str(jp))
            await pg.close()
        await b.close()
    return files


BUILDERS = {'lundi': build_lundi, 'mardi': build_mardi, 'jeudi': build_jeudi, 'mois': build_mois}


def make(kind, day, data, races):
    TMP.mkdir(parents=True, exist_ok=True)
    outdir = OUT / f'{day.isoformat()}-{kind}'
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True)
    if kind == 'vendredi':
        import reel
        res = reel.build(day, data, races, outdir)
        if not res:
            return None
        path, lines, tags = res
        files = {'reel': [str(path)]}
    else:
        res = BUILDERS[kind](day, data, races)
        if not res:
            return None
        pages, lines, tags = res
        files = asyncio.run(_render(pages, outdir))
    for fmt in ('instagram', 'tiktok'):
        (outdir / f'legende-{fmt}.txt').write_text(caption(lines, tags, fmt))
    files['legendes'] = [str(outdir / 'legende-instagram.txt'), str(outdir / 'legende-tiktok.txt')]
    (outdir / 'files.json').write_text(json.dumps(files, ensure_ascii=False, indent=1))
    return outdir, files


def plan_week(monday):
    """[(kind, date)] for the week starting monday; the 1st of the month replaces that day's post."""
    plan = [('lundi', monday), ('mardi', monday + D.timedelta(days=1)), ('jeudi', monday + D.timedelta(days=3)),
            ('vendredi', monday + D.timedelta(days=4))]
    for k in range(7):
        dd = monday + D.timedelta(days=k)
        if dd.day == 1:
            plan = [p for p in plan if p[1] != dd] + [('mois', dd)]
    return sorted(plan, key=lambda p: p[1])


def main():
    kind, day = sys.argv[1], D.date.fromisoformat(sys.argv[2])
    data, races = load()
    todo = plan_week(day) if kind == 'semaine' else [(kind, day)]
    report = []
    for k, dd in todo:
        try:
            r = make(k, dd, data, races)
            report.append({'kind': k, 'date': dd.isoformat(), 'ok': bool(r), 'dir': str(r[0]) if r else None,
                           'files': r[1] if r else None, 'note': None if r else 'aucune course pour ce format'})
        except Exception as e:
            import traceback; traceback.print_exc()
            report.append({'kind': k, 'date': dd.isoformat(), 'ok': False, 'note': f'erreur : {e}'})
    (OUT / 'rapport.json').write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
