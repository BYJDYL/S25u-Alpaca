import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import frames

ROOT = Path(__file__).resolve().parent.parent
STAGING = ROOT / "staging"
INBOX = ROOT / "nina-inbox"

def pipp_executable() -> str:
    configured = os.environ.get("PIPP_CORE")
    if configured:
        path = Path(configured.strip('"'))
        if path.is_file():
            return str(path)
        raise FileNotFoundError(f"PIPP_CORE does not exist: {path}")

    found = shutil.which("pipp_core.exe")
    if found:
        return found

    for path in(
        Path(r"C:\Program Files\PIPP\pipp_core.exe"),
        Path(r"C:\Program Files (x86)\PIPP\pipp_core.exe"),
    ):
        if path.is_file():
            return str(path)

    raise FileNotFoundError("Set PIPP_CORE to the full path of pipp_core.exe")

def run_tool(command: list[str], label: str, timeout: float = 120) -> None:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=timeout,
    )
    if result.returncode:
        details = (result.stderr + "\n" + result.stdout).strip()
        raise RuntimeError(f"{label} failed (exit {result.returncode}): {details[-1500:]}")

def make_focus_image(video: Path, sequence: int, crop: int = 512) -> Path:
    """Extract frame, centre planet using PIPP, publish to NINA"""
    source = frames.extract_frame(Path(video), at_s=1.0)

    STAGING.mkdir(exist_ok=True)
    INBOX.mkdir(exist_ok=True)

    destination = INBOX / f"af_{sequence:03d}_{Path(video).stem}.tif"
    if destination.exists():
        raise FileExistsError(destination)

    with tempfile.TemporaryDirectory(prefix="pipp_", dir=STAGING) as temp:
        run_tool([
            pipp_executable(),
            "-centre",
            f"-crop={crop}",
            "-frames=1",
            "-bmp",
            f"-outdir={temp}",
            str(source),
        ], "PIPP",)

        outputs = sorted(Path(temp).rglob("*.bmp"))
        if len(outputs) != 1:
            raise RuntimeError(
                f"PIPP returned {len(outputs)} BMP files; expected 1"
                "Check planet detection and CLI options"
            )

        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("FFmpeg not found in PATH")

        staged = STAGING / destination.name
        if staged.exists():
            raise FileExistsError(staged)

        try:
            run_tool([
                ffmpeg,
                "-hide_banner", "-loglevel", "error",
                "-n",
                "-i", str(outputs[0]),
                "-frames:v", "1",
                "-pix_fmt", "gray16le",
                "-c:v", "tiff",
                "-update", "1",
                str(staged),
            ], "FFmpeg",)

            if not staged.is_file() or staged.stat().st_size == 0:
                raise RuntimeError("Centred TIFF was not created")

            os.replace(staged, destination)
        except Exception:
            staged.unlink(missing_ok=True)
            raise

    return destination