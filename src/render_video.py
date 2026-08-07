"""Render a captioned 1080p baseline using the selected narration audio."""

from pathlib import Path
import subprocess
import imageio_ffmpeg

def render_baseline(video: Path, narration: Path, captions: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    subtitle_path = captions.resolve().as_posix().replace(":", "\\:")
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", str(video), "-i", str(narration), "-vf", f"scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,subtitles='{subtitle_path}'", "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-shortest", str(output)], check=True)
