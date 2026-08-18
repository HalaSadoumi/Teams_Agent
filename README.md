# S2M — Transformation IA de formations enregistrées en cours e-learning

Système qui transforme un enregistrement brut de formation (Teams, diapositives,
partage d'écran) en un cours e-learning structuré en chapitres — pas un résumé,
une **transformation** (voir le cahier des charges, `docs/cahier_des_charges.pdf`, section 2).

Stage 4ème année AI & Data Science (EMSI Casablanca) — S2M Casablanca.

## État actuel : Sprint 1 (Semaines 1-2)

Objectif du sprint : pipeline d'ingestion fonctionnel — extraction audio,
transcription ASR, détection de locuteurs, détection de scènes visuelles, OCR
des diapositives — produisant une première représentation multimodale du
contenu (liste d'objets `Scene`, cahier des charges section 8.1).

Ce que le pipeline ne fait **pas encore** (Sprints 2-4) : compréhension
sémantique LLM, chapitrage automatique, génération du script pédagogique,
storyboard, visuels, narration TTS, assemblage vidéo final.

## Installation

```bash
python -m venv .venv
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

Puis copier `.env.example` vers `.env` et renseigner `HF_TOKEN` (voir les
instructions dans `.env.example`). Sans token, le pipeline fonctionne quand
même : tous les segments sont étiquetés `speaker_1`.

## Utilisation

```bash
.venv\Scripts\python -m s2m_pipeline.pipeline --video "data/ma_formation.mp4" --output output/scenes.json
```

Sortie : `output/scenes.json`, une liste d'objets `Scene` (id, start, end,
speaker, transcript, ocr_text, frame_path), plus les fichiers intermédiaires
(audio extrait, frames représentatives) dans `output/<nom_video>/`.

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
  pipeline.py           Orchestrateur Sprint 1 + CLI
```

## Choix techniques

Voir le cahier des charges (`docs/cahier_des_charges.pdf`, section 9) pour la justification
complète. En résumé : aucune brique ne nécessite de GPU ni de budget, tout
tourne en local ou via des quotas API gratuits, en traitement différé.
