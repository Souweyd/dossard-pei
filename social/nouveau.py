"""Story / TikTok « Nouveau dossard » : vidéo 1080x1920 de 11 s (modèle validé le 14/11/2026).
0-1,5 s : « Nouveau dossard » + nom de la course sur la carte de l'île floutée ;
1,5-3,5 s : la carte se précise et zoome sur le lieu de départ (commune entourée, repère, lieu) ;
4-7 s : la carte de la course monte (affiche, nom, date, lieu, statut, une ligne par course :
discipline, nom, heure, distance, D+), puis le logo ; image fixe jusqu'à 11 s.

Usage (depuis la racine du dépôt) : python3 social/nouveau.py <id> [<id> ...]
Sortie : social/out/nouveau/<id>.mp4 ; affiche le texte du post pour chaque course.
Requiert Playwright (Chromium préinstallé), Pillow et ffmpeg.
"""
import sys, re, pathlib, html, datetime as D
from core import load, status, MAP, P_xy, _same, poster_path, art_path, fmt_km, JOURS, JOURS_C, MOIS, MOIS_C, TYPE_COL, TYPE_EMO, ROOT, SOC
import rec

OUT = SOC / 'out' / 'nouveau'
F = (SOC / 'fonts').as_uri()
LOGO = (SOC / 'assets' / 'logo-512.png').as_uri()
INK, TEAL, CREAM, SURF, MUTED, SEA = '#1d2523', '#0d6b67', '#f5efe6', '#fffcf7', '#6b625a', '#cfe1e4'
W, H, DUR = 1080, 1920, 11.0
esc = lambda s: html.escape(str(s))
TLAB = {'trail': 'Trail', 'route': 'Route', 'marche': 'Rando', 'cross': 'Cross', 'relais': 'Relais',
        'multisport': 'Multisport', 'jeunes': 'Jeunes', 'autre': 'Course'}
TCOL = dict(TYPE_COL); TCOL.setdefault('relais', '#6a4fb3'); TCOL.setdefault('multisport', '#1f6fb2'); TCOL.setdefault('jeunes', '#d07a12')


def island():
    """Whole-island relief (site tiles, level 2: 4 x 4 tiles = 4 px per map unit), built once."""
    f = SOC / 'out' / 'island.webp'
    if not f.exists():
        from PIL import Image
        t = Image.open(ROOT / 'tiles' / 't2_0_0.webp'); tw, th = t.size
        img = Image.new('RGBA', (4 * tw, 4 * th), (0, 0, 0, 0))
        for i in range(4):
            for j in range(4):
                t = Image.open(ROOT / 'tiles' / f't2_{i}_{j}.webp').convert('RGBA'); img.paste(t, (j * tw, i * th), t)
        f.parent.mkdir(parents=True, exist_ok=True); img.save(f, quality=88)
    return f.as_uri()


def bbox(nom):
    M = MAP(); xs, ys = [], []
    for c in M['communes']:
        if _same(c['nom'], [nom]):
            n = [float(v) for v in re.findall(r'-?\d+\.?\d*', c['d'])]
            xs += n[0::2]; ys += n[1::2]
    return min(xs), min(ys), max(xs), max(ys)


def cam(k, cx, cy, sx, sy):
    """transform putting world point (cx,cy) at screen (sx,sy) with zoom k"""
    # zoom about the start point (px, py) so that it travels straight to its place
    px, py = cam.p
    sx, sy = sx + (px - cx) * k, sy + (py - cy) * k
    return f'translate({sx:.1f}px,{sy:.1f}px) scale({k:.4f}) translate({-px:.2f}px,{-py:.2f}px)'


def when(r):
    d0 = D.date.fromisoformat(r['date'])
    if r.get('fin') and r['fin'] != r['date']:
        d1 = D.date.fromisoformat(r['fin'])
        return f"Du {JOURS[d0.weekday()]} {d0.day}{'' if d0.month == d1.month else ' ' + MOIS[d0.month - 1]} au {JOURS[d1.weekday()]} {d1.day} {MOIS[d1.month - 1]} {d1.year}"
    return f"{JOURS[d0.weekday()].capitalize()} {d0.day} {MOIS[d0.month - 1]} {d0.year}"


