"""Story « Météo des courses » du week-end (1080×1920), vidéo animée + image fixe, à partir de weather.json.
Usage (depuis la racine du dépôt) : python3 social/meteo.py <date du vendredi>   ex. python3 social/meteo.py 2026-10-30
Sortie : social/out/meteo/story-meteo-<vendredi>.mp4 et .jpg ; « rien » s'il n'y a pas de course avec météo samedi / dimanche.
Charte : décor du site (ciel bleu), étiquette bleu marine des stories, bloc météo identique au site (couleur selon le temps)."""
import sys, json, pathlib, datetime as D
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from core import C, ROOT, JOURS, MOIS, LOGO, load, esc, css, scene
from rec import record

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / 'out' / 'meteo'
W, H, T, B, R = 1080, 1920, 250, 320, 170
EASE = 'cubic-bezier(.2,.8,.2,1)'
BACK = 'cubic-bezier(.34,1.56,.64,1)'

WXT = {'clearsky': 'Ensoleillé', 'fair': 'Plutôt beau', 'partlycloudy': 'Éclaircies', 'cloudy': 'Nuageux', 'fog': 'Brouillard',
       'lightrain': 'Faible pluie', 'rain': 'Pluie', 'heavyrain': 'Fortes pluies', 'lightrainshowers': 'Quelques averses',
       'rainshowers': 'Averses', 'heavyrainshowers': 'Fortes averses'}
# line icons of the site (same drawings as the weather block of a race page)
SUN = '<circle cx="12" cy="12" r="4.2"/><g class="rays"><path d="M12 2.5v2.2M12 19.3v2.2M2.5 12h2.2M19.3 12h2.2M5.3 5.3l1.6 1.6M17.1 17.1l1.6 1.6M5.3 18.7l1.6-1.6M17.1 6.9l1.6-1.6"/></g>'
CLOUD = '<path d="M7 18.5h10.2a3.8 3.8 0 0 0 .4-7.6 5.6 5.6 0 0 0-10.9 1.2A3.2 3.2 0 0 0 7 18.5Z"/>'
PART = '<g class="rays"><path d="M8.5 4.2v1.6M3.6 9.1h1.6M5 5.6l1.1 1.1M12 5.6l-1.1 1.1"/></g><path d="M5.9 11.6a3.2 3.2 0 0 1 5.6-3"/><g class="drift"><path d="M9 19.5h8.6a3.4 3.4 0 0 0 .3-6.8 5 5 0 0 0-9.7 1.1A2.9 2.9 0 0 0 9 19.5Z"/></g>'
RAIN = '<path d="M7 15h10.2a3.6 3.6 0 0 0 .4-7.2 5.4 5.4 0 0 0-10.5 1.1A3 3 0 0 0 7 15Z"/><g class="drops"><path d="M8.5 18l-1 2.5M12.5 18l-1 2.5M16.5 18l-1 2.5"/></g>'
STORM = '<path d="M7 14.5h10.2a3.6 3.6 0 0 0 .4-7.2 5.4 5.4 0 0 0-10.5 1.1A3 3 0 0 0 7 14.5Z"/><g class="flash"><path d="m12.5 15.5-2 3.5h3l-2 3.5"/></g>'
ICON = dict(sun=(SUN, '#fff4d6', '#e39a00'), part=(PART, '#fff1d9', '#d98a00'), cloud=(CLOUD, '#eef1f4', '#6b7a88'),
            fog=(CLOUD, '#eef1f4', '#6b7a88'), rain=(RAIN, '#e3f0fb', '#2b7bc0'), storm=(STORM, '#ece8f7', '#5b4bb0'))
TEMP = '<path d="M10 14.5V5a2 2 0 0 1 4 0v9.5a4 4 0 1 1-4 0Z"/><path d="M12 9v7.5"/>'
SMALL = {'drop': '<path d="M12 3.5s-5.5 6.2-5.5 10a5.5 5.5 0 0 0 11 0c0-3.8-5.5-10-5.5-10Z"/>',
         'wind': '<path d="M3 9h11a2.5 2.5 0 1 0-2.5-2.5M3 13h15a2.5 2.5 0 1 1-2.5 2.5M3 17h7"/>',
         'peak': '<path d="m3 19 6.5-11 3.5 6 2-3.2L21 19Z"/><path d="m8 10.4 1.5 1.3 1.5-1.3"/>',
         'wet': '<path d="M4 18c2 0 2-1.5 4-1.5s2 1.5 4 1.5 2-1.5 4-1.5 2 1.5 4 1.5"/><path d="M12 4s-3 3.4-3 5.5a3 3 0 0 0 6 0C15 7.4 12 4 12 4Z"/>'}


