from . import adb, feeder, focus, server

def confirm(message: str) -> bool:
    """Enter to continue, Q to cancel"""
    while True:
        answer = input(f"{message} [Enter/Q]: ").strip().upper()

        if answer == "":
            return True
        if answer == "Q":
            return False

        print("Press Enter to continue or Q to cancel")

def main() -> None:
    if adb.run_adb("get-state") != "device":
        raise RuntimeError("ADB phone not connected")
    
    print(f"Connected; {adb.DEVICE}")
    print("Open Pro Video and show the manual focus ruler")
    print("Set focus to 1.00 and wait until it settles")

    if not confirm("Ready to home focus?"):
        return
    
    controller = focus.FocusController()
    controller.home_zero()

    if not confirm("Confirm phone displays 0.00"):
        return

    controller.move_to(100)

    if not confirm("Confirm phone displays 0.50"):
        return

    httpd = server.start(controller)

    try: 
        feeder.run(server.AlpacaHandler.device)
    finally:
        print("Stopping Alpaca server...")
        httpd.shutdown()
        httpd.server_close()

if __name__ == "__main__":
    main()