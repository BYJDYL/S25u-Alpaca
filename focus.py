import time
from . import adb

FOCUS_Y = 2360
RIGHT_STEP_X = 753
LEFT_EDGE_X = 304
HOME_TAPS = 8
TAP_DELAY_S = 0.4

def step_right() -> None:
    """Move Samsung manual focus one full tick to the right."""
    adb.tap(RIGHT_STEP_X, FOCUS_Y)

def home_zero() -> None:
    """Home to 0.00. Requires manual focus slider to be open."""
    for _ in range(HOME_TAPS):
        adb.tap(LEFT_EDGE_X, FOCUS_Y)
        time.sleep(TAP_DELAY_S)