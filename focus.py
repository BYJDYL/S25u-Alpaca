import time
from . import adb

FOCUS_Y = 2360
CENTER_X = 720
LEFT_EDGE_X = 304
RIGHT_EDGE_X = 1138

PIXELS_PER_HALF_STEP = 16
MAX_TAP_STEPS = 26 # 0.13 focus movement
HOME_TAPS = 8
TAP_DELAY_S = 0.4

class FocusController:
    def __init__(self) -> None:
        self.position: int | None = None

    def home_zero(self) -> None:
        """Use 0.00 as the focus reference"""
        self.position = None

        for _ in range(HOME_TAPS):
            adb.tap(LEFT_EDGE_X, FOCUS_Y)
            time.sleep(TAP_DELAY_S)

        self.position = 0

    def move_to(self, target: int) -> None:
        """Move to focus position from 0 to 200 (0.005 per unit) in least amount of taps needed"""
        if not 0 <= target <= 200:
            raise ValueError(f"Target must be between 0 and 200")

        if self.position is None:
            raise RuntimeError("Focus position unknown. Home first")

        difference = target - self.position
        if difference == 0:
            return

        direction = 1 if difference > 0 else - 1
        full, remainder = divmod(abs(difference), MAX_TAP_STEPS)

        movements = [direction * MAX_TAP_STEPS] * full
        if remainder:
            movements.append(direction * remainder)

        try:
            for movement in movements:
                x = CENTER_X + movement * PIXELS_PER_HALF_STEP + direction
                x = max(LEFT_EDGE_X, min(RIGHT_EDGE_X, x))

                adb.tap(x, FOCUS_Y)
                time.sleep(TAP_DELAY_S)
                self.position += movement

        except Exception:
            self.position = None
            raise