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

def has_denoiser() -> bool:
    """Return whether the DeepFilterNet denoiser binary is available."""
    return DEEP_FILTER.is_file()


def enhance_audio(source: Path, output_dir: Path, denoise: bool = True) -> Path:
    """Standardize and optionally denoise audio for downstream processing.

    Produces a 48 kHz mono WAV 'master' file suitable for final production. Does
    not overwrite the original. Returns the path to the 48 kHz master (denoised
    if denoise=True and a denoiser is available).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    standardized = output_dir / f"{source.stem}_48khz_mono.wav"
    standardize_audio(source, standardized)

    # If a high-quality denoiser binary is available, run it and return that.
    if denoise and has_denoiser():
        denoised = output_dir / f"{source.stem}_denoised.wav"
        denoise_audio(standardized, denoised)
        return denoised

    # If no external denoiser is available but denoise requested, apply a
    # conservative ffmpeg denoise chain as a fallback (keeps master at 48 kHz).
    if denoise and not has_denoiser():
        fallback = output_dir / f"{source.stem}_48khz_denoised.wav"
        ffmpeg_denoise_audio(standardized, fallback)
        return fallback

    # Default: return the standardized 48 kHz master
    return standardized


def ffmpeg_denoise_audio(source: Path, destination: Path) -> Path:
    """Conservative denoising using an ffmpeg filter chain (fallback).

    This is intentionally conservative to avoid over-processing speech which
    can hurt ASR. It is used only when no specialized denoiser binary exists.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-i",
        str(source),
        "-af",
        "highpass=f=120, lowpass=f=12000, afftdn=nf=-25, dynaudnorm=p=0.95",
        "-ar",
        "48000",
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        str(destination),
    ]
    run(cmd)
    return destination


def generate_asr_version(source_48k: Path, dest_dir: Path) -> Path:
    """Create a 16 kHz mono WAV optimized for ASR from a 48 kHz master.

    Applies loudness normalization (loudnorm) and resamples to 16 kHz mono.
    Returns the path to the ASR-ready WAV file.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    asr_path = dest_dir / f"{source_48k.stem}_16khz_mono.wav"
    # Use ffmpeg to resample and apply loudness normalization suitable for ASR
    run([
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-i",
        str(source_48k),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-af",
        "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-c:a",
        "pcm_s16le",
        str(asr_path),
    ])
    return asr_path

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
