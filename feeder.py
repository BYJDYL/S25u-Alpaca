import uiautomator2 as u2

from . import camera, media, pipp
from .adb import DEVICE

def run(focuser) -> None:
    device = u2.connect(DEVICE)
    device.jsonrpc.setConfigurator({
        "waitForIdleTimeout": 0,
        "waitForSelectorTimeout": 0,
    })

    count = 0

    print("\nNINA bridge ready")
    print("Enter = fresh focus image after NINA requests exposure")
    print("R 10 = ten second MP4; R120 = two minute MP4")
    print("Q = quit")

    while True:
        instruction = input("\nBridge command: ").strip()
        if instruction.upper() == "Q":
            return

        focus_frame = instruction == ""
        if focus_frame:
            duration = 2.0
        else:
            parts = instruction.upper().split()
            if not (1 <= len(parts) <= 2 and parts[0] == "R"):
                print("Unknown command")
                continue

            try:
                duration = float(parts[1]) if len(parts) == 2 else 120.0
            except ValueError:
                print("Invalid recording duration")
                continue

            if duration <= 0:
                print("Recording duration must be positive")
                continue

        try:
            if focuser.get("ismoving"):
                raise RuntimeError("Wait for the focuser to stop moving")

            position = focuser.get("position")

            if focus_frame and not focuser.get("connected"):
                raise RuntimeError("Connect the Alpaca focuser in NINA first")

            print(f"Focus position: {position} | recording {duration:g}s")

            before = media.list_videos()
            camera.record_clip(device, duration)

            filename = media.wait_for_new_video(before, timeout_s=60)
            video = media.pull_video(filename, timeout_s=900 if duration > 30 else 300,)
            print("Saved MP4:", video)

            if focus_frame:
                if (focuser.get("ismoving") or focuser.get("position") != position):
                    raise RuntimeError("Focus changed during capture; refusing to publish image")
                
                count += 1
                image = pipp.make_focus_image(video, count)
                print(f"NINA image at position {position}:", image)

        except Exception as exc:
            print("Capture/processing failed:", exc)
            if focus_frame:
                print("If NINA is waiting, stop autofocus before retrying")