def badge(r):
    code, lab = status(r, D.date.today())
    if code == 'complet':
        return 'Complet', '', '#c62828'
    if code == 'bientot':
        return ('Inscriptions à venir', '', TEAL) if r.get('avenir') else ('Ouverture des inscriptions', lab.replace('Inscriptions dès le ', 'le '), TEAL)
    if code == 'clot':
        return lab, '', '#d2481e'
    return 'Inscriptions ouvertes', lab.replace('Inscriptions ', ''), '#2e7d32'


def rows(r):
    eps = r.get('epreuves', [])
    eps = sorted(eps, key=lambda e: (-(e.get('km') or 0)))
    out = []
    for e in eps:
        t = e.get('type') or 'autre'
        nm = re.sub(r'\s*\((%s)\)$' % '|'.join(TLAB.values()), '', e['nom'], flags=re.I)
        fig = f"{fmt_km(e['km'])}<small> km</small>" if e.get('km') else ''
        dp = f"{e['dp']:,}".replace(',', ' ') + ' D+' if e.get('dp') else ''
        out.append((t, nm, e.get('h') or '', fig, dp))
    return out


def page(r):
    M = MAP()
    x0, y0, x1, y1 = bbox(r['commune'])
    px, py = P_xy(*r['ll'])
    cam.p = (px, py)
    k0 = 1000 / M['W']
    k1 = min(820 / (x1 - x0), 760 / (y1 - y0), 4.2)
    zc = (px, py)   # centred on the start
    PIN_Z = (W / 2 + (px - zc[0]) * k1, 900 + (py - zc[1]) * k1)      # pin on screen after the zoom
    PIN_F = (PIN_Z[0], PIN_Z[1] - 900 + 480)                            # after the shift up
    T0 = cam(k0 * .96, M['W'] / 2, M['H'] / 2, W / 2, 900)
    T1 = cam(k0, M['W'] / 2, M['H'] / 2, W / 2, 900)
    T2 = cam(k1, zc[0], zc[1], W / 2, 900)
    T3 = cam(k1, zc[0], zc[1], W / 2, 480)
    p = lambda t: f'{t / DUR * 100:.2f}%'
    poster = poster_path(r)
    if poster and 'utoi-logo' in str(poster):
        poster = None
    img = (poster or art_path(r)).as_uri()
    b1, b2, bc = badge(r)
    nm = r['nom']; nfs = 96 if len(nm) <= 20 else (80 if len(nm) <= 30 else 66); fs = 68 if len(nm) <= 20 else (58 if len(nm) <= 30 else 48)
    rw = rows(r); more = 0
    if len(rw) > 5:
        more = len(rw) - 4; rw = rw[:4]
    lieu = r.get('lieu') or ''
    lieu = '' if _same(lieu, [r['commune']]) else lieu
    communes = ''.join(f'<path d="{c["d"]}"/>' for c in M['communes'] if not _same(c['nom'], [r['commune']]))
    mine = ''.join(f'<path d="{c["d"]}"/>' for c in M['communes'] if _same(c['nom'], [r['commune']]))
    allc = ''.join(f'<path d="{c["d"]}"/>' for c in M['communes'])
    rows_html = ''.join(f'''<div class="row" style="animation-delay:{5.5 + i * .14:.2f}s">
      <span class="chip" style="background:{TCOL.get(t, '#666')}">{esc(TLAB.get(t, 'Course'))}</span>
      <span class="rn">{esc(n)}</span><span class="rh">{esc(h)}</span>
      <span class="rf">{f}{f'<em>{esc(dp)}</em>' if dp else ''}</span></div>''' for i, (t, n, h, f, dp) in enumerate(rw))
    if more:
        rows_html += f'<div class="row more" style="animation-delay:{5.5 + 4 * .14:.2f}s">+ {more} autres formats</div>'
    ncourses = len(r.get('epreuves', []))
    head = f"{ncourses} course{'s' if ncourses > 1 else ''} au programme" if ncourses > 1 else 'Au programme'
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:S;font-weight:800;src:url('{F}/SairaCondensed-800.woff2')}}
@font-face{{font-family:S;font-weight:700;src:url('{F}/SairaCondensed-700.woff2')}}
@font-face{{font-family:I;font-weight:400;src:url('{F}/inter-latin-400-normal.woff2')}}
@font-face{{font-family:I;font-weight:600;src:url('{F}/inter-latin-600-normal.woff2')}}
@font-face{{font-family:I;font-weight:700;src:url('{F}/inter-latin-700-normal.woff2')}}
@font-face{{font-family:I;font-weight:800;src:url('{F}/inter-latin-800-normal.woff2')}}
*{{box-sizing:border-box;margin:0;padding:0}} html,body{{width:{W}px;height:{H}px;overflow:hidden;background:{SEA}}}
body{{font-family:I,sans-serif;color:{INK};position:relative}} .s{{font-family:S,sans-serif}}
.anim{{animation-duration:{DUR}s;animation-fill-mode:both;animation-timing-function:linear}}
#lens{{position:absolute;inset:0;animation-name:lens}}
@keyframes lens{{0%{{filter:blur(22px) saturate(.8)}} {p(1.3)}{{filter:blur(22px) saturate(.8);animation-timing-function:ease-out}} {p(2.3)}{{filter:blur(0) saturate(1)}} 100%{{filter:blur(0) saturate(1)}}}}
#world{{position:absolute;left:0;top:0;width:{M['W']}px;height:{M['H']}px;transform-origin:0 0;animation-name:cam}}
@keyframes cam{{0%{{transform:{T0}}} {p(1.4)}{{transform:{T1};animation-timing-function:cubic-bezier(.6,0,.25,1)}}
  {p(3.2)}{{transform:{T2}}} {p(3.9)}{{transform:{T2};animation-timing-function:cubic-bezier(.5,0,.2,1)}} {p(4.7)}{{transform:{T3}}} 100%{{transform:{T3}}}}}
