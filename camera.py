import time

CAMERA_PACKAGE = "com.sec.android.app.camera"
START_ID = CAMERA_PACKAGE + ":id/center_button_container"
STOP_ID = CAMERA_PACKAGE + ":id/stop_button"

def record_clip(device, duration_s: float) -> None:
    """Record a short video in pro video mode"""
    if duration_s <= 0:
        raise ValueError("Recording duration must be positive")

    if device.app_current().get("package") != CAMERA_PACKAGE:
        raise RuntimeError("Samsung Camera is not in the foreground")

    start = device(resourceId=START_ID)
    stop = device(resourceId=STOP_ID)

    if not start.wait(timeout=5):
        raise RuntimeError("Start recording control not found")

    try:
        start.click()
        if not stop.wait(timeout=10):
            raise RuntimeError("Recording state not detected")
        
        time.sleep(duration_s)

    finally:
        if stop.wait(timeout=5):
            stop.click()

    if not start.wait(timeout=15):
        raise RuntimeError("Camera did not return to idle")