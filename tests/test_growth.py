import numpy as np
import pytest

from plate_screen.growth import Cell, growth_rates, read, summary
from plate_screen.key import Plate
from plate_screen.measure import ANGLES, Outline

VOGEL = "Vogel"
BASTA = "Vogel + 0.1 mg/mL Basta"


def disc(mm: float, at_rim=False, change=40.0) -> Outline:
    return Outline(np.full(ANGLES, 1.0), (300, 300), mm, mm, mm, at_rim, change)


def cell(day, a, b=None, c=None, plate=1, condition=VOGEL, replicate="A", choice=None, at=None) -> Cell:
    b, c = (a if b is None else b), (a if c is None else c)
    return Cell(f"p{plate}_d{day}.jpg", Plate(plate, "St 06", condition, replicate), day, {"A": a, "B": b, "C": c}, choice, at)


def test_agreeing_candidates_give_the_diameter():
    [r] = read([cell(2, disc(20), disc(21), disc(19.5))])
    assert (r.outline, r.diameter, r.flags) == ("A", 20, [])


def test_disagreeing_candidates_are_left_for_review():
    [r] = read([cell(2, disc(20), disc(35))])
    assert r.diameter is None and r.outline == ""
    assert r.flags == ["candidates differ"]


@pytest.mark.parametrize("choice, outline, diameter", [("B", "B", 35), ("empty", "empty", 0.0), ("none", "none", None), ("rim", "rim", None)])
def test_a_reviewed_choice_settles_the_diameter(choice, outline, diameter):
    [r] = read([cell(2, disc(20), disc(35), choice=choice)])
    assert (r.outline, r.diameter) == (outline, diameter)


def test_no_candidate_means_no_colony():
    [r] = read([cell(1, None, None, None)])
    assert (r.outline, r.diameter, r.flags) == ("empty", 0.0, [])


def test_a_colony_that_shrinks_is_flagged_on_both_days():
    rs = read([cell(1, disc(20)), cell(2, disc(15))])
    assert all(r.flags == ["shrinks"] and r.diameter is None for r in rs)


def test_a_replicate_far_from_the_others_is_flagged():
    rs = read([cell(2, disc(d), plate=p, replicate=x) for p, x, d in [(1, "A", 20), (2, "B", 21), (3, "C", 35)]])
    assert [r.flags for r in rs] == [[], [], ["replicates differ"]]


def test_a_faint_colony_is_flagged():
    [r] = read([cell(1, disc(14, change=9))])
    assert r.flags == ["faint"]


def test_growth_rate_is_fitted_before_the_colony_reaches_the_rim():
    days = [cell(d, disc(10 * d)) for d in (1, 2, 3, 4)] + [cell(5, disc(77, at_rim=True))]
    [g] = growth_rates(read(days))
    assert g.rate == pytest.approx(10)
    assert g.days == [1, 2, 3, 4]


def test_growth_rate_stops_where_the_review_says_the_colony_reached_the_rim():
    days = [cell(1, disc(10)), cell(2, disc(20)), cell(3, disc(50), choice="rim"), cell(4, disc(35))]
    [g] = growth_rates(read(days))
    assert g.days == [1, 2]


def test_growth_rate_is_fitted_on_the_same_days_for_every_plate():
    days = [cell(d, disc(10 * d)) for d in (1, 2, 3, 4)] + [cell(5, disc(42)), cell(6, disc(43))]
    [g] = growth_rates(read(days))
    assert g.rate == pytest.approx(10)
    assert g.days == [1, 2, 3, 4]


def test_growth_rate_goes_by_when_each_photo_was_taken():
    days = [cell(1, disc(10), at=1.0), cell(2, disc(20), at=2.0), cell(3, disc(25), at=2.5)]
    [g] = growth_rates(read(days))
    assert g.rate == pytest.approx(10)


# Until the Colony first shows, the dish holds only the inoculum, and the first Diameter already includes it
@pytest.mark.parametrize("shows, sizes, rate", [
    (2, [12, 17, 22], 3.5),  # 12, 12, 17, 22
    (3, [15, 18], 0.9),  # 15, 15, 15, 18
    (4, [15], 0.0),  # held back until Day 4: no faster than a Plate that never grows
])
def test_days_before_the_colony_shows_count_at_its_first_size(shows, sizes, rate):
    days = [cell(d, None, None, None) for d in range(1, shows)] + [cell(d, disc(s)) for d, s in zip(range(shows, 5), sizes)]
    [g] = growth_rates(read(days))
    assert g.rate == pytest.approx(rate)
    assert g.days == [1, 2, 3, 4]


def test_a_later_colony_never_grows_faster_than_an_earlier_one():
    rates = [growth_rates(read([cell(d, None, None, None) for d in range(1, shows)] + [cell(shows, disc(15))]))[0].rate
             for shows in (2, 3)]
    assert rates[0] >= rates[1]


def test_a_plate_that_never_grows_has_no_growth():
    [g] = growth_rates(read([cell(d, None, None, None) for d in (1, 2, 3)]))
    assert g.rate == pytest.approx(0)


def test_choosing_a_candidate_that_found_nothing_is_an_error():
    c = cell(2, disc(20), disc(35), choice="C")
    c.outlines["C"] = None
    with pytest.raises(ValueError, match="p1_d2.jpg"):
        read([c])


def test_growth_rate_needs_two_days():
    [g] = growth_rates(read([cell(1, disc(10)), cell(2, disc(20), disc(40))]))
    assert g.rate is None


def test_summary_gives_each_condition_as_percent_of_vogel():
    cells = [cell(d, disc(10 * d), plate=1) for d in (1, 2, 3)]
    cells += [cell(d, disc(5 * d), plate=2, condition=BASTA) for d in (1, 2, 3)]
    rows = summary(growth_rates(read(cells)))
    assert [(s.condition, s.rate, s.percent_of_vogel) for s in rows] == [
        (VOGEL, pytest.approx(10), pytest.approx(100)),
        (BASTA, pytest.approx(5), pytest.approx(50)),
    ]
