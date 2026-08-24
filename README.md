# S2M — Transformation IA de formations enregistrées en cours e-learning

Système qui transforme un enregistrement brut de formation (Teams, diapositives,
partage d'écran) en un cours e-learning structuré en chapitres — pas un résumé,
une **transformation** (voir le cahier des charges, `docs/cahier_des_charges.pdf`, section 2).

Stage 4ème année AI & Data Science (EMSI Casablanca) — S2M Casablanca.

Nouveau sur le projet ? Voir [docs/GUIDE_PROJET.md](docs/GUIDE_PROJET.md) — explication
complète et accessible du projet, du problème de départ jusqu'à ce qu'il reste à faire.

## État actuel : Sprint 2 (Semaines 3-4)

**Sprint 1** (ingestion) : pipeline fonctionnel — extraction audio,
transcription ASR + sous-titres, détection de locuteurs, détection de scènes
visuelles, OCR des diapositives — produisant une première représentation
multimodale du contenu (liste d'objets `Scene`, cahier des charges section 8.1).

**Sprint 2** (compréhension + chapitrage) : segmentation par ruptures
sémantiques (Sentence-Transformers) puis génération, par chapitre, d'un
titre/résumé/points clés via un LLM multimodal (Gemini) qui reçoit à la fois
la transcription ET les frames représentatives — pas seulement l'OCR (cahier
des charges section 5.2, "point critique du projet").

Ce que le pipeline ne fait **pas encore** (Sprints 3-4) : génération du
script pédagogique, storyboard visuel, génération des visuels, narration
TTS, assemblage vidéo final, lecteur de cours navigable par chapitres.

## Installation

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

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
  config.py          Paramètres (variables d'environnement, .env)
  models.py           Schémas Scene / Chapter / StoryboardScene (section 8)
  audio.py             Extraction audio (FFmpeg)
  transcription.py     ASR (faster-whisper, CPU)
  diarization.py        Détection des locuteurs (pyannote.audio, optionnel)
  scenes.py            Détection de scènes visuelles + extraction de frames
  ocr.py                 OCR des diapositives (Tesseract)
  subtitles.py           Génération SRT / VTT à partir du transcript ASR
  pipeline.py           Orchestrateur Sprint 1 + CLI
  embeddings.py          Détection de ruptures sémantiques (Sentence-Transformers)
  llm.py                  Génération de contenu multimodale (Gemini)
  chaptering.py           Orchestrateur Sprint 2 (chapitrage) + CLI
```

## Choix techniques

Voir le cahier des charges (`docs/cahier_des_charges.pdf`, section 9) pour la justification
complète. En résumé : aucune brique ne nécessite de GPU ni de budget, tout
tourne en local ou via des quotas API gratuits, en traitement différé.
