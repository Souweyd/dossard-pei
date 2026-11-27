"""Story 1080x1920 « Course annulée », nouvelle DA « mer et île » (15/11/2026) : île floutée sous un voile bleu,
étiquette turquoise, nom sur panneau crème, affiche passée en gris avec un tampon ANNULÉE, pastille logo.

Usage (depuis la racine du dépôt) :
  python3 social/annule.py --a-annoncer   → courses annulées à venir absentes de state/annules.json
  python3 social/annule.py <id> ["motif court"] ["info pratique"]
La course peut être masquée (annule/hidden) : on la lit directement dans data.json.
Sortie : social/out/annule/<id>.mp4 (vidéo de 9 s), <id>-couverture.jpg et <id>.jpg ; affiche le texte du post.
"""
import sys, asyncio, json, datetime as D
from core import ROOT, SOC, poster_path, art_path
import nouveau as N
from core import MAP
import post_lundi as PL
import picto, safe

OUT = SOC / 'out' / 'annule'
RED = '#b3261e'


def race(rid):
    d = json.load(open(ROOT / 'data.json'))
    for r in d['races']:
        if r['id'] == rid:
            r = dict(r); r['_d'] = D.date.fromisoformat(r['date'])
            return r


def source_txt(r):
    """Annulation apprise ailleurs que chez l'organisateur : annule_source = {"nom": ..., "date": "AAAA-MM-JJ", "url"?}."""
    s = r.get('annule_source')
    if not s:
        return ''
    if isinstance(s, str):
        s = {'nom': s}
    out = f"Source : {s['nom']}"
    if s.get('date'):
        d = D.date.fromisoformat(s['date'])
        out += f", {d.day} {N.MOIS[d.month - 1]}"
    return out


