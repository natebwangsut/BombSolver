from enum import Enum
from time import sleep, time
from numpy import array
import cv2
import config
import features.util as feature_util

def is_solved(image):
    rgb = feature_util.split_channels(cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    pixel = (18, 270)
    lit_low = (0, 200, 0)
    lit_high = (50, 255, 50)
    return feature_util.color_in_range(pixel, rgb, lit_low, lit_high)

def get_response_color(color, coords, features):
    if features["contains_vowel"]:
        if color == 0: # Red.
            return coords[1] # Press blue.
        if color == 1: # Blue.
            return coords[0] # Press red.
        if color == 2: # Green.
            return coords[3] # Press yellow.
        if color == 3: # Yellow.
            return coords[2] # Press green.
    else:
        if color == 0: # Red.
            return coords[1] # Press blue.
        if color == 1: # Blue.
            return coords[3] # Press yellow.
        if color == 2: # Green.
            return coords[2] # Press green.
        if color == 3: # Yellow.
            return coords[0] # Press red.
    return -1

def get_next_color(img, sc_func, ranges, features, curr_match):
    coords = [(140, 95), (74, 155), (204, 156), (140, 216)]
    button_coords = []
    rgb = feature_util.split_channels(img)
    pause_between_blinks = 0.35
    colors_matched = 0
    timestamp = 0
    while True:
        sc, _, _ = sc_func()
        rgb = feature_util.split_channels(cv2.cvtColor(array(sc), cv2.COLOR_RGB2BGR))
        for i, (low, high) in enumerate(ranges):
            coord = coords[i]
            if feature_util.color_in_range(coord, rgb, low, high) and time() - timestamp > pause_between_blinks:
                colors_matched += 1
                print(f"Color {colors_matched}: {i}")
                button_coords.append(get_response_color(i, coords, features))
                timestamp = time()
                if colors_matched == curr_match:
                    return button_coords
        sleep(0.1) # Lamps are lit for 0.25 seconds.

def solve(image, screenshot_func, features, color_num=1):
    ranges = config.SIMON_COLOR_RANGE
    coords = get_next_color(image, screenshot_func, ranges, features, color_num)
    return coords