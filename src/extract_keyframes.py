"""Extract periodic reference frames from the source video for visual review."""

from pathlib import Path
import subprocess
import imageio_ffmpeg

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_VIDEO = PROJECT_ROOT / "data" / "input" / "input_video.mp4.mp4"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "keyframes"

def extract_keyframes(interval_seconds: int = 20) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", str(SOURCE_VIDEO), "-vf", f"fps=1/{interval_seconds}", "-q:v", "2", str(OUTPUT_DIR / "frame_%03d.jpg")], check=True)

if __name__ == "__main__":
    extract_keyframes()
