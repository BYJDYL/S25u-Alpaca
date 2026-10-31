from . import adb, feeder, focus, server

def main() -> None:
    if adb.run_adb("get-state") != "device":
        raise RuntimeError("ADB phone not connected")
    
    print(f"Connected; {adb.DEVICE}")
    print("Open Pro Video and show the manual focus ruler")
    print("Set focus to 1.00 and wait until it settles")

    if input("Type HOME: ").strip().upper() != "HOME":
        return
    
    controller = focus.FocusController()
    controller.home_zero()

    if input ("Confirm phone displayes 0.00 type ZERO: ").strip() != "ZERO":
        return

    controller.move_to(100)

    if input("Confirm phone displays 0.50; type MID: ").strip().upper() != "MID":
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