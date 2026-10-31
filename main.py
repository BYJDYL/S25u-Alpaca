from . import adb, focus, server

def main() -> None:
    state = adb.run_adb("get-state")

    if state != "device":
        raise RuntimeError(f"Unexpected ADB connection state: {state!r}")

    print(f"Connected; {adb.DEVICE}")
    print("Model:", adb.run_adb("shell", "getprop", "ro.product.model"))
    print("Display:", adb.run_adb("shell", "wm", "size"))

    print("\nOpen Samsung Pro Video manual focus slider.")
    print("Set focus to 1.00.")

    if input("Type HOME to move focus to zero: ").strip() == "HOME":
        controller = focus.FocusController()
        controller.home_zero()

        if input ("Confirm phone displayes 0.00 type ZERO: ").strip() != "ZERO":
            return

        server.serve(controller)
    else:
        print("Home skipped.")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        raise SystemExit(str(exc))