"""Entry point: read head tilt from the IMU and show it live on the OLED.

    cd src && python -m glasses.main            # normal screen
    cd src && python -m glasses.main --mirror   # flipped for the beam splitter
"""

from __future__ import annotations

import argparse
import time

from glasses.display import Display
from glasses.imu import MPU6050, TiltTracker


def tilt_lines(pitch: float, roll: float) -> list[str]:
    return [
        "Head tilt",
        "",
        f"Pitch {pitch:6.1f} deg",
        f"Roll  {roll:6.1f} deg",
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Show live head tilt on the OLED.")
    parser.add_argument("--mirror", action="store_true", help="flip for the beam splitter")
    parser.add_argument("--hz", type=float, default=20.0, help="screen updates per second")
    args = parser.parse_args()

    display = Display(mirror=args.mirror)
    imu = MPU6050()

    display.show_text("Calibrating... keep still")
    imu.calibrate_gyro()

    tracker = TiltTracker()
    period = 1.0 / args.hz
    last = time.monotonic()
    try:
        while True:
            now = time.monotonic()
            pitch, roll = tracker.update(imu.read(), now - last)
            last = now
            display.show_lines(tilt_lines(pitch, roll))
            time.sleep(max(0.0, period - (time.monotonic() - now)))
    except KeyboardInterrupt:
        pass
    finally:
        display.clear()


if __name__ == "__main__":
    main()
