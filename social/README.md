# Kits réseaux sociaux (Dossard Péi)

Génère chaque semaine les posts Instagram / Facebook (4:5) et TikTok (9:16) à partir de `data.json`
et de captures du site en ligne.

| Jour | Contenu | Fonction du site mise en avant |
|---|---|---|
| 1er du mois | Les courses du mois | Calendrier |
| Lundi | Les courses du week-end (avec les clôtures) | Calendrier / « Ce week-end » |
| Mardi | Un thème (rotation : première course, relais, gros D+…) | Filtres |
| Jeudi | Une région (rotation : Ouest, Sud, Est, Nord) | Carte |
| Vendredi | Le parcours d'une course (reel 9:16, Reels + TikTok) | Tracé, profil, GPX |

Le 1er du mois remplace le post du jour s'il tombe un lundi, mardi, jeudi ou vendredi.

```
pip install playwright pillow   # Chromium + ffmpeg requis
python social/gen.py semaine 2026-10-26     # date du lundi
python social/gen.py jeudi 2026-10-22       # un seul post : lundi | mardi | jeudi | vendredi | mois
```

Sortie : `social/out/<date>-<type>/` (images `instagram/`, `tiktok/`, reel `.mp4`, `legende-instagram.txt`,
`legende-tiktok.txt`) et `social/out/rapport.json`. Ce dossier n'est pas versionné.

Fichiers : `core.py` (données, couleurs, carte, gabarits communs), `gen.py` (formats et rendu),
`capture.py` (captures du site), `reel.py` (vidéo du vendredi), `fonts/` (Instrument Sans, Saira Condensed — OFL).
