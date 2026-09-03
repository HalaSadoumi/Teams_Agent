# Guide de reprise

Ce document s'adresse à la personne qui reprendra le système après le stage.
Il ne décrit pas l'architecture — c'est le rôle de
[ARCHITECTURE_TECHNIQUE.md](ARCHITECTURE_TECHNIQUE.md) — mais répond à une
question pratique : **je veux changer telle chose, où et comment ?**

---

## 1. Le principe à ne pas casser

Le système n'a aucun code spécifique à une vidéo, à un sujet ou à une scène.
C'est ce qui lui permet de traiter un enregistrement qu'il n'a jamais vu.

Trois règles en découlent, et toute modification devrait les respecter :

1. **Aucun seuil n'est une constante réglée sur une vidéo.** Les paramètres de
   `config.py` expriment des objectifs (« un chapitre dure environ 5 min 30 »),
   et le code cherche la valeur qui les atteint sur l'enregistrement traité.
   Si vous vous surprenez à ajuster un nombre jusqu'à ce que « ça rende bien »
   sur une vidéo précise, c'est le signe d'un surapprentissage : cherchez
   plutôt la règle dont ce nombre est la conséquence.
2. **Le vocabulaire visuel reste neutre de domaine.** Un archétype décrit une
   forme de raisonnement (« un acteur agit sur une cible »), jamais un sujet
   (« une attaque par hameçonnage »). Sinon le système ne sert plus qu'aux
   formations de sécurité.
3. **Chaque étage écrit un fichier et ignore les autres.** C'est ce qui rend
   chaque étape inspectable et remplaçable — et c'est ce qui a permis de
   remplacer entièrement le mode de narration sans toucher aux six autres.

---

## 2. Produire un cours

Une fois seulement, après avoir créé l'environnement virtuel :

```bash
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\pip install -e .
```

La seconde ligne installe le paquet en mode édition. Sans elle, toutes les
commandes ci-dessous échouent avec `ModuleNotFoundError: No module named
's2m_pipeline'` — le code vit dans `src/`, qui n'est pas sur le chemin
d'import par défaut.

**Puis, à chaque session de travail, activez l'environnement** :

```bash
.venv\Scripts\Activate.ps1
```

Sans activation, `python` reste celui du système, où le paquet n'est pas
installé — c'est l'erreur la plus fréquente à la prise en main. L'installation
crée quatre commandes nommées qui évitent le problème :

| commande | rôle |
|---|---|
| `s2m-course` | produire un cours à partir d'un **enregistrement vidéo** |
| `s2m-course-pdf` | produire un cours à partir d'un **support PDF** |
| `s2m-publish` | publier un cours déjà produit vers la plateforme web |
| `s2m-quiz-docx` | convertir un quiz officiel Word au format du lecteur |

Produire un cours à partir d'un enregistrement :

```bash
s2m-course --video "chemin/vers/enregistrement.mp4"
```

Produire un cours à partir d'un support, de bout en bout — c'est la commande
unique demandée pour tout nouveau PDF :

```bash
s2m-course-pdf --pdf "support.pdf" --course-id mon_cours --title "Mon cours" --quiz-docx "quiz.docx"
```

`--quiz-docx` est facultatif : sans lui, les questions sont générées à partir
de la narration. Neuf étapes s'enchaînent — lecture du support, rédaction de
la narration, découpage en scènes, synthèse vocale, sous-titres, plan visuel,
arrière-plans, rendu, publication — et chacune est ignorée si son résultat
existe déjà.