#world img{{position:absolute;left:0;top:0;width:{M['W']}px;height:{M['H']}px}}
#world svg{{position:absolute;left:0;top:0;overflow:visible}}
.dim{{animation-name:dim}} @keyframes dim{{0%,{p(2.6)}{{opacity:0}} {p(3.3)},100%{{opacity:1}}}}
.hl{{animation-name:hl}} @keyframes hl{{0%,{p(2.8)}{{opacity:0}} {p(3.3)},100%{{opacity:1}}}}
#veil{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(245,239,230,0) 30%,rgba(245,239,230,.0) 100%);animation-name:veil}}
@keyframes veil{{0%,{p(3.9)}{{opacity:0}} {p(4.7)},100%{{opacity:1;background:linear-gradient(180deg,rgba(245,239,230,0) 28%,rgba(245,239,230,.9) 42%)}}}}
#tag{{position:absolute;left:0;right:0;top:0;display:flex;flex-direction:column;align-items:center;transform-origin:50% 0;animation-name:tag}}
#tag .t{{background:{TEAL};color:#fff;font-weight:800;font-size:92px;letter-spacing:1px;padding:10px 44px 14px;border-radius:22px;box-shadow:0 18px 40px rgba(13,60,58,.35);line-height:1}}
@keyframes tag{{0%{{transform:translateY(700px) scale(.5);opacity:0}} {p(.25)}{{transform:translateY(700px) scale(.5);opacity:0;animation-timing-function:cubic-bezier(.3,1.6,.5,1)}}
  {p(.8)}{{transform:translateY(700px) scale(1);opacity:1}} {p(1.5)}{{transform:translateY(700px) scale(1);opacity:1;animation-timing-function:cubic-bezier(.6,0,.2,1)}}
  {p(2.4)}{{transform:translateY(250px) scale(.62);opacity:1}} 100%{{transform:translateY(250px) scale(.62);opacity:1}}}}
