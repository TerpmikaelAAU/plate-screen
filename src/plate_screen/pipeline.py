"""The steps of a Round, in order: sort, label, check, crop, table, measure. Each reads and writes files in the Round folder."""

import csv
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path

from PIL import Image, ImageDraw

from .align import logo_turns
from . import plots
from .check import check as check_labels
from .crop import Circle, crop_plate, find_dish
from .growth import CHOICES, Cell, Growth, Reading, Summary, growth_rates, read, summary
from .key import Key, Plate
from .labels import Label, Labels
from .measure import measure_plate, references
from .review import annotated, sheets
from .round import Move, Round
from .table import font, render_table, table_name

KEY_FILE = "key.csv"
OVERRIDES_FILE = "crop_overrides.csv"
MEASURE_OVERRIDES_FILE = "measure_overrides.csv"
REVIEW = "Review"
TABLES = "Tables"
MEASUREMENTS = "Measurements"
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


def _used(round: Round) -> list[Label]:
    """Labels whose Photos go into Crops and Tables. The same set every time, as each Crop's turn depends on the rest."""
    return [r for r in Labels.load(round).rows if r.status in USED and r.plate is not None]


def _crop_dir(round: Round) -> Path:
    return round.folder / REVIEW / "crops"


def crop(round: Round) -> list[str]:
    """Crop every labelled Photo (cached in Review/crops) and draw Review/crops.jpg. Returns Photos with no dish found."""
    labels = _used(round)
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


def _cached(round: Round, labels) -> dict[tuple[int, int], tuple[str, Image.Image]]:
    found = {}
    for r in labels:
        path = _crop_dir(round) / r.photo
        if path.exists():
            found[(r.plate, r.day)] = (r.photo, Image.open(path))
    return found


def _crops(round: Round, labels) -> dict[tuple[int, int], Image.Image]:
    """Cached Crops, each turned so the logo moulded into the dish sits at the bottom; left as they are where none is found."""
    cached = _cached(round, labels)
    turns = logo_turns({k: im for k, (_, im) in cached.items()})
    return {
        k: im if turns[k] is None else im.rotate(turns[k], resample=Image.Resampling.BICUBIC)
        for k, (_, im) in cached.items()
    }


def unturned(round: Round) -> list[str]:
    """Photos whose Crop shows no logo to turn by, so they keep the angle they were shot at."""
    labels = _used(round)
    cached = _cached(round, labels)
    turns = logo_turns({k: im for k, (_, im) in cached.items()})
    return sorted(photo for k, (photo, _) in cached.items() if turns[k] is None)


