import time
from pathlib import Path

from . import adb

VIDEO_DIR = "/sdcard/DCIM/Camera"
CAPTURE_DIR = Path(__file__).resolve().parent.parent / "captures"

def list_videos() -> set[str]:
    """Returns MP4 filenames in the camera directory"""
    output = adb.run_adb("shell", "ls", "-1", VIDEO_DIR)
    return {
        name for name in output.splitlines()
        if name.lower().endswith(".mp4")
    }

def wait_for_new_video(before: set[str], timeout_s: float = 10.0) -> str:
    """Waits for exactly one new MP4 after recording as stopped"""
    if timeout_s <= 0:
        raise ValueError("Timeout msut be positive")

    deadline = time.monotonic() + timeout_s

    while True:
        new_videos = list_videos() - before

        if len(new_videos) > 1:
            raise RuntimeError(f"Expected on new MP4, found: {sorted(new_videos)}")

        if new_videos:
            return next(iter(new_videos))

        if time.monotonic() >= deadline:
            raise TimeoutError("No new MP4 appeared on the phone")

        time.sleep(0.5)

def pull_video(filename: str, output_dir: Path | None = None, timeout_s: float = 120.0,) -> Path:
    """Copy MP4 from phone to PC"""
    if (not filename or "/" in filename or "\\" in filename or not filename.lower().endswith(".mp4")):
         raise ValueError(f"Invalid MP4 filename: {filename!r}")

    if timeout_s <= 0:
         raise ValueError("Timeout must be positive")

    directory = CAPTURE_DIR if output_dir is None else Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    local_path = directory / filename

    if local_path.exists():
          raise FileExistsError(local_path)

    try:   
        adb.run_adb("pull", f"{VIDEO_DIR}/{filename}", str(local_path), timeout=timeout_s,)

        if not local_path.is_file() or local_path.stat().st_size == 0:
            raise RuntimeError("Transferred MP4 is missing or empty: {local_path}")

    except Exception:
        local_path.unlink(missing_ok=True)
        raise

    return local_path