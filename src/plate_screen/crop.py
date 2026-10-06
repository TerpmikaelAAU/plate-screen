"""Crops: finding the dish in a Photo and cutting it out onto black."""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps

Circle = tuple[float, float, float]  # centre x, centre y, radius, in Photo pixels

WORK_WIDTH = 768  # detection runs on a downscaled copy
MARGIN = 1.04  # keep a sliver of background around the rim


def _gray(image: Image.Image) -> tuple[np.ndarray, float]:
    image = ImageOps.exif_transpose(image).convert("L")
    scale = image.width / WORK_WIDTH
    small = image.resize((WORK_WIDTH, round(image.height / scale)), Image.Resampling.BOX)
    return np.asarray(small, dtype=np.uint8), scale


def _fit_rim(gray: np.ndarray, x: float, y: float, r: float) -> Circle:
    """Hough often locks onto the inner wall of the dish and lands a little off centre. Walk outwards
    along each ray to where the dish meets the cloth, then fit a circle through those rim points."""
    radii = np.arange(0.7 * r, 1.4 * r)
    angles = np.linspace(0, 2 * np.pi, 180, endpoint=False)
    xs = np.clip((x + np.outer(radii, np.cos(angles))).astype(int), 0, gray.shape[1] - 1)
    ys = np.clip((y + np.outer(radii, np.sin(angles))).astype(int), 0, gray.shape[0] - 1)
    rays = gray[ys, xs].astype(float)  # one column per angle
    background = np.median(rays[-5:])
    dish = np.median(rays[: len(radii) // 2])
    inside = rays > (dish + background) / 2
    if not inside.any():
        return x, y, r
    edge = radii[len(radii) - 1 - np.argmax(inside[::-1], axis=0)]  # outermost bright point per ray
    keep = inside.any(axis=0) & (np.abs(edge - np.median(edge)) < 0.08 * r)  # drop rays that hit a note
    if keep.sum() < 20:
        return x, y, r
    px, py = x + edge[keep] * np.cos(angles[keep]), y + edge[keep] * np.sin(angles[keep])
    # Least-squares circle: x^2 + y^2 = 2ax + 2by + c
    a, b, c = np.linalg.lstsq(np.c_[2 * px, 2 * py, np.ones_like(px)], px**2 + py**2, rcond=None)[0]
    return float(a), float(b), float(np.sqrt(c + a * a + b * b))


def find_dish(image: Image.Image) -> Circle | None:
    gray, scale = _gray(image)
    blurred = cv2.GaussianBlur(gray, (5, 5), 1.5)
    w = gray.shape[1]
    found = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.5,
        minDist=w,
        param1=80,
        param2=40,
        minRadius=int(w * 0.12),
        maxRadius=int(w * 0.3),
    )
    if found is None:
        return None
    x, y, r = _fit_rim(blurred, *(float(v) for v in found[0][0]))
    return x * scale, y * scale, r * scale


def crop_plate(image: Image.Image, circle: Circle, size: int = 600) -> Image.Image:
    image = ImageOps.exif_transpose(image).convert("RGB")
    x, y, r = circle
    half = r * MARGIN
    box = tuple(round(v) for v in (x - half, y - half, x + half, y + half))
    square = Image.new("RGB", (box[2] - box[0], box[3] - box[1]))
    square.paste(image.crop(box))
    square = square.resize((size, size), Image.Resampling.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    edge = size * (1 - 1 / MARGIN) / 2
    ImageDraw.Draw(mask).ellipse((edge, edge, size - edge, size - edge), fill=255)
    out = Image.new("RGB", (size, size))
    out.paste(square, mask=mask)
    return out
