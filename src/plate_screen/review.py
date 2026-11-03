"""Drawing Outlines on Crops, and the sheets a reviewer reads them from."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .growth import Reading
from .table import font

COLOURS = {"A": (70, 225, 100), "B": (240, 90, 240), "C": (60, 215, 240)}
LETTER_AT = {"A": 315, "B": 225, "C": 0}  # degrees, clockwise from 3 o'clock: where each candidate's letter goes
SAME_MM = 0.5  # candidates closer than this are drawn once
FLAG = (255, 90, 80)
TEXT = (240, 240, 240)
TILE = 380
BANNER = 44


def _draw(draw: ImageDraw.ImageDraw, outline, colour, letter: str | None = None) -> None:
    pts = [tuple(p) for p in outline.points()]
    draw.line(pts + pts[:1], fill=colour, width=3)
    if letter:
        i = LETTER_AT[letter[0]] % len(pts)
        x, y = pts[i]
        draw.text((x, y), letter, font=font(30), fill=colour, anchor="mm", stroke_width=3, stroke_fill="black")


def annotated(crop: Image.Image, r: Reading) -> Image.Image:
    """The Crop with the chosen Outline and its Diameter once decided; with every candidate, lettered, and the flags
    while it waits for review."""
    im = crop.convert("RGB").copy()
    draw = ImageDraw.Draw(im)
    if r.outline:
        if r.chosen is not None:
            _draw(draw, r.chosen, COLOURS[r.outline])
        label = r.outline if r.diameter is None or r.outline == "empty" else f"{r.diameter:.1f} mm"
        if r.outline in COLOURS:
            label = f"{r.outline}  {label}"
        draw.text((12, 10), label, font=font(36), fill=TEXT)
    else:
        drawn: list[tuple[list[str], object]] = []
        for k, o in r.cell.outlines.items():
            if o is None:
                continue
            same = next((d for d in drawn if abs(d[1].diameter - o.diameter) < SAME_MM), None)
            if same:
                same[0].append(k)
            else:
                drawn.append(([k], o))
        for letters, o in drawn:
            _draw(draw, o, COLOURS[letters[0]], "=".join(letters))
        sizes = "  ".join(f"{k} {'-' if o is None else f'{o.diameter:.1f}'}" for k, o in r.cell.outlines.items())
        draw.text((12, 10), sizes, font=font(28), fill=TEXT)
    if r.flags:
        draw.text((12, im.height - 12), ", ".join(r.flags), font=font(26), fill=FLAG, anchor="ld")
    return im


def sheets(items: list[tuple[str, list[Image.Image]]], name: str, folder: Path, per_row: int, rows: int = 4) -> list[Path]:
    """Numbered sheets of tiles, each item a label above one or more images side by side; returns their paths."""
    for stale in folder.glob(f"{name}_*.jpg"):
        stale.unlink()
    per_sheet = per_row * rows
    written = []
    for n, start in enumerate(range(0, len(items), per_sheet), 1):
        batch = items[start : start + per_sheet]
        width = max(len(ims) for _, ims in batch) * TILE
        sheet = Image.new("RGB", (per_row * width, rows * (TILE + BANNER)), "black")
        draw = ImageDraw.Draw(sheet)
        for i, (label, ims) in enumerate(batch):
            x, y = (i % per_row) * width, (i // per_row) * (TILE + BANNER)
            draw.text((x + 8, y + 6), label, font=font(28), fill=TEXT)
            for j, im in enumerate(ims):
                sheet.paste(im.convert("RGB").resize((TILE, TILE)), (x + j * TILE, y + BANNER))
        used = int(np.ceil(len(batch) / per_row)) * (TILE + BANNER)
        path = folder / f"{name}_{n:02d}.jpg"
        sheet.crop((0, 0, sheet.width, used)).save(path, quality=88)
        written.append(path)
    return written
