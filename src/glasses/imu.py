"""MPU-6050 motion sensor: raw readings and head tilt (pitch and roll).

Run on the Pi to print live values:
    cd src && python -m glasses.imu
"""

from __future__ import annotations

import math
import struct
import time
from dataclasses import dataclass

I2C_BUS = 1
ADDRESS = 0x68

# Registers (MPU-6050 register map)
PWR_MGMT_1 = 0x6B
CONFIG = 0x1A
GYRO_CONFIG = 0x1B
ACCEL_CONFIG = 0x1C
ACCEL_XOUT_H = 0x3B
WHO_AM_I = 0x75

# Default ranges: +-2 g and +-250 deg/s
ACCEL_LSB_PER_G = 16384.0
GYRO_LSB_PER_DPS = 131.0


@dataclass
class Reading:
    """One sample. Acceleration in g, rotation rate in degrees per second."""

    ax: float
    ay: float
    az: float
    gx: float
    gy: float
    gz: float
    temp_c: float


def accel_tilt(ax: float, ay: float, az: float) -> tuple[float, float]:
    """Pitch and roll in degrees from gravity alone.

    Pitch is rotation around the sensor's Y axis and roll is rotation around its
    X axis (the arrows printed on the GY-521). Flat and level gives (0, 0).
    Which one is nodding and which is tilting toward a shoulder depends on how
    the board is mounted on the frame (#12).
    """
    pitch = math.degrees(math.atan2(-ax, math.sqrt(ay * ay + az * az)))
    roll = math.degrees(math.atan2(ay, az))
    return pitch, roll


class MPU6050:
    def __init__(self, bus=None, address: int = ADDRESS):
        if bus is None:
            from smbus2 import SMBus

            bus = SMBus(I2C_BUS)
        self.bus = bus
        self.address = address
        self.gyro_bias = (0.0, 0.0, 0.0)

        # Wake up (the chip starts asleep), use the gyro X clock for stability.
        self.bus.write_byte_data(self.address, PWR_MGMT_1, 0x01)
        # Low-pass filter at ~44 Hz to smooth out vibration.
        self.bus.write_byte_data(self.address, CONFIG, 0x03)
        self.bus.write_byte_data(self.address, GYRO_CONFIG, 0x00)
        self.bus.write_byte_data(self.address, ACCEL_CONFIG, 0x00)
        time.sleep(0.05)

    def who_am_i(self) -> int:
        return self.bus.read_byte_data(self.address, WHO_AM_I)

    def read(self) -> Reading:
        raw = bytes(self.bus.read_i2c_block_data(self.address, ACCEL_XOUT_H, 14))
        ax, ay, az, t, gx, gy, gz = struct.unpack(">7h", raw)
        bx, by, bz = self.gyro_bias
        return Reading(
            ax=ax / ACCEL_LSB_PER_G,
            ay=ay / ACCEL_LSB_PER_G,
            az=az / ACCEL_LSB_PER_G,
            gx=gx / GYRO_LSB_PER_DPS - bx,
            gy=gy / GYRO_LSB_PER_DPS - by,
            gz=gz / GYRO_LSB_PER_DPS - bz,
            temp_c=t / 340.0 + 36.53,
        )

    def calibrate_gyro(self, samples: int = 200, delay: float = 0.005) -> None:
        """Measure gyro drift while the sensor is held still and subtract it from now on."""
        self.gyro_bias = (0.0, 0.0, 0.0)
        sx = sy = sz = 0.0
        for _ in range(samples):
            r = self.read()
            sx, sy, sz = sx + r.gx, sy + r.gy, sz + r.gz
            time.sleep(delay)
        self.gyro_bias = (sx / samples, sy / samples, sz / samples)


class TiltTracker:
    """Smooth pitch and roll with a complementary filter.

    The gyro is smooth but drifts over time; the accelerometer never drifts but
    jumps around whenever the head moves. Blending the two gives a steady angle.
    `alpha` is how much to trust the gyro on each step (0.98 is typical).
    """

    def __init__(self, alpha: float = 0.98):
        self.alpha = alpha
        self.pitch: float | None = None
        self.roll: float | None = None

    def update(self, r: Reading, dt: float) -> tuple[float, float]:
        acc_pitch, acc_roll = accel_tilt(r.ax, r.ay, r.az)
        if self.pitch is None or self.roll is None:
            self.pitch, self.roll = acc_pitch, acc_roll
        else:
            a = self.alpha
            self.pitch = a * (self.pitch + r.gy * dt) + (1 - a) * acc_pitch
            self.roll = a * (self.roll + r.gx * dt) + (1 - a) * acc_roll
        return self.pitch, self.roll


def main() -> None:
    imu = MPU6050()
    print(f"WHO_AM_I = 0x{imu.who_am_i():02X} (expected 0x68)")
    print("Calibrating gyro, keep the sensor still...")
    imu.calibrate_gyro()

    tracker = TiltTracker()
    last = time.monotonic()
    try:
        while True:
            now = time.monotonic()
            r = imu.read()
            pitch, roll = tracker.update(r, now - last)
            last = now
            print(
                f"pitch {pitch:7.1f}  roll {roll:7.1f}  |  "
                f"accel g {r.ax:5.2f} {r.ay:5.2f} {r.az:5.2f}  "
                f"gyro dps {r.gx:7.1f} {r.gy:7.1f} {r.gz:7.1f}"
            )
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