def html_story(r, motif='', info=''):
    poster = poster_path(r)
    if poster and 'utoi-logo' in str(poster):
        poster = None
    img = (poster or art_path(r)).as_uri()
    src = source_txt(r)
    nm = r['nom']; fs = 84 if len(nm) <= 20 else (70 if len(nm) <= 30 else 58)
    E = N.esc; M = MAP(); F = N.F
    bg = PL.world(1000 / M['W'], M['W'] / 2, M['H'] / 2, N.W / 2, N.H / 2)
    extra = ''.join([
        f'<div style="font-size:34px;font-weight:600;margin-top:16px">{E(motif)}</div>' if motif else '',
        f'<div style="font-size:30px;font-weight:600;color:{N.MUTED};margin-top:12px">{E(src)}</div>' if src else '',
        f'<div style="display:inline-block;margin-top:20px;font-weight:700;font-size:32px;color:#fff;background:{RED};border-radius:16px;padding:10px 26px">{E(info)}</div>' if info else ''])
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:S;font-weight:800;src:url('{F}/SairaCondensed-800.woff2')}}
@font-face{{font-family:I;font-weight:400;src:url('{F}/inter-latin-400-normal.woff2')}}
@font-face{{font-family:I;font-weight:600;src:url('{F}/inter-latin-600-normal.woff2')}}
@font-face{{font-family:I;font-weight:700;src:url('{F}/inter-latin-700-normal.woff2')}}
*{{box-sizing:border-box;margin:0;padding:0}} html,body{{width:{N.W}px;height:{N.H}px;overflow:hidden;background:#083b5a}}
body{{font-family:I,sans-serif;color:{N.INK};position:relative}} .s{{font-family:S,sans-serif;font-weight:800}} .abs{{position:absolute}}
.world{{position:absolute;left:0;top:0;transform-origin:0 0}} .world img,.world svg{{position:absolute;left:0;top:0}}
</style></head><body>
<div class="abs" style="inset:0;filter:blur(14px) saturate(.85)">{bg}</div>
<div class="abs" style="inset:0;background:rgba(8,59,90,.35)"></div>
<div class="abs" style="left:0;right:0;top:210px;display:flex;flex-direction:column;align-items:center;gap:20px">
  <div class="s" style="background:{N.TEAL};color:#fff;font-size:64px;letter-spacing:1px;padding:8px 36px 12px;border-radius:20px;box-shadow:0 18px 40px rgba(13,60,58,.35);line-height:1">Course annulée</div>
  <div class="s" style="max-width:940px;background:{N.SURF};font-size:{fs}px;line-height:.98;text-align:center;padding:14px 40px 18px;border-radius:22px;box-shadow:0 18px 40px rgba(29,37,35,.3)">{E(nm)}</div></div>
<div class="abs" style="left:150px;right:150px;top:{560 if len(nm) <= 30 else 620}px;height:640px;display:flex;align-items:center;justify-content:center">
  <div style="position:relative;display:inline-block">
    <img src="{img}" style="max-width:700px;max-height:640px;border-radius:22px;box-shadow:0 26px 54px rgba(4,20,30,.45);display:block;filter:grayscale(1) contrast(.9) brightness(1.08)">
    <div class="abs" style="inset:0;display:flex;align-items:center;justify-content:center">
      <div class="s" style="transform:rotate(-14deg);color:{RED};background:rgba(255,255,255,.9);border:10px solid {RED};border-radius:18px;padding:4px 34px;font-size:112px;letter-spacing:6px;line-height:1.05;box-shadow:0 14px 30px rgba(29,37,35,.3)">ANNULÉE</div></div></div></div>
<div class="abs" style="left:72px;right:72px;top:1290px;background:{N.SURF};border-radius:32px;box-shadow:0 24px 50px rgba(4,20,30,.35);padding:30px 40px 34px;text-align:center">
  <div style="font-size:40px;font-weight:700">{E(N.when(r))} · {E(r['commune'])}</div>{extra}</div>
<div class="abs" style="left:0;right:0;top:1660px;display:flex;justify-content:center">
  <div style="display:flex;align-items:center;gap:20px;background:#fff;border:5px solid {N.INK};border-radius:999px;padding:12px 38px 12px 16px;box-shadow:0 16px 30px rgba(4,20,30,.3)">
    <img src="{N.LOGO}" style="width:96px;display:block">
    <div><div class="s" style="font-size:50px;line-height:.95">Dossard Péi</div>
    <div style="font-weight:700;font-size:28px;color:{N.TEAL};margin-top:4px">dossardpei.re</div></div></div></div>
</body></html>'''


def post_text(r, motif='', info=''):
    lines = [f"❌ Course annulée : {r['nom']}", f"📅 {N.when(r)} · 📍 {r['commune']}"]
    if motif:
        lines.append(motif)
    if info:
        lines.append(info)
    if source_txt(r):
        lines.append(f"ℹ️ {source_txt(r)}")
    lines.append('Toutes les autres courses 👉 dossardpei.re')
    lines.append('#trail #run #iledelareunion #reunionisland')
    return '\n'.join(lines)


DUR = 9.0


def html_video(r, motif='', info=''):
    """Vidéo 1080x1920 de 9 s : pastille « dossard barré » + étiquette rouge + nom sur l'île floutée (image de couverture à 1,2 s),
    l'étiquette monte, l'affiche arrive en couleur puis passe en gris quand le tampon ANNULÉE tombe, panneau d'infos, logo."""
    poster = poster_path(r)
    if poster and 'utoi-logo' in str(poster):
        poster = None
    img = (poster or art_path(r)).as_uri()
    src = source_txt(r)
    nm = r['nom']; fs = 96 if len(nm) <= 20 else (84 if len(nm) <= 30 else 70)
    E = N.esc; M = MAP(); F = N.F; p = lambda t: f'{t / DUR * 100:.2f}%'
    bg = PL.world(1000 / M['W'], M['W'] / 2, M['H'] / 2, N.W / 2, N.H / 2)
    top = 470 if len(nm) <= 30 else 520      # zone de sécurité 9:16 (safe.py) : affiche, infos et logo au-dessus de y = 1500
    extra = ''.join([
        f'<div style="font-size:34px;font-weight:600;margin-top:16px">{E(motif)}</div>' if motif else '',
        f'<div style="font-size:30px;font-weight:600;color:{N.MUTED};margin-top:12px">{E(src)}</div>' if src else '',
        f'<div style="display:inline-block;margin-top:20px;font-weight:700;font-size:32px;color:#fff;background:{RED};border-radius:16px;padding:10px 26px">{E(info)}</div>' if info else ''])
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:S;font-weight:800;src:url('{F}/SairaCondensed-800.woff2')}}
@font-face{{font-family:I;font-weight:400;src:url('{F}/inter-latin-400-normal.woff2')}}
@font-face{{font-family:I;font-weight:600;src:url('{F}/inter-latin-600-normal.woff2')}}
@font-face{{font-family:I;font-weight:700;src:url('{F}/inter-latin-700-normal.woff2')}}
*{{box-sizing:border-box;margin:0;padding:0}} html,body{{width:{N.W}px;height:{N.H}px;overflow:hidden;background:#083b5a}}
body{{font-family:I,sans-serif;color:{N.INK};position:relative}} .s{{font-family:S,sans-serif;font-weight:800}} .abs{{position:absolute}}
.world{{position:absolute;left:0;top:0;transform-origin:0 0}} .world img,.world svg{{position:absolute;left:0;top:0}}
.anim{{animation-duration:{DUR}s;animation-fill-mode:both;animation-timing-function:linear}}
#bg{{animation-name:bg}} @keyframes bg{{0%{{transform:scale(1.06)}} 100%{{transform:scale(1)}}}}
#tag{{position:absolute;left:0;right:0;top:0;display:flex;flex-direction:column;align-items:center;transform-origin:50% 0;animation-name:tag}}
#tag .t{{background:{picto.TAG['annule'][0]};color:{picto.TAG['annule'][1]};font-size:92px;letter-spacing:1px;padding:10px 44px 14px;border-radius:22px;box-shadow:0 18px 40px rgba(0,0,0,.35);line-height:1}}
#tag .n{{margin-top:22px;max-width:{safe.BTN_X - (N.W - safe.BTN_X)}px;background:{N.SURF};font-size:{fs}px;line-height:.98;text-align:center;padding:14px 40px 18px;border-radius:22px;box-shadow:0 18px 40px rgba(29,37,35,.3);animation-name:nm}}
@keyframes tag{{0%,{p(.25)}{{transform:translateY(700px) scale(.5);opacity:0}} {p(.25)}{{animation-timing-function:cubic-bezier(.3,1.6,.5,1)}}
  {p(.8)},{p(1.5)}{{transform:translateY(700px) scale(1);opacity:1}} {p(1.5)}{{animation-timing-function:cubic-bezier(.6,0,.2,1)}} {p(2.4)},100%{{transform:translateY({safe.Y0 + 10}px) scale(.66);opacity:1}}}}
@keyframes nm{{0%,{p(.55)}{{opacity:0;transform:translateY(30px)}} {p(.55)}{{animation-timing-function:cubic-bezier(.2,.9,.3,1)}} {p(1.0)},100%{{opacity:1;transform:none}}}}
{picto.badge_css(p)}
#po{{animation-name:po}} @keyframes po{{0%,{p(2.2)}{{opacity:0;transform:translateY(500px) rotate(6deg)}} {p(2.2)}{{animation-timing-function:cubic-bezier(.2,.9,.3,1)}} {p(2.9)},{p(3.3)}{{opacity:1;transform:none}}
  {p(3.36)}{{transform:translate(-12px,8px) rotate(-1.200deg)}} {p(3.42)}{{transform:translate(10px,-6px) rotate(1deg)}} {p(3.48)}{{transform:translate(-6px,4px)}} {p(3.56)},100%{{opacity:1;transform:none}}}}
#po img{{animation-name:gr}} @keyframes gr{{0%,{p(3.25)}{{filter:none}} {p(3.5)},100%{{filter:grayscale(1) contrast(.9) brightness(1.08)}}}}
#st{{animation-name:st}} @keyframes st{{0%,{p(3.0)}{{opacity:0;transform:rotate(-14deg) scale(3.4)}} {p(3.0)}{{animation-timing-function:cubic-bezier(.7,0,.9,.5)}} {p(3.3)}{{opacity:1;transform:rotate(-14deg) scale(.92)}} {p(3.42)},100%{{opacity:1;transform:rotate(-14deg) scale(1)}}}}
#inf{{animation-name:up}} @keyframes up{{0%,{p(4.0)}{{opacity:0;transform:translateY(160px);filter:blur(16px)}} {p(4.0)}{{animation-timing-function:cubic-bezier(.15,.85,.25,1)}} {p(4.6)},100%{{opacity:1;transform:none;filter:blur(0)}}}}
#lg{{animation-name:lg}} @keyframes lg{{0%,{p(4.8)}{{opacity:0;transform:scale(.4)}} {p(4.8)}{{animation-timing-function:cubic-bezier(.3,1.6,.5,1)}} {p(5.3)},100%{{opacity:1;transform:none}}}}
</style></head><body>
<div class="abs" style="inset:0;background:#083b5a;filter:saturate(.3)"><div id="bg" class="abs anim" style="inset:0;filter:blur(14px)">{bg}</div></div>
<div class="abs" style="inset:0;background:rgba(8,59,90,.35)"></div>
<div id="tag" class="anim">{picto.badge('annule')}<div class="s t">Course annulée</div><div class="s n anim">{E(nm)}</div></div>
<div class="abs" style="left:150px;right:150px;top:{top}px;height:{1000 - top}px;display:flex;align-items:center;justify-content:center">
  <div id="po" class="anim" style="position:relative;display:inline-block">
    <img class="anim" src="{img}" style="max-width:700px;max-height:{1000 - top}px;border-radius:22px;box-shadow:0 26px 54px rgba(4,20,30,.45);display:block">
    <div class="abs" style="inset:0;display:flex;align-items:center;justify-content:center">
      <div id="st" class="s anim" style="color:{RED};background:rgba(255,255,255,.9);border:10px solid {RED};border-radius:18px;padding:4px 34px;font-size:112px;letter-spacing:6px;line-height:1.05;box-shadow:0 14px 30px rgba(29,37,35,.3)">ANNULÉE</div></div></div></div>
<div class="abs" style="left:{safe.X0}px;right:{N.W - safe.X1}px;bottom:{N.H - safe.Y1}px;display:flex;flex-direction:column;align-items:center;gap:16px">
<div id="inf" class="anim" style="align-self:stretch;background:{N.SURF};border-radius:32px;box-shadow:0 24px 50px rgba(4,20,30,.35);padding:26px {40 + safe.X1 - safe.BTN_X}px 28px 40px;text-align:center">
  <div style="font-size:40px;font-weight:700">{E(N.when(r))} · {E(r['commune'])}</div>{extra}</div>
<div style="display:flex;justify-content:center">
  <div id="lg" class="anim" style="display:flex;align-items:center;gap:16px;background:#fff;border:5px solid {N.INK};border-radius:999px;padding:8px 32px 8px 12px;box-shadow:0 16px 30px rgba(4,20,30,.3)">
    <img src="{N.LOGO}" style="width:72px;display:block">
    <div><div class="s" style="font-size:40px;line-height:.95">Dossard Péi</div>
    <div style="font-weight:700;font-size:24px;color:{N.TEAL};margin-top:4px">dossardpei.re</div></div></div></div></div>
</body></html>"""


def render(rid, motif='', info=''):
    """Sortie : social/out/annule/<id>.mp4 (vidéo), <id>-couverture.jpg (image de couverture, 1,2 s) et <id>.jpg (image fixe, fin de la vidéo)."""
    import rec, sfx
    r = race(rid)
    if not r:
        print(f'{rid} : introuvable'); return
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / f'_{rid}.html'; f.write_text(html_video(r, motif, info)); tmp = OUT / f'_{rid}.mp4'
    rec.record(f, tmp, DUR, stills=[(1.2, OUT / f'{rid}-couverture.jpg'), (DUR - .1, OUT / f'{rid}.jpg')])
    ev = [(.25, 'pop', 520), (.5, 'pop', 420), (.6, 'pop', 700), (1.45, 'whoosh', 1.2), (2.2, 'whoosh', .7, .4), (3.28, 'thud'), (3.3, 'pop', 300, .2, .5), (4.05, 'pop', 480, .12, .35), (4.85, 'chime')]
    wav = OUT / f'_{rid}.wav'; sfx.track(ev, DUR, wav); sfx.mux(tmp, wav); wav.unlink()
    tmp.replace(OUT / f'{rid}.mp4'); f.unlink()
    print(f'=== {OUT / (rid + ".mp4")}\n{post_text(r, motif, info)}\n')


def a_annoncer():
    """Courses annulées à venir pas encore annoncées (absentes de state/annules.json)."""
    d = json.load(open(ROOT / 'data.json'))
    try:
        fait = json.load(open(ROOT / 'state' / 'annules.json'))
    except Exception:
        fait = {}
    today = D.datetime.now(D.timezone(D.timedelta(hours=4))).date().isoformat()
    for r in d['races']:
        if r.get('annule') and (r.get('fin') or r['date']) >= today and r['id'] not in fait:
            print(r['id'], r['date'], r['nom'])


if __name__ == '__main__':
    if sys.argv[1:2] == ['--a-annoncer']:
        a_annoncer(); sys.exit()
    a = sys.argv[1:] + ['', '']
    render(a[0], a[1], a[2])
