# Étape 1 : rapport sur les sources et les licences

Vérifié le 10 novembre 2026, en lisant les pages officielles et en interrogeant les API.

## 1. Récitation (audio)

**Source retenue :** `api.alquran.cloud`, qui sert un fichier MP3 par verset depuis `cdn.islamic.network`. Les fichiers d'Alafasy y sont les mêmes que ceux d'`everyayah.com` (durées identiques au millième de seconde sur les versets testés), donc `everyayah.com` sert de source de secours.

**Ce que disent les conditions d'alquran.cloud** (mises à jour le 14 juin 2026) :

- les récitations leur sont concédées par les récitateurs « pour une redistribution gratuite et non commerciale » ;
- on peut les écouter, les intégrer et les télécharger « pour un usage personnel et éducatif » ;
- les droits restent aux récitateurs, qui « peuvent demander le retrait du contenu ».

**Conclusion :** la republication sur TikTok n'est ni explicitement autorisée ni interdite. Un compte non commercial, qui cite le récitateur, reste dans l'esprit de ces conditions, mais ce n'est pas une autorisation écrite. `everyayah.com` ne publie aucune licence. Je n'ai trouvé, dans ces sources, aucun récitateur pour lequel la réutilisation serait plus clairement autorisée que pour Alafasy : le choix du récitateur ne change donc rien à ce risque.

**Conséquences pratiques :**

- le compte ne doit pas être monétisé ;
- le récitateur est cité dans chaque légende ;
- si un ayant droit demande un retrait, il faudra retirer les vidéos.

## 2. Texte arabe

- **Source principale :** alquran.cloud, édition `quran-uthmani`, qui vient de Tanzil.net.
- **Licence Tanzil :** Creative Commons Attribution 3.0. Copie à l'identique autorisée, **modification interdite**, source à indiquer clairement avec un lien vers tanzil.net.
- **Seconde source pour le contrôle croisé :** `api.quran.com` (champ `text_uthmani`). Elle est accessible sans clé.
- **Différence constatée :** les deux sources n'écrivent pas l'alif suscrit de la même façon (Quran.com ajoute un trait d'allongement). La comparaison devra neutraliser cette seule différence.

**Conséquence :** ajouter « Texte : Tanzil.net » dans la bio ou la légende.

## 3. Traduction française

- Muhammad Hamidullah est disponible sur alquran.cloud (`fr.hamidullah`) et sur Quran.com (identifiant 31).
- alquran.cloud demande de citer le traducteur par son nom. Tanzil réserve ses traductions à un usage non commercial.

**Conséquence :** déjà couvert, le traducteur est cité dans chaque légende et le compte est non commercial.

## 4. Minutages et basmala

- **Minutage par verset :** un fichier par verset, donc la durée du fichier donne le minutage exact.
- **Basmala, piège confirmé :** pour le verset 1 d'une sourate (testé sur 112:1), le **texte** d'alquran.cloud contient la basmala, mais le **fichier audio** ne la contient pas (2,98 s). Le script devra retirer la basmala du texte du verset 1 et, pour la faire entendre, insérer avant lui le fichier audio de 1:1 (6,09 s) sur son propre écran.
- **Minutages mot à mot :** Quran.com les fournit pour Alafasy, mais calés sur un fichier par sourate, différent des nôtres. La durée du verset 1:1 y est presque identique (6,090 s contre 6,087 s), ce qui laisse penser que c'est le même enregistrement. À confirmer verset par verset avant de s'en servir ; sinon, répartition au prorata des lettres.

## 5. TikTok : le point bloquant

Lu dans la documentation officielle (Content Posting API et « Content Sharing Guidelines ») :

- Une application **non auditée** ne peut publier qu'en visibilité « moi uniquement », et le compte doit être **privé** au moment de la publication.
- Pour lever cette limite, il faut un audit. Or les règles d'audit citent comme **non acceptable** : « un outil utilitaire pour téléverser du contenu sur le ou les comptes que vous ou votre équipe gérez ». C'est exactement notre cas : l'audit sera très probablement refusé.
- La couverture ne peut être qu'une image de la vidéo (`video_cover_timestamp_ms`), pas un fichier séparé.
- Je n'ai trouvé aucune fonction de playlist dans cette API.
- Plafond d'environ 15 publications par jour et par compte, sans effet pour nous.

**Conclusion :** la publication publique entièrement automatique par l'API officielle n'est pas réaliste pour ce projet. Trois voies restent possibles :

1. **Publication manuelle quotidienne (recommandée).** Le robot prépare chaque jour la vidéo et la légende ; vous publiez depuis votre téléphone, en une minute environ.
2. **Brouillon envoyé dans l'application.** L'API a un second mode (`video.upload`) qui dépose la vidéo dans vos notifications TikTok, où vous terminez la publication. Je n'ai pas pu vérifier s'il est utilisable sans audit ; il faudra le tester avec une application développeur.
3. **Tenter l'audit quand même**, en sachant que le refus est probable.

## 6. Clips vidéo

Les API de Pexels et de Pixabay répondent et attendent une clé. Je n'ai pas encore relu leurs licences ni testé de recherche : ce sera fait à l'étape des clips, une fois les clés fournies.

## 7. Décisions attendues

1. **Récitateur :** garder Mishary Rashid Alafasy en acceptant le risque décrit au point 1 ?
2. **Publication :** partir sur la publication manuelle quotidienne (voie 1), avec un test de la voie 2 plus tard ?

## 8. Décisions prises le 10 novembre 2026

- **Récitateur :** Mishary Rashid Alafasy, aux conditions du point 1.
- **Publication :** elle doit rester automatique. La voie retenue est Buffer, un service de planification déjà audité par TikTok :
  - son API officielle est ouverte à toutes les formules, y compris la gratuite (source : centre d'aide de Buffer) ;
  - elle crée des publications vidéo pour TikTok et permet de choisir l'image de couverture par un décalage dans la vidéo ;
  - la vidéo doit être accessible par une adresse publique, Buffer ne recevant pas de fichier directement ;
  - la formule gratuite limite à 3 comptes et 10 publications en attente par compte, ce qui suffit pour une vidéo par jour.
- **Reste à vérifier par un essai réel :** que la formule gratuite publie bien en public sur TikTok sans intervention, et ses quotas d'appels. Le plan B manuel reste en secours.
