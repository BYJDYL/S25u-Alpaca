from . import adb

FOCUS_Y = 2360
RIGHT_STEP_X = 753

def step_right() -> None:
    """Move Samsung manual focus one full tick to the right."""
    adb.tap(RIGHT_STEP_X, FOCUS_Y)