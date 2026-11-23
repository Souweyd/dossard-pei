"""Pictogramme et couleur d'étiquette par type de vidéo (Météo, Nouveau dossard, Course annulée) :
sur la grille, on doit reconnaître le type d'un coup d'œil. Dessins au trait, pas d'emoji.
Drapeau du dossard : 5 rayons depuis le sommet du volcan (voir README)."""
INK, TEAL, SUN, RED = '#1d2523', '#0d6b67', '#ffd400', '#b3261e'
# étiquette : (fond, texte)
TAG = {'meteo': (SUN, INK), 'nouveau': (TEAL, '#fff'), 'annule': (RED, '#fff'),
       'weekend': (INK, SUN),                    # reel 3D du lundi (dépôt dossard-pei-posts)
       'theme': ('#e8743b', '#fff'), 'region': ('#1f6fb2', '#fff'), 'mois': ('#4b3f8f', '#fff')}      # reels du mercredi, du vendredi, du 1er du mois
_S = f'stroke="{INK}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"'


def _sun(cx, cy, r):
    import math
    rays = ''.join(f'<path d="M{cx + (r + 9) * math.cos(a):.1f} {cy + (r + 9) * math.sin(a):.1f}L{cx + (r + 19) * math.cos(a):.1f} {cy + (r + 19) * math.sin(a):.1f}"/>'
                   for a in (i * math.pi / 4 for i in range(8)))
    return f'<g {_S} fill="{SUN}">{rays}<circle cx="{cx}" cy="{cy}" r="{r}"/></g>'


def _cloud(dy=0, fill='#fff'):
    return f'<path transform="translate(0 {dy})" d="M38 96a17 17 0 0 1 1-34 24 24 0 0 1 45-6 20.500 20.500 0 0 1 2 40z" fill="{fill}" {_S}/>'


def _drops(y):
    return ''.join(f'<path d="M{x} {y}l-7 16" stroke="#2f7fc9" stroke-width="7" stroke-linecap="round"/>' for x in (46, 64, 82))


def _bib(grey=False):
    blue, yel, red = ('#8b9499', '#d9dcdd', '#5d666b') if grey else ('#1d4f9c', '#ffd400', '#e3242b')
    return f'''<clipPath id="pbib"><rect x="14" y="26" width="92" height="70" rx="9"/></clipPath>
<g clip-path="url(#pbib)"><rect x="14" y="26" width="92" height="70" fill="#fff"/>
<svg x="14" y="26" width="92" height="27" viewBox="6.5 11.5 51 10.5" preserveAspectRatio="none"><rect x="6.5" y="11.5" width="51" height="10.5" fill="{blue}"/><path d="M32 17 9.5 11.5h5zM32 17 21.6 11.5h4zM32 17 30.2 11.5h3.6zM32 17 38.4 11.5h4zM32 17 49.5 11.5h5z" fill="{yel}"/><path d="M24 22h16L32 16z" fill="{red}"/></svg></g>
<rect x="14" y="26" width="92" height="70" rx="9" fill="none" {_S}/>
<text x="60" y="87" text-anchor="middle" font-family="S,sans-serif" font-weight="800" font-size="34" fill="{INK}">974</text>
<circle cx="23" cy="62" r="2.6" fill="{INK}"/><circle cx="97" cy="62" r="2.600" fill="{INK}"/>'''


def _wrap(body): return f'<svg viewBox="0 0 120 120" width="100%" height="100%" style="display:block;overflow:visible">{body}</svg>'


