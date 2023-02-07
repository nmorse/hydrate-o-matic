# hydrate-o-matic hydrate-glide-path
# circuitpython 7.3.2
import time
import board
import neopixel
from cedargrove_nau7802 import NAU7802

import displayio
import terminalio
from adafruit_display_text import label
from adafruit_display_shapes.line import Line
import adafruit_displayio_ssd1306

displayio.release_displays()

oled_reset = board.D9

# Use for I2C
i2c = board.I2C()
display_bus = displayio.I2CDisplay(i2c, device_address=0x3C, reset=oled_reset)

WIDTH = 128
HEIGHT = 32  # Change to 64 if needed
BORDER = 1

display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)

# Make a splash display Group
splash = displayio.Group()
display.show(splash)
# Draw a label
text = "hydrate-glide-path"
text_area = label.Label(
    terminalio.FONT, text=text, color=0xffffff, x=20, y=HEIGHT // 2 - 1
)
splash.append(text_area)

# Make a graph display Group 
graph = displayio.Group()

color_bitmap2 = displayio.Bitmap(WIDTH, HEIGHT, 1)
color_palette2 = displayio.Palette(1)
color_palette2[0] = 0x000000 

bg_sprite2 = displayio.TileGrid(color_bitmap2, pixel_shader=color_palette2, x=0, y=0)
graph.append(bg_sprite2)
# draw a line
# graph.append(Line(0, 0, 127, 31, 0xffffff))
lastX = 0
lastY = 0