L'orchestrateur enchaîne sept étapes et **détecte celles déjà faites** : si le
traitement est interrompu (quota d'API épuisé, coupure, arrêt volontaire), la
même commande reprend où il s'était arrêté. Pour forcer la reprise à une étape
précise :

```bash
python -m s2m_pipeline.build_course --video "..." --from render
```

Étapes disponibles : `ingest`, `chapters`, `narration`, `visuals`, `images`,
`render`, `assemble`.

Puis, pour publier vers la plateforme de consultation :

```bash
s2m-publish --course-id <id> --subtitles output/<id>/subtitles
s2m-studio
```

`s2m-studio` sert la plateforme **et** le studio sur le même port : le
catalogue sur `/`, le dépôt d'un nouveau support sur `/studio.html`.

Comptez environ **sept heures** pour un enregistrement de 95 minutes sur un
poste sans carte graphique. Les deux étapes coûteuses — génération des images
et rendu vidéo — représentent plus de 80 % du temps et sont les premières à
accélérer si une machine plus puissante est disponible.

---

## 2 bis. Deux entrées, une seule chaîne

Le système produit deux cours à partir de la même formation, et il est utile de
savoir d'emblée ce qui les sépare — c'est peu.

| | Parcours détaillé | Parcours essentiel |
|---|---|---|
| source | l'enregistrement de la session | le support de formation (PDF) |
| commande | `s2m-course` | `s2m-course-pdf` |
| narration | la voix réelle de l'intervenant, remontée | une voix de synthèse |
| durée | celle de la session, moins les silences | chapitres de moins de 5 min |
| sortie vidéo | `remotion/out/` | `remotion/out_pdf/` |

**L'arborescence dit à quoi sert chaque module** : le paquet est rangé en
trois zones, et une seule regarde la provenance du contenu.

```
src/s2m_pipeline/
    config.py          réglages, lus par tout le monde
    models.py          structures de données partagées

    core/              commun aux deux entrées — ne connaît pas la provenance
        llm.py                 appels au modèle de langage, invites, schémas
        audio.py               extraction, amélioration, découpe, conversion
        scene_visuals.py       archétype, points et phrase par scène
        scene_images.py        arrière-plans générés
        chapter_subtitles.py   appariement et écriture des sous-titres
        quiz.py                génération des questions
        quiz_reference.py      lecture d'un quiz officiel fourni en Word
        assemble.py            concaténation et métadonnées de navigation
        web_export.py          publication vers la plateforme

    from_video/        entrée « enregistrement de session »
        transcription.py, scenes.py, ocr.py, diarization.py    ingestion
        embeddings.py, chaptering.py                           chapitrage
        content_selection.py, narration_original.py            voix réelle
        script.py, subtitles.py, pipeline.py                   étapes héritées
        build_course.py                                        orchestrateur

    from_slides/       entrée « support de formation »
        pdf_source.py                          lecture du document
        storyboard.py                          découpage en scènes
        narration.py, tts.py                   synthèse vocale
        build_course_from_pdf.py               orchestrateur
```

Neuf modules sur vingt-neuf sont dans `core/` et servent aux deux parcours ;
les autres appartiennent à une entrée précise. **Ajouter une troisième source**
— un document Word, une page web — demande un module de lecture et un
orchestrateur dans une nouvelle zone, et rien d'autre : tout `core/`,
`remotion/src/` et `web/` fonctionnent tels quels.

Les imports internes sont **absolus** (`from s2m_pipeline.core import llm`) et
non relatifs : on voit d'où vient chaque chose sans compter les points.

**Les répertoires de travail**, non versionnés :

```
output/<cours>/          artefacts du cours (pages, chapitres, plans, sous-titres)
output/_archives/        anciennes versions mises de côté, jamais écrasées
remotion/out/            vidéos du parcours détaillé
remotion/out_pdf/        vidéos du parcours essentiel
remotion/archives/       rendus précédents conservés pour comparaison
web/data/<cours>/        ce que la plateforme sert réellement
```

---

## 3. Les modifications les plus courantes

### 3.1 Ajouter un archétype visuel

C'est l'évolution la plus fréquente, et elle demande **deux fichiers, jamais
plus** :

1. Écrire le composant dans `remotion/src/scenes/MonArchetype.tsx`. Il reçoit
   `label`, `items`, `primary`, `secondary`, `durationInFrames` et dessine la
   scène. Prenez `PillarsDiagram.tsx` comme modèle : il est court et montre
   les conventions (ressorts d'animation, `WrappedText` pour tout libellé).
2. L'inscrire au vocabulaire dans `src/s2m_pipeline/llm.py`, dictionnaire
   `SCENE_ARCHETYPES`, avec une définition d'une ligne **sans référence à un
   domaine** :

   ```python
   "mon_archetype": "ce que le schema montre, decrit par la forme du raisonnement",
   ```

3. Le brancher dans `remotion/src/components/SceneRenderer.tsx` : un `case`
   dans le `switch`.

Le bandeau de la phrase à retenir et le décalage vertical sont appliqués par
`SceneRenderer` pour tous les archétypes — votre composant n'a rien à en
savoir.

**Piège à connaître** : `<text>` en SVG ne va pas à la ligne. Tout libellé
issu du plan doit passer par `WrappedText` (`illustrations/primitives.tsx`),
sinon il débordera dès qu'un libellé sera un peu long. Les treize schémas
existants ont dû être repris pour cette raison.

### 3.2 Changer le rythme des scènes

`src/s2m_pipeline/narration_original.py`, en tête de fichier :

| constante | rôle |
|---|---|
| `_TARGET_SCENE_SECONDS` | durée visée d'une scène (20 s) |
| `_MIN_SCENE_SECONDS` | plancher ; en dessous, la scène est fusionnée avec sa voisine (8 s) |
| `_MAX_SCENE_SECONDS` | plafond d'une scène fusionnée (34 s) |
| `_MERGE_MAX_GAP_SECONDS` | au-delà, on ne fusionne pas : trop de contenu a été retiré entre les deux |

Baisser `_MIN_SCENE_SECONDS` accélère le montage, l'augmenter le calme.
Après modification, relancer à partir de l'étape `narration` — et **régénérer
les sous-titres**, dont le calage dépend du découpage.

### 3.3 Changer la granularité du chapitrage

`src/s2m_pipeline/config.py` : `chapter_target_seconds` (durée visée d'un
chapitre), `chapter_count_min` / `chapter_count_max` (garde-fous),
`chapter_min_seconds` (plancher).

Ne cherchez pas un seuil de similarité : il n'y en a pas dans la
configuration, il est calculé par `chaptering.calibrate()` pour chaque vidéo.

### 3.4 Remplacer le modèle de langage

Tous les appels passent par `src/s2m_pipeline/llm.py`, aucune autre module
n'importe le client. Pour changer de fournisseur, il suffit de réécrire
`_get_client()` et `_generate_content()` en conservant deux propriétés :

- la **sortie contrainte par schéma** (le modèle ne peut pas répondre autre
  chose qu'un objet conforme) ;
- la **relance automatique** sur les erreurs temporaires.

Le modèle se change sans toucher au code via la variable d'environnement
`GEMINI_MODEL`.

### 3.5 Changer la charte graphique

`remotion/src/theme.ts` (couleurs, police, ressort d'animation) et
`remotion/src/sceneAccent.ts` (rotation des couleurs d'accent par scène).
Pour la plateforme web : `web/assets/style.css`.

---

## 4. Les tests

```bash
python -m pytest tests/ -q
```

Quatorze tests couvrent les quatre fonctions qui portent les décisions du
système : calibration du chapitrage, fusion des scènes courtes, appariement
des sous-titres à la parole réelle, coupe du texte de repli. Ils sont purs —
ni réseau, ni modèle, ni clé d'API — et tournent en une vingtaine de secondes.

Ce sont les régressions **invisibles** qu'ils protègent : un sous-titre qui
dérive ou une scène de deux secondes ne se voient qu'à la lecture, des heures
après avoir été introduits. Si vous modifiez le rythme, le chapitrage ou les
sous-titres, lancez-les avant de relancer un rendu de plusieurs heures.

---

## 5. Points de vigilance

**Les commandes `npx remotion` se lancent depuis `remotion/`,** jamais depuis
la racine : c'est là que se trouvent `package.json` et `node_modules`. Depuis
la racine, npm répond `could not determine executable to run`.

**Le rendu ne doit pas être modifié pendant qu'il tourne.** Chaque chapitre
est rendu par un appel séparé qui reconstruit le paquet JavaScript : modifier
un composant entre deux chapitres produit une série incohérente, voire un
échec. Attendez la fin.

**Les artefacts coûteux ne se suppriment pas à la légère.** Trois heures de
rendu ne se distinguent pas d'un fichier temporaire dans un explorateur.
La convention retenue : les répertoires de sortie sont nommés par intention
(`out`, `out_avec_soustitres`, `out_ancienne_version`) et jamais écrasés.

**Les identifiants de scène changent quand le découpage change.** Si vous
modifiez le rythme, les anciens arrière-plans et sous-titres ne correspondent
plus : régénérez-les, ne les réutilisez pas.

**Le quota gratuit du modèle de langage est la contrainte principale.** Un
cours complet consomme quelques dizaines d'appels. En cas d'épuisement, le
traitement s'arrête proprement et reprend le lendemain sans rien recalculer.

**Le système est reproductible, et doit le rester.** Deux exécutions sur le
même enregistrement doivent donner le même cours. Deux mécanismes le
garantissent, et tous deux sont faciles à casser sans s'en rendre compte :

- la température est forcée à zéro dans `llm._generate_content`, point d'entrée
  unique de tous les appels au modèle. Sans elle, le modèle échantillonne et le
  découpage change à chaque exécution — sur la vidéo de validation, une
  seconde passe avait retiré 23 secondes de remplissage supplémentaires et fait
  passer un chapitre de 6 min 49 à 6 min 26 ;
- la graine des arrière-plans vient de `scene_images.seed_for()`, un condensé
  de l'identifiant de scène. Ne revenez pas au `hash()` de Python : il est
  réinitialisé aléatoirement à chaque processus, donc trois exécutions donnent
  trois graines différentes pour la même scène.

Deux tests verrouillent ces deux propriétés.

---

## 6. Ce qui reste à faire

- **Empaquetage SCORM**, pour déposer les cours dans une plateforme
  d'apprentissage du marché. Les métadonnées produites (chapitres, durées,
  quiz, sous-titres) contiennent déjà l'essentiel de ce qu'exige le format.
- **Interface de validation** : le système produit un cours prêt à être relu,
  pas prêt à être diffusé. Un écran permettant de corriger un titre ou une
  question avant publication est l'évolution la plus utile.
- **Validation sur un second enregistrement réel**, d'un autre sujet et d'un
  autre intervenant. La généralité a été vérifiée sur du contenu inventé et
  sur trois durées, jamais sur une seconde vidéo de bout en bout.
- **Mesure du taux d'erreur de la transcription** contre une référence
  humaine, aujourd'hui inconnue faute de corpus annoté.
