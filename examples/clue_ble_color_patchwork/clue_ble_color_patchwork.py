"""
Circuit Python BLE Color Patchwork
This demo uses advertising to broadcast a color of the users choice.
We will show a color "patch" on the screen for every unique device
advertisement that we find.
"""

import time
import random
import board
from adafruit_clue import clue
import displayio
from adafruit_ble import BLERadio
from adafruit_ble.advertising.adafruit import AdafruitColor

MODE_COLOR_SELECT = 0
MODE_SHOW_PATCHWORK = 1

COLOR_TRANSPARENT = 0
COLOR_OFFWHITE = 1

GRID_SIZE_8x8 = 30
GRID_SIZE_15x15 = 16

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

display = board.DISPLAY

# Create a bitmap with two colors
bitmap = displayio.Bitmap(display.width, display.height, len(color_options) + 2)

# Create a two color palette
palette = displayio.Palette(len(color_options) + 2)
palette[0] = 0x000000
palette[1] = 0xDFDFDF
palette.make_transparent(0)
for i, option in enumerate(color_options):
    palette[i + 2] = option

# Create a TileGrid using the Bitmap and Palette
tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)

# Create a Group
group = displayio.Group()

# Add the TileGrid to the Group
group.append(tile_grid)

# Add the Group to the Display
display.show(group)

cur_color = 0

prev_b = clue.button_b
prev_a = clue.button_a

nearby_addresses = ["myself"]
nearby_colors = [color_options[cur_color]]


def draw_grid(patch_size):
    for i, color in enumerate(nearby_colors):
        _grid_size = (240 / patch_size)
        if i < _grid_size * _grid_size:
            _grid_loc = (int(i % _grid_size), int(i / _grid_size))
            _screen_loc = (_grid_loc[0] * patch_size, _grid_loc[1] * patch_size)
            print(_grid_loc)
            print(color)
            _drawing_color = color_options.index(color) + 2
            print(_drawing_color)
            if bitmap[_screen_loc[0], _screen_loc[1]] != _drawing_color:
                for x_pixels in range(_screen_loc[0], _screen_loc[0] + patch_size):
                    for y_pixels in range(_screen_loc[1], _screen_loc[1] + patch_size):
                        # print("drawing ({}, {})".format(x_pixels, y_pixels))
                        bitmap[x_pixels, y_pixels] = _drawing_color


def fill_bitmap(color_index):
    # fill bitmap with single color
    for x in range(0, 240):
        for y in range(0, 240):
            bitmap[x, y] = color_index


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

fill_bitmap(COLOR_OFFWHITE)
ble_scan()
draw_grid(GRID_SIZE_8x8)

# image for color slector layout
with open("/color_select_background.bmp", "rb") as color_select_background:
    odb = displayio.OnDiskBitmap(color_select_background)
    # TileGrid for the color select background. We will insert and remove this from the
    # main group as needed.
    bg_grid = displayio.TileGrid(odb, pixel_shader=displayio.ColorConverter())
    while True:
        cur_a = clue.button_a
        cur_b = clue.button_b
        if current_mode == MODE_SHOW_PATCHWORK:
            # a button was pressed
            if cur_a and not prev_a:
                current_mode = MODE_COLOR_SELECT
                # insert color select background
                group.insert(0, bg_grid)
                # make front bitmap transparent by setting pixels to 0
                fill_bitmap(COLOR_TRANSPARENT)
            # b button was pressed
            if cur_b and not prev_b:
                ble_scan()
                # for i in range(19):
                #    add_fake()
                print("after scan found {} results".format(len(nearby_colors)))
                # print(nearby_addresses)
                draw_grid(GRID_SIZE_8x8)

        elif current_mode == MODE_COLOR_SELECT:
            # current selection preview
            for x in range(83, 83 + 72):
                for y in range(182, 182 + 56):
                    bitmap[x, y] = cur_color + 2
            # a button was pressed
            if cur_a and not prev_a:
                print("a button")
                # increment currently selected color index
                cur_color += 1
                # reset to 0 if it's too big
                if cur_color >= len(color_options):
                    cur_color = 0
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
                fill_bitmap(COLOR_OFFWHITE)
                draw_grid(GRID_SIZE_8x8)