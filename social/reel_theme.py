"""Reel motion design du mercredi (thème de la semaine), version validée le 24/11/2026 : remplace le déroulé « point par point »
de reel_post.py pour kind=theme (reel_post.py l'appelle ; même sélection, mêmes sorties, même ligne « ok … »).
Déroulé (≈ 16 à 23 s, bruitages sans musique) :
 1. accroche en typo cinétique sur l'île floutée : le chiffre fort du thème (même chiffre que la couverture du carrousel,
    post_lundi.HEROES), compteur qui défile, trait jaune ; Sam et/ou Ana avec leur bulle (post_lundi.PERSO_TH) ;
 2. pastille + étiquette orange « Le thème de la semaine » + titre, qui montent en haut (image de couverture à 3,2 s) ;
 3. une carte crème par course (au plus 8, dans l'ordre des dates), entrée et sortie avec flou de mouvement : date, commune,
    nom, compteurs km et D+, profil d'altitude qui se dresse s'il existe dans profiles.json, sinon jauge (pas de profil inventé) ;
    s'il y a plus de 8 courses, les autres points apparaissent ensuite avec « + N autres » ;
 4. final : les barres (D+ pour « Les gros D+ », distance sinon) qui se dressent, le total et la pastille logo."""
import json, math, datetime as D
from core import upcoming, week_index, MAP, P_xy, ROOT, JOURS_C, MOIS_C, fmt_km
import nouveau as N
import picto, safe
from gen import THEMES
import post_lundi as PL

W, H = 1080, 1920
INK, TEAL, SURF, MUTED = N.INK, N.TEAL, N.SURF, N.MUTED
SEA = '#083b5a'
KMAX = 8                      # cartes de course au plus ; au-delà, points seuls et « + N autres »
COVER_T = 3.2                 # image de couverture : pastille + étiquette + titre
ICON = {'gros-dp': 'theme-mont', 'longues': 'theme-mont', 'rando': 'theme-mont', 'relais': 'theme-duo', 'marmailles': 'theme-duo'}
PHRASE = {'route': 'courses sur route', 'rando': 'randos et marches', 'marmailles': 'courses avec les marmailles',
          'multisport': 'courses multisport', 'premiere': 'courses pour se lancer'}


def nb(v):
    return f'{v:,}'.replace(',', ' ') if isinstance(v, int) else fmt_km(v)


def select(ref, races):
    """même choix que gen.build_mardi / reel_post.select('theme') → (thème, courses) ou (None, None)"""
    horizon = upcoming(races, ref, ref + D.timedelta(days=70)); k0 = week_index(ref) % len(THEMES)
    for k in range(len(THEMES)):
        t = THEMES[(k0 + k) % len(THEMES)]
        if t.get('off'):
            continue
        s = [r for r in horizon if t['pred'](r)]
        if len(s) >= 3:
            return t, s[:30]
    return None, None


# épreuve qui fait entrer la course dans le thème (comme les prédicats de gen.THEMES) : c'est elle que montrent la carte et les barres
QUAL = {'gros-dp': lambda e: (e.get('dp') or 0) >= 1500 and e.get('type') in ('trail', 'marche'),
        'longues': lambda e: (e.get('km') or 0) > 30 and e.get('type') in ('trail', 'route', 'marche'),
        'premiere': lambda e: e.get('km') and e['km'] < 15 and (e.get('dp') or 0) < 500 and e.get('type') in ('route', 'trail', 'cross'),
        'relais': lambda e: e.get('type') == 'relais', 'route': lambda e: e.get('type') == 'route', 'rando': lambda e: e.get('type') == 'marche',
        'multisport': lambda e: e.get('type') == 'multisport', 'marmailles': lambda e: e.get('type') == 'jeunes'}


def qual(r, tid):
    """→ (km, D+) de l'épreuve du thème la plus grande (D+ pour gros-dp, distance sinon) ; repli sur l'épreuve principale"""
    key = 'dp' if tid == 'gros-dp' else 'km'
    es = [e for e in r['epreuves'] if QUAL.get(tid, lambda e: True)(e) and (e.get(key) or 0) > 0]
    e = max(es, key=lambda e: e[key]) if es else (r['_main'] or {})
    return e.get('km') or 0, e.get('dp') or 0


