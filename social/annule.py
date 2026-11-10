"""Story 1080x1920 « Course annulée » : même gabarit que « Nouveau dossard » (ciel bleu, étiquette
bleu marine soulignée de jaune, pastille logo), affiche passée en gris avec un tampon ANNULÉE.

Usage (depuis la racine du dépôt) :
  python3 social/annule.py --a-annoncer   → courses annulées à venir absentes de state/annules.json
  python3 social/annule.py <id> ["motif court"] ["info pratique"]
La course peut être masquée (annule/hidden) : on la lit directement dans data.json.
Sortie : social/out/annule/<id>.jpg ; affiche le texte du post.
"""
import sys, asyncio, json, datetime as D
from core import ROOT, SOC, poster_path, art_path
import nouveau as N

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
    img = (poster or art_path(r)).as_uri()
    src = source_txt(r)
    nm = r['nom']; fs = 80 if len(nm) <= 22 else (66 if len(nm) <= 32 else 56)
    E = N.esc
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:S;font-weight:800;src:url('{N.F}/SairaCondensed-800.woff2')}}
@font-face{{font-family:S;font-weight:700;src:url('{N.F}/SairaCondensed-700.woff2')}}
@font-face{{font-family:I;font-weight:400 700;src:url('{N.F}/InstrumentSans.woff2')}}
*{{box-sizing:border-box;margin:0;padding:0}} html,body{{width:{N.W}px;height:{N.H}px;overflow:hidden}}
body{{font-family:I,sans-serif;color:{N.INK};position:relative;background:{N.CREAM}}} .s{{font-family:S,sans-serif}}
</style></head><body>{N.scene()}
<div style="position:absolute;left:0;right:0;top:200px;display:flex;justify-content:center">
  <div class="s" style="background:{N.NAVY};color:#fff;font-weight:800;font-size:46px;letter-spacing:1px;padding:8px 30px;border-radius:14px;border:5px solid {N.INK};border-bottom:8px solid {N.SUN};transform:rotate(-2deg);box-shadow:0 12px 24px rgba(29,37,35,.25)">Course annulée</div></div>
<div style="position:absolute;left:150px;right:150px;top:340px;height:860px;display:flex;align-items:center;justify-content:center">
  <div style="position:relative;display:inline-block">
    <img src="{img}" style="max-width:780px;max-height:860px;border-radius:26px;border:8px solid #fff;box-shadow:0 30px 60px rgba(29,37,35,.35);display:block;filter:grayscale(1) contrast(.9) brightness(1.08)">
    <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center">
      <div class="s" style="transform:rotate(-14deg);color:{RED};background:rgba(255,255,255,.88);border:10px solid {RED};border-radius:18px;padding:4px 34px;font-weight:800;font-size:118px;letter-spacing:6px;line-height:1.05;box-shadow:0 14px 30px rgba(29,37,35,.3)">ANNULÉE</div></div></div></div>
<div style="position:absolute;left:64px;right:64px;top:1236px;text-align:center">
  <div class="s" style="font-weight:800;font-size:{fs}px;line-height:.95">{E(nm)}</div>
  <div style="font-size:40px;font-weight:600;margin-top:14px">{E(N.when(r))} · {E(r['commune'])}</div>
  {f'<div style="font-size:38px;font-weight:600;margin-top:12px">{E(motif)}</div>' if motif else ''}
  {f'<div style="font-size:34px;font-weight:600;margin-top:10px">{E(src)}</div>' if src else ''}
  {f'<div style="display:inline-block;margin-top:18px;font-weight:700;font-size:34px;color:#fff;background:{RED};border-radius:999px;padding:8px 28px">{E(info)}</div>' if info else ''}</div>
<div style="position:absolute;left:0;right:0;top:1620px;display:flex;justify-content:center">
  <div style="display:flex;align-items:center;gap:22px;background:#fff;border:6px solid {N.INK};border-radius:999px;padding:14px 40px 14px 18px;box-shadow:0 16px 30px rgba(29,37,35,.22)">
    <img src="{N.LOGO}" style="width:110px;display:block">
    <div><div class="s" style="font-weight:800;font-size:54px;line-height:.95">Dossard Péi</div>
    <div style="font-weight:700;font-size:30px;color:{N.TEAL};margin-top:4px">dossardpei.re</div></div></div></div>
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
    return '\n'.join(lines)


async def render(rid, motif='', info=''):
    from playwright.async_api import async_playwright
    from PIL import Image
    r = race(rid)
    if not r:
        print(f'{rid} : introuvable'); return
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': N.W, 'height': N.H})
        f = OUT / f'_{rid}.html'; f.write_text(html_story(r, motif, info))
        await pg.goto(f.as_uri()); await pg.evaluate('document.fonts.ready'); await pg.wait_for_timeout(300)
        png = OUT / f'{rid}.png'; await pg.screenshot(path=str(png))
        Image.open(png).convert('RGB').save(OUT / f'{rid}.jpg', quality=92); png.unlink(); f.unlink()
        await b.close()
    print(f'=== {OUT / (rid + ".jpg")}\n{post_text(r, motif, info)}\n')


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
    asyncio.run(render(a[0], a[1], a[2]))
