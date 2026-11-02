# Wiring

Pin connections for every part on the Raspberry Pi Zero 2 W. Pin numbers are **physical header pins** (1 to 40), with the BCM GPIO name in brackets. Pin 1 is the corner pin next to the microSD slot, marked by the square pad.

> This is the planned wiring for bring-up. When something gets wired differently, update this file in the same PR so it always matches the real glasses.

## Pi Zero 2 W header (only the pins we use)

| Pin | Name | Used by |
|---|---|---|
| 1 | 3.3V | OLED VCC, microphone VDD |
| 2 | 5V | MAX98357A VIN, MT3608 output (battery power) |
| 3 | GPIO2 (SDA) | OLED SDA, MPU-6050 SDA |
| 5 | GPIO3 (SCL) | OLED SCL, MPU-6050 SCL |
| 6 | GND | OLED GND, MT3608 output GND |
| 9 | GND | MPU-6050 GND |
| 12 | GPIO18 (I2S BCLK) | MAX98357A BCLK, microphone SCK |
| 14 | GND | MAX98357A GND |
| 17 | 3.3V | MPU-6050 VCC |
| 20 | GND | Microphone GND, microphone L/R |
| 35 | GPIO19 (I2S LRCLK) | MAX98357A LRC, microphone WS |
| 38 | GPIO20 (I2S DIN) | Microphone SD |
| 40 | GPIO21 (I2S DOUT) | MAX98357A DIN |

```
            3.3V  [ 1] [ 2]  5V
     SDA  GPIO2   [ 3] [ 4]  5V
     SCL  GPIO3   [ 5] [ 6]  GND
                  [ 7] [ 8]
             GND  [ 9] [10]
                  [11] [12]  GPIO18  BCLK
                  [13] [14]  GND
                  [15] [16]
            3.3V  [17] [18]
                  [19] [20]  GND
                   ...
   LRCLK  GPIO19  [35] [36]
                  [37] [38]  GPIO20  I2S DIN (mic)
             GND  [39] [40]  GPIO21  I2S DOUT (amp)
```

## I2C bus (bus 1)

The OLED and the MPU-6050 share the same two I2C wires. Both boards have their own pull-up resistors, so no extra resistors are needed.

### 0.96" OLED (SSD1306, 128x64), address `0x3C`

| OLED pin | Pi pin |
|---|---|
| VCC | 1 (3.3V) |
| GND | 6 (GND) |
| SCL | 5 (GPIO3) |
| SDA | 3 (GPIO2) |

### MPU-6050 (GY-521), address `0x68`

| GY-521 pin | Pi pin |
|---|---|
| VCC | 17 (3.3V) |
| GND | 9 (GND) |
| SCL | 5 (GPIO3) |
| SDA | 3 (GPIO2) |
| AD0 | Not connected (pulled low on the board, which gives `0x68`) |
| XDA, XCL, INT | Not connected |

Check both with `i2cdetect -y 1`. You should see `3c` and `68` in the grid.

## I2S audio

The amplifier and the microphone share the clock lines (BCLK and LRCLK). The amp uses the Pi's data out line and the mic uses the data in line.

### MAX98357A amplifier

| MAX98357A pin | Connects to |
|---|---|
| VIN | Pi pin 2 (5V) |
| GND | Pi pin 14 (GND) |
| BCLK | Pi pin 12 (GPIO18) |
| LRC | Pi pin 35 (GPIO19) |
| DIN | Pi pin 40 (GPIO21) |
| GAIN | Not connected (9 dB default) |
| SD | Not connected (on, mono mix of left and right) |
| Speaker + / - | Speaker terminals |

### I2S MEMS microphone (INMP441 style)

**3.3V only. 5V will destroy the microphone.**

| Mic pin | Pi pin |
|---|---|
| VDD | 1 (3.3V) |
| GND | 20 (GND) |
| SCK | 12 (GPIO18) |
| WS | 35 (GPIO19) |
| SD | 38 (GPIO20) |
| L/R | 20 (GND), so the mic sends on the left channel |

Turning on I2S audio in software is part of issues #7 and #8.

## Power

```
LiPo + ──► TP4056 (charger) ──► switch ──► MT3608 VIN+ ── MT3608 VOUT+ ──► Pi pin 2 (5V)
LiPo - ──► TP4056          ─────────────► MT3608 VIN- ── MT3608 VOUT- ──► Pi pin 6 (GND)
```

| From | To |
|---|---|
| LiPo + / - | TP4056 B+ / B- |
| TP4056 OUT+ | Power switch, then MT3608 VIN+ |
| TP4056 OUT- | MT3608 VIN- |
| MT3608 VOUT+ | Pi pin 2 (5V) |
| MT3608 VOUT- | Pi pin 6 (GND) |

**Before connecting the Pi, set the MT3608 output to 5.0V with a multimeter.** Turn the small brass screw on the MT3608 to adjust it. It often ships set to a higher voltage, which would kill the Pi.

Feeding 5V into pin 2 skips the Pi's input fuse, so double-check polarity before you power it on. While developing, power the Pi from the **PWR** micro-USB port instead and leave the battery disconnected.

## Software settings

These lines go in `/boot/firmware/config.txt` on the Pi:

```
dtparam=i2c_arm=on    # set by raspi-config > Interface Options > I2C
```

The I2S audio settings will be added here once #7 and #8 are done.
