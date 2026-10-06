from datetime import datetime

import numpy as np
from PIL import Image

from conftest import DISH, H, W
from plate_screen.crop import crop_plate, find_dish


def test_finds_the_outer_rim_of_the_dish(photo):
    p = photo("a.jpg", datetime(2026, 9, 28, 13, 0))
    x, y, r = find_dish(Image.open(p))
    assert abs(x - DISH[0]) <= 4 and abs(y - DISH[1]) <= 4
    assert abs(r - DISH[2]) <= 4


def test_finds_a_dish_off_centre(photo):
    p = photo("a.jpg", datetime(2026, 9, 28, 13, 0), dish=(200, 250, 120))
    x, y, r = find_dish(Image.open(p))
    assert abs(x - 200) <= 4 and abs(y - 250) <= 4 and abs(r - 120) <= 4


def test_no_dish_gives_none():
    assert find_dish(Image.new("RGB", (W, H), (60, 62, 66))) is None


def test_crop_is_square_with_black_outside_the_dish(photo):
    p = photo("a.jpg", datetime(2026, 9, 28, 13, 0))
    crop = crop_plate(Image.open(p), DISH, size=200)
    assert crop.size == (200, 200)
    a = np.asarray(crop)
    assert a[0, 0].max() == 0
    assert a[100, 50].min() > 100  # dish, not cloth