def best(r, key, tid):
    km, dp = qual(r, tid)
    return dp if key == 'dp' else km


def hook(t, sel):
    """le chiffre fort, comme sur la couverture du carrousel → dict(pre, val, unit, line, pose, text, duo)"""
    tid = t['id']; pose, text = PL.PERSO_TH.get(tid, (3, 'Lé pa loin !'))
    if tid == 'gros-dp':
        return dict(pre="Jusqu'à", val=int(max(best(r, 'dp', tid) for r in sel)), unit='m de D+', line=None, pose=pose, text=text, duo=False)
    if tid == 'longues':
        return dict(pre="Jusqu'à", val=max(best(r, 'km', tid) for r in sel), unit='km', line=None, pose=pose, text=text, duo=False)
    if tid == 'premiere':
        kms = sorted(e['km'] for r in sel for e in r['epreuves'] if e.get('km') and e['km'] < 15 and (e.get('dp') or 0) < 500 and e.get('type') in ('route', 'trail', 'cross'))
        five = [k for k in kms if k >= 5]
        return dict(pre='Dès', val=five[0] if five else kms[0], unit='km', line='sans gros dénivelé', pose=pose, text=text, duo=False)
    if tid == 'relais':
        kms = [e['km'] for r in sel for e in r['epreuves'] if e.get('type') == 'relais' and e.get('km')]
        line = f'de {fmt_km(min(kms))} à {fmt_km(max(kms))} km' if kms else None
        return dict(pre='En équipe', val=len(sel), unit='relais', line=line, pose=pose, text=text, duo=True)
    return dict(pre='Ces 10 semaines', val=len(sel), unit=PHRASE.get(tid, 'courses'), line=None, pose=pose, text=text, duo=bool(t.get('duo')))


def counter(cls, val, t0, dur, p, big=False):
    """compteur CSS que rec.py peut caler image par image : --n entier animé de 0 à val (ease-out par paliers).
    Valeur non entière (42,2 km) : affichée telle quelle, sans défilement."""
    if not float(val).is_integer():
        return '', f'<span>{fmt_km(val)}</span>'
    val = int(val)
    stops = ' '.join(f'{p(t0 + dur * i / 12)}{{--n:{round(val * (1 - (1 - i / 12) ** 3))}}}' for i in range(13))
    css = f'.{cls}{{animation:{cls} var(--D) linear both}} @keyframes {cls}{{0%{{--n:0}} {stops} 100%{{--n:{val}}}}}'
    return css, f'<span class="cnt{" big" if big else ""} {cls}"></span>'