def _crops_sheet(round: Round, labels) -> Image.Image:
    """Every Crop at a glance: a small Table of all Plates, to spot a bad Crop or a wrong Label."""
    key = _key(round)
    everything = Key([Plate(n, "all", f"{key[n].strain} · {key[n].condition}", key[n].replicate) for n in key.plates()])
    days = sorted({r.day for r in labels})
    sheet = render_table(everything, "all", _crops(round, labels), days, title=f"{round.folder.name}: all Crops")
    return sheet.resize((sheet.width // 3, sheet.height // 3))


def table(round: Round) -> list[Path]:
    key = _key(round)
    labels = _used(round)
    crops = _crops(round, labels)
    days = list(range(max((r.day for r in labels if r.plate in key), default=0) + 1))
    out = round.folder / TABLES
    out.mkdir(exist_ok=True)
    written = []
    for strain in key.strains():
        path = out / table_name(strain)
        render_table(key, strain, crops, days, title=f"{strain}  ·  {round.folder.name}").save(path, quality=90)
        written.append(path)
    return written


def _measure_overrides(round: Round) -> dict[str, dict[str, str]]:
    """The review's say per Photo: which Outline is right (blank to leave it to the measuring), Satellites, a note."""
    path = round.folder / MEASURE_OVERRIDES_FILE
    if not path.exists():
        return {}
    rows = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f, restkey="more"):
            # A note with an unquoted comma spills into more fields
            r["note"] = ",".join([r.get("note") or "", *r.pop("more", [])])
            r = {k: (v or "").strip() for k, v in r.items()}
            rows[r["photo"]] = r
    for photo, r in rows.items():
        if r.get("outline") and r["outline"] not in CHOICES:
            raise ValueError(f"{MEASURE_OVERRIDES_FILE}: {photo} has outline {r['outline']!r}, not one of {', '.join(CHOICES)}")
    return rows


@dataclass
class Measured:
    readings: list[Reading]
    growth: list[Growth]
    summary: list[Summary]
    diameters: Path
    sheets: list[Path]  # Review/outlines_<Strain>.jpg, then the flagged and decided sheets for review
    figures: list[Path]


def _mm(x: float | None) -> str:
    return "" if x is None else f"{x:.1f}"


def _write(path: Path, header: list[str], rows: list[list]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def measure(round: Round) -> Measured:
    """Measure the Colony on every Crop after Day 0, write Measurements/ (Diameters, Growth rates, plots), and draw
    the Outlines into Review/ for checking. Rerun after editing measure_overrides.csv."""
    key = _key(round)
    labels = _used(round)
    photos = {k: photo for k, (photo, _) in _cached(round, labels).items()}
    crops = _crops(round, labels)
    refs = references(crops)
    if not refs:
        raise ValueError("no Crops to measure: measuring needs a Day 0 Photo of each Plate and `run` done first")
    overrides = _measure_overrides(round)
    day0 = datetime.combine(round.start, time())
    at = {p.name: (p.taken - day0) / timedelta(days=1) for p in round.photos()}

    unknown = sorted(set(overrides) - set(photos.values()))
    if unknown:
        raise ValueError(f"{MEASURE_OVERRIDES_FILE}: no labelled Crop for {', '.join(unknown)}")

    cells = []
    for plate in key.plates():
        days = sorted(d for p, d in refs if p == plate)
        if not days:
            continue
        outlines = measure_plate({d: crops[(plate, d)] for d in days}, {d: refs[(plate, d)] for d in days})
        for d in days:
            photo = photos[(plate, d)]
            cells.append(Cell(photo, key[plate], d, outlines[d], overrides.get(photo, {}).get("outline") or None, at.get(photo)))
    readings = read(cells)
    growth = growth_rates(readings)
    rows = summary(growth)

    out = round.folder / MEASUREMENTS
    out.mkdir(exist_ok=True)
    diameters = out / "diameters.csv"
    _write(
        diameters,
        ["photo", "plate", "day", "strain", "condition", "replicate", "A_mm", "B_mm", "C_mm", "outline",
         "diameter_mm", "longest_mm", "shortest_mm", "at_rim", "change", "satellites", "flags", "note"],
        [
            [r.cell.photo, p.number, r.cell.day, p.strain, p.condition, p.replicate,
             *(_mm(None if o is None else o.diameter) for o in r.cell.outlines.values()),
             r.outline, _mm(r.diameter), _mm(r.chosen and r.chosen.longest), _mm(r.chosen and r.chosen.shortest),
             "" if r.chosen is None else int(r.chosen.at_rim), _mm(r.chosen and r.chosen.change),
             overrides.get(r.cell.photo, {}).get("satellites", ""), "; ".join(r.flags),
             overrides.get(r.cell.photo, {}).get("note", "")]
            for r in readings
            for p in [r.cell.plate]
        ],
    )
    _write(
        out / "growth.csv",
        ["plate", "strain", "condition", "replicate", "rate_mm_per_day", "days"],
        [[g.plate.number, g.plate.strain, g.plate.condition, g.plate.replicate,
          "" if g.rate is None else f"{g.rate:.2f}", " ".join(map(str, g.days))] for g in growth],
    )
    _write(
        out / "summary.csv",
        ["strain", "condition", "plates", "rate_mm_per_day", "sd", "percent_of_vogel"],
        [[s.strain, s.condition, s.plates, "" if s.rate is None else f"{s.rate:.2f}",
          "" if s.spread is None else f"{s.spread:.2f}", _mm(s.percent_of_vogel)] for s in rows],
    )

    review = round.folder / REVIEW
    review.mkdir(exist_ok=True)
    drawn = {(r.cell.plate.number, r.cell.day): annotated(crops[(r.cell.plate.number, r.cell.day)], r) for r in readings}
    days = sorted({r.cell.day for r in readings})
    written = []
    for strain in key.strains():
        path = review / f"outlines_{table_name(strain)}"
        render_table(key, strain, drawn, days, title=f"{strain}  ·  {round.folder.name}  ·  Outlines").save(path, quality=88)
        written.append(path)
    tag = lambda r: f"p{r.cell.plate.number} D{r.cell.day}"  # noqa: E731
    flagged = [(f"{tag(r)}  {', '.join(r.flags)}", [crops[(r.cell.plate.number, r.cell.day)], drawn[(r.cell.plate.number, r.cell.day)]])
               for r in readings if not r.outline]
    decided = [(tag(r), [drawn[(r.cell.plate.number, r.cell.day)]]) for r in readings if r.outline]
    written += sheets(flagged, "flagged", review, per_row=2) + sheets(decided, "decided", review, per_row=4)

    colour = plots.colours([key[n].condition for n in key.plates()])
    figures = []
    for strain in key.strains():
        path = out / table_name(strain).replace(".jpg", ".png")
        plots.save(plots.strain_figure(strain, readings, growth, rows, colour), path)
        figures.append(path)
    path = out / "summary.png"
    plots.save(plots.summary_figure(f"{round.folder.name}: Growth rate against Vogel", rows, colour), path)
    figures.append(path)
    return Measured(readings, growth, rows, diameters, written, figures)


def embed(path: Path) -> str:
    """The notebook link for a file: relative to the folder holding .terpnotes/, if any."""
    path = path.resolve()
    for parent in path.parents:
        if (parent / ".terpnotes").is_dir():
            return f"![[{path.relative_to(parent).as_posix()}]]"
    return f"![[{path}]]"
