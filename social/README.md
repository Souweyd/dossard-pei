# Kits réseaux sociaux (Dossard Péi)

Génère chaque semaine les posts Instagram / Facebook (4:5) et TikTok (9:16) à partir de `data.json`
et de captures du site en ligne.

| Jour | Contenu | Fonction du site mise en avant |
|---|---|---|
| 1er du mois | Les courses du mois | Calendrier |
| Lundi | Les courses du week-end (avec les clôtures) | Calendrier / « Ce week-end » |
| Mercredi | Un thème (rotation : première course, relais, gros D+…) | Filtres |
| Vendredi | Une région (rotation : Ouest, Sud, Est, Nord) | Carte |

Le 1er du mois remplace le post du jour s'il tombe un lundi, mercredi ou vendredi. (`reel.py` / `vendredi` : reel du parcours d'une course, plus utilisé dans le planning.)

```
pip install playwright pillow   # Chromium + ffmpeg requis
python social/gen.py semaine 2026-10-26     # date du lundi
python social/gen.py jour 2026-10-22        # le post du jour (lundi, mercredi, vendredi ; rien le 1er du mois)
python social/gen.py mois 2026-11-01        # le post du mois
python social/gen.py jeudi 2026-10-22       # un format précis : lundi | mardi | jeudi | vendredi | mois
```

Sortie : `social/out/<date>-<type>/` (images `instagram/`, `tiktok/`, reel `.mp4`, `legende-instagram.txt`,
`legende-tiktok.txt`) et `social/out/rapport.json`. Ce dossier n'est pas versionné.

Fichiers : `core.py` (données, couleurs, carte, gabarits communs), `gen.py` (formats et rendu),
`capture.py` (captures du site), `reel.py` (vidéo du vendredi), `fonts/` (Inter — OFL, police des visuels depuis la DA « épuré + running » ; Instrument Sans et Saira Condensed conservées).

Automatisation : des tâches planifiées Claude lancent `jour` 30 min avant chaque publication (lundi 6 h 30, mercredi 18 h, vendredi 16 h 30) et `mois` le 1er à 18 h, puis envoient images et légendes.