def page(ref, races):
    t, sel = select(ref, races)
    if not t:
        return None, 0
    tid = t['id']; key = 'dp' if tid == 'gros-dp' else 'km'
    n = len(sel); K = min(n, KMAX); shown = sel[:K]; rest = sel[K:]
    M = MAP(); E = N.esc; F = N.F
    prof = json.loads((ROOT / 'profiles.json').read_text())
    bg, fg = picto.TAG['theme']
    hk = hook(t, sel)
    vals = [best(r, key, tid) for r in shown]; VMAX = max(vals) or 1
    # ---- ligne de temps
    HOOK = 2.3; T0 = 4.2; STEP = 1.95 if K <= 6 else 1.65
    TR = T0 + K * STEP; TS = TR + (min(1.6, .5 + .07 * len(rest)) if rest else 0); DUR = TS + 5.2
    p = lambda x: f'{max(0, min(DUR, x)) / DUR * 100:.3f}%'
    css = []
    AX, AY = 540, 745; KF = 780 / M['W']; cx, cy = M['W'] / 2, M['H'] / 2      # zone de sécurité 9:16 (safe.py)
    world = f'translate({AX - cx * KF:.1f}px,{AY - cy * KF:.1f}px) scale({KF:.4f})'
    pins, cards, seen = [], [], {}
    for i, r in enumerate(sel):
        col = N.TCOL.get(_rtype(r), N.TCOL['autre'])
        mx, my = P_xy(*r['ll']); px, py = AX + (mx - cx) * KF, AY + (my - cy) * KF
        kk = (round(px / 26), round(py / 26)); j = seen.get(kk, 0); seen[kk] = j + 1
        if j:
            a = j * 2.4; px += 30 * math.sqrt(j) * math.cos(a); py += 30 * math.sqrt(j) * math.sin(a)
        if i < K:
            ti = T0 + i * STEP
            css.append(f'@keyframes pin{i}{{0%,{p(ti)}{{opacity:0;transform:scale(.1)}} {p(ti + .18)}{{opacity:1;transform:scale(1.9)}} {p(ti + .35)},{p(ti + STEP - .15)}{{opacity:1;transform:scale(1.35)}}'
                       f' {p(ti + STEP + .1)},{p(TS)}{{opacity:1;transform:scale(1)}} {p(TS + .5)},100%{{opacity:0;transform:scale(1)}}}}')
        else:
            ti = TR + .07 * (i - K)
            css.append(f'@keyframes pin{i}{{0%,{p(ti)}{{opacity:0;transform:scale(.1)}} {p(ti + .15)}{{opacity:1;transform:scale(1.5)}} {p(ti + .3)},{p(TS)}{{opacity:1;transform:scale(1)}} {p(TS + .5)},100%{{opacity:0;transform:scale(1)}}}}')
        css.append(f'@keyframes ring{i}{{0%,{p(ti)}{{opacity:0;transform:scale(.6)}} {p(ti + .1)}{{opacity:.9}} {p(ti + .9)},100%{{opacity:0;transform:scale(4.5)}}}}')
        pins.append(f'<div class="pin anim" style="left:{px:.0f}px;top:{py:.0f}px;--c:{col};animation-name:pin{i}"></div>'
                    f'<div class="ring anim" style="left:{px:.0f}px;top:{py:.0f}px;animation-name:ring{i}"></div>')
        if i >= K:
            continue
        # carte : entre par la droite avec flou de mouvement, sort par la gauche
        t1 = ti + STEP; m = r['_main'] or {}; dt = r['_d']
        css.append(f'@keyframes cd{i}{{0%,{p(ti)}{{opacity:0;transform:translateX(620px) skewX(-8deg);filter:blur(16px)}} {p(ti)}{{animation-timing-function:cubic-bezier(.15,.85,.25,1)}}'
                   f' {p(ti + .38)},{p(t1 - .2)}{{opacity:1;transform:none;filter:blur(0)}} {p(t1 - .2)}{{animation-timing-function:cubic-bezier(.6,0,.9,.4)}} {p(t1 + .05)},100%{{opacity:0;transform:translateX(-640px) skewX(8deg);filter:blur(16px)}}}}')
        km, dp = qual(r, tid)
        stats = ''
        if km:
            c, h = counter(f'k{i}', km, ti + .25, .9, p); css.append(c); stats += f'<div class="s v">{h}<em> km</em></div>'
        if dp:
            c, h = counter(f'd{i}', dp, ti + .25, 1.0, p, big=True); css.append(c); stats += f'<div class="s v dp">{h}<em> m D+</em></div>'
        pr = prof.get(r['id'])
        if pr:
            lo, hi = min(pr), max(pr); w, h = 470, 170
            pts = ' '.join(f'{k / (len(pr) - 1) * w:.1f},{h - (v - lo) / max(1, hi - lo) * (h - 12):.1f}' for k, v in enumerate(pr))
            vis = (f'<svg class="pf anim" style="animation-name:pf{i}" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
                   f'<defs><linearGradient id="g{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{col}" stop-opacity=".9"/><stop offset="1" stop-color="{col}" stop-opacity=".15"/></linearGradient></defs>'
                   f'<polygon points="0,{h} {pts} {w},{h}" fill="url(#g{i})"/><polyline points="{pts}" fill="none" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/></svg>'
                   f'<div class="alt">Point haut {nb(int(hi))} m</div>')
            css.append(f'@keyframes pf{i}{{0%,{p(ti + .2)}{{transform:scaleY(0);clip-path:inset(0 100% 0 0)}} {p(ti + .2)}{{animation-timing-function:cubic-bezier(.2,.8,.2,1)}} {p(ti + 1.1)},100%{{transform:none;clip-path:inset(0 0 0 0)}}}}')
        elif not vals[i]:
            vis = ''
        else:      # pas de tracé connu : jauge par rapport au plus grand de la liste (pas de profil inventé)
            lab = f'D+ comparé aux {nb(int(VMAX))} m' if key == 'dp' else f'Distance comparée aux {fmt_km(VMAX)} km'
            vis = f'<div class="gauge"><div class="gl">{lab}</div><div class="gb"><i class="anim" style="background:{col};animation-name:gg{i}"></i></div></div>'
            css.append(f'@keyframes gg{i}{{0%,{p(ti + .25)}{{width:0}} {p(ti + .25)}{{animation-timing-function:cubic-bezier(.2,.8,.2,1)}} {p(ti + 1.15)},100%{{width:{max(4, 100 * vals[i] / VMAX):.1f}%}}}}')
        when = f"{JOURS_C[dt.weekday()].capitalize()} {dt.day} {MOIS_C[dt.month - 1]}"
        cards.append(f'''<div class="cd anim" style="animation-name:cd{i}"><i class="bar" style="background:{col}"></i>
 <div class="top"><div class="dt">{E(when)} · {E(r['commune'])}</div><div class="ct s">{i + 1}<small>/{n}</small></div></div>
 <div class="nm s">{E(r['nom'])}</div>
 <div class="row"><div class="vis">{vis}</div><div class="st">{stats}</div></div></div>''')
    more = ''
    if rest:
        more = f'<div id="more" class="s anim">+ {len(rest)} autre{"s" if len(rest) > 1 else ""}</div>'
        css.append(f'@keyframes more{{0%,{p(TR)}{{opacity:0;transform:scale(.5)}} {p(TR)}{{animation-timing-function:cubic-bezier(.3,1.6,.5,1)}} {p(TR + .4)},{p(TS)}{{opacity:1;transform:none}} {p(TS + .3)},100%{{opacity:0}}}}')
    # ---- final : les barres qui se dressent
    BW = min(110, 760 // K - 22); bars = []
    for i, r in enumerate(shown):
        if not vals[i]:
            continue
        tt = TS + .5 + i * .12; col = N.TCOL.get(_rtype(r), N.TCOL['autre'])
        css.append(f'@keyframes fb{i}{{0%,{p(tt)}{{transform:scaleY(0)}} {p(tt)}{{animation-timing-function:cubic-bezier(.3,1.4,.5,1)}} {p(tt + .6)},100%{{transform:none}}}}'
                   f'@keyframes fv{i}{{0%,{p(tt + .35)}{{opacity:0;transform:translateY(20px)}} {p(tt + .6)},100%{{opacity:1;transform:none}}}}')
        v = nb(int(vals[i])) if key == 'dp' else fmt_km(vals[i])
        bars.append(f'<div class="fc"><div class="fv s anim" style="animation-name:fv{i}">{v}</div><div class="fbar anim" style="height:{30 + 270 * vals[i] / VMAX:.0f}px;width:{BW}px;background:{col};animation-name:fb{i}"></div>'
                    f'<div class="fn">{E(r["nom"].split(" : ")[0].split(" (")[0])}</div></div>')
    ftitle = {'gros-dp': 'Le plus gros D+ de chaque course', 'premiere': 'La distance pour se lancer', 'relais': 'La distance du relais'}.get(tid, 'La plus longue distance de chaque course') + (f' (les {K} premières)' if rest else '')
    hc, hh = counter('hk', hk['val'], .45, 1.15, p, big=True); css.append(hc)
    figs = (f'<div style="width:232px;height:314px">{PL.perso(ref, hk["pose"], "jeremi")}</div><div style="width:232px;height:314px;margin-left:-32px">{PL.perso(ref, hk["pose"], "nadia")}</div>'
            if hk['duo'] else f'<div style="width:270px;height:365px">{PL.perso(ref, hk["pose"])}</div>')
    ufs = 112 if len(hk['unit']) <= 10 else (84 if len(hk['unit']) <= 18 else 70)
    line = f'<div class="hl">{E(hk["line"])}</div>' if hk['line'] else ''
    html = f'''<!doctype html><html><head><meta charset="utf-8"><style>
@property --n{{syntax:'<integer>';inherits:false;initial-value:0}}
@property --k{{syntax:'<integer>';inherits:true;initial-value:0}}
@property --u{{syntax:'<integer>';inherits:true;initial-value:0}}
@counter-style p3{{system:extends decimal;pad:3 "0"}}
.cnt{{--k:round(down,var(--n)/1000,1);--u:mod(var(--n),1000);counter-reset:n var(--n) k var(--k) u var(--u)}}
.cnt::after{{content:counter(n)}}
.cnt.big{{display:inline-grid;justify-items:end}} #hook .cnt.big{{justify-items:center}}
.cnt.big::before,.cnt.big::after{{grid-area:1/1}}
.cnt.big::before{{content:counter(n);opacity:calc(1 - min(var(--k),1))}}
.cnt.big::after{{content:counter(k) "\\202F" counter(u,p3);opacity:min(var(--k),1)}}
@font-face{{font-family:S;font-weight:800;src:url('{F}/SairaCondensed-800.woff2')}}
@font-face{{font-family:I;font-weight:400;src:url('{F}/inter-latin-400-normal.woff2')}}
@font-face{{font-family:I;font-weight:600;src:url('{F}/inter-latin-600-normal.woff2')}}
@font-face{{font-family:I;font-weight:700;src:url('{F}/inter-latin-700-normal.woff2')}}
*{{box-sizing:border-box;margin:0;padding:0}} html,body{{width:{W}px;height:{H}px;overflow:hidden;background:{SEA}}}
body{{font-family:I,sans-serif;color:{INK};position:relative;--D:{DUR}s}} .s{{font-family:S,sans-serif;font-weight:800}}
.anim{{animation-duration:{DUR}s;animation-fill-mode:both;animation-timing-function:linear}}
#lens{{position:absolute;inset:0;background:{SEA};animation-name:lens}}
@keyframes lens{{0%,{p(2.4)}{{filter:blur(24px) saturate(.8);transform:scale(1.12)}} {p(2.4)}{{animation-timing-function:cubic-bezier(.4,0,.2,1)}} {p(3.6)},{p(TS)}{{filter:blur(0) saturate(1);transform:none}}
  {p(TS + .3)},100%{{filter:blur(18px) saturate(.8);transform:scale(1.06)}}}}
#world{{position:absolute;left:0;top:0;width:{M['W']}px;height:{M['H']}px;transform-origin:0 0;transform:{world}}}
#world img{{position:absolute;left:0;top:0;width:{M['W']}px;height:{M['H']}px}}
#veil{{position:absolute;inset:0;background:rgba(8,59,90,.62);animation-name:veil}}
@keyframes veil{{0%,{p(2.4)}{{opacity:1}} {p(3.6)},{p(TS)}{{opacity:.12}} {p(TS + .4)},100%{{opacity:1}}}}
#hook{{position:absolute;left:0;right:0;top:450px;text-align:center;color:#fff;animation-name:hook}}
@keyframes hook{{0%,{p(HOOK - .15)}{{transform:none;filter:blur(0);opacity:1}} {p(HOOK - .15)}{{animation-timing-function:cubic-bezier(.6,0,.9,.5)}} {p(HOOK + .25)},100%{{transform:translateY(-520px) scaleY(1.25);filter:blur(22px);opacity:0}}}}
#hook .a{{font-size:96px;line-height:1;animation-name:ha}} @keyframes ha{{0%,{p(.1)}{{opacity:0;transform:translateY(40px);filter:blur(12px)}} {p(.1)}{{animation-timing-function:cubic-bezier(.2,.8,.2,1)}} {p(.45)},100%{{opacity:1;transform:none;filter:blur(0)}}}}
#hook .b{{font-size:290px;line-height:.92;letter-spacing:-4px;margin-top:6px;text-shadow:0 10px 40px rgba(0,0,0,.35);animation-name:hb}}
@keyframes hb{{0%,{p(.35)}{{opacity:0;transform:scale(.6);filter:blur(14px)}} {p(.35)}{{animation-timing-function:cubic-bezier(.3,1.5,.5,1)}} {p(.75)},100%{{opacity:1;transform:none;filter:blur(0)}}}}
#hook .u{{font-size:{ufs}px;line-height:1;margin-top:4px;padding:0 40px}}
#hook .hl{{font-weight:700;font-size:48px;margin-top:18px}}
#hook .ln{{height:12px;width:560px;margin:26px auto 0;border-radius:6px;background:#ffd400;box-shadow:0 0 30px rgba(255,212,0,.7);transform-origin:0 50%;animation-name:ln}}
@keyframes ln{{0%,{p(1.0)}{{transform:scaleX(0)}} {p(1.0)}{{animation-timing-function:cubic-bezier(.2,.8,.2,1)}} {p(1.5)},100%{{transform:none}}}}
#figs{{position:absolute;right:{W - safe.BTN_X}px;bottom:{H - safe.Y1 - 30}px;display:flex;align-items:flex-end;animation-name:figs}}
@keyframes figs{{0%,{p(1.05)}{{opacity:0;transform:translateY(260px)}} {p(1.05)}{{animation-timing-function:cubic-bezier(.3,1.4,.5,1)}} {p(1.5)},{p(HOOK - .1)}{{opacity:1;transform:none}} {p(HOOK - .1)}{{animation-timing-function:ease-in}} {p(HOOK + .25)},100%{{opacity:0;transform:translateY(300px)}}}}
#bub{{position:absolute;left:{safe.X0}px;top:{safe.Y1 - 300}px;max-width:{'380' if hk['duo'] else '470'}px;background:{SURF};color:{INK};font-size:60px;line-height:1.02;padding:18px 30px 22px;border-radius:30px;box-shadow:0 18px 40px rgba(0,0,0,.35);transform-origin:100% 100%;animation-name:bub}}
#bub:after{{content:"";position:absolute;right:-26px;bottom:34px;border:18px solid transparent;border-left:34px solid {SURF}}}
@keyframes bub{{0%,{p(1.35)}{{opacity:0;transform:scale(.3);filter:blur(0)}} {p(1.35)}{{animation-timing-function:cubic-bezier(.3,1.6,.5,1)}} {p(1.7)},{p(HOOK - .1)}{{opacity:1;transform:none;filter:blur(0)}} {p(HOOK + .2)},100%{{opacity:0;transform:scale(.6) translateX(-200px);filter:blur(10px)}}}}
#tag{{position:absolute;left:0;right:0;top:0;display:flex;flex-direction:column;align-items:center;transform-origin:50% 0;animation-name:tag}}
#tag .t{{background:{bg};color:{fg};font-size:76px;letter-spacing:1px;padding:10px 44px 14px;border-radius:22px;box-shadow:0 18px 40px rgba(0,0,0,.35);line-height:1}}
#tag .n{{margin-top:22px;max-width:{safe.BTN_X - (W - safe.BTN_X)}px;background:{SURF};color:{INK};font-size:{92 if len(t['short']) <= 18 else 74}px;line-height:1;text-align:center;padding:12px 40px 16px;border-radius:22px;box-shadow:0 18px 40px rgba(0,0,0,.3)}}
@keyframes tag{{0%,{p(HOOK + .05)}{{transform:translateY(1300px) scale(.8);opacity:0;filter:blur(18px)}} {p(HOOK + .05)}{{animation-timing-function:cubic-bezier(.15,.85,.25,1)}}
  {p(HOOK + .45)},{p(T0 - .75)}{{transform:translateY(840px) scale(1);opacity:1;filter:blur(0)}} {p(T0 - .75)}{{animation-timing-function:cubic-bezier(.6,0,.2,1)}} {p(T0 - .1)},{p(TS)}{{transform:translateY({safe.Y0 + 8}px) scale(.66);opacity:1;filter:blur(0)}}
  {p(TS + .3)},100%{{transform:translateY({safe.Y0 + 8}px) scale(.66);opacity:0;filter:blur(0)}}}}
{picto.badge_css(p, t_in=HOOK + .2, t_out=T0 - .8)}
.pin{{position:absolute;width:46px;height:46px;margin:-23px 0 0 -23px;border-radius:50%;background:var(--c);border:7px solid #fff;box-shadow:0 4px 12px rgba(0,0,0,.55)}}
.ring{{position:absolute;width:38px;height:38px;margin:-19px 0 0 -19px;border-radius:50%;border:6px solid #fff}}
.cd{{position:absolute;left:{safe.X0}px;right:{W - safe.X1}px;top:{safe.Y1 - 420}px;height:420px;background:{SURF};border-radius:34px;box-shadow:0 26px 60px rgba(4,20,30,.5);overflow:hidden;padding:24px {36 + safe.X1 - safe.BTN_X}px 0 48px}}
.cd .bar{{position:absolute;left:0;top:0;bottom:0;width:22px}}
.cd .top{{display:flex;justify-content:space-between;align-items:baseline}} .dt{{font-weight:700;font-size:36px;color:{TEAL}}}
.ct{{font-size:64px;line-height:1;color:{INK}}} .ct small{{font-size:34px;color:{MUTED}}}
.nm{{font-size:68px;line-height:1.04;margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.row{{display:flex;align-items:flex-end;gap:22px;margin-top:16px}} .vis{{position:relative;width:470px;height:180px;flex:none}}
.pf{{position:absolute;left:0;bottom:0;transform-origin:50% 100%;overflow:visible}}
.alt{{position:absolute;left:0;top:-6px;font-weight:700;font-size:28px;color:{MUTED}}}
.gauge{{position:absolute;left:0;right:0;bottom:20px}} .gl{{font-weight:700;font-size:28px;color:{MUTED};margin-bottom:12px}}
.gb{{height:46px;border-radius:23px;background:#e9e4da;overflow:hidden}} .gb i{{display:block;height:100%;border-radius:23px}}
.st{{flex:1;text-align:right;padding-bottom:6px}} .v{{font-size:84px;line-height:1;color:{INK}}} .v em{{font-style:normal;font-size:44px;color:{MUTED}}}
.v.dp{{color:{TEAL};margin-top:6px}}
#more{{position:absolute;left:0;right:0;top:1300px;margin:auto;width:max-content;background:{SURF};color:{INK};font-size:80px;line-height:1;padding:14px 44px 20px;border-radius:26px;box-shadow:0 20px 44px rgba(0,0,0,.4);animation-name:more}}
#fin{{position:absolute;left:{safe.X0}px;right:{W - safe.X1}px;top:{safe.Y0 + 70}px;height:620px;background:{SURF};border-radius:34px;box-shadow:0 26px 60px rgba(4,20,30,.5);padding:34px {30 + safe.X1 - safe.BTN_X}px 0 30px;animation-name:fin}}
@keyframes fin{{0%,{p(TS + .1)}{{opacity:0;transform:translateY(160px) scale(.9);filter:blur(14px)}} {p(TS + .1)}{{animation-timing-function:cubic-bezier(.2,.9,.3,1)}} {p(TS + .5)},100%{{opacity:1;transform:none;filter:blur(0)}}}}
#fin h2{{font-size:{56 if len(ftitle) <= 34 else (44 if len(ftitle) <= 42 else 38)}px;line-height:1;text-align:center;margin-bottom:24px}}
#fin .bars{{display:flex;justify-content:center;align-items:flex-end;gap:22px;height:470px}}
.fc{{display:flex;flex-direction:column;align-items:center;width:{BW + 22}px}} .fv{{font-size:34px;line-height:1;margin-bottom:8px}}
.fbar{{border-radius:14px 14px 0 0;transform-origin:50% 100%}} .fn{{height:74px;margin-top:10px;font-weight:700;font-size:24px;line-height:1.1;text-align:center;color:{INK};overflow:hidden}}
#sum{{position:absolute;left:0;right:0;top:1000px;display:flex;flex-direction:column;align-items:center;gap:18px;animation-name:sum}}
@keyframes sum{{0%,{p(TS + 1.5)}{{opacity:0;transform:scale(.5)}} {p(TS + 1.5)}{{animation-timing-function:cubic-bezier(.3,1.6,.5,1)}} {p(TS + 2.0)},100%{{opacity:1;transform:none}}}}
#sum .b{{background:{bg};color:{fg};font-size:120px;line-height:1;padding:10px 50px 18px;border-radius:28px;box-shadow:0 20px 44px rgba(0,0,0,.4)}}
#sum .l{{background:{SURF};font-weight:700;font-size:26px;white-space:nowrap;padding:10px 30px 12px;border-radius:18px;box-shadow:0 14px 30px rgba(0,0,0,.3)}}
#foot{{position:absolute;left:0;right:0;top:1330px;display:flex;justify-content:center;animation-name:foot}}
@keyframes foot{{0%,{p(TS + 2.2)}{{opacity:0;transform:translateY(30px)}} {p(TS + 2.7)},100%{{opacity:1;transform:none}}}}
#foot .b{{display:flex;align-items:center;gap:18px;background:#fff;border:5px solid {INK};border-radius:999px;padding:10px 36px 10px 14px;box-shadow:0 16px 30px rgba(4,20,30,.3)}}
#foot .b img{{width:84px;display:block}} #foot .b div{{font:800 46px/1 S,sans-serif}} #foot .b small{{display:block;font:700 26px I,sans-serif;color:{TEAL};margin-top:3px}}
{''.join(css)}
</style></head><body>
<div id="lens" class="anim"><div id="world"><img src="{N.OCEAN}"><img src="{N.island()}"></div></div>
<div id="veil" class="anim"></div>
{''.join(pins)}
<div id="hook" class="anim"><div class="s a anim">{E(hk['pre'])}</div><div class="s b anim">{hh}</div><div class="s u">{E(hk['unit'])}</div>{line}<div class="ln anim"></div></div>
<div id="figs" class="anim">{figs}</div><div id="bub" class="s anim">{E(hk['text'])}</div>
<div id="tag" class="anim">{picto.badge(ICON.get(tid, 'theme-shoe'))}<div class="s t">Le thème de la semaine</div><div class="s n">{E(t['short'])}</div></div>
{''.join(cards)}{more}
<div id="fin" class="anim"><h2 class="s">{E(ftitle)}</h2><div class="bars">{''.join(bars)}</div></div>
<div id="sum" class="anim"><div class="s b">{n} course{'s' if n > 1 else ''}</div><div class="l">ces 10 prochaines semaines · détail dans le carrousel</div></div>
<div id="foot" class="anim"><div class="b"><img src="{N.LOGO}"><div>Dossard Péi<small>dossardpei.re</small></div></div></div>
</body></html>'''
    ev = [(.1, 'whoosh', .6), (.4, 'pop', 420)] + [(.45 + k * .1, 'tick', 1500 + 60 * k, .04, .1) for k in range(11)] + \
         [(1.0, 'whoosh', .5), (1.1, 'pop', 600), (1.4, 'pop', 820), (HOOK - .1, 'whoosh', 1.0), (HOOK + .3, 'pop', 520), (HOOK + .55, 'pop', 700), (T0 - .7, 'whoosh', .8)]
    for i in range(K):
        ti = T0 + i * STEP
        ev += [(ti - .05, 'whoosh', .45), (ti, 'pop', 520 + 380 * i / max(1, K - 1), .1, .38)] + [(ti + .3 + k * .09, 'tick', 1700, .03, .08) for k in range(8)]
    ev += [(TR + .07 * j, 'pop', 600 + 20 * j, .06, .2) for j in range(len(rest))]
    ev += [(TS, 'whoosh', .7)] + [(TS + .5 + i * .12, 'pop', 400 + 90 * i, .08, .3) for i in range(K)] + [(TS + 1.5, 'thud'), (TS + 2.3, 'chime')]
    page.ev = ev; page.n = n; page.title = t['short']
    return html, DUR


def _rtype(r):
    t = (r.get('_main') or {}).get('type')
    return t if t in N.TCOL else next((x for x in ('trail', 'route', 'relais', 'multisport', 'cross', 'marche', 'jeunes') if x in r['_types']), 'autre')
