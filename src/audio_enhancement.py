"""Standardize and denoise audio without modifying original media."""

from pathlib import Path
import shutil
import subprocess

import imageio_ffmpeg

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_AUDIO = PROJECT_ROOT / "data" / "input" / "output-audio.mp3"
ENHANCED_DIR = PROJECT_ROOT / "data" / "processed" / "enhanced_audio"
STANDARDIZED_AUDIO = ENHANCED_DIR / "output-audio_48khz_mono.wav"
DENOISED_AUDIO = ENHANCED_DIR / "output-audio_denoised.wav"
DEEP_FILTER = PROJECT_ROOT / "tools" / "deep-filter.exe"

def run(command: list[str]) -> None:
    subprocess.run(command, check=True)

def standardize_audio(source: Path = INPUT_AUDIO, destination: Path = STANDARDIZED_AUDIO) -> Path:
    """Create a mono, 48 kHz, 16-bit PCM WAV from source."""
    if not source.is_file():
        raise FileNotFoundError(f"Audio input not found: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", str(source), "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(destination)])
    return destination

def denoise_audio(source: Path = STANDARDIZED_AUDIO, destination: Path = DENOISED_AUDIO) -> Path:
    """Run DeepFilterNet's official Windows binary and keep source untouched."""
    if not DEEP_FILTER.is_file():
        raise FileNotFoundError(f"DeepFilterNet executable not found: {DEEP_FILTER}")
    staging_dir = destination.parent / "deepfilter_staging"
    staging_dir.mkdir(parents=True, exist_ok=True)
    staged_output = staging_dir / source.name
    run([str(DEEP_FILTER), "-D", "-o", str(staging_dir), str(source)])
    if not staged_output.is_file():
        raise RuntimeError(f"DeepFilterNet did not create: {staged_output}")
    shutil.copy2(staged_output, destination)
    return destination

if __name__ == "__main__":
    standardized = standardize_audio()
    denoised = denoise_audio(standardized)
    print(f"Standardized: {standardized}")
    print(f"Denoised: {denoised}")
