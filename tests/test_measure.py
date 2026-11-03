import numpy as np
import pytest
from PIL import Image, ImageDraw

from plate_screen.crop import MARGIN
from plate_screen.measure import DISH_MM, measure_plate, references

SIZE = 600
C = SIZE / 2
DISH = C / MARGIN  # dish radius in Crop pixels
MM = DISH / (DISH_MM / 2)  # Crop pixels per mm


def crop(colony=0.0, halo=0.0, satellite=False, seed=0) -> Image.Image:
    """A turned Crop: agar with a darker meniscus disc, and a brown Colony of the given radius (in mm) at the centre."""
    im = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((C - DISH, C - DISH, C + DISH, C + DISH), fill=(205, 210, 215))
    m = 0.72 * DISH
    d.ellipse((C - m, C - m, C + m, C + m), fill=(185, 195, 205))
    a = np.asarray(im, dtype=np.float32)
    yy, xx = np.mgrid[:SIZE, :SIZE]
    r = np.hypot(xx - C, yy - C) / MM
    if halo:
        fade = np.clip(1 - (r - colony) / halo, 0, 1) * (r > colony)
        a += fade[..., None] * np.array([25, -20, -10])
    a[r < colony] = (120, 100, 70)
    if satellite:
        a[np.hypot(xx - C - 30 * MM, yy - C) / MM < 2.5] = (130, 110, 70)
    a += np.random.default_rng(seed).normal(0, 3, a.shape)
    a[np.hypot(xx - C, yy - C) > DISH] = 0
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def chosen(result, day, which="A"):
    return result[day][which]


def test_a_growing_colony_is_measured_on_every_day():
    sizes = {1: 4, 2: 9, 3: 16, 4: 24}
    days = {d: crop(colony=s / 2, seed=d) for d, s in sizes.items()}
    result = measure_plate(days, {d: crop(seed=10 + d) for d in days})
    for d, s in sizes.items():
        for which in "ABC":
            assert chosen(result, d, which).diameter == pytest.approx(s, abs=1.0), (d, which)


def test_a_pigment_halo_is_not_part_of_the_colony():
    result = measure_plate({2: crop(colony=6, halo=8)}, {2: crop(seed=5)})
    assert chosen(result, 2).diameter == pytest.approx(12, abs=1.0)


def test_a_satellite_is_not_measured():
    result = measure_plate({3: crop(colony=8, satellite=True)}, {3: crop(seed=5)})
    assert chosen(result, 3).diameter == pytest.approx(16, abs=1.0)


def test_an_empty_plate_has_no_colony():
    result = measure_plate({1: crop(seed=1), 2: crop(seed=2)}, {1: crop(seed=3), 2: crop(seed=4)})
    assert all(result[d] == {"A": None, "B": None, "C": None} for d in (1, 2))


def test_a_colony_past_the_limit_is_marked_at_the_rim():
    result = measure_plate({7: crop(colony=44)}, {7: crop(seed=5)})
    assert chosen(result, 7).at_rim
    assert result[7]["B"] is None  # B stops inside the rim, finds no edge there, and gives up rather than shrink to a dot
    assert not measure_plate({3: crop(colony=10)}, {3: crop(seed=5)})[3]["A"].at_rim


def test_a_plate_is_compared_with_its_own_day_0_unless_the_lid_was_fogged():
    clear = {(p, 0): crop(seed=p) for p in (1, 2, 3)}
    fog = Image.blend(crop(seed=9), Image.new("RGB", (SIZE, SIZE), (250, 250, 250)), 0.6)
    later = {(p, d): crop(colony=3 * d, seed=10 * p + d) for p in (1, 2, 3, 4) for d in (1, 2)}
    refs = references({**clear, (4, 0): fog, **later})
    assert refs[(1, 2)] is clear[(1, 0)]
    assert refs[(4, 2)] is later[(4, 1)]  # fogged Day 0: the next Day instead
    assert set(refs) == set(later)  # Day 0 itself is not measured
    assert refs[(4, 1)].size == (SIZE, SIZE)  # Day 1 of a fogged Plate: the Round's typical Day 0