def kind(s):
    s = s or ''
    if 'thunder' in s: return 'storm'
    if any(k in s for k in ('rain', 'sleet', 'snow')): return 'rain'
    if s == 'fog': return 'fog'
    if s == 'cloudy': return 'cloud'
    if s in ('partlycloudy', 'fair'): return 'part'
    return 'sun'


def svg(p, s, col, sw=1.8): return f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{col}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round" style="overflow:visible">{p}</svg>'


def mm(x): return '0 mm' if x < 1 else (f'{round(x)} mm' if x >= 10 else f'{x:.1f} mm'.replace('.', ','))


def build(friday):
    wx = json.loads((ROOT / 'weather.json').read_text())
    data, races = load()
    byid = {r['id']: r for r in races}
    days = [friday + D.timedelta(days=1), friday + D.timedelta(days=2)]
    items = []
    for rid, lst in wx['races'].items():
        r = byid.get(rid)
        for x in lst:
            if r and D.date.fromisoformat(x['date']) in days:
                items.append((x['date'], x.get('h') or '99', r, x))
    items.sort(key=lambda t: (t[0], t[1]))
    if not items:
        return None, 0, [], 0
    more = max(0, len(items) - 5)
    items = items[:5]                       # 5 blocks at most, readable on a phone
    sure = all(x['j'] < 3 for *_, x in items)
    dset = sorted({D.date.fromisoformat(i[0]) for i in items})
    when = ' et '.join(f"{JOURS[d.weekday()]} {d.day}" for d in dset) + f" {MOIS[dset[-1].month - 1]}"
    n = len(items)
    Z = max(1.1, min(1.75, 1000 / (n * 222 + (n - 1) * 14)))      # zoom of the site block (site css px -> story px)
    cards = []
    for k, (ds, h, r, x) in enumerate(items):
        dly = 1.0 + k * .35
        kd = kind(x['start']['sym'])
        path, bg, col = ICON[kd]
        w = x['window']
        rain = mm(w['rain'])
        tile = lambda ic, val, lab: f'<div class="wxc">{svg(SMALL[ic] if ic in SMALL else TEMP, 18, "rgba(255,255,255,.85)", 1.7)}<b>{val}</b><span>{lab}</span></div>'
        tiles = [tile('temp', f"{w['tmin']}°" if w['tmin'] == w['tmax'] else f"{w['tmin']}–{w['tmax']}°",
                      f"Pendant la course (≈ {round(w['hours'])} h)" if w.get('hours', 0) >= 1.5 else 'Pendant la course'),
                 tile('drop', rain, 'Pluie prévue'), tile('wind', f"{w['w']} km/h", 'Vent max')]
        if x.get('top'):
            tiles.append(tile('peak', f"{x['top']['t']}°", f"Au sommet ({x['top']['alt']:,} m)".replace(',', ' ')))
        alert = (f'<p class="wxv">{svg(SMALL["wet"], 18, "#fff", 1.7)}Pluie la veille (≈ {x["veille"]} mm) : terrain probablement glissant</p>') if x.get('veille') else ''
        hh = (x.get('h') or '').replace('h00', 'h').lstrip('0')
        dd = D.date.fromisoformat(ds)
        txt = WXT.get(x['start']['sym'].replace('andthunder', ''), 'Orages' if kd == 'storm' else '')
        tag = 'Prévision' if x['j'] < 3 else 'Tendance'
        cards.append(f'''
      <div style="animation:slide .6s {EASE} {dly:.2f}s both">
        <section class="wx k-{kd}"><div class="wxh"><h4 class="rname">{esc(r['nom'])}</h4><span class="wxtag{' sure' if tag == 'Prévision' else ''}">{tag}</span></div>
          <div class="wxtop"><span class="wxbig ic ic-{kd}">{svg(path, 34, "#fff", 1.6)}</span>
            <div><b class="wxt" style="animation:pop .5s {BACK} {dly + .35:.2f}s both">{x['start']['t']}°</b><span class="wxs">{txt}{' · départ ' + hh if hh else ''} · {esc(r['commune'])}</span></div></div>
          <div class="wxg">{''.join(tiles)}</div>{alert}</section>
      </div>''')
    total = 1.0 + n * .35 + 7.5
    style = f'''{css()}
    html,body{{height:{H}px}}
    @keyframes up{{from{{opacity:0;transform:translateY(50px)}}to{{opacity:1;transform:none}}}}
    @keyframes slide{{from{{opacity:0;transform:translateX(140px)}}to{{opacity:1;transform:none}}}}
    @keyframes pop{{from{{opacity:0;transform:scale(.3)}}to{{opacity:1;transform:scale(1)}}}}
    @keyframes spin{{to{{transform:rotate(90deg)}}}}
    @keyframes fall{{0%{{transform:translateY(-3px);opacity:0}}30%{{opacity:1}}100%{{transform:translateY(4px);opacity:0}}}}
    @keyframes drift{{from{{transform:translateX(-1.2px)}}to{{transform:translateX(1.2px)}}}}
    @keyframes flash{{0%,60%,100%{{opacity:1}}70%,90%{{opacity:.15}}}}
    .cards{{zoom:{Z:.3f}}}
    .wxh h4.rname{{font-family:Saira;font-weight:800;font-size:1.15rem;letter-spacing:-.02em;line-height:1.1;color:#fff;text-transform:none}}
    .rsub{{font-size:14px;color:#6e6e73;font-weight:500;margin:2px 0 8px}}
    .wx{{--g1:#4aa3e8;--g2:#1f6fb8;border-radius:18px;padding:16px;color:#fff;background:linear-gradient(145deg,var(--g1),var(--g2));box-shadow:0 8px 24px color-mix(in srgb,var(--g2) 35%,transparent)}}
    .wx.k-sun{{--g1:#f6b73c;--g2:#e3762a}} .wx.k-part{{--g1:#5fb3ec;--g2:#2f7fc9}} .wx.k-cloud,.wx.k-fog{{--g1:#8597a8;--g2:#536576}}
    .wx.k-rain{{--g1:#4f86b8;--g2:#2a4f7a}} .wx.k-storm{{--g1:#5b5891;--g2:#2e2b57}}
    .wxh{{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:12px}}
    .wxh h4{{margin:0;font-size:.78rem;text-transform:uppercase;letter-spacing:.08em;color:rgba(255,255,255,.85);font-weight:700}}
    .wxtag{{font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;padding:3px 9px;border-radius:99px;background:rgba(255,255,255,.2);color:#fff}}
    .wxtag.sure{{background:#fff;color:var(--g2)}}
    .wxtop{{display:flex;align-items:center;gap:14px}}
    .wxbig{{width:56px;height:56px;border-radius:16px;display:grid;place-items:center;background:rgba(255,255,255,.22);color:#fff;flex:none}}
    .wxt{{display:block;font-size:2.3rem;line-height:1;letter-spacing:-.03em;font-weight:800}}
    .wxs{{display:block;margin-top:4px;color:rgba(255,255,255,.88);font-size:.9rem}}
    .wxg{{display:grid;grid-template-columns:repeat(auto-fit,minmax(118px,1fr));gap:8px;margin-top:14px}}
    .wxc{{background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.18);border-radius:13px;padding:10px 11px;display:grid;gap:2px;align-content:start}}
    .wxc svg{{margin-bottom:2px}}
    .wxc b{{font-size:1.1rem;letter-spacing:-.01em}} .wxc span{{font-size:.74rem;color:rgba(255,255,255,.82);line-height:1.25}}
    .wxv{{display:flex;align-items:center;gap:8px;margin:10px 0 0;padding:8px 10px;border-radius:10px;background:rgba(255,255,255,.2);color:#fff;font-size:.84rem}}
    .ic .rays{{transform-box:view-box;transform-origin:12px 12px;animation:spin 6s linear infinite}}
    .ic-part .rays{{transform-origin:8.5px 9px}}
    .ic .drops{{animation:fall .9s linear infinite}}
    .ic .drift{{animation:drift 1.6s ease-in-out infinite alternate}}
    .ic .flash{{animation:flash 1.4s linear infinite}}
    '''
    F = (ROOT / 'social' / 'fonts').as_uri(); LOGOPNG = (ROOT / 'social' / 'assets' / 'logo-512.png').as_uri()
    title = (f"{JOURS[dset[0].weekday()]} {dset[0].day} {MOIS[dset[0].month - 1]}" if len(dset) == 1
             else f"{JOURS[dset[0].weekday()][:3]}. {dset[0].day} et {JOURS[dset[1].weekday()][:3]}. {dset[1].day} {MOIS[dset[1].month - 1]}")
    style += f"""@font-face{{font-family:SC;font-weight:800;src:url('{F}/SairaCondensed-800.woff2')}}
    @font-face{{font-family:IS;font-weight:400 700;src:url('{F}/InstrumentSans.woff2')}}
    .sc{{font-family:SC,sans-serif}} .wxh h4.rname{{font-family:SC,sans-serif;font-weight:800;font-size:1.3rem;letter-spacing:.01em}}"""
    body = f'''
    {scene(dict(W=W, H=H), .36)}
    <div style="position:absolute;left:0;right:0;top:200px;display:flex;justify-content:center;animation:pop .5s {BACK} .05s both">
      <div class="sc" style="background:#1d4f9c;color:#fff;font-weight:800;font-size:46px;letter-spacing:1px;padding:8px 30px;border-radius:14px;border:5px solid #1d2523;border-bottom:8px solid #ffd400;transform:rotate(-2deg);box-shadow:0 12px 24px rgba(29,37,35,.25)">Météo des courses</div></div>
    <div class="sc" style="position:absolute;left:64px;right:64px;top:335px;text-align:center;font-weight:800;font-size:92px;line-height:1;color:#1d2523;animation:up .6s {EASE} .2s both">{title[0].upper() + title[1:]}</div>
    <div style="position:absolute;left:56px;right:56px;top:475px">
      <div class="cards" style="display:flex;flex-direction:column;gap:14px">{''.join(cards)}</div></div>
    <div style="position:absolute;left:0;right:0;bottom:185px;display:flex;flex-direction:column;align-items:center;gap:16px;animation:up .6s {EASE} {1.0 + n * .35 + .3:.2f}s both">
      <div style="display:flex;align-items:center;gap:22px;background:#fff;border:6px solid #1d2523;border-radius:999px;padding:14px 40px 14px 18px;box-shadow:0 16px 30px rgba(29,37,35,.22)">
        <img src="{LOGOPNG}" style="width:110px;display:block">
        <div><div class="sc" style="font-weight:800;font-size:54px;line-height:.95;color:#1d2523">Dossard Péi</div>
        <div style="font-family:IS;font-weight:700;font-size:30px;color:#0d6b67;margin-top:4px">dossardpei.re</div></div></div>
      {f'<div style="font-family:IS;font-size:30px;font-weight:700;color:#1d2523">+ {more} autre{"s" if more > 1 else ""} course{"s" if more > 1 else ""} sur dossardpei.re</div>' if more else ''}
      <div style="font-family:IS;font-size:24px;font-weight:600;color:#1d2523">Prévisions MET Norway du {D.datetime.fromisoformat(wx['at']).strftime('%d/%m à %Hh')}</div></div>'''
    html = f'<!doctype html><html><head><meta charset="utf-8"><style>{style}</style></head><body>{body}</body></html>'
    return html, total, items, more


if __name__ == '__main__':
    fri = D.date.fromisoformat(sys.argv[1])
    html, total, items, more = build(fri)
    if not html:
        print('rien : aucune course avec météo samedi / dimanche'); sys.exit(0)
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / '_meteo.html'; f.write_text(html)
    mp4, jpg = OUT / f'story-meteo-{fri}.mp4', OUT / f'story-meteo-{fri}.jpg'
    record(f, mp4, total, stills=[(total - .05, jpg)])
    f.unlink()
    wx_at = json.loads((ROOT / 'weather.json').read_text())['at']
    print(f'ok {len(items) + more} course(s) · météo du {wx_at}\n{jpg}\n{mp4}')
