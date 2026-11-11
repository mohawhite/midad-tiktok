# Midad

Robot qui prépare chaque jour une vidéo de récitation du Coran pour le compte TikTok `@midad.coran` : une sourate courte entière, ou une partie d'une sourate longue.

Le cahier des charges est dans `docs/prompt.md`, le rapport sur les sources et les licences dans `docs/rapport-sources.md`.

## État du projet

| Élément | État |
|---|---|
| Texte, traduction, audio verset par verset | fait |
| Rendu de la vidéo (miniature, accroche, versets, logo) | fait |
| Découpage des sourates longues et des versets longs | fait |
| Planning (vendredi Al-Kahf, Ramadan) et fichier de suivi | fait |
| Légende | fait |
| Contrôles avant publication, dont la reconnaissance vocale | fait |
| Exécution quotidienne sur GitHub Actions et alertes | fait, désactivée par défaut |
| Clips de fond Pexels et Pixabay | fait |
| Publication automatique par Buffer | écrite, à tester avec la clé |

Tant que la publication par Buffer n'est pas branchée, le robot applique le plan B : il remet la vidéo, la couverture et la légende, et ouvre une alerte pour une publication à la main.

## Installation

```bash
pip install -r requirements.txt
```

```bash
python -m playwright install chromium
```

FFmpeg doit être installé sur la machine.

## Lancer un essai

Produire la vidéo prévue pour une date, sans rien publier ni modifier le suivi :

```bash
python -m midad.cli jour --date 2026-11-11 --dry-run
```

Produire un passage précis :

```bash
python -m midad.cli essai --sourate 2 --versets 282-282 --partie 38 --total 40
```

Les fichiers sont écrits dans `out/` : `video.mp4`, `couverture.png`, `legende.txt`.

Lancer les tests :

```bash
python -m pytest -q
```

## Réglages

Tout se règle dans deux fichiers, sans toucher au code :

- `config.yaml` : récitateur, traducteur, heure, durées de découpage, seuil de la reconnaissance vocale, hashtags, ordre des sourates, passages du Ramadan.
- `sourates.yaml` : nom affiché et mots-clés de clips pour chacune des 114 sourates.
- `clips_exclus.yaml` : clips à ne jamais utiliser, par identifiant.

Changer de récitateur après le début modifie les durées : il faut alors vider la rubrique `decoupages` de `suivi.json` pour les sourates pas encore commencées.

## Exécution quotidienne

Le workflow `.github/workflows/quotidien.yml` tourne chaque jour à 15 h UTC, mais seulement si la variable de dépôt `MIDAD_ACTIF` vaut `true` (Settings › Secrets and variables › Actions › Variables). Sans cette variable, rien ne se passe.

Il peut aussi être lancé à la main depuis l'onglet Actions, avec une case « Essai » cochée par défaut.

Secrets attendus (Settings › Secrets and variables › Actions › Secrets) :

| Secret | Usage |
|---|---|
| `PEXELS_API_KEY` | recherche des clips de fond |
| `PIXABAY_API_KEY` | recherche des clips de fond |
| `BUFFER_API_KEY` | publication automatique sur TikTok |

## Quand une alerte arrive

Le robot ouvre une issue GitHub, et GitHub envoie un e-mail.

- **« Vidéo du … à publier à la main »** : ouvrez le lien, téléchargez l'archive, publiez la vidéo sur TikTok avec la légende fournie, puis fermez l'issue. Le passage est déjà noté comme traité.
- **« Échec de la vidéo du … »** : rien n'a été publié et le suivi n'a pas bougé. Le même passage sera repris le lendemain. Le journal joint indique l'étape en cause.

## Contrôles avant publication

Une vidéo n'est remise que si tous ces contrôles passent :

1. le texte arabe de chaque verset est identique sur alquran.cloud et Quran.com ;
2. le nombre et les numéros de versets correspondent à la table de référence ;
3. chaque fichier audio est le bon, non vide, de durée plausible ;
4. la reconnaissance vocale de chaque verset ressemble assez au texte affiché ;
5. la durée des écrans de texte est égale à celle de l'audio ;
6. la vidéo est en 1080 × 1920, avec une piste audio et la durée attendue ;
7. aucun texte ne déborde des zones masquées par TikTok.

## Crédits

- Texte arabe : Tanzil.net (Creative Commons Attribution 3.0), via alquran.cloud.
- Traduction : Muhammad Hamidullah.
- Récitation : Mishary Rashid Alafasy, via alquran.cloud.
- Polices : Aref Ruqaa, Amiri Quran et Inter (licence OFL).
