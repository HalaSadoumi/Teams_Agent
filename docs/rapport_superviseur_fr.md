# Rapport de progrès pour le superviseur

## Contexte

Ce projet transforme des enregistrements de formation bruts en cours e-learning structurés. La voix originale du formateur est conservée et améliorée (débruitage + normalisation), sans synthèse vocale.

## Ce qui a été fait

### 1. Audio — voix originale améliorée
- Extraction audio depuis la vidéo source
- Master production 48 kHz : débruitage conservateur + compression légère + normalisation loudness
- Fichier ASR séparé 16 kHz pour une transcription fiable
- Assemblage vidéo synchronisé (plus de troncature audio)

### 2. Transcription et correction
- Modèle Whisper `medium` (meilleure précision qu'avant)
- Prompt initial construit à partir du vocabulaire OCR des slides
- Correction post-ASR : les termes visibles sur les slides corrigent les erreurs de transcription
- Sous-titres corrigés exportés en SRT

### 3. Structure pédagogique
- Scènes sémantiques (pauses + similarité de sujet)
- Chapitres automatiques avec titres et points clés
- Scripts de narration nettoyés par chapitre
- Storyboard JSON avec directions visuelles

### 4. Assemblage
- Vidéo finale : image source + audio amélioré + sous-titres corrigés
- Package complet : `course_package.json`

## Fichiers clés

- `src/pipeline.py` — orchestration complète
- `src/audio_enhancement.py` — nettoyage audio (voix originale)
- `src/transcript_correction.py` — correction OCR des transcriptions
- `src/transcribe.py` — Whisper avec paramètres optimisés

## Sorties à présenter

```
data/processed/
  final_course.mp4
  transcript/transcript_corrected.json
  transcript/captions_corrected.srt
  scripts/chapter_01_narration.txt
  course_package.json
  storyboard.json
```

## Commande

```powershell
python -m src.pipeline data\input\training.mp4 --output-dir data\processed --language fr
```

## Prochaines étapes

1. Réécriture LLM des narrations pour un style pédagogique professionnel
2. Génération visuelle (diagrammes, cartes concept, animations)
3. Interface de navigation par chapitres
