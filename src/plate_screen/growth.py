"""From candidate Outlines to Diameters and Growth rates: picking an Outline per Crop, flagging doubtful ones for
review, and fitting each Plate's Growth rate."""

from dataclasses import dataclass, field
from statistics import mean, median, stdev

import numpy as np

from .key import Plate
from .measure import DISH_MM, Outline

CONTROL = "Vogel"  # the Condition every other Condition of a Strain is compared with
CHOICES = ("A", "B", "C", "empty", "none", "rim")
# empty: no Colony (0 mm); none: no candidate is right (no Diameter); rim: the Colony has reached the dish wall (no Diameter)
AGREE_MM = 2.0  # candidates closer than this agree
SHRINK_MM = 1.0  # a Diameter may fall this much from one Day to the next before it is doubted
REPLICATE_MM, REPLICATE_SHARE = 3.0, 0.25  # a Replicate is doubted further than both of these from the median
FAINT = 15.0  # colour change (ΔE) under which a Colony is doubted: a thin Colony, or just the inoculum
FIT_SHARE = 0.8  # Days from where the Colony spans this share of the dish are left out of the Growth rate
FIT_DAYS = 4  # every Plate's Growth rate is fitted on Days 1 to this, so Plates are compared over the same time


@dataclass
class Cell:
    """One Plate on one Day: its candidate Outlines, and the review's choice if there is one."""

    photo: str
    plate: Plate
    day: int
    outlines: dict[str, Outline | None]
    choice: str | None = None
    at: float | None = None  # Days since Day 0 began, by the Photo's clock; the Day number when not known


@dataclass
class Reading:
    cell: Cell
    outline: str  # the chosen candidate, empty, none or rim; "" while undecided
    diameter: float | None  # mm; None until decided, when no candidate is right, or at the rim
    flags: list[str] = field(default_factory=list)

    @property
    def chosen(self) -> Outline | None:
        return self.cell.outlines.get(self.outline)


def _guess(c: Cell) -> str:
    """The choice to judge a Cell by before review: the review's, else the first candidate found."""
    if c.choice:
        return c.choice
    return next((k for k in "ABC" if c.outlines[k] is not None), "empty")


def _size(c: Cell, choice: str) -> float | None:
    if choice == "empty":
        return 0.0
    o = c.outlines.get(choice)
    return None if o is None else o.diameter


def read(cells: list[Cell]) -> list[Reading]:
    """A Reading per Cell, in the same order. A Cell gets a Diameter when the review chose for it, or when nothing
    about it is in doubt; otherwise it is flagged and waits for review."""
    guess = {id(c): _size(c, _guess(c)) for c in cells}
    flags: dict[int, list[str]] = {id(c): [] for c in cells}

    for c in cells:
        found = [o.diameter for o in c.outlines.values() if o is not None]
        if found and (len(found) < len(c.outlines) or max(found) - min(found) > AGREE_MM):
            flags[id(c)].append("candidates differ")
        chosen = c.outlines.get(_guess(c))
        if chosen is not None and chosen.change < FAINT:
            flags[id(c)].append("faint")

    by_plate: dict[int, list[Cell]] = {}
    for c in cells:
        by_plate.setdefault(c.plate.number, []).append(c)
    for days in by_plate.values():
        days.sort(key=lambda c: c.day)
        for before, after in zip(days, days[1:]):
            if None not in (guess[id(before)], guess[id(after)]) and guess[id(before)] - guess[id(after)] > SHRINK_MM:
                for c in (before, after):
                    if "shrinks" not in flags[id(c)]:
                        flags[id(c)].append("shrinks")

    for c in cells:
        same = [
            guess[id(o)]
            for o in cells
            if o.day == c.day and (o.plate.strain, o.plate.condition) == (c.plate.strain, c.plate.condition)
        ]
        same = [g for g in same if g is not None]
        if len(same) > 1 and guess[id(c)] is not None:
            m = median(same)
            if abs(guess[id(c)] - m) > max(REPLICATE_MM, REPLICATE_SHARE * m):
                flags[id(c)].append("replicates differ")

    for c in cells:
        if c.choice in c.outlines and c.outlines[c.choice] is None:
            raise ValueError(f"{c.photo}: the review chose {c.choice}, but {c.choice} found no Colony there")

    readings = []
    for c in cells:
        decided = c.choice or ("" if flags[id(c)] else _guess(c))
        size = _size(c, decided) if decided else None
        readings.append(Reading(c, decided, size, flags[id(c)]))
    return readings


@dataclass
class Growth:
    plate: Plate
    rate: float | None  # mm per Day
    days: list[int]  # the Days the rate is fitted on


def growth_rates(readings: list[Reading]) -> list[Growth]:
    """Each Plate's Growth rate: the slope of a straight line through its Diameters against the time each Photo was
    taken, over Days 1 to FIT_DAYS before the Colony reaches the rim or FIT_SHARE of the dish. None with fewer than two
    such Days."""
    by_plate: dict[int, list[Reading]] = {}
    for r in readings:
        by_plate.setdefault(r.cell.plate.number, []).append(r)
    out = []
    for rs in by_plate.values():
        rs.sort(key=lambda r: r.cell.day)
        fit = []
        for r in rs:
            if r.outline == "rim":
                break
            if r.diameter is None or r.cell.day > FIT_DAYS:
                continue
            if r.diameter >= FIT_SHARE * DISH_MM or (r.chosen is not None and r.chosen.at_rim):
                break
            fit.append(r)
        # Before the Colony first shows the dish holds only the inoculum, which its first Diameter already includes: count
        # those Days at that size, so a Plate held back by its Condition comes out slow rather than fast
        first = next((r.diameter for r in fit if r.diameter > 0), 0.0)
        sizes, seen = [], False
        for r in fit:
            seen = seen or r.diameter > 0
            sizes.append(r.diameter if seen else first)
        days = [r.cell.day for r in fit]
        times = [r.cell.day if r.cell.at is None else r.cell.at for r in fit]
        rate = float(np.polyfit(times, sizes, 1)[0]) if len(fit) >= 2 else None
        out.append(Growth(rs[0].cell.plate, rate, days))
    return out


@dataclass
class Summary:
    strain: str
    condition: str
    plates: int  # with a Growth rate
    rate: float | None  # mean mm per Day
    spread: float | None  # standard deviation between Plates
    percent_of_vogel: float | None


def summary(growth: list[Growth]) -> list[Summary]:
    """Mean Growth rate per Strain and Condition, and as a percentage of the same Strain on Vogel."""
    groups: dict[tuple[str, str], list[float]] = {}
    for g in growth:
        rates = groups.setdefault((g.plate.strain, g.plate.condition), [])
        if g.rate is not None:
            rates.append(g.rate)
    out = []
    for (strain, condition), rates in groups.items():
        control = groups.get((strain, CONTROL)) or []
        rate = mean(rates) if rates else None
        base = mean(control) if control else None
        out.append(
            Summary(
                strain,
                condition,
                len(rates),
                rate,
                stdev(rates) if len(rates) > 1 else None,
                100 * rate / base if rate is not None and base else None,
            )
        )
    return out
