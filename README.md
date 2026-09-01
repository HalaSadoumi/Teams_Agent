# S2M — Transformation IA de formations enregistrées en cours e-learning

Système qui transforme un enregistrement brut de formation (Teams, diapositives,
partage d'écran) en un cours e-learning structuré en chapitres — pas un résumé,
une **transformation** (voir le cahier des charges, `docs/cahier_des_charges.pdf`, section 2).

Stage 4ème année AI & Data Science (EMSI Casablanca) — S2M Casablanca.

Nouveau sur le projet ? Voir [docs/GUIDE_PROJET.md](docs/GUIDE_PROJET.md) — explication
complète et accessible du projet, du problème de départ jusqu'à ce qu'il reste à faire.

Profil technique ? Voir [docs/ARCHITECTURE_TECHNIQUE.md](docs/ARCHITECTURE_TECHNIQUE.md) —
documentation module par module (architecture, schémas de données, décisions
d'implémentation), avec un état d'avancement honnête par composant.

Vous reprenez le projet ? Voir [docs/GUIDE_REPRISE.md](docs/GUIDE_REPRISE.md) —
comment ajouter un archétype visuel, changer le rythme des scènes, remplacer le
modèle de langage, et les pièges à connaître.

## État actuel

Le système est **complet et fonctionnel de bout en bout** : d'un enregistrement
brut, une seule commande produit un cours chapitré, narré à la voix de
l'intervenant, illustré de schémas animés, sous-titré et accompagné de
questions de compréhension, consultable dans une plateforme web.

Validé sur un enregistrement réel de 95 minutes : 17 chapitres, 79,6 minutes de
cours (84 % de la durée d'origine conservée — le système transforme, il ne
résume pas), 261 scènes animées, 1 445 sous-titres, 51 questions.

| étage | état |
|---|---|
| Ingestion (audio, transcription, scènes, OCR) | fonctionnel |
| Chapitrage sémantique auto-calibré | fonctionnel, validé sur 3 durées |
| Narration à la voix originale | fonctionnel |
| Planification visuelle (18 archétypes) | fonctionnel |
| Arrière-plans générés | fonctionnel, service gratuit sans garantie |
| Rendu vidéo | fonctionnel |
| Quiz, sous-titres, assemblage, plateforme web | fonctionnel |
| Empaquetage SCORM | non commencé |
| Interface de validation avant diffusion | non commencée |

Les limites connues et les suites possibles sont listées en fin de
[docs/GUIDE_REPRISE.md](docs/GUIDE_REPRISE.md).

## Tests

```bash
python -m pytest tests/ -q
```

Quatorze tests couvrent les fonctions qui portent les décisions du système
(calibration du chapitrage, rythme des scènes, calage des sous-titres). Purs :
ni réseau, ni modèle, ni clé d'API.

## Installation

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\pip install -e .
```

La dernière ligne installe le paquet en mode édition. Elle est **indispensable** :
le code vit dans `src/`, et sans elle toutes les commandes `python -m s2m_pipeline...`
échouent avec `ModuleNotFoundError: No module named 's2m_pipeline'`. Le mode
édition signifie que vos modifications du code sont prises en compte
immédiatement, sans réinstaller.

`sentence-transformers` dépend de PyTorch ; sur Windows, l'installation par
défaut peut tirer une version CUDA volumineuse même sans GPU. Pour une
installation CPU plus légère (conforme à la contrainte "pas de GPU" du
cahier, section 10) :

```bash
.venv\Scripts\pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv\Scripts\pip install -r requirements.txt
```

Prérequis système :
- [FFmpeg](https://www.gyan.dev/ffmpeg/builds/) sur le PATH
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract) — installé via
  `winget install --id UB-Mannheim.TesseractOCR -e`. Le pack de langue
  français (`fra.traineddata`) n'est pas inclus par défaut dans l'installeur
  Windows ; ce projet en garde une copie locale dans `.tessdata/` (non
  versionnée), utilisée automatiquement via la variable `TESSDATA_PREFIX`
  (voir `src/s2m_pipeline/ocr.py`).

Diarisation des locuteurs (optionnel — nécessite un compte Hugging Face) :

```bash
.venv\Scripts\pip install -r requirements-diarization.txt
```

Copier `.env.example` vers `.env` et renseigner :
- `HF_TOKEN` — optionnel, pour la diarisation. Sans token, tous les segments
  sont étiquetés `speaker_1`.
- `GEMINI_API_KEY` — requis à partir du Sprint 2 (chapitrage). Clé gratuite
  sur https://aistudio.google.com/apikey.

## Utilisation

**Sprint 1 — ingestion :**

```bash
.venv\Scripts\python -m s2m_pipeline.pipeline --video "data/ma_formation.mp4" --output output/scenes.json
```

Sortie, dans `output/<nom_video>/` : `scenes.json` (liste d'objets `Scene` :
id, start, end, speaker, transcript, ocr_text, frame_path), `transcript.json`
(segments ASR bruts), `subtitles.srt` / `subtitles.vtt`, `audio.wav`, et les
frames représentatives par scène.

**Sprint 2 — chapitrage :**

```bash
.venv\Scripts\python -m s2m_pipeline.chaptering --scenes output/scenes.json --transcript output/<nom_video>/transcript.json --output output/chapters.json
```

- `--dry-run` : affiche les frontières de chapitres candidates sans appeler
  le LLM (utile pour ajuster `chapter_similarity_threshold` sans consommer
  de quota API).
- `--resume` : réutilise les chapitres déjà présents dans `--output` au lieu
  de les régénérer — utile après une erreur de quota (voir ci-dessous), le
  résultat est sauvegardé après chaque chapitre généré.

**Sprint 3 — narration + storyboard.** Deux modes sont implémentés (voir
« Deux modes de narration » ci-dessous). Mode actuellement retenu, voix
originale de l'intervenant :

```bash
.venv\Scripts\python -m s2m_pipeline.narration_original --chapters output/chapters.json --scenes output/scenes.json --transcript output/<nom_video>/transcript.json --master-audio output/<nom_video>/audio.wav --output-dir output/<nom_video>/narration_original --output output/storyboard.json
```

**Sprint 3 — plan des visuels animés** (choisit un archétype de scène animée
par scène et remplit ses textes) :

```bash
.venv\Scripts\python -m s2m_pipeline.scene_visuals --storyboard output/storyboard.json --scenes output/scenes.json --chapters output/chapters.json --output output/scene_visuals.json --resume
```

**Rendu vidéo** (Remotion). Copier d'abord les données et l'audio dans
`remotion/public/`, puis :

```bash
cd remotion && bash render-all.sh
```

**Sprint 4 — assemblage du cours complet** (concaténation + métadonnées de
chapitrage) :

```bash
.venv\Scripts\python -m s2m_pipeline.assemble --chapters output/chapters.json --video-dir remotion/out --output-dir output/course
```

## Deux modes de narration

Le cahier des charges (section 6.2) demande d'évaluer trois approches de
narration. Deux sont implémentées ici, et restent interchangeables : elles
produisent toutes deux un `storyboard.json` au même format, donc tout ce qui
suit (plan des visuels, rendu, assemblage) est identique.

**Mode A — voix originale de l'intervenant (retenu actuellement).**
`content_selection.py` classe chaque segment de parole en « garder » ou
« couper », puis `narration_original.py` découpe et recolle directement le
vrai audio. Les mots ne sont jamais réécrits : la narration est exactement ce
que l'intervenant a dit, débarrassé des hésitations.

**Mode B — narration par synthèse vocale (en veille, réactivable).**
`script.py` fait réécrire le transcript en un script pédagogique propre,
`storyboard.py` le découpe en scènes, puis `narration.py` + `tts.py`
synthétisent la voix (edge-tts, gratuit, sans clé API) :

```bash
.venv\Scripts\python -m s2m_pipeline.script --chapters output/chapters.json --scenes output/scenes.json --transcript output/<nom_video>/transcript.json --output output/scripts.json
.venv\Scripts\python -m s2m_pipeline.storyboard --chapters output/chapters.json --scripts output/scripts.json --scenes output/scenes.json --output output/storyboard.json
.venv\Scripts\python -m s2m_pipeline.narration --storyboard output/storyboard.json --output-dir output/<nom_video>/narration --output output/storyboard.json
```

Ces quatre modules ne sont importés par aucun module du mode A : ils sont
conservés délibérément comme alternative, pas par oubli. Basculer d'un mode à
l'autre ne demande que de lancer la série de commandes correspondante.

### ⚠️ Quota Gemini (limite du tier gratuit)

`gemini-3.6-flash` (le modèle le plus capable) est limité à **20
requêtes/jour** sur le tier gratuit — insuffisant pour chapitrer une vidéo
d'1h30 (17 chapitres) plus les Sprints 3-4 (script, storyboard, un appel par
scène). `gemini-flash-lite-latest` a un quota séparé, plus généreux, et est
utilisé par défaut (`GEMINI_MODEL` dans `.env`) une fois le quota du modèle
principal épuisé. C'est exactement le risque anticipé par le cahier des
charges (section 13.6, "quotas des API gratuites insuffisants") — sa
mitigation prévue (répartir les appels entre plusieurs fournisseurs/modèles)
reste à approfondir si le volume augmente encore en Sprint 3-4 (ex. ajouter
Groq comme deuxième repli).

## Structure du projet

```
src/s2m_pipeline/
  config.py               Paramètres (variables d'environnement, .env)
  models.py               Schémas Scene / Chapter / StoryboardScene (section 8)
  llm.py                  Appels au LLM multimodal (Gemini) + prompts

  # Ingestion
  audio.py                Extraction, amélioration, découpage/recollage audio (FFmpeg)
  transcription.py        ASR (faster-whisper, CPU)
  diarization.py          Détection des locuteurs (pyannote.audio, optionnel)
  scenes.py               Détection de scènes visuelles + extraction de frames
  ocr.py                  OCR des diapositives (Tesseract)
  subtitles.py            Génération SRT / VTT à partir du transcript ASR
  pipeline.py             Orchestrateur d'ingestion + CLI

  # Compréhension et chapitrage
  embeddings.py           Détection de ruptures sémantiques (Sentence-Transformers)
  chaptering.py           Orchestrateur de chapitrage + CLI

  # Narration — mode A, voix originale (retenu)
  content_selection.py    Classification garder / couper par segment
  narration_original.py   Regroupement, découpage audio réel, storyboard

  # Narration — mode B, synthèse vocale (en veille)
  script.py               Réécriture du script pédagogique
  storyboard.py           Découpage du script réécrit en scènes
  narration.py            Orchestrateur de synthèse vocale
  tts.py                  Synthèse vocale (edge-tts)

  # Visuels et assemblage
  scene_visuals.py        Choix d'un archétype animé par scène + textes
  assemble.py             Cours complet + métadonnées de chapitrage

remotion/
  src/scenes/             Les 12 archétypes de scènes animées (un composant chacun)
  src/illustrations/      Primitives vectorielles (personnages, appareils, flèches...)
  src/components/         Fond animé, sous-titres, dispatcher, composition de chapitre
  render-all.sh           Rendu de tous les chapitres (reprenable)
```

## Choix techniques

Voir le cahier des charges (`docs/cahier_des_charges.pdf`, section 9) pour la justification
complète. En résumé : aucune brique ne nécessite de GPU ni de budget, tout
tourne en local ou via des quotas API gratuits, en traitement différé.
