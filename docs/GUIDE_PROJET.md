# Guide complet du projet — tout comprendre, du début à la fin

Ce document explique le projet dans son ensemble, en partant de zéro. Il ne suppose aucune
connaissance préalable en intelligence artificielle ou en programmation : chaque terme
technique est défini au moment où il apparaît. L'objectif est que n'importe qui — collègue,
encadrant, futur stagiaire qui reprend le projet — puisse le lire et comprendre exactement ce
qui a été construit, pourquoi, comment, et ce qu'il reste à faire.

Pour les instructions techniques (installation, commandes à lancer), voir le
[README.md](../README.md) à la racine du projet. Ce guide-ci est le « pourquoi » et le
« comment ça marche » ; le README est le « comment l'utiliser ».

---

## 1. Le projet, en une phrase

On prend l'enregistrement brut d'une réunion de formation (une vidéo Teams, avec quelqu'un
qui parle, des diapositives partagées à l'écran, parfois des questions) et on le transforme,
automatiquement grâce à l'intelligence artificielle, en un vrai cours en ligne structuré —
avec des chapitres, une narration propre, et des visuels animés — comparable à ce qu'on
trouve sur Coursera.

## 2. Le problème de départ

S2M organise régulièrement des formations internes (par exemple sur la cybersécurité),
enregistrées via Microsoft Teams. Le problème : un enregistrement de réunion n'est **pas**
conçu pour être regardé après coup comme un cours. C'est la capture brute d'un événement en
direct :

- il y a des silences, des hésitations (« euh... », « donc voilà... »), des répétitions ;
- la vidéo montre soit la fenêtre de la réunion (visages des participants), soit une
  diapositive statique — rien de conçu pour l'apprentissage ;
- il n'y a aucune structure : pas de chapitres, pas de moyen de revenir directement sur un
  point précis sans tout re-regarder.

Pourtant, le contenu pédagogique **est bien là**, il est juste mal emballé.

## 3. Ce qu'on veut obtenir à la fin

Un point essentiel, à ne jamais perdre de vue :

> **Ce projet n'est PAS un résumé.** L'objectif n'est pas de réduire une vidéo d'une heure à
> une vidéo de dix minutes. Si la formation originale dure une heure, le cours transformé
> peut aussi durer environ une heure. Ce qui change, c'est la présentation : la vidéo est
> découpée en chapitres logiques (par sujet, pas par horloge), la narration est propre et
> claire, les visuels sont des animations explicatives (et non plus une capture de réunion),
> et l'apprenant peut naviguer directement vers le chapitre qui l'intéresse. Le contenu
> pédagogique, lui, reste intégralement préservé.

Le résultat final visé : à partir d'un fichier vidéo brut, obtenir un cours composé de
plusieurs chapitres, chacun avec sa propre vidéo animée et sa narration, plus une table des
matières pour naviguer entre eux.

## 4. Vue d'ensemble : comment le système fonctionne

Le système est un **pipeline** : une chaîne d'étapes, chacune prenant le résultat de la
précédente et le transformant un peu plus, jusqu'au résultat final. Cinq grandes étapes :

1. **Extraire la matière première** — sortir tout ce qu'on peut de la vidéo : le son, le
   texte parlé, le texte affiché à l'écran, les changements visuels.
2. **Comprendre le sens** — une IA lit tout ça (ce qui est dit ET ce qui est montré) et
   identifie les sujets abordés, pour découper la vidéo en chapitres logiques.
3. **Décider quoi garder** — trier ce qui doit être conservé (les explications, les
   exemples) de ce qui doit être nettoyé (hésitations, répétitions, silences).
4. **Préparer la transformation** — pour chaque morceau de contenu conservé, décider quel
   visuel l'accompagnera (une animation, un schéma, une liste...).
5. **Assembler** — produire la vidéo finale : narration + visuels + transitions, chapitre par
   chapitre.

Les sections suivantes détaillent chacune de ces étapes, dans l'ordre où elles ont
effectivement été construites pendant le stage.

---

## 5. Le voyage, étape par étape

### 5.1 Étape 1 — Extraire la matière première (« ingestion »)

**Ce qu'on fait :** à partir du fichier vidéo, on extrait séparément l'audio, on le
transcrit en texte, on identifie qui parle, on repère les moments où l'image à l'écran
change, et on lit le texte visible sur les diapositives.

**Extraction et amélioration audio.** Le son est d'abord séparé de l'image (on n'a besoin
que du son pour la suite). Ensuite, il est **amélioré** : le bruit de fond est réduit et le
volume est uniformisé sur toute la durée (certains passages étaient plus forts ou plus
faibles que d'autres). Cette étape rend la transcription plus fiable, et sert aussi plus
tard pour la narration finale.

**Transcription automatique (ASR — *Automatic Speech Recognition*).** C'est la technologie
qui transforme la parole en texte écrit, avec un horodatage précis (on sait exactement à
quelle seconde chaque phrase a été dite). Le modèle utilisé (*faster-whisper*) tourne
directement sur l'ordinateur, sans carte graphique ni connexion internet — une contrainte du
projet (voir le cahier des charges : pas de budget, pas de GPU disponible).

**Diarisation.** C'est le nom technique pour « identifier qui parle, et quand ». Utile pour
un enregistrement de réunion avec plusieurs intervenants. (Cette étape reste optionnelle
dans le projet actuel : sans configuration spécifique, tout le monde est simplement étiqueté
comme un seul locuteur, ce qui ne bloque pas le reste du pipeline.)

**Détection de scènes visuelles.** Le système repère les moments où l'image affichée change
nettement (changement de diapositive, passage à l'écran partagé, etc.), et en extrait une
image représentative.

> **Une surprise en cours de route :** on pourrait penser que chaque changement de sujet dans
> la formation correspond à un changement d'image à l'écran. Ce n'est pas vrai. Sur la vraie
> vidéo de test (1h35), une seule « scène visuelle » a duré plus de **30 minutes** sans aucun
> changement d'image, alors que l'intervenant abordait plusieurs sujets différents pendant ce
> temps. Conclusion : on ne peut pas se fier aux coupures d'image pour découper la vidéo en
> chapitres — il faut comprendre le **sens** de ce qui est dit (voir étape 2).

**OCR (*Optical Character Recognition*, reconnaissance de texte dans une image).** Pour
chaque image représentative extraite, le système lit automatiquement le texte visible
(titre de diapositive, listes à puces, schémas annotés). Ce texte complète la transcription :
parfois, une information n'est écrite QUE sur la diapositive, jamais dite à voix haute.

**Résultat de cette étape :** une liste de « scènes », chacune avec sa transcription, son
texte OCR, une image, et ses horodatages — la matière première brute, mais déjà bien
organisée.

### 5.2 Étape 2 — Comprendre le sens et découper en chapitres

C'est ici qu'intervient une intelligence artificielle générative pour la première fois de
façon substantielle.

**Le découpage par sens, pas par horloge.** Plutôt que de couper la vidéo toutes les 10
minutes (arbitraire) ou à chaque changement d'image (on vient de voir que ça ne marche pas),
le système compare le **sens** de chaque minute de discours à celui de la minute suivante.
Concrètement : un modèle d'IA (appelé *Sentence-Transformers*) convertit chaque segment de
texte en une liste de nombres (un *embedding*) qui représente son sens — un peu comme une
empreinte digitale numérique du sujet abordé. Quand cette empreinte change beaucoup d'un
segment à l'autre, c'est le signe qu'on a changé de sujet : une frontière de chapitre.

Ce réglage a demandé plusieurs essais (voir section 6, « Les obstacles »).

**Le « point critique » du projet : comprendre le son ET l'image ensemble.** Une fois les
chapitres délimités, pour chacun d'eux, un **LLM** (*Large Language Model* — un modèle
d'IA entraîné à comprendre et produire du texte, comme celui qui répond aux questions dans
ChatGPT) génère un titre, un résumé et des points clés. La particularité importante : ce
modèle reçoit **à la fois** la transcription **et** les images de la vidéo — pas seulement le
texte OCR. Il peut donc « voir » un schéma ou un diagramme et en tenir compte, même si rien
de ce qui y est écrit n'a été prononcé à voix haute. C'est exactement le défi que le cahier
des charges désigne comme le point critique du projet.

**Résultat concret sur la vraie vidéo de test (1h35, formation cybersécurité) :** 17
chapitres cohérents, de 3 à 10 minutes chacun, avec des titres comme « Impacts financiers et
mesures de protection en cybersécurité » ou « Cadre réglementaire et bonnes pratiques ».

### 5.3 Étape 3 — Décider quoi garder, avec la vraie voix

Cette étape a changé de méthode en cours de route (voir section 6 pour l'histoire complète).

Le cahier des charges propose trois façons de gérer la narration du cours transformé :
1. garder la voix originale de l'intervenant (nettoyée) ;
2. générer une voix de synthèse (une IA qui « lit » un texte réécrit) ;
3. un mélange des deux.

Après avoir testé et validé l'option 2 (voix de synthèse, via un outil appelé *TTS* —
*Text-to-Speech*), le choix s'est porté sur l'**option 1** : garder la vraie voix de
l'intervenant. Voici comment :

**Classification « garder » / « couper ».** Chaque petit morceau de transcription (quelques
secondes) est examiné par une IA, qui décide s'il doit être **gardé** (une explication, un
exemple, un fait technique important) ou **coupé** (une hésitation, une répétition, un
silence, une digression). Cette classification suit exactement les trois catégories définies
dans le cahier des charges : contenu à préserver, contenu à nettoyer, contenu à traiter au
cas par cas.

**Découpage et recollage audio.** Une fois qu'on sait quels morceaux garder, le système va
chercher, directement dans l'enregistrement audio amélioré, les portions de son
correspondantes, et les recolle bout à bout — sans jamais réécrire ce qui a été dit. Le
résultat est une narration qui utilise la vraie voix de l'intervenant, débarrassée des
hésitations et longueurs, mais fidèle mot pour mot à ce qui a réellement été dit.

### 5.4 Étape 4 — Prévoir les visuels (storyboard)

Pour chaque petit morceau de narration ainsi obtenu (environ 20 secondes chacun), une IA
propose un habillage visuel : quel **type** de visuel utiliser (une liste à puces, une rangée
d'icônes, un diagramme qui montre un processus, une comparaison, un chiffre clé mis en
avant, une citation, une frise chronologique...), une description de ce qui doit s'animer à
l'écran, et un court texte à afficher. C'est le plan de production — le "storyboard" — qui
servira de base à l'étape suivante.

**Statut :** cette étape est prototypée et validée (elle fonctionne bien sur les chapitres
testés), mais n'a pas encore été exécutée sur l'ensemble des 17 chapitres de la vidéo
complète.

### 5.5 Étape 5 — À venir : générer les visuels et assembler la vidéo finale

**Ce qui reste à construire.** Le storyboard décrit ce qu'il faut montrer à l'écran, mais ne
le montre pas encore : il faut maintenant fabriquer réellement ces animations (des
« motion graphics » — texte animé, icônes, diagrammes — générés par ordinateur, pas dessinés
à la main), puis assembler, pour chaque scène, la narration audio et son visuel en une courte
vidéo, avant de mettre bout à bout toutes les scènes d'un chapitre, puis tous les chapitres,
pour obtenir le cours final complet et navigable.

---

## 6. Les obstacles rencontrés et comment on les a résolus

Un projet réel ne se déroule jamais exactement comme prévu sur le papier. Voici les
vrais problèmes rencontrés pendant le stage, et comment ils ont été résolus — cette partie a
volontairement sa place dans un guide de projet, car elle montre le travail d'ingénierie
réel, pas seulement le résultat final.

**Les chapitres étaient trop longs au premier essai.** Le tout premier réglage du
découpage par sens (étape 2) a produit un seul chapitre de 37 minutes — bien trop long et
peu utile pour un cours en ligne. En ajustant la sensibilité de la comparaison de sens (un
paramètre appelé « seuil de similarité »), et en testant plusieurs valeurs avant de lancer le
traitement complet (pour ne pas gaspiller de temps de calcul), un réglage donnant des
chapitres de 3 à 10 minutes a été trouvé — beaucoup plus proche de ce qu'on attend d'un vrai
cours en ligne.

**Le quota gratuit de l'IA s'est épuisé en cours de route.** Le service d'IA utilisé pour
comprendre le contenu (le LLM) est gratuit, mais limité : seulement 20 requêtes par jour pour
le modèle le plus performant. Or, chapitrer toute la vidéo (17 chapitres) nécessitait
exactement 17 requêtes, et d'autres tests avaient déjà consommé une partie du quota du jour.
Résultat : le traitement s'est arrêté en pleine exécution avec une erreur de quota dépassé.
Solution : le système sauvegarde maintenant sa progression après chaque chapitre traité (donc
rien n'est perdu en cas d'erreur), retente automatiquement en cas d'erreur temporaire, et
peut basculer vers un second modèle d'IA (avec son propre quota séparé) pour continuer le
travail sans perdre ce qui était déjà fait.

**Le modèle de secours produisait du texte sans accents.** En basculant vers ce second
modèle d'IA (plus léger), un défaut est apparu : le texte généré perdait systématiquement ses
accents français (« securite » au lieu de « sécurité »). Ce n'est pas acceptable pour un cours
destiné à des francophones. La solution a été d'ajouter une consigne explicite dans les
instructions données à l'IA, exigeant l'usage correct des accents — et de vérifier le
résultat avant de continuer.

**Le choix de la voix de narration a changé en cours de projet.** La première version
utilisait une voix de synthèse (IA qui lit un texte entièrement réécrit) — une approche
validée techniquement et qui fonctionnait bien. Mais après réflexion, le choix s'est porté
sur la voix originale de l'intervenant (étape 3 ci-dessus), jugée plus fidèle et plus
authentique pour ce type de contenu. Ce changement a nécessité de revoir en profondeur les
étapes 3 et 4 du pipeline, en particulier de remplacer la réécriture du texte par un système
de sélection (garder/couper) et de découpage audio réel.

---

## 7. Ce qu'il reste à faire, dans l'ordre

1. ~~Terminer le storyboard sur l'ensemble des 17 chapitres~~ — fait : 261 scènes de
   narration/storyboard générées sur la vidéo complète (voir `output/full_storyboard.json`).
2. **Construire la génération des visuels** : transformer chaque description de storyboard
   en une véritable animation (motion graphics), au lieu d'une simple description textuelle —
   en cours (projet Remotion sous `remotion/`).
3. **Assembler chaque scène** : combiner l'audio (voix originale découpée) et son visuel en
   une courte vidéo.
4. **Assembler chaque chapitre**, puis **le cours complet**, avec une table des matières
   permettant de naviguer directement vers un chapitre.
5. **Évaluer le résultat** selon les critères du cahier des charges (le contenu est-il bien
   préservé ? le résultat ressemble-t-il à un vrai cours ? la navigation est-elle pratique ?).
6. **Documenter et préparer la restitution** (rapport de stage, soutenance).
7. **Quiz de compréhension** (hors périmètre MVP du cahier des charges, section 14, mais
   retenu comme évolution) : une interface de test/prototype sera développée séparément.
   Matériel de référence disponible dans `docs/reference/` : les diapositives originales de
   la formation (`slides_source.pdf`, 28 pages — bien plus propres que l'OCR extrait des
   frames vidéo) et un exemple de quiz réel sur ce même contenu (`quiz_reference.docx`).

## 8. Petit glossaire pour les non-initiés

| Terme | Explication simple |
|---|---|
| **IA / Intelligence artificielle** | Un programme informatique capable d'accomplir des tâches qui demandent normalement de la compréhension humaine (comprendre un texte, reconnaître une image...). |
| **LLM** (*Large Language Model*) | Un type d'IA entraîné sur d'énormes quantités de texte, capable de comprendre et de produire du langage naturel (comme ChatGPT). Certains LLM sont *multimodaux* : ils peuvent aussi recevoir des images en entrée, pas seulement du texte. |
| **ASR** (*Automatic Speech Recognition*) | La technologie qui transforme la parole (audio) en texte écrit. |
| **OCR** (*Optical Character Recognition*) | La technologie qui lit et extrait le texte visible dans une image (par exemple, le texte d'une diapositive). |
| **Diarisation** | Identifier automatiquement qui parle, et à quel moment, dans un enregistrement audio. |
| **TTS** (*Text-to-Speech*) | Une IA qui « lit » un texte à voix haute avec une voix synthétique. |
| **Embedding** | Une façon de représenter le sens d'un texte (ou d'une image) sous forme d'une liste de nombres, permettant de comparer mathématiquement si deux contenus parlent « de la même chose ». |
| **Pipeline** | Une chaîne d'étapes de traitement, où chaque étape prend le résultat de la précédente et le transforme un peu plus. |
| **Chapitrage sémantique** | Découper un contenu en chapitres en fonction des changements de *sujet*, et non d'une durée fixe. |
| **Storyboard** | Un plan de production détaillant, pour chaque scène, la narration et le visuel à afficher — avant que la vidéo ne soit réellement fabriquée. |
| **Motion graphics** | Des animations graphiques (texte qui apparaît, icônes qui bougent, diagrammes animés), générées par ordinateur plutôt que filmées. |
| **CPU / GPU** | Le CPU est le processeur standard de tout ordinateur ; le GPU (carte graphique) est un processeur spécialisé, beaucoup plus rapide pour l'IA, mais coûteux. Ce projet est volontairement conçu pour fonctionner sans GPU. |
| **Quota (API)** | Le nombre maximum de requêtes qu'on a le droit d'envoyer à un service en ligne gratuit, sur une période donnée (ici, par jour). |

## 9. Où trouver quoi dans le projet

```
docs/
  cahier_des_charges.pdf   Le document de référence complet du projet (exigences détaillées)
  GUIDE_PROJET.md           Ce document
README.md                   Instructions d'installation et d'utilisation technique
src/s2m_pipeline/           Le code du pipeline (voir le README pour le détail de chaque fichier)
output/                     Les résultats produits (scènes, chapitres, storyboard...) — non versionnés
```

Pour toute question sur une étape précise, ce guide peut être complété au fur et à mesure de
l'avancement du projet.

*Document mis à jour le 24 août 2026.*
