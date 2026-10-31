import subprocess

ADB_PATH = r"C:\Users\Y3J5bw\Desktop\scrcpy-win64-v5.0.1\adb.exe"
DEBUG_PORT = 41881
DEVICE = f"192.168.1.131:{DEBUG_PORT}"

def run_adb(*arguments: str, timeout: float = 10.0) -> str:
    command = [ADB_PATH, "-s", DEVICE, *arguments]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"ADB executable not found: {ADB_PATH}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"ADB timed out after {timeout:g}s: {' '.join(arguments)}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(f"ADB command failed: {detail or f'exit code {exc.returncode}'}") from exc

    return result.stdout.strip()

def tap(x: int, y: int) -> None:
    """Send a tap event to the device at the specified coordinates."""
    run_adb("shell", "input", "tap", str(x), str(y))