#tag .n{{margin-top:22px;max-width:940px;background:{SURF};color:{INK};font-weight:800;font-size:{nfs}px;line-height:.98;text-align:center;padding:14px 40px 18px;border-radius:22px;box-shadow:0 18px 40px rgba(29,37,35,.3);animation-name:nm}}
@keyframes nm{{0%,{p(.55)}{{opacity:0;transform:translateY(30px)}} {p(.55)}{{animation-timing-function:cubic-bezier(.2,.9,.3,1)}} {p(1.0)},{p(3.7)}{{opacity:1;transform:none}} {p(4.1)},100%{{opacity:0;transform:translateY(-10px)}}}}
#pin{{position:absolute;left:0;top:0;animation-name:pinmove}}
@keyframes pinmove{{0%,{p(3.9)}{{transform:translate({PIN_Z[0]:.0f}px,{PIN_Z[1]:.0f}px)}} {p(3.9)}{{animation-timing-function:cubic-bezier(.5,0,.2,1)}} {p(4.7)},100%{{transform:translate({PIN_F[0]:.0f}px,{PIN_F[1]:.0f}px)}}}}
#pin .drop{{animation-name:drop}}
@keyframes drop{{0%,{p(3.15)}{{transform:translateY(-260px);opacity:0}} {p(3.2)}{{opacity:1;animation-timing-function:cubic-bezier(.5,0,1,.5)}} {p(3.5)}{{transform:translateY(0)}} {p(3.6)}{{transform:translateY(-18px)}} {p(3.7)},100%{{transform:translateY(0);opacity:1}}}}
.mk{{position:absolute;left:-30px;top:-82px;width:60px;height:82px}}
.ring{{position:absolute;left:-50px;top:-20px;width:100px;height:40px;border-radius:50%;border:4px solid {TEAL};animation-name:ring}}
@keyframes ring{{0%,{p(3.5)}{{transform:scale(.2);opacity:0}} {p(3.55)}{{opacity:.9;transform:scale(.3)}} {p(4.3)},100%{{transform:scale(1.6);opacity:0}}}}
.lab{{position:absolute;top:22px;left:0;transform:translateX(-50%);white-space:nowrap;text-align:center;animation-name:lab}}
.lab b{{display:inline-block;background:{INK};color:#fff;font-family:S;font-weight:800;font-size:48px;padding:4px 26px 6px;border-radius:14px;line-height:1.05}}
.lab i{{display:block;font-style:normal;font-weight:700;font-size:28px;color:{INK};margin-top:6px;text-shadow:0 0 8px #fff,0 0 4px #fff}}
@keyframes lab{{0%,{p(3.55)}{{opacity:0;transform:translate(-50%,14px)}} {p(3.9)},100%{{opacity:1;transform:translate(-50%,0)}}}}
#stack{{position:absolute;left:36px;right:36px;top:700px}}
#card{{position:relative;background:{SURF};border-radius:40px;box-shadow:0 -10px 50px rgba(29,37,35,.18),0 30px 60px rgba(29,37,35,.2);padding:40px 40px 26px;animation-name:card}}
@keyframes card{{0%,{p(3.95)}{{transform:translateY(1500px)}} {p(3.95)}{{animation-timing-function:cubic-bezier(.2,.9,.25,1)}} {p(4.8)},100%{{transform:translateY(0)}}}}
.top{{display:flex;gap:36px;height:420px}}
.post{{flex:0 0 300px;height:420px;display:flex;align-items:flex-start;justify-content:center;animation-name:post}}
.post img{{max-width:300px;max-height:420px;border-radius:18px;box-shadow:0 14px 30px rgba(29,37,35,.28);display:block}}
@keyframes post{{0%,{p(4.5)}{{opacity:0;transform:scale(.9) rotate(-3deg)}} {p(5.0)},100%{{opacity:1;transform:scale(1) rotate(0)}}}}
.info{{flex:1;min-width:0;display:flex;flex-direction:column;gap:22px;padding-top:4px}}
.f{{animation-name:f}} @keyframes f{{0%{{opacity:0;transform:translateY(16px)}} 6%,100%{{opacity:1;transform:none}}}}
.nm{{font-weight:800;font-size:{fs}px;line-height:.98}}
.ln{{display:flex;gap:14px;align-items:flex-start;font-size:31px;font-weight:600;line-height:1.2}}
.ln svg{{flex:0 0 34px;margin-top:2px}} .ln small{{display:block;font-size:25px;font-weight:400;color:{MUTED};margin-top:3px}}
.st{{display:inline-flex;flex-direction:column;align-self:flex-start;color:#fff;border-radius:16px;padding:10px 20px 11px;font-weight:700;font-size:28px;line-height:1.15}}
.st small{{font-weight:600;font-size:24px;opacity:.92}}
.ph{{font-family:S;font-weight:700;font-size:30px;letter-spacing:2px;text-transform:uppercase;color:{MUTED};margin:30px 0 8px}}
.row{{display:grid;grid-template-columns:150px 1fr 84px 150px;align-items:center;gap:18px;min-height:72px;padding:8px 0;border-top:2px solid #ece4d8;animation-name:f;animation-duration:{DUR}s;animation-fill-mode:both}}
.chip{{color:#fff;font-weight:700;font-size:22px;text-transform:uppercase;letter-spacing:1px;text-align:center;border-radius:10px;padding:7px 0}}
.rn{{font-size:28px;font-weight:600;line-height:1.15;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
.rh{{font-size:26px;color:{MUTED};text-align:right}}
.rf{{font-family:S;font-weight:800;font-size:44px;text-align:right;line-height:.9}} .rf small{{font-size:28px}}
.rf em{{display:block;font-family:I;font-style:normal;font-weight:600;font-size:22px;color:{MUTED};margin-top:4px}}
.more{{display:block;line-height:72px;color:{MUTED};font-size:26px;font-weight:600}}
#brand{{margin-top:34px;display:flex;justify-content:center;animation-name:brand}}
#brand>div{{display:flex;align-items:center;gap:18px;background:#fff;border:5px solid {INK};border-radius:999px;padding:10px 34px 10px 14px;box-shadow:0 14px 26px rgba(29,37,35,.22)}}
@keyframes brand{{0%,{p(6.2)}{{opacity:0;transform:translateY(30px)}} {p(6.7)},100%{{opacity:1;transform:none}}}}
</style></head><body>
<div id="lens" class="anim"><div id="world" class="anim"><img src="{island()}">
 <svg width="{M['W']}" height="{M['H']}" viewBox="0 0 {M['W']} {M['H']}">
  <g class="anim dim" fill="{CREAM}" fill-opacity=".55">{communes}</g>
  <g fill="none" stroke="#fff" stroke-opacity=".85" stroke-width="2" vector-effect="non-scaling-stroke" style="vector-effect:non-scaling-stroke">{allc.replace('<path ', '<path vector-effect="non-scaling-stroke" ')}</g>
  <g class="anim hl" fill="none" stroke="{TEAL}" stroke-width="6" stroke-linejoin="round">{mine.replace('<path ', '<path vector-effect="non-scaling-stroke" ')}</g>
 </svg></div></div>
<div id="veil" class="anim"></div>
<div id="pin" class="anim"><div class="drop anim">
  <div class="ring anim"></div>
  <svg class="mk" viewBox="0 0 60 82"><path d="M30 80C30 80 4 48 4 28a26 26 0 0 1 52 0c0 20-26 52-26 52z" fill="{TEAL}" stroke="#fff" stroke-width="5"/><circle cx="30" cy="28" r="10" fill="#fff"/></svg></div>
  <div class="lab anim"><b>{esc(r['commune'])}</b>{f'<i>{esc(lieu)}</i>' if lieu else ''}</div></div>
<div id="tag" class="anim"><div class="s t">Nouveau dossard</div><div class="s n anim">{esc(nm)}</div></div>
<div id="stack"><div id="card" class="anim">
 <div class="top"><div class="post anim"><img src="{img}"></div>
  <div class="info">
   <div class="nm s f anim" style="animation-delay:4.75s;animation-duration:{DUR}s">{esc(nm)}</div>
   <div class="ln f anim" style="animation-delay:4.95s"><svg viewBox="0 0 24 24" fill="none" stroke="{TEAL}" stroke-width="2.2"><rect x="3" y="5" width="18" height="16" rx="3"/><path d="M3 10h18M8 3v4M16 3v4"/></svg><span>{esc(when(r))}</span></div>
   <div class="ln f anim" style="animation-delay:5.1s"><svg viewBox="0 0 24 24" fill="none" stroke="{TEAL}" stroke-width="2.2"><path d="M12 22s-7-7.5-7-13a7 7 0 0 1 14 0c0 5.5-7 13-7 13z"/><circle cx="12" cy="9" r="2.5"/></svg><span>{esc(r['commune'])}{f'<small>{esc(lieu)}</small>' if lieu else ''}</span></div>
   <div class="st f anim" style="background:{bc};animation-delay:5.25s">{esc(b1)}{f'<small>{esc(b2)}</small>' if b2 else ''}</div>
  </div></div>
 <div class="ph f anim" style="animation-delay:5.4s">{esc(head)}</div>
 {rows_html}
</div>
<div id="brand" class="anim"><div><img src="{LOGO}" style="width:84px;display:block">
 <div><div class="s" style="font-weight:800;font-size:44px;line-height:.95">Dossard Péi</div>
 <div style="font-weight:700;font-size:26px;color:{TEAL};margin-top:2px">Parcours, infos et inscription · dossardpei.re</div></div></div></div></div>
</body></html>'''


def when_c(r):
    d0 = r['_d']
    s = f"{JOURS_C[d0.weekday()]} {d0.day} {MOIS[d0.month - 1]}"
    if r.get('fin') and r['fin'] != r['date']:
        d1 = D.date.fromisoformat(r['fin'])
        s = f"du {JOURS_C[d0.weekday()]} {d0.day}{'' if d0.month == d1.month else ' ' + MOIS[d0.month - 1]} au {JOURS_C[d1.weekday()]} {d1.day} {MOIS[d1.month - 1]}"
    if d0.year != D.date.today().year:
        s += f' {d0.year}'
    return s


def distances(r):
    ep = sorted([e for e in r.get('epreuves', []) if e.get('km')], key=lambda e: -e['km'])
    if not ep:
        return ''
    if len(ep) > 3:
        return f"{len(ep)} formats, de {fmt_km(ep[-1]['km'])} à {fmt_km(ep[0]['km'])} km"
    m = ep[0]
    s = f"{fmt_km(m['km'])} km" + (f" · {m['dp']} D+" if m.get('dp') else '')
    return s + ''.join(f" · {fmt_km(e['km'])} km" for e in ep[1:3])


TAG = {'trail': '#trail', 'route': '#courseapied', 'marche': '#rando', 'cross': '#cross', 'relais': '#relais',
       'multisport': '#triathlon', 'jeunes': '#coursesenfants', 'autre': '#running'}
LOW = {'trail': 'trail', 'route': 'course', 'marche': 'rando', 'cross': 'cross', 'relais': 'relais',
       'multisport': 'multisport', 'jeunes': 'courses enfants', 'autre': 'course'}


def formats(r):
    """« trail 25 km, course 12 km, rando 12 km et courses enfants » (au plus 3, sinon « 5 formats de 10 à 85 km »)"""
    eps = sorted(r.get('epreuves', []), key=lambda e: -(e.get('km') or 0))
    kms = [e['km'] for e in eps if e.get('km')]
    if len(eps) > 4 and kms:
        return f"{len(eps)} formats de {fmt_km(min(kms))} à {fmt_km(max(kms))} km"
    groups = {}                                   # type -> distances, in order of the longest course
    for e in eps:
        g = groups.setdefault(LOW.get(e.get('type') or 'autre', 'course'), [])
        if e.get('km') and fmt_km(e['km']) not in g:
            g.append(fmt_km(e['km']))
    et = lambda xs: (', '.join(xs[:-1]) + ' et ' + xs[-1]) if len(xs) > 1 else (xs[0] if xs else '')
    return et([f"{t} {et(k)} km" if k else t for t, k in groups.items()])


def hashtag(s):
    import unicodedata
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return '#' + re.sub(r'[^A-Za-z0-9]', '', s).lower()


def post_text(r):
    """Titre, une ligne d'infos, les hashtags (format validé le 14/11/2026)."""
    emo = TYPE_EMO.get(r['_type'], '🏅')
    code, lab = status(r, D.date.today())
    d = when_c(r); d = d[0].upper() + d[1:]
    f = formats(r)
    insc = {'complet': 'Complet', 'bientot': lab}.get(code, 'Inscriptions ouvertes')
    line = f"{d} à {r['commune']}" + (f" : {f}" if f else '') + f". {insc} 👉 dossardpei.re"
    tags = []
    for e in sorted(r.get('epreuves', []), key=lambda e: -(e.get('km') or 0)):
        t = TAG.get(e.get('type') or 'autre')
        if t and t not in tags:
            tags.append(t)
    tags = tags[:3] + [hashtag(r['commune']), '#lareunion', '#974', '#dossardpei']
    return '\n'.join([f"{emo} Nouveau dossard : {r['nom']}", line, ' '.join(tags)])




def main(ids):
    data, races = load()
    byid = {r['id']: r for r in races}
    OUT.mkdir(parents=True, exist_ok=True)
    for rid in ids:
        r = byid.get(rid)
        if not r:
            print(f'{rid} : introuvable ou masquée'); continue
        f = OUT / f'_{rid}.html'; f.write_text(page(r))
        tmp = OUT / f'_{rid}.mp4'
        rec.record(f, tmp, DUR)
        tmp.replace(OUT / f'{rid}.mp4'); f.unlink()
        print(f'=== {OUT / (rid + ".mp4")}\n{post_text(r)}\n')


if __name__ == '__main__':
    main(sys.argv[1:])