def mapRange(val, in_min, in_max, out_min, out_max) :
  return (val - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;

def addLine(t, level):
    global lastX, lastY
    if level < bottom :
        return
    toX = int(mapRange( t, 0, duration_seconds, 0, 127))
    if not toX > lastX + 2 :
        return
    toY = int(mapRange(level, bottom, top, 31, 0))
    print(lastX, lastY, toX, toY)
    graph.append(Line(lastX, lastY, toX, toY, 0xffffff))
    lastX = toX
    lastY = toY

# Make the display context
darkGroup = displayio.Group()
bg_sprite3 = displayio.TileGrid(color_bitmap2, pixel_shader=color_palette2, x=0, y=0)
darkGroup.append(bg_sprite3)

bg_sprite2 = displayio.TileGrid(color_bitmap2, pixel_shader=color_palette2, x=0, y=0)

def touchEventTimer(happeningId) :
    global happenings, boot_s    
    for h in happenings:
        if h["id"] == happeningId:
            h["last"] = time.monotonic() - boot_s
            return
    print("happening Id", happeningId, "not found")

def displayMsg(msgs):
    print(msgs)
    messages = len(msgs)
    while len(splash) :
        splash.pop()
    i = 1
    for m in msgs :
        text_area = label.Label(
            terminalio.FONT, text=m, color=0xffffff, x=1, y=(HEIGHT // (2 * messages) * i * 2) + ((6 - messages) * -1) - 3
        )
        splash.append(text_area)
        i += 1
    display.show(splash)
    touchEventTimer("screen_off_timer")

from digitalio import DigitalInOut, Direction, Pull

# buttons Left and Right
btnL = DigitalInOut(board.A3)
btnL.direction = Direction.INPUT
btnL.pull = Pull.DOWN
btnR = DigitalInOut(board.D2)
btnR.direction = Direction.INPUT
btnR.pull = Pull.UP
btnL_state = '' # ['', 'click', 'long-press', 'dbl_click']
btnR_state = ''
btnL_acc_s = 0 # accumulate button down seconds 
btnR_acc_s = 0

pixel_pin = board.NEOPIXEL
num_pixels = 1

pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.1, auto_write=False)

# Instantiate 24-bit load sensor ADC; two channels, default gain of 128
nau7802 = NAU7802(board.I2C(), address=0x2A, active_channels=2)

# zero out the scale to a reference value with no weight on the scale to start
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

def reDisplayMsg():
    if last_state == "green":
        displayMsg(["Great, all caught up"])
    if last_state == "red":
        displayMsg(["Time to take a sip"])
    if last_state == "sipping":
        displayMsg(["Sip", "then place back", "on scale"])
    if last_state == "end":
        displayMsg(["times up", "Hold down the left", "button to restart"])

def guard_timed(last, interval, t):
    return last + interval < t

def guard_on_flash_timed(last, interval, t):
    return ledMode == "flash" and guard_timed(last, interval, t)

def guard_on_sipping(last, interval, t):
    return ledMode == "sipping" and guard_timed(last, interval, t)

def sipping(t):
    global last_state
    if last_state != "sipping" and last_state != "end":
        displayMsg(["Sip", "then place back", "on scale"])
        last_state = "sipping"
    pixels[0] = (0, 0, 0)
    pixels.show()

def guard_on_steady(last, interval, t):
    return ledMode == "steady" and guard_timed(last, interval, t)

def green_on(t):
    global last_state
    if last_state != "green" and last_state != "end":
        displayMsg(["Great, all caught up"])
        last_state = "green"
    pixels[0] = (0, 255, 0)
    pixels.show()

def red_toggle(t):
    global led, last_state
    if last_state != "red" and last_state != "end":
        displayMsg(["Time to take a sip"])
        last_state = "red"
    if led == "flash off":
        pixels[0] = (255, 0, 0)
        led = "flash on"
    else:
        pixels[0] = (0, 0, 0)
        led = "flash off"
    pixels.show()

def screen_off(t) :
    print("display off")
    display.show(darkGroup)

long_press_s = 0.9
def check_buttons(t):
    global btnL_acc_s, btnL_state, btnR_acc_s, btnR_state
    if btnL.value: # button down
        if btnL_acc_s > 0.0 and (btnL_acc_s + long_press_s) < t and btnL_state == '':
            # print("left button long", (btnL_acc_s + long_press_s), t)
            btnL_state = 'long-click'
            btnL_acc_s = -1.0
        if btnL_acc_s == 0.0 :
            btnL_acc_s = t            
    else : # button up
        if btnL_acc_s == -1.0 and btnL_state == '':
            btnL_acc_s = 0.0
        if btnL_acc_s > 0.0 and (btnL_acc_s + long_press_s) >= t and btnL_state == '':
            # print("left button", btnL_acc_s, t)
            btnL_state = 'click'
            btnL_acc_s = 0.0
    
    if not btnR.value: # button down
        if btnR_acc_s > 0.0 and (btnR_acc_s + long_press_s) < t and btnR_state == '':
            # print("right button long", btnR_acc_s, t)
            btnR_state = 'long-click'
            btnR_acc_s = -1.0
        if btnR_acc_s == 0.0 :
            btnR_acc_s = t
    else : # button up
        if btnR_acc_s == -1.0 and btnR_state == '':
            btnR_acc_s = 0.0
        if btnR_acc_s > 0.0 and (btnR_acc_s + long_press_s) >= t and btnR_state == '':
            # print("right button", btnR_acc_s, t)
            btnR_state = 'click'
            btnR_acc_s = 0.0

def checkVal(t):
    global ledMode, level, last_state
    print("t > boot_s + duration_seconds", t, duration_seconds, (t > duration_seconds))
    if t > duration_seconds:
        ledMode = "end"
        last_state = "end"
        displayMsg(["times up", "Hold down the left", "button to restart"])
        return

    level = read_raw_value()
    addLine(t, level)
    # the classic y = m * x + b
    yIntercept = slope * t + top
    # print("raw value: %7.0f yIntercept: %7.0f" % (value, yIntercept))
    if level > yIntercept:
        ledMode = "flash"
        return
    if level > bottom:
        ledMode = "steady"
        return
    ledMode = "sipping"


happenings = [
{
    'id': "button_state",
    'guard': guard_timed,
    'interval': 0,
    'last': 0.0,
    'fn': check_buttons
},
{
    'id': "checkVal",
    'guard': guard_timed,
    'interval': 2.0,
    'last': 0.0,
    'fn': checkVal
},
{
    'id': "red_toggle",
    'guard': guard_on_flash_timed,
    'interval': 0.5,
    'last': 0.0,
    'fn': red_toggle
},
{
    'id': "green_on",
    'guard': guard_on_steady,
    'interval': 0.3,
    'last': 0.0,
    'fn': green_on
},
{
    'id': "sipping",
    'guard': guard_on_sipping,
    'interval': 0.3,
    'last': 0.0,
    'fn': sipping
},
{
    'id': "screen_off_timer",
    'guard': guard_timed,
    'interval': 30.0,
    'last': 0.0,
    'fn': screen_off
}
]
def findSlope(top, bottom, duration_seconds) :
    return (bottom - top)/duration_seconds
def findDuration(top, bottom, slope) :
    return (bottom - top)/slope




# Instantiate and calibrate load cell inputs
print("*** Instantiate and calibrate load cell")
# Enable NAU7802 digital and analog power
enabled = nau7802.enable(True)
print("Digital and analog power enabled:", enabled)

boot_s = time.monotonic()
pixels[0] = (128, 128, 128)
pixels.show()
print("REMOVE WEIGHTS FROM LOAD CELL")
displayMsg(["REMOVE WEIGHTS", "FROM THE SCALE", "(0 reference weight)"])
time.sleep(3)

nau7802.channel = 1
zero_channel()  # Calibrate and zero channel

bottom = 10000
top = 20000
slope = -40.0
duration_seconds = 10
ledMode = "steady"
led = "flash off"
ledColor = (0,0,0)
last_state = "init"

def setTop (bottom):
    displayMsg(["Ready: Place full", "water bottle on", "  the scale :)"])
    print("READY")
    tp = 0
    # measure of full water bottle
    pixels[0] = (0, 0, 255)
    pixels.show()
    while tp < bottom :
        tp = 0
        samples = 5
        if read_raw_value() > bottom :
            time.sleep(0.25)
            for i in range(0, samples):
                tp += read_raw_value()
                time.sleep(0.05)
            tp /= samples
    return tp

def startInit():
    global btnL_state, btnR_state, btnL_acc_s, btnR_acc_s, level, bottom, top, slope, duration_seconds, ledMode, led, ledColor, last_state, lastX, lastY
    btnL_state = '' # ['', 'click', 'long-press', 'dbl_click']
    btnR_state = ''
    btnL_acc_s = 0 # accumulate button down seconds 
    btnR_acc_s = 0
    ledMode = "steady"
    led = "flash off"
    ledColor = (0,0,0)
    last_state = "init"
    # start up 
    level = 0
    bottom = 10000
    top = setTop(bottom)
    # duration_seconds = 60 * 60 * 2.5 # some hours
    # slope = findSlope(top, bottom, duration_seconds)
    slope = -40.0
    duration_seconds = findDuration(top, bottom, slope)
    ### Main loop: Read load cells and calculate red green status
    while(len(graph) > 0):
        graph.pop()
    lastX = 0
    lastY = 0
    for h in happenings:
        h['last'] = 0.0
    return time.monotonic()

boot_s = startInit()

while True:
    this_s = time.monotonic() - boot_s
    for h in happenings:
        if h['guard'](h['last'], h['interval'], this_s) :
            h['fn'](this_s)
            h['last'] = this_s

    if btnL_state == 'click':
        btnL_state = ''
        displayMsg([" Time to empty", " {:.2f} minutes".format((time.monotonic() - duration_seconds - boot_s)/60)])
        
    if btnL_state == 'long-click':
        btnL_state = ''
        if last_state == 'end':
            boot_s = startInit()
        else:
            displayMsg(["Hydration rate:", " {:+.2f} g/min".format(slope)])
        
    if btnR_state == 'click':
        btnR_state = ''
        reDisplayMsg()

    if btnR_state == 'long-click':
        btnR_state = ''
        display.show(graph)
        touchEventTimer("screen_off_timer")


    time.sleep(0.02)



hydrominder_states = {
  "id": "blinky",
  "initial": "led_off",
  "states": {
    "led_off": {
      "entry": turn_off_led,
      "on": {
        "toggle": {
          "target": "led_on"
        }
      }
    },
    "led_on": {
      "entry": turn_on_led,
      "on": {
        "toggle": {
          "target": "led_off"
        }
      }
    }
  }
}