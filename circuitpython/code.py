# SPDX-FileCopyrightText: 2021, 2022 Cedar Grove Maker Studios
# SPDX-License-Identifier: MIT

"""
nau7802_simpletest.py  2022-04-23 1.0.1  Cedar Grove Maker Studios

Instantiates both NAU7802 channels with default gain of 128 and sample
average count of 100.
"""

import time
import board
import neopixel
from cedargrove_nau7802 import NAU7802

pixel_pin = board.NEOPIXEL
num_pixels = 1

pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.1, auto_write=False)


# Instantiate 24-bit load sensor ADC; two channels, default gain of 128
nau7802 = NAU7802(board.I2C(), address=0x2A, active_channels=2)


def zero_channel():
    """Initiate internal calibration for current channel; return raw zero
    offset value. Use when scale is started, a new channel is selected, or to
    adjust for measurement drift. Remove weight and tare from load cell before
    executing."""
    print(
        "channel %1d calibrate.INTERNAL: %5s"
        % (nau7802.channel, nau7802.calibrate("INTERNAL"))
    )
    print(
        "channel %1d calibrate.OFFSET:   %5s"
        % (nau7802.channel, nau7802.calibrate("OFFSET"))
    )
    zero_offset = read_raw_value(100)  # Read 100 samples to establish zero offset
    print("...channel %1d zeroed" % nau7802.channel)
    return zero_offset


def read_raw_value(samples=100):
    """Read and average consecutive raw sample values. Return average raw value."""
    sample_sum = 0
    sample_count = samples
    while sample_count > 0:
        if nau7802.available:
            sample_sum = sample_sum + nau7802.read()
            sample_count -= 1
    return int(sample_sum / samples)


# Instantiate and calibrate load cell inputs
print("*** Instantiate and calibrate load cell")
# Enable NAU7802 digital and analog power
enabled = nau7802.enable(True)
print("Digital and analog power enabled:", enabled)

pixels[0] = (128, 128, 128)
pixels.show()
print("REMOVE WEIGHTS FROM LOAD CELLS")
time.sleep(3)

nau7802.channel = 1
zero_channel()  # Calibrate and zero channel


print("READY")
boot_s = time.monotonic()
top = 0 # 520000
bottom = 100000 # weight of empty water bottle

# initial measure of full water bottle
pixels[0] = (0, 0, 255)
pixels.show()
while top < bottom :
    top = 0
    samples = 5
    if read_raw_value() > bottom :
        time.sleep(0.25)
        for i in range(0, samples):
            top += read_raw_value()
            time.sleep(0.05)
        top /= samples
    print("--- ", top, " ---")

duration_seconds = 60 * 60 * 2.5 # some hours
slope = -1.0 * (top - bottom)/duration_seconds
### Main loop: Read load cells and calculate red green status
ledMode = "steady"
led = "flash off"
ledColor = (0,0,0)
def checkVal(t):
    global ledMode, ledColor
    value = read_raw_value()
    line = slope * t + top
    # print("raw value: %7.0f line: %7.0f" % (value, line))
    if value > line:
        ledMode = "flash"
        ledColor = (255, 0, 0)
    else:
        ledMode = "steady"
        ledColor = (0, 255, 0)

def _timed(last, interval, t):
    return last + interval < t

def on_flash_timed(last, interval, t):
    return ledMode == "flash" and _timed(last, interval, t)

def on_steady(last, interval, t):
    return ledMode == "steady"

def green_on(t):
    pixels[0] = (0, 255, 0)
    pixels.show()

def red_toggle(t):
    global led
    if led == "flash off":
        pixels[0] = (255, 0, 0)
        led = "flash on"
    else:
        pixels[0] = (0, 0, 0)
        led = "flash off"

    pixels.show()

happenings = [{
    'guard': _timed,
    'interval': 2.0,
    'last': 0.0,
    'fn': checkVal
},
{
    'guard': on_flash_timed,
    'interval': 0.5,
    'last': 0.0,
    'fn': red_toggle
},
{
    'guard': on_steady,
    'interval': 0.2,
    'last': 0.0,
    'fn': green_on
}
]

while True:
    this_s = time.monotonic() - boot_s
    for h in happenings:
        if h['guard'](h['last'], h['interval'], this_s) :
            h['fn'](this_s)
            h['last'] = this_s
    time.sleep(0.05)
# why the "Code stopped by auto-reload. Reloading soon." randomly?