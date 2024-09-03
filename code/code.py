# SPDX-FileCopyrightText: 2024 JG for Cedar Grove Maker Studios
#
# SPDX-License-Identifier: MIT

"""A custom sound effects player for The Highway 12 Band"""

import time
import board
from analogio import AnalogIn
from digitalio import DigitalInOut
import sdcardio
import storage
import audiocore
import audioio
import audiomixer
import neopixel
from simpleio import map_range
import terminalio
import keypad
import displayio
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font
import adafruit_imageload

# Instantiate the integral display and define its size
display = board.DISPLAY
display.brightness = 0.6
WIDTH = display.width
HEIGHT = display.height

# Display splash graphics first before instantiating everything
track_group = displayio.Group(scale=1)
splash_group = displayio.Group(scale=1)
sign_bright = displayio.OnDiskBitmap("/HW12_sign_bw_2012-11-17_v00.bmp")
sign_faded = displayio.OnDiskBitmap("/HW12_sign_bw_2012-11-17_v01_faded.bmp")
splash_group.append(
    displayio.TileGrid(sign_faded, pixel_shader=sign_faded.pixel_shader)
)
splash_group.append(
    displayio.TileGrid(sign_bright, pixel_shader=sign_bright.pixel_shader)
)
display.root_group = splash_group

# Instantiate and clear the NeoPixels
pixels = neopixel.NeoPixel(board.NEOPIXEL, 5, pixel_order=neopixel.GRB)
pixels.brightness = 0.06
pixels.fill(0x202020)

# Battery indicator
battery = AnalogIn(board.A6)
sprite_sheet, battery_palette = adafruit_imageload.load(
    "/batt_sprite_sheet.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette
)
battery_icon = displayio.TileGrid(
    sprite_sheet,
    pixel_shader=battery_palette,
    width=1,
    height=1,
    tile_width=16,
    tile_height=16,
)
battery_icon.x = WIDTH - 16
battery_icon.y = 1
battery_palette.make_transparent(0)  # Set icon background to transparent

# Define track titles and associated SD card file names
TRACK_TITLE = [
    ["409 REV", "409_22.wav"],
    ["Jet START", "jet_start_22.wav"],
    ["Jet END", "jet_start_22.wav"],
    ["Wipeout", "wipeout_22.wav"],
]
CURRENT_TRACK = 0


# Define the state machine states
class State:
    INIT = "INIT"
    PLAYING = "PLAY"
    PAUSED = "PAUSE"
    STOPPED = "STOP"


STATE = State.INIT
print(f"STATE: {STATE}")

# Enable the speaker
DigitalInOut(board.SPEAKER_ENABLE).switch_to_output(value=True)

# Instantiate PyGamer joystick
joystick_x = AnalogIn(board.JOYSTICK_X)
joystick_y = AnalogIn(board.JOYSTICK_Y)

# Initialize ShiftRegisterKeys to read PyGamer buttons
panel = keypad.ShiftRegisterKeys(
    clock=board.BUTTON_CLOCK,
    data=board.BUTTON_OUT,
    latch=board.BUTTON_LATCH,
    key_count=8,
    value_when_pressed=True,
)

# Define front panel button event values
BUTTON_SELECT = 3  # Not used
BUTTON_START = 2  # Not used
BUTTON_A = 1  # Player START/STOP
BUTTON_B = 0  # Not used

# Instantiate the SD card storage system
sd = sdcardio.SDCard(board.SPI(), board.SD_CS)
vfs = storage.VfsFat(sd)
storage.mount(vfs, "/sd")
# print(os.listdir('/sd/SFX'))

# Instantiate the mixer and audio output stream
audio_out = audioio.AudioOut(
    left_channel=board.A0, right_channel=board.A1, quiescent_value=32_768
)
mixer = audiomixer.Mixer(
    voice_count=1,
    buffer_size=2048,
    sample_rate=22050,
    channel_count=2,
    bits_per_sample=16,
    samples_signed=True,
)
audio_out.play(mixer)

# Create a list of opened wave files from TRACK_TITLE list
wave_files = [open("sd/SFX/" + t[1], "rb") for t in TRACK_TITLE]
# Create a list of wave objects from the opened wave files list
waves = [audiocore.WaveFile(f) for f in wave_files]

# Define track labels
font_0 = bitmap_font.load_font("/fonts/helvB14.bdf")
label_padding = 7

