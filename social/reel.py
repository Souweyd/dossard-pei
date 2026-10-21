"""Friday reel: the course of one race drawn on the relief map, with its profile (9:16 MP4, Reels + TikTok)."""
import asyncio, subprocess, json, math, datetime as D, pathlib
from core import *
from core import _norm

FPS, DUR = 30, 15.0


def pick(ref, data, races):
    def cands(a, b):
        out = []
        for r in upcoming(races, ref + D.timedelta(days=a), ref + D.timedelta(days=b)):
            if status(r, ref)[0] in ('complet', 'clos'):
                continue
            tr = [t for t in gpx_tracks(data, r['id']) if len(t['pts']) > 20]
            if tr:
                out.append((r, max(tr, key=lambda t: t.get('km') or len(t['pts']))))
        return out
    c = cands(12, 30) or cands(8, 45) or cands(5, 90)
    if not c:
        return None
    return c[week_index(ref) % len(c)]


def stitch(pts, outfile, aspect=1080 / 1920):
    """Background image around the track from the site's relief tiles. Returns (file, x0, y0, scale) in map units."""
    from PIL import Image
    M = MAP()
    xy = [P_xy(p[0], p[1]) for p in pts]
    xs, ys = [p[0] for p in xy], [p[1] for p in xy]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    tw_, th_ = max(xs) - min(xs) + 1e-6, max(ys) - min(ys) + 1e-6
    # the track must fit a 900 x 600 px box centred at (540, 790) of the 1080 x 1920 frame
    k = min(900 / tw_, 600 / th_, 1080 / 12)          # px per map unit (cap the zoom for tiny courses)
    w = 1080 / k; H_full = 1920 / k
    x0, y0 = cx - 540 / k, cy - 790 / k
    L, n = 3, 8
    tw, th = M['W'] / n, M['H'] / n
    pxu = n * 1100 / M['W']                      # tile pixels per map unit at level 3
    Wpx, Hpx = int(w * pxu), int(H_full * pxu)
    img = Image.new('RGB', (max(Wpx, 1), max(Hpx, 1)), (207, 225, 228))
    for i in range(max(0, int(y0 // th)), min(n - 1, int((y0 + H_full) // th)) + 1):
        for j in range(max(0, int(x0 // tw)), min(n - 1, int((x0 + w) // tw)) + 1):
            f = ROOT / 'tiles' / f't{L}_{i}_{j}.webp'
            if not f.exists():
                continue
            t = Image.open(f).convert('RGBA')
            img.paste(t, (int((j * tw - x0) * pxu), int((i * th - y0) * pxu)), t)
    img.save(outfile, quality=92)
    return outfile, x0, y0, w, H_full


def figures(r, tr, dist):
    """Official distance / D+ of the matching épreuve when the track is that épreuve, else the track's own."""
    tkm = tr.get('km') or round(dist[-1], 1)
    best = None
    for e in r.get('epreuves', []):
        if e.get('km') and abs(e['km'] - tkm) / e['km'] < .15:
            if best is None or abs(e['km'] - tkm) < abs(best['km'] - tkm):
                best = e
    if best:
        return best['km'], best.get('dp') or tr.get('dp')
    return tkm, tr.get('dp')


def profile(pts):
    dist = [0.0]
    for a, b in zip(pts, pts[1:]):
        dy = (b[0] - a[0]) * 111.2; dx = (b[1] - a[1]) * 111.2 * math.cos(math.radians(a[0]))
        dist.append(dist[-1] + math.hypot(dx, dy))
    return dist, [p[2] for p in pts]


def html_reel(r, tr, bg, ref):
    file, x0, y0, w, H_full = bg
    pts = tr['pts']
    sc = 1080 / w
    xy = [((P_xy(p[0], p[1])[0] - x0) * sc, (P_xy(p[0], p[1])[1] - y0) * sc) for p in pts]
    path = 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in xy)
    dist, ele = profile(pts)
    km, dp = figures(r, tr, dist)
    emin, emax = min(ele), max(ele)
    PW, PH = 840, 230
    prof = ' L'.join(f'{d_ / dist[-1] * PW:.1f},{PH - (e - emin) / max(1, emax - emin) * (PH - 20):.1f}' for d_, e in zip(dist, ele))
    code, lab = status(r, ref)
    dt = r['_d']
    col = TYPE_COL.get(r['_type'], C['accent'])
    st = lab if code in ('clot', 'ouvert') and lab else ''
    nm = r['nom']; ns = 96 if len(nm) < 20 else (80 if len(nm) < 30 else 64)
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>{css()}html,body{{height:1920px}}
#bg{{position:absolute;left:0;top:0;width:1080px;height:{H_full * sc:.0f}px;transform-origin:540px 600px}}
#bg img{{width:100%;height:100%;display:block}}
.shade{{position:absolute;left:0;right:0}}
</style></head><body style="background:#0f1f1d">
<div id="bg"><img src="{pathlib.Path(file).as_uri()}">
 <svg width="1080" height="{H_full * sc:.0f}" style="position:absolute;left:0;top:0">
  <path id="halo" d="{path}" fill="none" stroke="#fff" stroke-width="16" stroke-linejoin="round" stroke-linecap="round" opacity=".85"/>
  <path id="trk" d="{path}" fill="none" stroke="{C['hot']}" stroke-width="9" stroke-linejoin="round" stroke-linecap="round"/>
  <circle cx="{xy[0][0]:.1f}" cy="{xy[0][1]:.1f}" r="15" fill="#1b8a3a" stroke="#fff" stroke-width="5"/>
  <circle id="dot" r="17" fill="#fff" stroke="{C['hot']}" stroke-width="7"/>
 </svg></div>
<div class="shade" style="top:0;height:520px;background:linear-gradient(180deg,rgba(15,31,29,.85),rgba(15,31,29,0))"></div>
<div class="shade" style="bottom:0;height:900px;background:linear-gradient(0deg,rgba(15,31,29,.96) 45%,rgba(15,31,29,0))"></div>
<div id="title" style="position:absolute;left:64px;right:64px;top:170px;color:#fff">
  <div class="saira" style="font-weight:800;font-size:52px;color:#ff9a72">{JOURS[dt.weekday()].upper()} {dt.day} {MOIS[dt.month - 1].upper()}</div>
  <div class="saira" style="font-weight:800;font-size:{ns}px;line-height:.92;margin-top:6px;text-shadow:0 4px 18px rgba(0,0,0,.4)">{esc(nm)}</div>
  <div style="font-size:36px;font-weight:600;margin-top:12px;opacity:.9">📍 {esc(r['commune'])} · <span class="chip" style="background:{col};font-size:28px">{TYPE_LAB.get(r['_type'], 'Course')}</span></div></div>
<div id="panel" style="position:absolute;left:64px;right:170px;top:1180px;color:#fff">
  <div style="display:flex;gap:44px;align-items:flex-end">
    <div><div class="saira" style="font-weight:800;font-size:110px;line-height:.9"><span id="km">0</span><span style="font-size:52px"> km</span></div><div style="font-size:26px;opacity:.75;font-weight:600">DISTANCE</div></div>
    {f'<div><div class="saira" style="font-weight:800;font-size:110px;line-height:.9"><span id="dp">0</span><span style="font-size:52px"> m</span></div><div style="font-size:26px;opacity:.75;font-weight:600">DÉNIVELÉ +</div></div>' if dp else ''}</div>
  <svg width="{PW}" height="{PH + 10}" style="margin-top:26px;overflow:visible">
    <clipPath id="pc"><rect id="pcr" x="0" y="-10" width="0" height="{PH + 30}"/></clipPath>
    <g clip-path="url(#pc)"><path d="M0,{PH} L{prof} L{PW},{PH} Z" fill="{C['hot']}" opacity=".35"/><path d="M{prof}" fill="none" stroke="#ff9a72" stroke-width="5"/></g>
    <line x1="0" y1="{PH}" x2="{PW}" y2="{PH}" stroke="#fff" stroke-opacity=".35" stroke-width="2"/>
    <text x="0" y="{PH + 36}" fill="#fff" fill-opacity=".7" font-size="24" font-family="Inst">{int(emin)} m</text>
    <text x="{PW}" y="{PH + 36}" fill="#fff" fill-opacity=".7" font-size="24" font-family="Inst" text-anchor="end">alt. max {int(emax)} m</text></svg></div>
<div id="end" style="position:absolute;inset:0;background:rgba(15,31,29,.92);color:#fff;opacity:0">
  <div style="position:absolute;left:64px;right:64px;top:330px;text-align:center">
    <div style="font-size:150px;line-height:1">⌚</div>
    <div class="saira" style="font-weight:800;font-size:104px;line-height:.92;margin-top:30px">LE TRACÉ GPX<br><span style="color:{C['mint']}">POUR TA MONTRE</span></div>
    <div style="font-size:40px;font-weight:500;color:#cfe1e4;margin-top:34px;line-height:1.3">Parcours, profil, infos<br>et inscription sur le site</div>
    <div class="saira" style="display:inline-block;font-weight:800;font-size:84px;color:{C['accent']};background:#f8faf7;border-radius:26px;padding:16px 44px;margin-top:56px">dossardpei.re</div>
    {f'<div style="font-size:38px;font-weight:700;color:#ff9a72;margin-top:40px">⏳ {esc(st)}</div>' if st else ''}
  </div></div>
<script>
const T=document.getElementById('trk'),Hh=document.getElementById('halo'),dot=document.getElementById('dot');
const L=T.getTotalLength();[T,Hh].forEach(p=>{{p.style.strokeDasharray=L;}});
const cl=(x,a=0,b=1)=>Math.max(a,Math.min(b,x)),pr=(t,a,b)=>cl((t-a)/(b-a)),ease=x=>x<.5?2*x*x:1-Math.pow(-2*x+2,2)/2;
const KM={km},DP={dp or 0};
window.render=(t)=>{{
  const z=1.12-0.12*ease(pr(t,0,2.2));document.getElementById('bg').style.transform='scale('+z+')';
  document.getElementById('title').style.opacity=pr(t,.2,.9);document.getElementById('title').style.transform='translateY('+(30*(1-ease(pr(t,.2,.9))))+'px)';
  const k=ease(pr(t,1.2,8.2));[T,Hh].forEach(p=>p.style.strokeDashoffset=L*(1-k));
  const q=T.getPointAtLength(L*k);dot.setAttribute('cx',q.x);dot.setAttribute('cy',q.y);dot.style.opacity=(k>0&&k<1)?1:0;
  const pp=ease(pr(t,6.5,10.5));document.getElementById('pcr').setAttribute('width',{PW}*pp);
  document.getElementById('panel').style.opacity=pr(t,6.2,7);document.getElementById('panel').style.transform='translateY('+(40*(1-ease(pr(t,6.2,7.2))))+'px)';
  document.getElementById('km').textContent=(KM*pp).toFixed(Number.isInteger(KM)?0:1).replace('.',',');
  const e=document.getElementById('dp');if(e)e.textContent=Math.round(DP*pp).toLocaleString('fr-FR');
  document.getElementById('end').style.opacity=pr(t,11.4,12.1);
}};
</script></body></html>'''


async def _frames(htmlfile, mp4):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 1080, 'height': 1920})
        await pg.goto(pathlib.Path(htmlfile).as_uri()); await pg.evaluate('document.fonts.ready'); await pg.wait_for_timeout(500)
        ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', str(FPS), '-i', '-',
                               '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '19', '-preset', 'medium', '-movflags', '+faststart', str(mp4)],
                              stdin=subprocess.PIPE)
        for i in range(int(DUR * FPS)):
            await pg.evaluate(f'render({i / FPS})')
            ff.stdin.write(await pg.screenshot(type='jpeg', quality=90))
        ff.stdin.close(); ff.wait()
        await pg.evaluate('render(9.5)'); await pg.screenshot(path=str(pathlib.Path(mp4).with_suffix('.jpg')), type='jpeg', quality=90)
        await b.close()


def build(ref, data, races, outdir):
    c = pick(ref, data, races)
    if not c:
        return None
    r, tr = c
    tmp = outdir / '_tmp'; tmp.mkdir(exist_ok=True)
    bg = stitch(tr['pts'], tmp / 'bg.jpg')
    h = tmp / 'reel.html'; h.write_text(html_reel(r, tr, bg, ref))
    mp4 = outdir / f'{outdir.name}-reel-{r["id"]}.mp4'
    asyncio.run(_frames(h, mp4))
    dist, ele = profile(tr['pts'])
    km, dp = figures(r, tr, dist)
    code, lab = status(r, ref)
    lines = [f"🗺️ Le parcours de {r['nom']}", f"📅 {fdate(r['_d']).capitalize()} · 📍 {r['commune']}",
             f"📏 {fmt_km(km)} km" + (f" · ⛰️ {dp} m D+" if dp else '')]
    if code == 'clot' or (code == 'ouvert' and lab):
        lines.append(f"⏳ {lab}")
    lines += ['', 'Tracé, profil et GPX à charger dans ta montre 👉 dossardpei.re (lien en bio)', '', 'Tu la cours ? Dis-le en commentaire 👇']
    tags = ['#trailreunion', '#run974', '#lareunion', '#974', '#' + _norm(r['commune']).replace(' ', '')]
    return mp4, lines, tags
