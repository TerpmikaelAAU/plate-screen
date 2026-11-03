"""Measuring the Colony on each turned Crop of a Plate.

The Colony's edge is traced as a closed path in polar coordinates about the Colony's centre: at each angle the
path picks the radius where the colour changes most sharply, discounting edges the reference already had (the
meniscus, the logo, the numbers on the dish) and edges with grainy texture just outside them, which lie inside a
sporulating Colony. A dynamic programme keeps the path smooth. Each Day gets three candidate Outlines:

A  traced from the last Day back, reluctant to grow past the next Day's A, and free to end at the rim;
B  traced on its own Day only, at the clearest edge inside the rim;
C  as A, but an edge counts only where the agar just outside it is unchanged since the reference.

None is right everywhere: A fails when a later Day went wrong, B on faint edges and rings inside the Colony, C when
the reference is poor (a fogged lid). Choosing between them is left to review.
"""

from dataclasses import dataclass, replace
from functools import cache

import cv2
import numpy as np
from PIL import Image

from .crop import MARGIN

DISH_MM = 92.0  # outer diameter of the dish, which is what a Crop's rim is fitted to (a guess: 90 mm dishes)
LIMIT = 0.84  # fraction of the dish radius an Outline may reach: further out is the wall and its reflections
ANGLES = 360
STEP = 4  # most an Outline moves outwards or inwards per degree, in pixels
SMOOTH = 2.0  # cost per pixel of that movement
TAU = 6.0  # how strongly grainy texture just outside an edge counts against it (a sporulating Colony is grainy)
OVERSHOOT = 0.3  # cost per pixel of Outline A (or C) beyond the next Day's (and 4 pixels of slack)
CHANGE_TAU = 25.0  # for Outline C, how strongly colour change just outside an edge counts against it
MU = 0.015  # cost per pixel of radius, so a weak edge further out loses to a clear one nearer in
RIM = 1.5  # score of the limit itself for Outline A: a Colony grown past the limit ends there
LOGO_SECTOR = (35, 0.62)  # half-width in degrees about the bottom, and inner radius, of the logo on a turned Crop
GROWN = 20  # colour change (ΔE) that counts as growth
PRESENT = 6  # mean colour change inside an Outline below which there is no Colony (faint ones go to review)
DOT = 16  # median radius in pixels under which an Outline is a dot
FOG = 15  # how much lighter (L) than the typical Day 0 a fogged lid makes the middle of the dish
AT_RIM = 0.1  # fraction of an Outline at the limit from which the Colony is at the rim


@dataclass(frozen=True)
class Outline:
    radii: np.ndarray  # pixels from the centre at each of ANGLES angles
    centre: tuple[float, float]
    diameter: float  # mm, of the circle of the same area
    longest: float  # mm
    shortest: float  # mm
    at_rim: bool
    change: float = 0.0  # mean colour change (ΔE) inside since the reference: low for a faint Colony

    def points(self) -> np.ndarray:
        theta = np.linspace(0, 2 * np.pi, ANGLES, endpoint=False)
        return np.c_[self.centre[0] + self.radii * np.cos(theta), self.centre[1] + self.radii * np.sin(theta)]

    def mask(self, size: int) -> np.ndarray:
        m = np.zeros((size, size), np.uint8)
        cv2.fillPoly(m, [np.round(self.points()).astype(np.int32)], 1)
        return m.astype(bool)


@cache
def _geometry(size: int):
    """Per-pixel radius (fraction of the dish radius) and angle (degrees, clockwise from 3 o'clock) of a Crop."""
    c = size / 2
    yy, xx = np.mgrid[:size, :size]
    rr = np.hypot(xx - c, yy - c) / (c / MARGIN)
    angle = np.degrees(np.arctan2(yy - c, xx - c)) % 360
    logo = (np.abs(angle - 90) < LOGO_SECTOR[0]) & (rr > LOGO_SECTOR[1])
    return rr, logo


def _lab(a: np.ndarray, blur: float = 1.5) -> np.ndarray:
    return cv2.cvtColor(cv2.GaussianBlur(a, (0, 0), blur), cv2.COLOR_RGB2LAB).astype(np.float32)


def _texture(a: np.ndarray) -> np.ndarray:
    g = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY).astype(np.float32)
    fine = g - cv2.GaussianBlur(g, (0, 0), 2)
    return np.sqrt(cv2.GaussianBlur(fine**2, (0, 0), 3))


def _change(img: np.ndarray, ref: np.ndarray, rr: np.ndarray, outside: np.ndarray | None = None) -> np.ndarray:
    """Colour change since the reference, with the overall shift in light removed. The shift is taken from
    bare agar near the rim (outside the given region); when the Colony covers most of that, none is removed."""
    d = _lab(img, 3) - _lab(ref, 3)
    ring = (rr > 0.78) & (rr < LIMIT)
    band = ring if outside is None else ring & outside
    if band.sum() >= 0.25 * ring.sum():
        d -= np.median(d[band], axis=0)
    return np.sqrt((d**2).sum(-1))


