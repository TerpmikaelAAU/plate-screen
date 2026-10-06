"""Synthetic Photos: a light dish on dark cloth with a yellow Sticky note, stamped with an EXIF date."""

from datetime import datetime
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

W, H = 600, 800
DISH = (360, 300, 110)  # centre x, centre y, radius


def write_photo(path: Path, taken: datetime, dish=DISH, offset="+02:00") -> Path:
    im = Image.new("RGB", (W, H), (60, 62, 66))
    d = ImageDraw.Draw(im)
    x, y, r = dish
    d.ellipse((x - r, y - r, x + r, y + r), fill=(200, 205, 210))
    d.ellipse((x - r + 12, y - r + 12, x + r - 12, y + r - 12), fill=(170, 185, 200))
    d.ellipse((x - 20, y - 20, x + 20, y + 20), fill=(150, 140, 100))
    d.rectangle((10, 520, 230, 790), fill=(235, 235, 150))
    exif = Image.Exif()
    stamp = taken.strftime("%Y:%m:%d %H:%M:%S")
    exif[306] = stamp
    sub = exif.get_ifd(0x8769)
    sub[36867] = stamp
    sub[36881] = offset
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, exif=exif)
    return path


@pytest.fixture
def photo(tmp_path):
    def make(name: str, taken: datetime, **kw) -> Path:
        return write_photo(tmp_path / "round" / name, taken, **kw)

    return make


@pytest.fixture
def round_dir(tmp_path):
    return tmp_path / "round"
