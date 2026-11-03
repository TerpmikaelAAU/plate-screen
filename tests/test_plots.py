from plate_screen.growth import Cell, Reading
from plate_screen.key import Plate
from plate_screen.plots import RIM_MM, means


def reading(plate, day, outline, diameter):
    return Reading(Cell(f"p{plate}_d{day}.jpg", Plate(plate, "St 07", "Vogel", "AB"[plate - 1]), day, {}), outline, diameter)


def test_the_mean_uses_the_replicates_measured_that_day_and_says_when_one_is_missing():
    rs = [reading(1, 1, "A", 10.0), reading(2, 1, "A", 14.0), reading(1, 2, "A", 20.0), reading(2, 2, "none", None)]
    assert means(rs) == [(1, 12.0, True), (2, 20.0, False)]


def test_replicates_that_all_reached_the_rim_put_the_mean_on_it():
    rs = [reading(1, 5, "rim", None), reading(2, 5, "rim", None), reading(1, 6, "rim", None), reading(2, 6, "none", None)]
    assert means(rs) == [(5, RIM_MM, True)]
