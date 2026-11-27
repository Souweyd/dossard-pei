"""Zone de sécurité commune aux vidéos 9:16 (stories Instagram / Facebook, reels, TikTok), validée le 27/11/2026.
TikTok remplit l'écran des téléphones allongés (les bords gauche et droit sont rognés) et son interface recouvre
le haut (onglets), le bas (pseudo, légende, son) et une bande à droite (j'aime, commentaires, partage) ;
Instagram a ses propres bandeaux en haut (profil) et en bas (« Envoyer un message »).
Le fond (carte, île floutée) peut occuper tout l'écran ; textes, cadres, points utiles et logo restent dans la zone.

Contrôle d'une page (HTML animé, comme rec.py) :
  python3 social/safe.py <page.html> <durée> [t1 t2 …]   → images <page>-safe-<t>.jpg avec les zones, et liste des débordements
"""
W, H = 1080, 1920
L, R, T, B = 90, 90, 220, 420          # marges : gauche, droite, haut, bas
BTN_X, BTN_Y = W - 150, 700            # boutons de TikTok : x > BTN_X, de BTN_Y jusqu'à la bande du bas
X0, X1, Y0, Y1 = L, W - R, T, H - B    # rectangle sûr : 90…990 × 220…1500

ZONES = [(0, 0, L, H), (W - R, 0, W, H), (0, 0, W, T), (0, H - B, W, H), (BTN_X, BTN_Y, W, H - B)]

JS = """(zones) => {
  const out = [], seen = new Set();
  const vis = el => { let o = 1; for (let e = el; e && e.nodeType === 1; e = e.parentElement) { const s = getComputedStyle(e);
      if (s.display === 'none' || s.visibility === 'hidden') return 0; o *= +s.opacity; } return o; };
  const els = [...document.body.querySelectorAll('*')].filter(e => !e.closest('#world') && !e.closest('#lens') &&
      ([...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()) || e.tagName === 'IMG'));
  for (const e of els) {
    let r = e.getBoundingClientRect(); if (e.tagName === 'IMG' && r.width > 900) continue;     // fond (carte, île)
    if (e.tagName !== 'IMG') {                     // emprise du texte lui-même, pas du bloc (souvent pleine largeur)
      const g = document.createRange(); let u = null;
      for (const n of e.childNodes) if (n.nodeType === 3 && n.textContent.trim()) { g.selectNodeContents(n); const q = g.getBoundingClientRect();
        u = u ? {left: Math.min(u.left, q.left), top: Math.min(u.top, q.top), right: Math.max(u.right, q.right), bottom: Math.max(u.bottom, q.bottom)} : q; }
      r = {left: u.left, top: u.top, right: u.right, bottom: u.bottom, width: u.right - u.left, height: u.bottom - u.top}; }
    if (r.width < 2 || r.height < 2 || vis(e) < .5) continue;
    if (r.right < 0 || r.left > 1080 || r.bottom < 0 || r.top > 1920) continue;
    for (const [x0, y0, x1, y1] of zones) {
      if (r.left < x1 - 2 && r.right > x0 + 2 && r.top < y1 - 2 && r.bottom > y0 + 2) {
        const k = (e.textContent || e.src || '').trim().slice(0, 40);
        if (!seen.has(k)) { seen.add(k); out.push(`${k}  [${Math.round(r.left)},${Math.round(r.top)} → ${Math.round(r.right)},${Math.round(r.bottom)}]`); }
        break; } } }
  return out; }"""


def overlay(src, dst):
    from PIL import Image, ImageDraw
    im = Image.open(src).convert('RGBA'); ov = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for z in ZONES:
        d.rectangle(z, fill=(230, 40, 40, 80))
    Image.alpha_composite(im, ov).convert('RGB').save(dst, quality=85)


async def _check(html, times):
    import pathlib
    from playwright.async_api import async_playwright
    from rec import SEEK
    html = pathlib.Path(html); res = {}
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width': W, 'height': H})
        await pg.goto(html.as_uri()); await pg.evaluate('document.fonts.ready')
        await pg.evaluate("Promise.all([...document.images].map(i=>i.complete?1:new Promise(r=>{i.onload=i.onerror=r})))")
        await pg.wait_for_timeout(300)
        for t in times:
            await pg.evaluate(SEEK, t); await pg.wait_for_timeout(80); await pg.evaluate(SEEK, t)
            png = html.with_name(f'{html.stem}-safe-{t:g}.png'); await pg.screenshot(path=str(png))
            overlay(png, png.with_suffix('.jpg')); png.unlink()
            res[t] = await pg.evaluate(JS, ZONES)
        await b.close()
    return res


def check(html, times):
    import asyncio
    return asyncio.run(_check(html, times))


if __name__ == '__main__':
    import sys
    dur = float(sys.argv[2]); ts = [float(x) for x in sys.argv[3:]] or [1.2, dur / 2, dur - .05]
    bad = 0
    for t, lst in check(sys.argv[1], ts).items():
        print(f't={t:g}s : ' + ('ok' if not lst else f'{len(lst)} débordement(s)'))
        for x in lst:
            print('   ', x)
        bad += len(lst)
    sys.exit(1 if bad else 0)
