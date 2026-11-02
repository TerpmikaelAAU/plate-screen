import numpy as np
import pytest
from PIL import Image, ImageDraw

from plate_screen.align import logo_turns
from plate_screen.crop import MARGIN

SIZE = 300
# An irregular cluster of marks standing in for the moulded logo: (degrees from the bottom, width in degrees)
MARKS = [(-14, 3), (-9, 2), (-5, 4), (1, 2), (4, 1), (9, 3), (14, 2)]


def dish(logo: bool = True, colony: int = 20, seed: int = 0) -> Image.Image:
    """A Crop with its logo at the bottom: a light dish on black, a colony in the middle, faint grain."""
    c, r = SIZE / 2, SIZE / 2 / MARGIN
    im = Image.new("L", (SIZE, SIZE), 0)
    d = ImageDraw.Draw(im)
    d.ellipse((c - r, c - r, c + r, c + r), fill=190)
    d.ellipse((c - colony, c - colony, c + colony, c + colony), fill=230)
    if logo:
        for at, width in MARKS:
            a0, a1 = np.radians(90 + at), np.radians(90 + at + width)
            inner, outer = 0.72 * r, 0.82 * r
            d.polygon([(c + q * np.cos(a), c + q * np.sin(a)) for q, a in [(inner, a0), (outer, a0), (outer, a1), (inner, a1)]], fill=110)
    grain = np.random.default_rng(seed).normal(0, 4, (SIZE, SIZE))
    return Image.fromarray(np.clip(np.asarray(im) + grain, 0, 255).astype(np.uint8)).convert("RGB")


def off(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def test_turns_every_dish_so_its_logo_ends_at_the_bottom():
    angles = {(1, 0): 0, (1, 1): 37, (2, 0): 140, (2, 1): 250, (3, 0): 311}
    crops = {k: dish(colony=15 + 5 * i, seed=i).rotate(a) for i, (k, a) in enumerate(angles.items())}
    turns = logo_turns(crops)
    for k, a in angles.items():
        assert turns[k] is not None
        assert off(turns[k], -a) <= 2, (k, turns[k])


def test_a_dish_without_a_logo_is_left_as_it_is():
    crops = {(1, 0): dish(seed=1).rotate(80), (2, 0): dish(seed=2).rotate(200), (3, 0): dish(logo=False, seed=3)}
    turns = logo_turns(crops)
    assert turns[(3, 0)] is None
    assert off(turns[(1, 0)], -80) <= 2


def test_plain_dishes_get_no_turn():
    plain = Image.new("RGB", (SIZE, SIZE), (190, 190, 190))
    assert logo_turns({(1, 0): plain, (2, 0): plain}) == {(1, 0): None, (2, 0): None}


def test_no_crops_no_turns():
    assert logo_turns({}) == {}
