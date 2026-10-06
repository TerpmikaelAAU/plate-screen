"""The Table: one image per Strain, a row per Plate (Condition and Replicate), a column per Day."""

from PIL import Image, ImageDraw, ImageFont

from .key import Key

CELL = 360
GAP = 16
LABEL_WIDTH = 420  # at least; widened to fit the longest row label
HEADER = 70
TITLE = 90
BACKGROUND = (0, 0, 0)
INK = (235, 235, 235)


def table_name(strain: str) -> str:
    """Tables are photos, so JPEG: a PNG of one runs past 10 MB."""
    return strain.replace(" ", "") + ".jpg"


def font(size: int) -> ImageFont.FreeTypeFont:
    """A font with µ in it; Pillow's built-in one draws a box."""
    for name in ("DejaVuSans.ttf", "NotoSans-Regular.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def render_table(
    key: Key,
    strain: str,
    crops: dict[tuple[int, int], Image.Image],
    days: list[int],
    title: str,
) -> Image.Image:
    """crops maps (Plate number, Day) to a Crop; a missing Crop leaves its cell black."""
    rows = key.rows(strain)
    labels = [f"{p.condition}\nReplicate {p.replicate} · Plate {p.number}" for p in rows]
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    label_width = max(
        [LABEL_WIDTH] + [measure.multiline_textbbox((0, 0), t, font=font(30), spacing=10)[2] + 4 * GAP for t in labels]
    )
    width = label_width + len(days) * (CELL + GAP) + GAP
    height = TITLE + HEADER + len(rows) * (CELL + GAP) + GAP
    table = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(table)
    draw.text((width / 2, TITLE / 2), title, font=font(48), fill=INK, anchor="mm")
    for col, day in enumerate(days):
        x = label_width + col * (CELL + GAP)
        draw.text((x + CELL / 2, TITLE + HEADER / 2), f"Day {day}", font=font(34), fill=INK, anchor="mm")
    for row, (plate, label) in enumerate(zip(rows, labels)):
        y = TITLE + HEADER + row * (CELL + GAP)
        draw.multiline_text((GAP * 2, y + CELL / 2), label, font=font(30), fill=INK, anchor="lm", spacing=10)
        for col, day in enumerate(days):
            crop = crops.get((plate.number, day))
            if crop is not None:
                table.paste(crop.resize((CELL, CELL)), (label_width + col * (CELL + GAP), y))
    return table
