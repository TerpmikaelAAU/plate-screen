"""The steps of a Round, in order: sort, label, check, crop, table. Each reads and writes files in the Round folder."""

import csv
from pathlib import Path

from PIL import Image, ImageDraw

from .check import check as check_labels
from .crop import Circle, crop_plate, find_dish
from .key import Key, Plate
from .labels import Labels
from .round import Move, Round
from .table import font, render_table, table_name

KEY_FILE = "key.csv"
OVERRIDES_FILE = "crop_overrides.csv"
REVIEW = "Review"
TABLES = "Tables"
USED = ("proposed", "ok")  # unlabelled and duplicate Photos stay out of Crops and Tables


def _key(round: Round) -> Key:
    return Key.load(round.folder / KEY_FILE)


def sort(round: Round, dry_run: bool = False) -> list[Move]:
    return round.sort(dry_run=dry_run)


def label(round: Round) -> Labels:
    """Propose a Plate number for each new Photo and draw a sheet per Day to check them against the Sticky notes."""
    labels = Labels.update(round, _key(round))
    by_name = {p.name: p for p in round.photos()}
    review = round.folder / REVIEW
    review.mkdir(exist_ok=True)
    for day in sorted({r.day for r in labels.rows}):
        rows = [r for r in labels.rows if r.day == day]
        _note_sheet([(by_name[r.photo], r) for r in rows if r.photo in by_name]).save(
            review / f"notes_Day_{day}.jpg", quality=85
        )
    return labels


def _note_sheet(items, tile=(300, 400), cols=6) -> Image.Image:
    banner = 64
    w, h = tile
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * (h + banner)), "white")
    draw = ImageDraw.Draw(sheet)
    big, small = font(20), font(14)
    for i, (photo, label) in enumerate(items):
        x, y = (i % cols) * w, (i // cols) * (h + banner)
        im = Image.open(photo.path)
        im.draft("RGB", (w * 2, h * 2))
        sheet.paste(im.convert("RGB").resize(tile), (x, y + banner))
        plate = "-" if label.plate is None else label.plate
        draw.text((x + 6, y + 4), f"#{i + 1}  {label.status}: {plate}", font=big, fill="black")
        draw.text((x + 6, y + 30), f"{photo.taken:%H:%M:%S}  {photo.name}", font=small, fill="gray")
    return sheet


def check(round: Round) -> list[str]:
    return check_labels(_key(round), Labels.load(round).rows)


def _overrides(round: Round) -> dict[str, Circle]:
    path = round.folder / OVERRIDES_FILE
    if not path.exists():
        return {}
    with open(path, newline="") as f:
        return {r["photo"]: (float(r["x"]), float(r["y"]), float(r["r"])) for r in csv.DictReader(f)}


def _crop_dir(round: Round) -> Path:
    return round.folder / REVIEW / "crops"


def crop(round: Round) -> list[str]:
    """Crop every labelled Photo (cached in Review/crops) and draw Review/crops.jpg. Returns Photos with no dish found."""
    labels = [r for r in Labels.load(round).rows if r.status in USED and r.plate is not None]
    paths = {p.name: p.path for p in round.photos()}
    overrides = _overrides(round)
    out = _crop_dir(round)
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.iterdir():
        if stale.name not in {r.photo for r in labels}:
            stale.unlink()
    failed = []
    for r in labels:
        target = out / r.photo
        if target.exists() and r.photo not in overrides:
            continue
        image = Image.open(paths[r.photo])
        circle = overrides.get(r.photo) or find_dish(image)
        if circle is None:
            failed.append(r.photo)
            continue
        crop_plate(image, circle).save(target, quality=92)
    _crops_sheet(round, labels).save(round.folder / REVIEW / "crops.jpg", quality=90)
    return failed


def _crops(round: Round, labels) -> dict[tuple[int, int], Image.Image]:
    crops = {}
    for r in labels:
        path = _crop_dir(round) / r.photo
        if path.exists():
            crops[(r.plate, r.day)] = Image.open(path)
    return crops


def _crops_sheet(round: Round, labels) -> Image.Image:
    """Every Crop at a glance: a small Table of all Plates, to spot a bad Crop or a wrong Label."""
    key = _key(round)
    everything = Key([Plate(n, "all", f"{key[n].strain} · {key[n].condition}", key[n].replicate) for n in key.plates()])
    days = sorted({r.day for r in labels})
    sheet = render_table(everything, "all", _crops(round, labels), days, title=f"{round.folder.name}: all Crops")
    return sheet.resize((sheet.width // 3, sheet.height // 3))


def table(round: Round) -> list[Path]:
    key = _key(round)
    labels = [r for r in Labels.load(round).rows if r.status in USED and r.plate in key]
    crops = _crops(round, labels)
    days = list(range(max((r.day for r in labels), default=0) + 1))
    out = round.folder / TABLES
    out.mkdir(exist_ok=True)
    written = []
    for strain in key.strains():
        path = out / table_name(strain)
        render_table(key, strain, crops, days, title=f"{strain}  ·  {round.folder.name}").save(path, quality=90)
        written.append(path)
    return written


def embed(path: Path) -> str:
    """The notebook link for a file: relative to the folder holding .terpnotes/, if any."""
    path = path.resolve()
    for parent in path.parents:
        if (parent / ".terpnotes").is_dir():
            return f"![[{path.relative_to(parent).as_posix()}]]"
    return f"![[{path}]]"
