"""
Circuit Python BLE Color Patchwork
This demo uses advertising to broadcast a color of the users choice.
We will show a color "patch" on the screen for every unique device
advertisement that we find.
"""

import time
import random
import board
import displayio
from adafruit_ble import BLERadio
from adafruit_ble.advertising.adafruit import AdafruitColor

from adafruit_gizmo import tft_gizmo
from adafruit_circuitplayground import cp

MODE_COLOR_SELECT = 0
MODE_SHOW_PATCHWORK = 1

COLOR_TRANSPARENT_INDEX = 0
COLOR_OFFWHITE_INDEX = 1

current_mode = MODE_SHOW_PATCHWORK

# The color pickers will cycle through this list with buttons A and B.
color_options = [0xEE0000,
                 0xEEEE00,
                 0x00EE00,
                 0x00EEEE,
                 0x0000EE,
                 0xEE00EE,
                 0xCCCCCC,
                 0xFF9999,
                 0x99FF99,
                 0x9999FF]

ble = BLERadio()

i = 0
advertisement = AdafruitColor()
advertisement.color = color_options[i]

# Create the TFT Gizmo display
display = tft_gizmo.TFT_Gizmo()

# Create a bitmap with two colors + 64 colors for the map
bitmap = displayio.Bitmap(8, 8, 64 + 2)

# Create a 8*8 bitmap pre-filled with 64 colors (color 0 and 1 are reserved)
for i in range(0, 8):
    for j in range(0, 8):
        bitmap[i, j]=2+i+j*8

# Create an empty palette that will be used in one to one mapping
palette_mapping = displayio.Palette(64 + 2)

palette_mapping[0] = 0x000000
palette_mapping[1] = 0xDFDFDF

color_select_palette = displayio.Palette(len(color_options))
for i, color in enumerate(color_options):
    color_select_palette[i] = color


def make_transparent():
    palette_mapping.make_transparent(0)
    for i in range(0, 8):
        for j in range(0, 8):
            bitmap[i, j] = 0


def make_white():
    for i in range (2, 66):
        palette_mapping[i] = 0xDFDFDF


def make_palette():
    for i, color in enumerate(nearby_colors):
        palette_mapping[i+2] = color


color_select_preview_bmp = displayio.Bitmap(1, 1, len(color_options))
color_preview_group = displayio.Group(scale=30*2)
color_preview_group.x = 240//2 - 60//2
color_preview_group.y = 240 - (60+2)

color_preview_tilegrid = displayio.TileGrid(color_select_preview_bmp, pixel_shader=color_select_palette)
color_preview_group.append(color_preview_tilegrid)

# Create a TileGrid using the Bitmap and Palette
tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette_mapping)

patchwork_group = displayio.Group(scale=30)

patchwork_group.append(tile_grid)

# Create a Group
group = displayio.Group()

# Add the TileGrid to the Group
group.append(patchwork_group)

# Add the Group to the Display
display.show(group)

cur_color = 0

prev_b = cp.button_b
prev_a = cp.button_a

nearby_addresses = ["myself"]
nearby_colors = [color_options[cur_color]]


def draw_grid():
    for i, color in enumerate(nearby_colors):
        if i < 64:
            palette_mapping[i+2] = color & 0xFFFFFF ### Mask 0xFFFFFF to avoid invalid color.
            print(i)
            print(color)


def add_fake():
    fake_mac = ''.join([random.choice("0123456789abcdef") for n in range(10)])
    while fake_mac in nearby_addresses:
        fake_mac = ''.join([random.choice("0123456789abcdef") for n in range(10)])
    fake_color = random.choice(color_options)
    nearby_addresses.append(fake_mac)
    nearby_colors.append(fake_color)


def ble_scan():
    print("scanning")
    # loop over all found devices
    for entry in ble.start_scan(AdafruitColor, minimum_rssi=-100, timeout=1):
        # if this device is not in the list already
        if entry.color in color_options:
            print("new color")
        if entry.address.address_bytes not in nearby_addresses:
            # print(entry.color)
            # add the address and color to respective lists
            nearby_addresses.append(entry.address.address_bytes)
            nearby_colors.append(entry.color)
        else:  # address was already in the list
            # print(entry.color)
            # update the color to currently advertised value
            _index = nearby_addresses.index(entry.address.address_bytes)
            nearby_colors[_index] = entry.color


make_white()
ble_scan()
draw_grid()

# image for color slector layout
with open("/color_select_background.bmp", "rb") as color_select_background:
    odb = displayio.OnDiskBitmap(color_select_background)
    # TileGrid for the color select background. We will insert and remove this from the
    # main group as needed.
    bg_grid = displayio.TileGrid(odb, pixel_shader=displayio.ColorConverter())
    while True:
        cur_a = cp.button_a
        cur_b = cp.button_b
        if current_mode == MODE_SHOW_PATCHWORK:
            # a button was pressed
            if cur_a and not prev_a:
                current_mode = MODE_COLOR_SELECT
                # insert color select background
                group.append(bg_grid)
                group.append(color_preview_group)
                # make front bitmap transparent by setting palette color to transparent
                # make_transparent()

            # b button was pressed
            if cur_b and not prev_b:
                ble_scan()
                # for i in range(19):
                #    add_fake()
                print("after scan found {} results".format(len(nearby_colors)))
                # print(nearby_addresses)
                draw_grid()

        elif current_mode == MODE_COLOR_SELECT:
            # current selection preview
            color_select_preview_bmp[0, 0] = cur_color

            # a button was pressed
            if cur_a and not prev_a:
                print("a button")
                # increment currently selected color index
                cur_color += 1
                # reset to 0 if it's too big
                if cur_color >= len(color_options):
                    cur_color = 0
                print(cur_color)
            # b button was pressed
            if cur_b and not prev_b:
                print("b button")
                # advertise new color selection
                ble.stop_advertising()
                advertisement.color = color_options[cur_color]
                ble.start_advertising(advertisement)

                # update top left self patch
                nearby_colors[0] = color_options[cur_color]

                # go back to patchwork mode
                current_mode = MODE_SHOW_PATCHWORK
                # remove color select background
                group.remove(bg_grid)
                group.remove(color_preview_group)
                make_white()
                draw_grid()
        prev_a = cur_a
        prev_b = cur_b
