"""Standardize and denoise audio while preserving the original speaker voice."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import imageio_ffmpeg

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEEP_FILTER = PROJECT_ROOT / "tools" / "deep-filter.exe"

PRODUCTION_FILTER = (
    "highpass=f=80,"
    "lowpass=f=14000,"
    "afftdn=nf=-20,"
    "acompressor=threshold=-18dB:ratio=3:attack=5:release=50,"
    "loudnorm=I=-16:TP=-1.5:LRA=11"
)


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def has_denoiser() -> bool:
    return DEEP_FILTER.is_file()


def enhance_audio(source: Path, output_dir: Path, denoise: bool = True) -> Path:
    """Create a clean 48 kHz mono production master from extracted audio."""
    output_dir.mkdir(parents=True, exist_ok=True)
    standardized = output_dir / f"{source.stem}_48khz_mono.wav"
    standardize_audio(source, standardized)

    if denoise and has_denoiser():
        denoised = output_dir / f"{source.stem}_denoised.wav"
        denoise_audio(standardized, denoised)
        return finalize_production_master(denoised, output_dir / f"{source.stem}_production.wav")

    if denoise:
        fallback = output_dir / f"{source.stem}_48khz_denoised.wav"
        ffmpeg_denoise_audio(standardized, fallback)
        return finalize_production_master(fallback, output_dir / f"{source.stem}_production.wav")

    return finalize_production_master(standardized, output_dir / f"{source.stem}_production.wav")


def finalize_production_master(source: Path, destination: Path) -> Path:
    """Apply final loudness normalization for consistent playback volume."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-i",
        str(source),
        "-af",
        "loudnorm=I=-16:TP=-1.5:LRA=11",
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


def ffmpeg_denoise_audio(source: Path, destination: Path) -> Path:
    """Conservative denoising using FFmpeg while preserving speech quality."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-i",
        str(source),
        "-af",
        PRODUCTION_FILTER,
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
    """Create a 16 kHz mono WAV optimized for ASR from the production master."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    asr_path = dest_dir / f"{source_48k.stem}_16khz_mono.wav"
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
        "highpass=f=100,lowpass=f=8000,loudnorm=I=-16:TP=-1.5:LRA=11",
        "-c:a",
        "pcm_s16le",
        str(asr_path),
    ])
    return asr_path


def standardize_audio(source: Path, destination: Path) -> Path:
    """Create a mono, 48 kHz, 16-bit PCM WAV from source."""
    if not source.is_file():
        raise FileNotFoundError(f"Audio input not found: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    run([
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-i",
        str(source),
        "-ac",
        "1",
        "-ar",
        "48000",
        "-c:a",
        "pcm_s16le",
        str(destination),
    ])
    return destination


def denoise_audio(source: Path, destination: Path) -> Path:
    """Run DeepFilterNet when available, keeping the original untouched."""
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
