# Prompt Claude Code : automatisation du compte TikTok « Midad »

Copie tout ce qui suit dans Claude Code, dans un dépôt GitHub vide et privé.

---

## Objectif

Construis un projet qui crée et publie chaque jour, sans intervention de ma part, une vidéo TikTok de récitation du Coran pour le compte **Midad** (`@midad.coran`). Une vidéo contient une sourate courte entière ou une partie d'une sourate longue. Le projet ne concerne que TikTok.

Tout doit tourner gratuitement sur GitHub Actions, sans dépendre de mon ordinateur.

## Façon de travailler

Avance par étapes et arrête-toi à la fin de chacune pour que je valide :

1. Vérification des sources (audio, texte, licences) et rapport écrit, avant d'écrire le reste du code.
2. Génération en local d'une vidéo d'exemple (Al-Fatiha) que je regarde.
3. Suivi, planning, légende et vérifications automatiques, avec tests.
4. Publication TikTok et plan B.
5. Workflow GitHub Actions et alertes.

N'active jamais la publication réelle sans mon accord explicite. Tant que je ne l'ai pas donné, tout tourne en mode `--dry-run` (la vidéo est produite, rien n'est publié).

Ne mets aucune clé ni aucun jeton dans le dépôt : tout passe par les secrets GitHub Actions. Dis-moi précisément quels secrets créer et comment obtenir chaque clé.

## Choix techniques imposés

- Python 3.12 et FFmpeg pour le montage.
- Les calques de texte sont rendus en PNG transparents à partir de gabarits HTML avec Playwright (Chromium), puis assemblés par FFmpeg. C'est la seule méthode que j'accepte pour l'arabe : elle garantit la mise en forme correcte des lettres et des voyelles. Ne dessine jamais le texte arabe avec le filtre `drawtext` de FFmpeg.
- Polices libres (licence OFL) placées dans le dépôt : **Aref Ruqaa Bold**, **Amiri Quran**, **Inter** (400 et 500).
- Configuration dans des fichiers lisibles (`config.yaml`, `sourates.yaml`) : je dois pouvoir changer le récitateur, l'heure, les hashtags et les mots-clés sans toucher au code.

## 1. Audio et texte

- **Récitateur :** un seul pour tout le compte. Choix provisoire : Mishary Rashid Alafasy.
- **Sources à évaluer :** `api.alquran.cloud` (audio verset par verset `ar.alafasy`, texte `quran-uthmani`, traduction `fr.hamidullah`), l'API de Quran.com / Quran Foundation (texte Uthmani, minutages mot à mot) et `everyayah.com` (un MP3 par verset).
- **Licence :** avant tout, lis les conditions d'utilisation de chaque source et celles des enregistrements du récitateur, puis écris-moi un rapport : ce qui est explicitement autorisé pour une republication sur TikTok, ce qui ne l'est pas, ce qui reste flou. Si la réutilisation des enregistrements d'Alafasy n'est pas clairement autorisée, propose-moi les récitateurs pour lesquels elle l'est, et attends ma décision. Ne suppose pas qu'une API gratuite vaut autorisation.
- **Minutages :** utilise un fichier audio par verset. La vidéo enchaîne ces fichiers, et le minutage de chaque verset vient de la durée réelle de son fichier (mesurée avec `ffprobe`). Aucun verset n'est donc jamais coupé.
- **Basmala :** traite-la de façon cohérente entre l'audio et le texte. Selon les sources, elle est incluse dans le verset 1 ou séparée. Elle doit s'afficher sur son propre écran quand elle est récitée, et jamais être affichée sans être récitée (ni l'inverse). Cas particuliers : Al-Fatiha (c'est le verset 1) et At-Tawba (aucune basmala).
- **Aucun ajout sonore :** pas de musique, pas d'effet, pas de normalisation agressive. Seulement un fondu de 0,3 s au début et à la fin.
- **Texte arabe :** écriture Uthmani complète avec toutes les voyelles, jamais modifiée, jamais tronquée.
- **Traduction :** Muhammad Hamidullah uniquement.
- **Cache :** garde en cache local les réponses d'API et les fichiers audio pendant l'exécution.

## 2. Découpage

- Une sourate dont la récitation dure 3 minutes ou moins fait une seule vidéo.
- Une sourate plus longue est découpée en parties de 1 à 3 minutes, toujours sur une frontière de verset. Si un verset seul dépasse 3 minutes, il forme une partie à lui seul.
- Le découpage de chaque sourate est calculé une fois, puis figé dans le fichier de suivi, pour que « partie 3/40 » ne change jamais en cours de route.
- **Verset long à l'écran :** un verset qui ne tient pas en 3 lignes d'arabe à la taille du modèle est découpé en plusieurs écrans successifs. Coupe sur les signes de pause coraniques ou, à défaut, entre deux mots, et découpe la traduction en autant de morceaux cohérents. Synchronise chaque écran avec les minutages mot à mot de Quran.com s'ils existent pour ce récitateur ; sinon, répartis la durée au prorata du nombre de lettres. Ne réduis jamais la taille du texte pour faire tenir un verset.

## 3. Modèle visuel à reproduire

Format : vertical 9:16, 1080 × 1920, 30 images par seconde, H.264 + AAC.

Couleurs : fond noir `#000000`, texte blanc `#FFFFFF`. Rien d'autre.

Zones à laisser libres de tout texte : 160 px en haut, 480 px en bas, 140 px à gauche et à droite. Le texte est centré dans la zone restante (800 px de large).

**Miniature (0 à 0,5 s)** — fond noir uni, contenu regroupé dans la bande centrale de 1440 px de haut :
- en haut : « SOURATE 1 », Inter 500, 40 px, capitales, interlettrage 0,3 em ;
- au centre : nom de la sourate en arabe, Aref Ruqaa Bold, 250 px ; trait blanc de 72 × 3 px ; nom latin en capitales, Inter 500, 60 px, interlettrage 0,4 em ; « Partie 1/1 », Inter 400, 48 px ;
- en bas : logo (voir ci-dessous) en petit.
- Cette image est aussi exportée en PNG et sert de couverture (`video_cover_timestamp_ms = 0`).

**Accroche (0,5 à 3 s environ)** — sur le fond vidéo :
- nom de la sourate en arabe, Aref Ruqaa Bold, 230 px ;
- trait blanc 72 × 3 px ;
- nom latin en capitales, Inter 500, 54 px, interlettrage 0,4 em ;
- « Versets 1 à 7 », Inter 400, 44 px.
- La récitation commence pendant l'accroche si nécessaire : l'accroche ne doit pas ajouter de silence de plus de 1 s.

**Corps** — sur le fond vidéo :
- en haut de la zone libre : repère « AL-FATIHA · 1:2 », Inter 500, 32 px, interlettrage 0,12 em ;
- au centre : verset en arabe, Amiri Quran, 84 px, interligne 2, direction droite-à-gauche ; 56 px plus bas, traduction, Inter 400, 46 px, interligne 1,4 ;
- en bas de la zone libre : barre de progression de 800 × 4 px, piste blanche à 30 % d'opacité, remplissage blanc, qui avance sur la durée totale de la vidéo ;
- chaque écran de texte apparaît à l'instant exact où le verset commence, avec un fondu de 0,3 s à l'apparition et à la disparition ;
- aucune translittération.

**Fin (2 s)** — fond vidéo assombri à 25 % d'opacité, logo centré :
- « مداد » en Aref Ruqaa Bold, 150 px ; trait blanc 40 × 2 px ; « MIDAD », Inter 500, 26 px, interlettrage 0,5 em.

**Logo :** le mot « مداد » en Aref Ruqaa Bold, un fin trait, puis « MIDAD » en capitales espacées. Blanc sur noir.

## 4. Fond vidéo

- Clips gratuits et libres de droits pris sur Pexels et Pixabay, via leurs API officielles.
- `sourates.yaml` associe à chaque sourate une liste de mots-clés (mer, ciel, montagnes, pluie, désert, nuit étoilée, forêt, nuages, etc.), avec une liste par défaut. Remplis ce fichier pour les 114 sourates en te fondant sur leurs thèmes.
- Uniquement des paysages et des éléments naturels. **Aucune personne, aucun visage, aucun animal.** Pour cela : n'utilise que des mots-clés de paysages ; rejette tout clip dont le titre, les tags ou la description contiennent un terme d'une liste d'exclusion (personne, homme, femme, enfant, visage, main, silhouette, animal, oiseau, cheval, etc., en français et en anglais) ; tiens un fichier `clips_exclus.yaml` où je peux bannir un clip par son identifiant.
- Clips verticaux ou recadrables en 9:16 sans perte, d'au moins 1080 px de large.
- Affichage à 50 % d'opacité sur fond noir, son du clip supprimé.
- Le fond change uniquement au début d'un verset, avec un fondu enchaîné d'environ 1 s. Un clip reste à l'écran entre 8 et 20 s ; s'il est trop court, il est mis en boucle proprement plutôt que coupé au milieu d'un verset.
- Un clip utilisé la veille n'est jamais réutilisé le lendemain (historique dans le fichier de suivi).
- Enregistre pour chaque vidéo la liste des clips utilisés, avec auteur et lien, dans le fichier de suivi.

## 5. Planning et fichier de suivi

- Une vidéo par jour, à heure fixe. Heure provisoire : 18 h 30, heure de Paris (paramètre dans `config.yaml`). Tiens compte du fait que le cron de GitHub Actions est en UTC, ne suit pas le changement d'heure et peut démarrer avec du retard.
- Ordre : Al-Fatiha, puis Al-Ikhlas, Al-Falaq, An-Nas, puis le reste de Juz Amma (sourates 78 à 114), puis les autres sourates. L'ordre complet est dans un fichier que je peux modifier.
- **Vendredi :** une partie de sourate Al-Kahf, dans l'ordre, d'un vendredi à l'autre. Cela n'avance pas la progression principale.
- **Ramadan :** pendant le mois de Ramadan (calculé avec une bibliothèque de calendrier hégirien), une liste de passages dédiés définie dans un fichier de configuration. Propose-moi cette liste, je la validerai.
- `suivi.json`, versionné dans le dépôt, garde : ce qui a été publié (date, sourate, versets, partie, identifiant TikTok ou mention « publication manuelle »), le découpage figé de chaque sourate, la position dans chaque progression, les clips utilisés. Il est mis à jour et commité par le workflow **uniquement après** une publication réussie ou une remise en plan B.
- Aucun passage n'est jamais répété ni sauté. Si l'exécution d'un jour échoue, le lendemain reprend le même passage. Deux exécutions le même jour ne publient pas deux fois.

## 6. Légende

Générée automatiquement, sur ce modèle :

```
Al-Baqara, partie 3/40 (versets 17 à 24)
Récitation : Mishary Rashid Alafasy
Traduction : Muhammad Hamidullah
#coran #quran #recitation #albaqara
```

Trois à cinq hashtags, dont un au nom de la sourate. Respecte la limite de longueur de TikTok.

## 7. Vérification avant publication

Avant toute publication, le script vérifie que le texte affiché correspond bien au verset récité. Au moindre doute, **la vidéo n'est pas publiée** et je suis prévenu.

Contrôles obligatoires :

1. Le texte arabe de chaque verset est identique dans deux sources indépendantes, après normalisation Unicode.
2. Le nombre de versets de la sourate et les numéros de versets correspondent à une table de référence intégrée au dépôt.
3. Chaque fichier audio correspond au bon numéro de sourate et de verset, n'est pas vide et a une durée plausible par rapport à la longueur du verset.
4. Reconnaissance vocale de l'audio avec un modèle libre qui tourne gratuitement sur GitHub Actions (par exemple Whisper), puis comparaison avec le texte du verset sans voyelles. En dessous d'un seuil de ressemblance réglable, la vidéo est bloquée. Calibre ce seuil sur des versets réels et montre-moi les résultats.
5. La somme des durées des écrans de texte est égale à la durée de l'audio, à 50 ms près.
6. La vidéo finale est bien en 1080 × 1920, a une piste audio, et sa durée correspond à celle attendue.
7. Contrôle visuel automatique : capture d'une image par écran de texte, et vérification qu'aucun texte ne déborde de la zone libre.

## 8. Publication

- **Voie principale :** API officielle de TikTok (Content Posting API, publication directe). Explique-moi pas à pas comment créer l'application développeur, quelles autorisations demander et comment obtenir le premier jeton. Gère le renouvellement automatique du jeton d'accès, y compris la mise à jour du secret GitHub quand le jeton de renouvellement change.
- Vérifie dans la documentation actuelle de TikTok les limites réelles et dis-les-moi clairement, notamment : la restriction des applications non auditées à des publications privées, la possibilité ou non de définir une couverture personnalisée, et la possibilité ou non d'ajouter une vidéo à une playlist par l'API.
- **Playlists :** une playlist par sourate longue ou par Juz. Si l'API ne le permet pas, indique-moi dans l'alerte quotidienne à quelle playlist ajouter la vidéo à la main.
- **Plan B**, utilisé automatiquement si l'API n'est pas accessible ou refuse la publication : le workflow dépose la vidéo, la couverture PNG et la légende dans un endroit d'où je peux les télécharger sur mon téléphone (artefact du workflow ou release privée), puis me prévient avec le lien. Le passage est noté « publication manuelle en attente » et n'est pas republié le lendemain.

## 9. Exécution quotidienne, erreurs et alertes

- Un workflow GitHub Actions planifié, plus un déclenchement manuel avec options (`dry-run`, forcer une sourate, forcer le plan B).
- Chaque appel réseau réessaie 4 fois avec une attente croissante avant d'abandonner.
- Journal détaillé de chaque exécution, conservé comme artefact du workflow.
- **Alertes :** en cas d'échec, de vérification bloquante ou de plan B, le workflow ouvre une issue GitHub qui m'est assignée (GitHub m'envoie alors un e-mail), avec la cause, l'étape concernée et le lien vers le journal. Pas d'alerte quand tout va bien, sauf un récapitulatif hebdomadaire.
- Le workflow ne doit jamais publier une vidéo partielle ou non vérifiée.

## 10. Livrables

- Le code, organisé en modules clairs (sources, découpage, clips, rendu, vérification, légende, publication, suivi).
- Des tests automatiques pour le découpage, la basmala, la légende, le suivi (ni répétition ni saut) et le planning (vendredi, Ramadan).
- Un `README.md` en français : installation, liste des secrets, comment lancer un essai, comment changer le récitateur ou l'heure, que faire quand je reçois une alerte.
- Une vidéo d'exemple d'Al-Fatiha et une d'une partie d'Al-Baqara (avec un verset long découpé en plusieurs écrans), produites en `--dry-run`.

À la fin de chaque étape, dis-moi ce qui a été testé et passe, ce qui n'a pas pu être testé, et ce qui reste à décider de mon côté.
