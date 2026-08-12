# AI-Powered Training Transformation

Transform raw training recordings into structured e-learning course assets while preserving the original speaker voice.

## Goal

The system takes a raw training video and produces:

- cleaned, enhanced original audio (same speaker voice)
- timestamped transcript with OCR-assisted corrections
- corrected subtitles (SRT)
- semantic chapter boundaries
- chapter narration scripts
- storyboard metadata
- an assembled course video with corrected captions

## Architecture

1. **ingest** — extract audio and reference keyframes
2. **audio_enhancement** — clean and normalize the original voice (48 kHz production master + 16 kHz ASR version)
3. **ocr** — extract slide/screen text from keyframes to improve transcription accuracy
4. **asr** — transcribe with faster-whisper (medium model by default)
5. **transcript_correction** — fix ASR errors using OCR vocabulary
6. **analysis** — build multimodal scenes from transcript + OCR
7. **chapterize** — detect semantic chapter boundaries
8. **script** — clean narration text and export per-chapter scripts
9. **storyboard** — generate visual direction metadata
10. **assemble** — render final video with enhanced audio and corrected subtitles

## Project layout

```
src/
  pipeline.py              # Main CLI entrypoint
  ingest.py                # Audio/video extraction
  audio_enhancement.py     # Audio cleaning (preserves original voice)
  transcribe.py            # faster-whisper transcription
  transcript_correction.py # OCR-assisted ASR correction
  asr.py                   # ASR wrapper
  ocr.py                   # Slide/screen OCR
  analysis.py              # Scene building
  chapterize.py            # Chapter detection
  script.py                # Narration cleanup + chapter script export
  storyboard.py            # Storyboard generation
  assemble.py              # Video assembly
  render_video.py          # FFmpeg rendering
  model.py                 # Shared data structures
data/
  input/                   # Place source videos here (gitignored)
  processed/               # Pipeline outputs (gitignored)
docs/                      # Progress reports
tools/                     # Optional DeepFilterNet binary
```

## Usage

Install dependencies:

```powershell
pip install -r requirements.txt
```

Optional: install [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) and add it to PATH for better slide text extraction and transcript correction.

Run the pipeline:

```powershell
python -m src.pipeline data\input\training.mp4 --output-dir data\processed
```

Useful options:

```powershell
python -m src.pipeline data\input\training.mp4 `
  --output-dir data\processed `
  --model medium `
  --language fr `
  --chapter-duration 300 `
  --keyframe-interval 20
```

Skip denoising if the source audio is already clean:

```powershell
python -m src.pipeline data\input\training.mp4 --no-denoise
```

## Outputs

All artifacts are written under `--output-dir` (default: `data/processed/`):

| File | Description |
|------|-------------|
| `audio/audio.wav` | Raw extracted audio |
| `enhanced_audio/*_production.wav` | Cleaned 48 kHz master (original voice) |
| `asr_audio/*_16khz_mono.wav` | ASR-optimized audio |
| `transcript/transcript.json` | Raw Whisper transcript |
| `transcript/transcript_corrected.json` | OCR-corrected transcript |
| `transcript/captions_corrected.srt` | Corrected subtitles |
| `scripts/chapter_XX_narration.txt` | Clean narration per chapter |
| `storyboard.json` | Visual direction metadata |
| `course_package.json` | Full course metadata |
| `final_course.mp4` | Assembled video with enhanced audio + corrected subtitles |

## Audio philosophy

The pipeline **does not replace the speaker's voice**. It:

- removes background noise conservatively
- normalizes loudness for consistent playback
- keeps the original speaker character intact
- uses the enhanced audio in the final video

For best results, optionally place `deep-filter.exe` in `tools/` for DeepFilterNet denoising.

## Transcription accuracy

Accuracy is improved by:

- using the **medium** Whisper model (upgrade to `large-v3` with `--model large-v3` for best quality)
- building a Whisper **initial prompt** from OCR slide vocabulary
- **OCR-assisted post-correction** of technical terms visible on slides
- forcing language with `--language fr` or `--language en` when known

## Next steps

- LLM-based script rewriting for polished educational narration
- Speaker diarization
- Visual scene rendering (motion graphics, diagrams)
- Chapter-based video navigation UI
