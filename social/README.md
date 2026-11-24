# Kits réseaux sociaux (Dossard Péi)

Génère chaque semaine les posts Instagram / Facebook (4:5) et TikTok (9:16) à partir de `data.json`
et de captures du site en ligne.

| Jour | Contenu | Fonction du site mise en avant |
|---|---|---|
| 1er du mois | Les courses du mois | Calendrier |
| Lundi | Les courses du week-end (`post_lundi.py`, style des stories : île et cadres reliés aux courses, une slide par course encore ouverte) | Calendrier / « Ce week-end » |
| Mercredi | Un thème (rotation : première course, relais, gros D+… ; le multisport est retiré depuis le 24/11/2026, `off=True` dans `gen.THEMES`) | Filtres |
| Vendredi | Une région (rotation : Ouest, Sud, Est, Nord) | Carte |
| Vendredi soir | Story vidéo « Météo des courses » du week-end (`meteo.py`) | Météo des fiches |

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

Fichiers : `charte.py` (charte graphique des posts du fil : décor en 4 ambiances, gabarits couverture / liste / course / capture / fin), `core.py` (données, couleurs, carte), `gen.py` (contenu de chaque post et rendu),
`capture.py` (captures du site), `reel.py` (vidéo du vendredi), `fonts/` (Inter — OFL, police des visuels depuis la DA « épuré + running » ; Instrument Sans et Saira Condensed conservées).

Automatisation : des tâches planifiées Claude lancent `jour` 30 min avant chaque publication (lundi 6 h 30, mercredi 18 h, vendredi 16 h 30) et `mois` le 1er à 18 h, puis envoient images et légendes.

## Charte : drapeau de La Réunion (Lo Mahavéli)
Tout dessin du drapeau (logo, dossard, bandeau) : fond bleu marine, volcan rouge en bas au centre et **exactement 5 rayons jaunes** qui partent du sommet du volcan, comme dans `favicon.svg`. Jamais 6 rayons, jamais des rayons partant du bas du bandeau.

## Reels des posts du fil
`reel_post.py theme|region|mois <jour>` : reel motion design (1080×1920, 11 à 16 s, bruitages) avec les mêmes courses que le carrousel du jour : pastille et étiquette à la couleur du type (thème orange, région bleue, mois violet), la carte se précise (zoom sur la région), un point par course dans l'ordre des dates avec sa fiche en bas, puis le total et le logo. Sortie : `social/out/reel/reel-<type>-<jour>.mp4` et `…-couverture.jpg`. Lancé par les tâches du mercredi, du vendredi et du 1er du mois après l'envoi du carrousel (le lundi garde son reel 3D, dépôt dossard-pei-posts).
Depuis le 24/11/2026, `theme` suit le déroulé de `reel_theme.py` (16 à 23 s) : accroche en typo cinétique avec le chiffre fort de la couverture (compteur, trait jaune, Sam et/ou Ana avec leur bulle), pastille et étiquette (couverture à 3,2 s), une carte crème par course (8 au plus, puis « + N autres ») avec flou de mouvement, compteurs km et D+ de l'épreuve du thème, profil d'altitude qui se dresse (`profiles.json`) ou jauge s'il n'y en a pas, puis les barres qui se dressent, le total et le logo. `region` et `mois` gardent le déroulé ci-dessus.

## Stories
Chaque vidéo s'ouvre sur une pastille ronde (pictogramme) et une étiquette à la couleur du type, pour les distinguer sur la grille (`picto.py`) : Météo = soleil / nuage / pluie selon le temps dominant, étiquette jaune ; Nouveau dossard = dossard « + », étiquette turquoise ; Course annulée = dossard barré, étiquette rouge, île grise. Chaque script écrit aussi l'image de couverture (`…-couverture.jpg`, image à 1,2 s).
- `nouveau.py <id>…` : story vidéo « Nouveau dossard » (MP4 1080×1920, 11 s : nom de la course sur la carte floutée, zoom sur le lieu de départ, puis carte de la course avec une ligne par épreuve), seulement pour une fiche dont les inscriptions sont ouvertes ou dont la date d'ouverture est annoncée (pas « À venir » sans date, pas complète).
- `annule.py <id> [motif] [info]` : story vidéo « Course annulée » (MP4 de 9 s avec bruitages : l'affiche arrive en couleur, le tampon ANNULÉE tombe et elle passe en gris, puis infos et logo), plus `<id>.jpg` (image fixe).
- `meteo.py <vendredi>` : story vidéo « Météo des courses » (samedi et dimanche, 8 courses au plus) : vue d'ensemble de l'île, un trait part de chaque course vers son cadre météo ; `rec.py` enregistre la vidéo image par image, `sfx.py` ajoute les bruitages (synthétisés, sans fichier son externe).

## Légendes
Pas d'appel à commenter, taguer ou enregistrer. Toujours ces 4 hashtags : #trail #run #iledelareunion #reunionisland.