def _polar(a: np.ndarray, cx: float, cy: float, n: int):
    theta = np.linspace(0, 2 * np.pi, ANGLES, endpoint=False)
    r = np.arange(n)
    xs, ys = cx + np.outer(np.cos(theta), r), cy + np.outer(np.sin(theta), r)
    return cv2.remap(a, xs.astype(np.float32), ys.astype(np.float32), cv2.INTER_LINEAR), xs, ys


def _edges(polar_lab: np.ndarray, d: int = 3) -> np.ndarray:
    g = np.zeros(polar_lab.shape[:2], np.float32)
    g[:, d:-d] = np.sqrt(((polar_lab[:, 2 * d :] - polar_lab[:, : -2 * d]) ** 2).sum(-1))
    return g


def _outside(polar: np.ndarray) -> np.ndarray:
    """Mean of each row 4 to 20 pixels beyond each radius (the last 20 radii are left out)."""
    total = np.cumsum(polar, axis=1)
    return (total[:, 20:] - total[:, 4:-16]) / 16


def _trace(
    img: np.ndarray,
    ref: np.ndarray,
    centre: tuple[float, float],
    rim: bool,
    bound: np.ndarray | None = None,
    unchanged_outside: bool = False,
) -> np.ndarray:
    """Radius of the Colony's edge at each angle about centre, in pixels; reluctantly beyond bound + 4 where given.
    With rim, the path may end at the limit where it finds no clearer edge inside it. With unchanged_outside, an
    edge counts only as far as the agar just outside it looks as it did in the reference."""
    size = img.shape[0]
    c, dish = size / 2, size / 2 / MARGIN
    cx, cy = centre
    n = int((LIMIT + 0.5) * dish)  # reaches the limit from a centre up to half the dish off the middle
    lab, xs, ys = _polar(_lab(img), cx, cy, n)
    tex, _, _ = _polar(_texture(img), cx, cy, n)
    before, _, _ = _polar(_lab(ref), cx, cy, n)
    static = cv2.dilate(_edges(before), np.ones((5, 9), np.uint8))
    edge = np.clip(_edges(lab) - static, 0, None)
    edge[:, :-20] *= np.exp(-_outside(tex) / TAU)
    if unchanged_outside:
        grown, _, _ = _polar(_change(img, ref, _geometry(size)[0]), cx, cy, n)
        edge[:, :-20] *= np.exp(-_outside(grown) / CHANGE_TAU)
    score = edge - MU * np.arange(n)[None]

    rr = np.hypot(xs - c, ys - c) / dish
    angle = np.degrees(np.arctan2(ys - c, xs - c)) % 360
    logo = (np.abs(angle - 90) < LOGO_SECTOR[0]) & (rr > LOGO_SECTOR[1])
    valid = rr < LIMIT
    score[~valid] = -1e3
    if rim:
        score[np.arange(ANGLES), valid.sum(axis=1) - 1] = RIM
    # Over the logo no radius is better than another, so the path carries straight across from either side
    score[logo & valid] = (-MU * logo.argmax(axis=1)[:, None] * np.ones_like(score))[logo & valid]
    if bound is not None:
        score -= OVERSHOOT * np.clip(np.arange(n)[None] - bound[:, None] - 4, 0, None)
    score[:, :6] = -1e3

    # Best closed path: run three laps round the dish and keep the middle one, so the start angle doesn't matter
    laps = np.vstack([score] * 3)
    total = laps[0].copy()
    back = np.zeros(laps.shape, np.int8)
    for i in range(1, len(laps)):
        best, arg = np.full(n, -np.inf), np.zeros(n, np.int8)
        for s in range(-STEP, STEP + 1):
            moved = np.roll(total, s) - SMOOTH * abs(s)
            if s > 0:
                moved[:s] = -np.inf
            elif s < 0:
                moved[s:] = -np.inf
            better = moved > best
            best[better], arg[better] = moved[better], s
        total = best + laps[i]
        back[i] = arg
    path = np.zeros(len(laps), int)
    path[-1] = int(total.argmax())
    for i in range(len(laps) - 1, 0, -1):
        path[i - 1] = path[i] - back[i][path[i]]
    return path[ANGLES : 2 * ANGLES].astype(float)


def _outline(radii: np.ndarray, centre: tuple[float, float], size: int) -> Outline:
    dish = size / 2 / MARGIN
    mm = dish / (DISH_MM / 2)  # pixels per mm
    theta = np.linspace(0, 2 * np.pi, ANGLES, endpoint=False)
    area = 0.5 * (radii**2).sum() * (2 * np.pi / ANGLES)
    x, y = radii * np.cos(theta), radii * np.sin(theta)
    spans = [np.ptp(x * np.cos(a) + y * np.sin(a)) for a in np.radians(np.arange(180))]
    from_middle = np.hypot(centre[0] + x - size / 2, centre[1] + y - size / 2)
    return Outline(
        radii=radii,
        centre=centre,
        diameter=float(2 * np.sqrt(area / np.pi) / mm),
        longest=float(max(spans) / mm),
        shortest=float(min(spans) / mm),
        at_rim=bool((from_middle > LIMIT * dish - 6).mean() >= AT_RIM),
    )


