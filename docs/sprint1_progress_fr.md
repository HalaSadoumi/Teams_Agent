# Sprint 1 — État d'avancement

## Ce qui est en place

- Extraction audio depuis la vidéo source
- Master audio 48 kHz nettoyé (voix originale conservée, pas de synthèse vocale)
- Fichier ASR 16 kHz dédié pour la transcription
- Transcription Whisper (modèle `medium` par défaut)
- Correction OCR des erreurs de transcription (termes visibles sur les slides)
- Sous-titres corrigés (`captions_corrected.srt`)
- Détection sémantique de scènes et chapitres
- Scripts de narration par chapitre (`scripts/chapter_XX_narration.txt`)
- Assemblage vidéo avec audio amélioré et sous-titres corrigés

## Structure des sorties

Tous les artefacts sont produits dans `data/processed/` :

```
data/processed/
  audio/
  enhanced_audio/
  asr_audio/
  keyframes/
  transcript/
  scripts/
  final_course.mp4
  course_package.json
  storyboard.json
```

## Commande

```powershell
python -m src.pipeline data\input\training.mp4 --output-dir data\processed --language fr
```

## Prochaines étapes

- Réécriture LLM des scripts pour une narration plus pédagogique
- Génération visuelle (graphiques, animations)
- Interface de navigation par chapitres
