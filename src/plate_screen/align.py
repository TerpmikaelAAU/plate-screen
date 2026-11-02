"""Turning every Crop so the logo moulded into the dish sits at the bottom, so all cells of a Table face the same way.

Each Crop's logo ring is unwrapped into a strip (angle × radius) and matched against the others by circular
cross-correlation. Averaging the matched strips cancels growth and scratches and leaves the logo, whose angle
gives the turn that brings it to the bottom.
"""

from typing import Hashable, TypeVar

import cv2
import numpy as np
from PIL import Image

from .crop import MARGIN

K = TypeVar("K", bound=Hashable)

BAND = (0.68, 0.85)  # where the logo sits, as a fraction of the dish radius
BINS = 720  # angle steps around the dish
LOGO_WIDTH = 100  # bins (50°): about the width of the SARSTEDT logo
MIN_CLARITY = 2.0  # best match must beat any match more than 10° away by this factor
MIN_STANDOUT = 3.0  # the logo must carry this many times the average detail of the ring (real dishes: about 7)
ROUNDS = 3


def _strip(crop: Image.Image) -> np.ndarray:
    a = np.asarray(crop.convert("L"), dtype=np.float32)
    half = a.shape[0] / 2
    radius = half / MARGIN
    polar = cv2.warpPolar(a, (int(half), BINS), (half, half), half, cv2.WARP_POLAR_LINEAR)
    band = polar[:, int(BAND[0] * radius) : int(BAND[1] * radius)]
    detail = band - cv2.GaussianBlur(band, (0, 0), 6)  # keep edges of the lettering, drop shading and growth
    detail -= detail.mean(axis=0)  # drop rings, which look the same at every angle
    spread = detail.std()
    return detail / spread if spread > 1e-3 else np.zeros_like(detail)


def _centre(ref: np.ndarray) -> float | None:
    """Angle bin at the middle of the logo: the energy-weighted centre of the brightest logo-wide stretch.
    None when no stretch stands out from the rest of the ring."""
    energy = (ref**2).sum(axis=1)
    sums = np.convolve(np.r_[energy, energy[:LOGO_WIDTH]], np.ones(LOGO_WIDTH), "valid")[:BINS]
    start = int(sums.argmax())
    if sums[start] / LOGO_WIDTH <= MIN_STANDOUT * energy.mean():
        return None
    window = np.arange(start, start + LOGO_WIDTH)
    weights = np.clip(energy - np.median(energy), 0, None)[window % BINS]
    return float((window * weights).sum() / weights.sum())


def logo_turns(crops: dict[K, Image.Image]) -> dict[K, float | None]:
    """Degrees to rotate each Crop counter-clockwise (as Image.rotate takes them) to bring its logo to the bottom;
    None where no logo stands out. Keys are (plate, day): the earliest Day seeds the match, as it has the least growth."""
    if not crops:
        return {}
    keys = sorted(crops, key=lambda k: (k[1], k[0]) if isinstance(k, tuple) else k)
    strips = np.stack([_strip(crops[k]) for k in keys])
    spectra = np.fft.rfft(strips, axis=1)

    def match(ref: np.ndarray) -> np.ndarray:
        """Correlation of every strip with ref at every shift: one row per Crop."""
        return np.fft.irfft(spectra * np.conj(np.fft.rfft(ref, axis=0))[None], n=BINS, axis=1).sum(axis=2)

    ref = strips[0]
    for _ in range(ROUNDS):
        shifts = match(ref).argmax(axis=1)
        aligned = np.stack([np.roll(s, -k, axis=0) for s, k in zip(strips, shifts)])
        ref = aligned.mean(axis=0)
    # Score each Crop against the average of the others, so a Crop never matches its own grain
    others = (aligned.sum(axis=0)[None] - aligned) / max(len(keys) - 1, 1) if len(keys) > 1 else aligned
    scores = np.fft.irfft(spectra * np.conj(np.fft.rfft(others, axis=1)), n=BINS, axis=1).sum(axis=2)
    shifts = scores.argmax(axis=1)
    logo = _centre(ref)
    if logo is None:
        return {k: None for k in keys}

    apart = np.arange(BINS)
    turns: dict[K, float | None] = {}
    for key, row, shift in zip(keys, scores, shifts):
        distance = np.minimum(np.abs(apart - shift), BINS - np.abs(apart - shift))
        best, rival = row[shift], row[distance > BINS // 36].max()
        clear = best > 0 and best > MIN_CLARITY * max(rival, 0)
        # warpPolar angles run clockwise from 3 o'clock; the bottom is 90°
        turns[key] = ((logo + shift) * 360 / BINS - 90) % 360 if clear else None
    return turns