def _grown_centre(img: np.ndarray, ref: np.ndarray) -> tuple[float, float]:
    """Middle of the largest patch of growth near the middle of the dish; the middle of the dish if there is none."""
    size = img.shape[0]
    rr, logo = _geometry(size)
    grown = ((_change(img, ref, rr) > GROWN) & (rr < LIMIT) & ~logo).astype(np.uint8)
    grown = cv2.morphologyEx(grown, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    n, _, stats, centres = cv2.connectedComponentsWithStats(grown)
    middle = size / 2
    near = np.hypot(centres[1:, 0] - middle, centres[1:, 1] - middle) < 0.5 * middle / MARGIN
    if n <= 1 or not near.any():
        return middle, middle
    k = 1 + int(np.where(near, stats[1:, cv2.CC_STAT_AREA], -1).argmax())
    return float(centres[k, 0]), float(centres[k, 1])


def _checked(img: np.ndarray, ref: np.ndarray, outline: Outline) -> Outline | None:
    """The Outline with its colour change filled in, or None if it holds no Colony: the agar inside it is unchanged,
    or it is a dot with growth all round (a trace that found no edge and shrank to nothing)."""
    size = img.shape[0]
    rr, _ = _geometry(size)
    inside = outline.mask(size)
    if not inside.any():
        return None
    change = float(_change(img, ref, rr, ~inside)[inside].mean())
    if change < PRESENT:
        return None
    if np.median(outline.radii) < DOT:
        # judged on the raw change: with growth all round, the light correction would take the Colony for light
        around = cv2.dilate(inside.astype(np.uint8), np.ones((31, 31), np.uint8)).astype(bool) & ~inside
        if _change(img, ref, rr, np.zeros_like(inside))[around].mean() >= GROWN:
            return None
    return replace(outline, change=change)


def measure_plate(days: dict[int, Image.Image], refs: dict[int, Image.Image]) -> dict[int, dict[str, Outline | None]]:
    """Candidate Outlines "A", "B" and "C" of the Colony of one Plate on each Day; None where there is no Colony.
    refs holds, for each Day, a Crop of the same Plate before growth."""
    imgs = {d: np.asarray(im.convert("RGB")) for d, im in days.items()}
    before = {d: np.asarray(refs[d].convert("RGB")) for d in days}
    size = next(iter(imgs.values())).shape[0]
    order = sorted(imgs, reverse=True)

    # One centre per Plate, from the last Day, where the Colony is largest
    last = order[0]
    centre = _grown_centre(imgs[last], before[last])
    first = _outline(_trace(imgs[last], before[last], centre, rim=True), centre, size).mask(size)
    if first.any():
        ys, xs = np.nonzero(first)
        centre = float(xs.mean()), float(ys.mean())

    out: dict[int, dict[str, Outline | None]] = {}
    a = c = None
    for d in order:
        a = _trace(imgs[d], before[d], centre, rim=True, bound=a)
        b = _trace(imgs[d], before[d], centre, rim=False)
        c = _trace(imgs[d], before[d], centre, rim=True, bound=c, unchanged_outside=True)
        outlines = {k: _outline(r, centre, size) for k, r in (("A", a), ("B", b), ("C", c))}
        out[d] = {k: _checked(imgs[d], before[d], o) for k, o in outlines.items()}
    return out


def _fogged(crop: Image.Image, typical: np.ndarray) -> bool:
    """A misted lid washes out the agar: the middle of the dish much lighter than on the Round's typical Day 0."""
    rr, _ = _geometry(typical.shape[0])
    middle = rr < 0.6
    return _lab(np.asarray(crop.convert("RGB")))[..., 0][middle].mean() > _lab(typical)[..., 0][middle].mean() + FOG


def references(crops: dict[tuple[int, int], Image.Image]) -> dict[tuple[int, int], Image.Image]:
    """For each Crop after Day 0, keyed (Plate, Day), a Crop of the same dish before growth to compare it with:
    the Plate's own Day 0, or if that is missing or fogged, its Day 1 (for Day 1 itself, the Round's typical Day 0)."""
    day0 = {p: im for (p, d), im in crops.items() if d == 0}
    if not day0:
        return {}
    typical = np.median(np.stack([np.asarray(im.convert("RGB")) for im in day0.values()]), axis=0).astype(np.uint8)
    out = {}
    for (p, d), im in crops.items():
        if d == 0:
            continue
        if p in day0 and not _fogged(day0[p], typical):
            out[(p, d)] = day0[p]
        elif d >= 2 and (p, 1) in crops:
            out[(p, d)] = crops[(p, 1)]
        else:
            out[(p, d)] = Image.fromarray(typical)
    return out