def picto(kind):
    """kind : meteo-sun | meteo-part | meteo-rain | nouveau | annule | weekend | region | mois | theme-mont | theme-shoe | theme-duo"""
    if kind == 'weekend':     # drapeau à damier
        sq = ''.join(f'<rect x="{38 + i * 16}" y="{22 + j * 15}" width="16" height="15" fill="{INK if (i + j) % 2 == 0 else "#fff"}"/>' for i in range(4) for j in range(3))
        return _wrap(f'<path d="M30 14v94" {_S} stroke-width="7"/>{sq}<rect x="38" y="22" width="64" height="45" fill="none" {_S}/>')
    if kind == 'region':      # repère de carte
        return _wrap(f'<path d="M60 12c-21 0-36 16-36 35 0 25 36 61 36 61s36-36 36-61c0-19-15-35-36-35z" fill="{TAG["region"][0]}" {_S}/><circle cx="60" cy="47" r="13" fill="#fff" {_S}/>')
    if kind == 'mois':        # calendrier
        cells = ''.join(f'<rect x="{30 + i * 22}" y="{60 + j * 20}" width="14" height="12" rx="3" fill="{SUN if (i, j) == (1, 0) else "#c9c4d8"}"/>' for j in range(2) for i in range(3))
        return _wrap(f'<clipPath id="pcal"><rect x="18" y="24" width="84" height="80" rx="11"/></clipPath><g clip-path="url(#pcal)"><rect x="18" y="24" width="84" height="80" fill="#fff"/><rect x="18" y="24" width="84" height="26" fill="{TAG["mois"][0]}"/></g>'
                     f'<rect x="18" y="24" width="84" height="80" rx="11" fill="none" {_S}/><path d="M40 14v20M80 14v20" {_S}/>{cells}')
    if kind == 'theme-mont':  # montagne
        return _wrap(f'<circle cx="92" cy="30" r="11" fill="{SUN}" {_S}/><path d="M8 100 46 32l17 28 14-20 35 60z" fill="#2e7d32" {_S}/><path d="M46 32 35 52l11-5 9 4z" fill="#fff" {_S}/>')
    if kind == 'theme-duo':   # deux coureurs : en équipe
        return _wrap(f'<path d="M56 102c0-19 10-31 23-31s23 12 23 31z" fill="{SUN}" {_S}/><circle cx="79" cy="48" r="14" fill="{SUN}" {_S}/>'
                     f'<path d="M16 102c0-21 11-34 26-34s26 13 26 34z" fill="{TEAL}" {_S}/><circle cx="42" cy="42" r="16" fill="{TEAL}" {_S}/>')
    if kind.startswith('theme'):   # chaussure
        return _wrap(f'<g transform="translate(3 12) scale(3.3)" stroke-linejoin="round"><path d="M3 10q4 3 8 1l3-5 7 7q3 3 8 4 3 1 3 5v3q0 2-2 2H5q-3 0-3-3z" fill="#ff5a36" stroke="{INK}" stroke-width="1.6"/><path d="M2 24h31" stroke="{INK}" stroke-width="1.6"/><path d="M15 13l-3 3M19 16l-3 3" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/></g>')
    if kind == 'meteo-sun':
        body = _sun(60, 60, 22)
    elif kind == 'meteo-rain':
        body = _cloud(-18, '#e8eef2') + _drops(88)
    elif kind.startswith('meteo'):
        body = _sun(46, 46, 17) + _cloud(4)
    elif kind == 'annule':
        body = _bib(True) + f'<g stroke-linecap="round"><path d="M22 22l76 78M98 22l-76 78" stroke="#fff" stroke-width="19"/><path d="M22 22l76 78M98 22l-76 78" stroke="{RED}" stroke-width="11"/></g>'
    else:
        body = _bib() + f'<circle cx="98" cy="28" r="18" fill="{SUN}" {_S}/><path d="M98 19v18M89 28h18" {_S}/>'
    return f'<svg viewBox="0 0 120 120" width="100%" height="100%" style="display:block;overflow:visible">{body}</svg>'


def badge_css(p, t_in=.45, t_out=1.5):
    """p(t) -> pourcentage de la durée de la vidéo. La pastille surgit au-dessus de l'étiquette, puis s'efface quand l'étiquette monte."""
    return f'''#tag .bd{{position:absolute;left:50%;bottom:100%;width:380px;height:380px;margin:0 0 36px -190px;border-radius:50%;background:#fff;border:9px solid {INK};
 box-shadow:0 20px 44px rgba(0,0,0,.4);padding:52px;animation-name:bd}}
@keyframes bd{{0%,{p(t_in)}{{opacity:0;transform:scale(.2) rotate(-25deg)}} {p(t_in)}{{animation-timing-function:cubic-bezier(.3,1.7,.5,1)}} {p(t_in + .5)},{p(t_out)}{{opacity:1;transform:none}}
 {p(t_out)}{{animation-timing-function:ease-in}} {p(t_out + .4)},100%{{opacity:0;transform:scale(.5) translateY(-60px)}}}}'''


def badge(kind):
    return f'<div class="bd anim">{picto(kind)}</div>'
