"""Story / TikTok 1080x1920 « Nouveau dossard » (template validé le 26/10/2026) :
affiche au centre en haut, description en dessous, logo + dossardpei.re en bas.

Usage (depuis la racine du dépôt) : python3 social/nouveau.py <id> [<id> ...]
Sortie : social/out/nouveau/<id>.jpg ; affiche le texte du post pour chaque course.
Le style est figé ici (polices Saira Condensed + Instrument Sans, décor du site), indépendamment de core.css().
"""
import sys, asyncio, pathlib, html, datetime as D
from core import load, status, ROOT, SOC, JOURS_C, MOIS, TYPE_EMO, poster_path, art_path, fmt_km

OUT = SOC / 'out' / 'nouveau'
F = (SOC / 'fonts').as_uri()
LOGO = (SOC / 'assets' / 'logo-512.png').as_uri()
INK, NAVY, SUN, TEAL, ORANGE, RED, MUTED, CREAM = '#1d2523', '#1d4f9c', '#ffd400', '#0d6b67', '#d2481e', '#c62828', '#5b6763', '#f5efe6'
W, H = 1080, 1920
esc = lambda s: html.escape(str(s))


def scene(horizon=.5):
    y = H * horizon
    return f'''<svg style="position:absolute;left:0;top:0" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
      <defs><linearGradient id="sk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5fb0e6"/><stop offset="{horizon:.2f}" stop-color="#bfe0f3"/></linearGradient>
      <linearGradient id="fd" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{CREAM}" stop-opacity="0"/><stop offset="1" stop-color="{CREAM}"/></linearGradient></defs>
      <rect width="{W}" height="{H}" fill="url(#sk)"/>
      <ellipse cx="{W * .72:.0f}" cy="{H * .12:.0f}" rx="{W * .26:.0f}" ry="{H * .045:.0f}" fill="#fff" opacity=".35"/>
      <path d="M0 {y - H * .10:.0f} L{W * .22:.0f} {y - H * .17:.0f} L{W * .45:.0f} {y - H * .09:.0f} L{W * .7:.0f} {y - H * .2:.0f} L{W} {y - H * .12:.0f} L{W} {H} L0 {H}Z" fill="#a9c2d3"/>
      <path d="M0 {y - H * .02:.0f} L{W * .3:.0f} {y - H * .1:.0f} L{W * .62:.0f} {y - H * .03:.0f} L{W} {y - H * .08:.0f} L{W} {H} L0 {H}Z" fill="#8eaabb"/>
      <path d="M0 {y + H * .05:.0f} Q{W * .35:.0f} {y - H * .02:.0f} {W * .7:.0f} {y + H * .03:.0f} T{W} {y + H * .02:.0f} L{W} {H} L0 {H}Z" fill="#9dbf93"/>
      <rect y="{y:.0f}" width="{W}" height="{H - y:.0f}" fill="url(#fd)"/></svg>'''


def when(r):
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


def badge(r):
    code, lab = status(r, D.date.today())
    if r.get('avenir') or code == 'bientot':
        return 'Inscriptions à venir', TEAL
    if code == 'complet':
        return 'Complet', RED
    if code == 'clot':
        return lab, ORANGE
    return None, None


def html_story(r):
    poster = poster_path(r)
    if poster and 'utoi-logo' in str(poster):
        poster = None
    img = (poster or art_path(r)).as_uri()
    b, bc = badge(r)
    nm = r['nom']; fs = 76 if len(nm) <= 22 else (64 if len(nm) <= 32 else 54)
    dist = distances(r)
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:S;font-weight:800;src:url('{F}/SairaCondensed-800.woff2')}}
@font-face{{font-family:S;font-weight:700;src:url('{F}/SairaCondensed-700.woff2')}}
@font-face{{font-family:I;font-weight:400 700;src:url('{F}/InstrumentSans.woff2')}}
*{{box-sizing:border-box;margin:0;padding:0}} html,body{{width:{W}px;height:{H}px;overflow:hidden}}
body{{font-family:I,sans-serif;color:{INK};position:relative;background:{CREAM}}} .s{{font-family:S,sans-serif}}
</style></head><body>{scene()}
<div style="position:absolute;left:0;right:0;top:200px;display:flex;justify-content:center">
  <div class="s" style="background:{NAVY};color:#fff;font-weight:800;font-size:46px;letter-spacing:1px;padding:8px 30px;border-radius:14px;border:5px solid {INK};border-bottom:8px solid {SUN};transform:rotate(-2deg);box-shadow:0 12px 24px rgba(29,37,35,.25)">Nouveau dossard</div></div>
<div style="position:absolute;left:150px;right:150px;top:340px;height:930px;display:flex;align-items:center;justify-content:center">
  <img src="{img}" style="max-width:780px;max-height:930px;border-radius:26px;border:8px solid #fff;box-shadow:0 30px 60px rgba(29,37,35,.35);display:block"></div>
<div style="position:absolute;left:64px;right:64px;top:1300px;text-align:center">
  <div class="s" style="font-weight:800;font-size:{fs}px;line-height:.95">{esc(nm)}</div>
  <div style="font-size:38px;font-weight:600;margin-top:14px">{esc(when(r))} · {esc(r['commune'])}</div>
  {f'<div style="font-size:34px;font-weight:600;color:{INK};margin-top:8px">{esc(dist)}</div>' if dist else ''}
  {f'<div style="display:inline-block;margin-top:16px;font-weight:700;font-size:30px;color:#fff;background:{bc};border-radius:999px;padding:6px 22px">{esc(b)}</div>' if b else ''}</div>
<div style="position:absolute;left:0;right:0;top:1580px;display:flex;justify-content:center">
  <div style="display:flex;align-items:center;gap:22px;background:#fff;border:6px solid {INK};border-radius:999px;padding:14px 40px 14px 18px;box-shadow:0 16px 30px rgba(29,37,35,.22)">
    <img src="{LOGO}" style="width:110px;display:block">
    <div><div class="s" style="font-weight:800;font-size:54px;line-height:.95">Dossard Péi</div>
    <div style="font-weight:700;font-size:30px;color:{TEAL};margin-top:4px">dossardpei.re</div></div></div></div>
</body></html>'''


def post_text(r):
    emo = TYPE_EMO.get(r['_type'], '🏅')
    b, _ = badge(r)
    lines = [f"{emo} Nouveau dossard : {r['nom']}", f"📅 {when(r)} · 📍 {r['commune']}"]
    if b == 'Complet':
        lines.append('Complet')
    elif distances(r):
        lines.append(distances(r))
    lines.append('Parcours, infos et inscription 👉 dossardpei.re')
    return '\n'.join(lines)


async def render(ids):
    from playwright.async_api import async_playwright
    from PIL import Image
    data, races = load()
    byid = {r['id']: r for r in races}
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': W, 'height': H})
        for rid in ids:
            r = byid.get(rid)
            if not r:
                print(f'{rid} : introuvable ou masquée'); continue
            f = OUT / f'_{rid}.html'; f.write_text(html_story(r))
            await pg.goto(f.as_uri()); await pg.evaluate('document.fonts.ready'); await pg.wait_for_timeout(300)
            png = OUT / f'{rid}.png'; await pg.screenshot(path=str(png))
            Image.open(png).convert('RGB').save(OUT / f'{rid}.jpg', quality=92); png.unlink(); f.unlink()
            print(f'=== {OUT / (rid + ".jpg")}\n{post_text(r)}\n')
        await b.close()


if __name__ == '__main__':
    asyncio.run(render(sys.argv[1:]))
