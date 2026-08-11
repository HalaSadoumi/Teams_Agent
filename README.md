# AI-Powered Training Transformation

This repository is a scaffold for an internship project to transform raw training recordings into structured, e-learning course assets.

## Goal

The system should take a raw video recording and produce:

- timestamped transcript
- OCR and visual references
- semantic chapter boundaries
- educational script drafts
- storyboard metadata
- an assembled course package with chapter metadata

## Architecture

The pipeline is organized as modular stages:

1. `ingest`
   - extract audio from the source video
   - create reference keyframes

2. `audio_enhancement`
   - standardize audio to 48 kHz mono WAV
   - optionally denoise if DeepFilterNet is available

3. `asr`
   - transcribe audio into timestamped segments
   - preserve speaker and timing information

3. `ocr`
   - extract text from periodic reference frames
   - label slide/screen content for multimodal analysis

4. `analysis`
   - merge transcript segments and visual references into structured scenes
   - split long continuous recordings into semantically coherent scenes
   - attach OCR, visual labels, and scene metadata

5. `chapterize`
   - detect chapter boundaries from scene structure
   - create chapter titles, summaries, and key points
   - use semantic topic segmentation to split long continuous recordings into meaningful course chapters

6. `script`
   - convert raw transcript segments into cleaner course narration
   - remove filler words and produce a polished narration draft

7. `storyboard`
   - produce a guided storyboard for course visuals
   - map scenes to chapter IDs and visual directions
   - infer visual type, screen text, and transitions from scene topics and OCR context

8. `assemble`
   - render a baseline course output with captions and narration
   - produce a final rendered video

## Project layout

- `src/`: pipeline modules and entrypoint
- `src/model.py`: shared data structures
- `src/pipeline.py`: orchestrator for the MVP workflow
- `src/ingest.py`: audio/video asset extraction
- `src/asr.py`: speech transcription wrapper
- `src/ocr.py`: OCR extraction from keyframes and visual label generation
- `src/analysis.py`: scene construction from transcripts and OCR references
- `src/chapterize.py`: chapter detection logic
- `src/script.py`: script rewriting and scene generation with cleaner narration output
- `src/storyboard.py`: storyboard generation
- `src/audio_enhancement.py`: audio normalization and optional denoising helper
- `src/ocr.py`: OCR extraction from keyframes with pytesseract/easyocr fallback
- `src/assemble.py`: baseline rendering support
- `src/transcribe.py`: existing local transcription script
- `src/render_video.py`: existing caption rendering helper
- `src/extract_keyframes.py`: existing keyframe extraction helper
- `src/create_storyboard.py`: existing storyboard markdown helper

## Usage

Run the pipeline from the repository root:

```powershell
python src\pipeline.py path\to\training_video.mp4 --output-dir data\processed
```

Optional OCR dependencies:
- Install `Pillow` and `pytesseract` for local OCR support.
- If using `pytesseract`, install the Tesseract binary on Windows and make sure it is available on PATH.
- `easyocr` can also be installed as an optional fallback for text extraction without external OCR binaries.

The command will create:

- `data/processed/audio/audio.wav`
- `data/processed/enhanced_audio/*`
- `data/processed/keyframes/*`
- `data/processed/transcript/transcript.json`
- `data/processed/course_package.json`
- `data/processed/storyboard.json`

## Next steps

The current code focuses on architecture and pipeline scaffolding. The chapter pipeline now uses semantic topic similarity to improve chapter boundaries for long continuous recordings. Future work includes:

- adding language-aware speaker diarization
- strengthening OCR and visual analysis for slides and screens
- adding LLM-based script rewriting
- generating polished storyboard visuals
- assembling a finished video course