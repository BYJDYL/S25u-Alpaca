import itertools
import json
import socket
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from typing import ClassVar

from . import adb

HTTP_PORT = 11111
DISCOVERY_PORT = 32227
DEVICE_NAME = "S25u-Alpaca Focuser"
DEVICE_ID = str(uuid.uuid5(uuid.NAMESPACE_OID, f"S25u-Alpaca:{uuid.getnode()}"))
NO_VALUE = object()

class AlpacaError(Exception):
    def __init__(self, number: int, message: str):
        self.number = number
        super().__init__(message)

class FocuserDevice:
    def __init__(self, controller):
        self.controller = controller
        self.connected = False
        self.moving = False
        self.error = None
        self.lock = threading.Lock()

    def set_connected(self, value: bool):
        with self.lock:
            if self.moving: 
                raise AlpacaError(1035, "Cannot change connection during a move")

            if value and self.controller.position is None:
                raise AlpacaError(1026, "Focus must be homed first")

            if value and adb.run_adb("get-state") != "device":
                raise AlpacaError(0x500, "ADB device is not connected")

            self.connected = value

    def start_move(self, target: int):
        with self.lock:
            if not self.connected:
                raise AlpacaError(1031, "Focuser is not connected")
            if self.error:
                raise AlpacaError(0x500, self.error)
            if self.moving:
                raise AlpacaError(1035, "Focus move is already in progress")
            if self.controller.position is None:
                raise AlpacaError(1026, "Focus position unknown")
            if not 0 <= target <= 200:
                raise AlpacaError(1025, "Position must be 0..200")
            if target == self.controller.position:
                return
            self.moving = True

        try:
            threading.Thread(target=self._move, args=(target,), daemon=True).start()
        except Exception:
            with self.lock:
                self.moving = False
            raise

    def _move(self, target: int):
        try:
            self.controller.move_to(target)
        except Exception as exc:
            with self.lock:
                self.error = f"Focus move failed: {exc}"
        finally:
            with self.lock:
                self.moving = False

    def get(self, name: str):
        with self.lock:
            if name in ("ismoving", "position") and self.error:
                raise AlpacaError(0x500, self.error)

            values = {
                "connected": self.connected,
                "ismoving": self.moving,
                "position": self.controller.position,
            }

            if name in values:
                if values[name] is None:
                    raise AlpacaError(1026, "Focus position unkonwn")
                return values[name]

            values = {
                "absolute": True,
                "maxstep": 200,
                "maxincrement": 200,
                "tempcompavailable": False,
                "tempcomp": False,
                "name": DEVICE_NAME,
                "description": "Samsung S25 Ultra manual focus through ADB",
                "driverinfo": "S25u-Alpaca Python Focuser",
                "driverversion": "0.1",
                "interfaceversion": 3,
                "supportedactions": [],
            }

            if name in values:
                return values[name]
            if name in ("stepsize", "temperature"):
                raise AlpacaError(1024, f"{name} is not available")
            raise KeyError(name)

class AlpacaHandler(BaseHTTPRequestHandler):
    device: ClassVar[FocuserDevice]
    transactions = itertools.count(1)

    def do_GET(self):
        self.handle_request("GET")

    def do_PUT(self):
        self.handle_request("PUT")

    def send_json(self, client_txid, value=NO_VALUE, error=0, message=""):
        payload = {
            "ClientTransactionID": client_txid,
            "ServerTransactionID": next(self.transactions),
            "ErrorNumber": error,
            "ErrorMessage": message,
        }

        if value is not NO_VALUE:
            payload["Value"] = value

        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def handle_request(self, method):
        url = urlsplit(self.path)
        params = parse_qs(url.query, keep_blank_values=True)

        if method == "PUT":
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 <= length <= 4096:
                self.send_error(413)
                return
            params.update(parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True))

        params = {k.lower(): v[-1] for k, v in params.items()}

        client_txid = 0

        try:
            client_txid = int(params.get("clienttransactionid", "0"))

            if method == "GET":
                if url.path == "/management/apiversions":
                    return self.send_json(client_txid, [1])

                if url.path == "/management/v1/description":
                    return self.send_json(client_txid, {
                        "ServerName": "S25u-Alpaca",
                        "Manufacturer": "BYJDYL",
                        "ManufacturerVersion": "0.1",
                        "Location": "Windows PC",
                    })

                if url.path == "/management/v1/configureddevices":
                    return self.send_json(client_txid, [{
                        "DeviceName": DEVICE_NAME,
                        "DeviceType": "Focuser",
                        "DeviceNumber": 0,
                        "UniqueID": DEVICE_ID,
                    }])

            prefix = "/api/v1/focuser/0/"
            if not url.path.startswith(prefix):
                self.send_error(404, "Unknown endpoint")
                return

            command = url.path[len(prefix):]
            if method == "GET":
                return self.send_json(client_txid, self.device.get(command))

            if command == "connected":
                value = params.get("connected", "").lower()
                if value not in ("true", "false"):
                    raise ValueError("Connected must be true or false")
                
                self.device.set_connected(value == "true")

            elif command == "move":
                self.device.start_move(int(params["position"]))

            elif command == "halt":
                raise AlpacaError(1024, "Halt is not implemented")

            elif command == "tempcomp":
                raise AlpacaError(1024, "Temperature compensation unavailable")

            else:
                self.send_error(404, "Unknown focuser command")
                return

            self.send_json(client_txid)

        except (ValueError, KeyError, UnicodeDecodeError):
            self.send_error(400, "Invalid or missing request parameter")
        except AlpacaError as exc:
            self.send_json(client_txid, error=exc.number, message=str(exc))
        except RuntimeError as exc:
            self.send_json(client_txid, error=0x500, message=str(exc))

def discovery_loop():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
        udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp.bind(("", DISCOVERY_PORT))

        while True:
            request, address = udp.recvfrom(1024)
            if request[:16] == b"alpacadiscovery1":
                udp.sendto(
                    json.dumps({"AlpacaPort": HTTP_PORT}).encode(), 
                    address,
                ) 

def start(controller):
    """Start the Alpaca focuser without blocking capture console"""
    httpd = ThreadingHTTPServer(("", HTTP_PORT), AlpacaHandler)
    AlpacaHandler.device = FocuserDevice(controller)
    
    threading.Thread(target=discovery_loop, daemon=True).start()
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    print(f"Alpaca focuser listening on port {HTTP_PORT}")
    return httpd

def serve(controller):
    AlpacaHandler.device = FocuserDevice(controller)
    threading.Thread(target=discovery_loop, daemon=True).start()

    with ThreadingHTTPServer(("", HTTP_PORT), AlpacaHandler) as httpd:
        print(f"Alpaca focuser on port {HTTP_PORT}. Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Server stopped")