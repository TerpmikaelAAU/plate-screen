"""Labels: the Plate number read off each Photo's Sticky note, kept in labels.csv for a person to check."""

import csv
from dataclasses import dataclass
from itertools import groupby
from pathlib import Path

from .key import Key
from .round import Round

FILE = "labels.csv"
FIELDS = ["photo", "day", "plate", "status"]
# proposed: guessed from shooting order, not yet checked against the Sticky note
STATUSES = ("proposed", "ok", "unlabelled", "duplicate")


@dataclass
class Label:
    photo: str
    day: int
    plate: int | None
    status: str


class Labels:
    def __init__(self, path: Path, rows: list[Label]):
        self.path = path
        self.rows = rows

    @classmethod
    def load(cls, round: Round) -> "Labels":
        path = round.folder / FILE
        rows = []
        if path.exists():
            with open(path, newline="") as f:
                for r in csv.DictReader(f):
                    plate = r["plate"].strip()
                    rows.append(Label(r["photo"], int(r["day"]), int(plate) if plate else None, r["status"].strip()))
        return cls(path, rows)

    @classmethod
    def update(cls, round: Round, key: Key) -> "Labels":
        """Add a proposed row for every Photo without one. Existing rows are never changed."""
        known = {r.photo: r for r in cls.load(round).rows}
        plates = key.plates()
        rows = []
        for _, day_photos in groupby(round.photos(), key=lambda p: p.day):
            following = 0  # index into the Key of the Plate expected next
            for p in day_photos:
                row = known.get(p.name)
                if row is None:
                    plate = plates[following] if following < len(plates) else None
                    row = Label(p.name, p.day, plate, "proposed")
                    following += 1
                elif row.plate in key:
                    following = plates.index(row.plate) + 1
                rows.append(row)
        labels = cls(round.folder / FILE, rows)
        labels.save()
        return labels

    def save(self) -> None:
        with open(self.path, "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(FIELDS)
            for r in self.rows:
                w.writerow([r.photo, r.day, "" if r.plate is None else r.plate, r.status])