track_0_label = Label(
    font_0,
    text=TRACK_TITLE[0][0],
    color=0xFFFFFF,
    padding_top=label_padding,
    padding_bottom=label_padding,
    padding_left=label_padding,
    padding_right=label_padding,
)
track_0_label.anchor_point = (0.5, 0.5)
track_0_label.anchored_position = ((WIDTH // 2), 1 * HEIGHT // 5)
track_group.append(track_0_label)

track_1_label = Label(
    font_0,
    text=TRACK_TITLE[1][0],
    color=0xFFFFFF,
    padding_top=label_padding,
    padding_bottom=label_padding,
    padding_left=label_padding,
    padding_right=label_padding,
)
track_1_label.anchor_point = (0.5, 0.5)
track_1_label.anchored_position = ((WIDTH // 2), 2 * HEIGHT // 5)
track_group.append(track_1_label)

track_2_label = Label(
    font_0,
    text=TRACK_TITLE[2][0],
    color=0xFFFFFF,
    padding_top=label_padding,
    padding_bottom=label_padding,
    padding_left=label_padding,
    padding_right=label_padding,
)
track_2_label.anchor_point = (0.5, 0.5)
track_2_label.anchored_position = ((WIDTH // 2), 3 * HEIGHT // 5)
track_group.append(track_2_label)

track_3_label = Label(
    font_0,
    text=TRACK_TITLE[3][0],
    color=0xFFFFFF,
    padding_top=label_padding,
    padding_bottom=label_padding,
    padding_left=label_padding,
    padding_right=label_padding,
)
track_3_label.anchor_point = (0.5, 0.5)
track_3_label.anchored_position = ((WIDTH // 2), 4 * HEIGHT // 5)
track_group.append(track_3_label)

state_status = Label(font_0, text="    ", color=0x404040)
state_status.anchor_point = (0, 1.0)
state_status.anchored_position = (0, 128)
track_group.append(state_status)

battery_status = Label(terminalio.FONT, text="   ", color=0x808080)
battery_status.anchor_point = (1.0, 0)
battery_status.anchored_position = (WIDTH, 12)
track_group.append(battery_status)

# Reveal faded sign bitmap image, battery icon and show tracks
display.root_group.pop()
display.root_group.append(track_group)
splash_group.append(battery_icon)


# FUNCTIONS
def stop():
    # Stop track playback
    global STATE, CURRENT_TRACK
    mixer.voice[0].stop()
    mixer.voice[0].level = 0.0
    STATE = State.STOPPED
    track_group[CURRENT_TRACK].color = 0x000000
    track_group[CURRENT_TRACK].background_color = 0xFFFF00
    pixels.fill(0x000000)
    print(f"STATE: {STATE}")


def play():
    # Start track playback
    global STATE, CURRENT_TRACK, pixel_lighted
    STATE = State.PLAYING
    mixer.voice[0].level = 1.0
    mixer.voice[0].play(waves[CURRENT_TRACK])
    track_group[CURRENT_TRACK].color = 0x000000
    track_group[CURRENT_TRACK].background_color = 0x00FF00
    pixels.fill(0x00FF00)
    pixel_lighted = 0
    print(f"STATE: {STATE}")


def get_joystick():
    # Read the joystick and interpret as up/down buttons
    if joystick_y.value < 20000:
        return 1  # UP
    if joystick_y.value > 44000:
        return -1  # DOWN
    return 0


def display_battery_level():
    """Display the battery level."""
    battery_volts = round(battery.value * 6.6 / 0xFFF0, 1)
    # battery_status.text = f"{battery_volts:3.1f}"
    battery_level = int(map_range(battery_volts, 3.1, 3.6, 0, 5))
    battery_icon[0] = battery_level


# Initialization completed
joystick_hold = False
pixel_lighted = 0
stop()  # Stop mixer/audio output
display_battery_level()

# Main Code Loop
while True:
    if time.monotonic() % 10 == 0:
        # Update the battery display every 10 seconds
        display_battery_level()
    state_status.text = STATE
    if STATE == State.STOPPED:
        # Select next track to play only when stopped
        joystick_delta = get_joystick()

        if joystick_delta != 0:
            if not joystick_hold:
                track_group[CURRENT_TRACK].color = 0xFFFFFF
                track_group[CURRENT_TRACK].background_color = None
                CURRENT_TRACK = CURRENT_TRACK - joystick_delta
                CURRENT_TRACK = min(max(0, CURRENT_TRACK), 3)
            joystick_hold = True
        else:
            joystick_hold = False

        track_group[CURRENT_TRACK].color = 0x000000
        track_group[CURRENT_TRACK].background_color = 0xFFFF00

        buttons = panel.events.get()
        if buttons and buttons.pressed:
            if buttons.key_number == BUTTON_A:  # START/STOP button pressed
                play()  # This is non-blocking

    if STATE == State.PLAYING:
        # Watch for STOP button press only when playing
        buttons = panel.events.get()
        if buttons and buttons.pressed:
            if buttons.key_number == BUTTON_A:  # START/STOP button pressed
                stop()

        if mixer.playing:
            if (
                pixels[pixel_lighted][0] * 0x010000
                + pixels[pixel_lighted][1] * 0x000100
                + pixels[pixel_lighted][2]
            ) == 0x00FF00:
                pixels[pixel_lighted] = 0x002000
            else:
                pixels[pixel_lighted] = 0x00FF00
            time.sleep(0.05)

            pixel_lighted += 1
            if pixel_lighted > 4:
                pixel_lighted = 0
        else:
            stop()
