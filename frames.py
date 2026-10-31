import shutil
import subprocess
from pathlib import Path

FRAME_DIR = Path(__file__).resolve().parent.parent / "frames"

def extract_frame(video_path: Path, at_s: float = 1.0) -> Path:
    """Extract a single video frame as a 16 bit grayscale TIFF for autofocus"""
    if at_s < 0:
        raise ValueError("Frame timestamp cannot be negative")

    video = Path(video_path)
    if not video.is_file():
        raise FileNotFoundError(video)

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("FFmpeg not found in PATH")

    FRAME_DIR.mkdir(parents=True, exist_ok=True)

    frame = FRAME_DIR / f"{video.stem}_{round(at_s * 1000)}ms.tif"
    if frame.exists():
        raise FileExistsError(frame)

    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel", "error",
        "-n",
        "-ss", str(at_s),
        "-i", str(video),
        "-map", "0:v:0",
        "-frames:v", "1",
        "-pix_fmt", "gray16le",
        "-c:v", "tiff",
        "-update", "1",
        str(frame),
    ]

    try:
        subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        frame.unlink(missing_ok=True)
        raise RuntimeError(
            f"Frame extraction failed: {getattr(exc, 'stderr', '') or exc}"
        ) from exc

    if not frame.is_file() or frame.stat().st_size == 0:
        frame.unlink(missing_ok=True)
        raise RuntimeError("Extracted frame is missing or empty")

    return frame