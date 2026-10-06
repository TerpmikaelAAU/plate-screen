"""A Round: one folder of Photos, sorted into Day folders by the date each was taken."""

import re
from dataclasses import dataclass
from datetime import date, datetime
from functools import cached_property
from pathlib import Path

from PIL import Image

PHOTO_SUFFIXES = {".jpg", ".jpeg"}
DAY_FOLDER = re.compile(r"^Day_(\d+)$")

EXIF_SUB_IFD = 0x8769
DATETIME_ORIGINAL = 36867
DATETIME = 306


def taken_at(path: Path) -> datetime:
    """Local wall-clock time the Photo was taken, from its EXIF."""
    exif = Image.open(path).getexif()
    stamp = exif.get_ifd(EXIF_SUB_IFD).get(DATETIME_ORIGINAL) or exif.get(DATETIME)
    if not stamp:
        raise ValueError(f"{path} has no EXIF date")
    return datetime.strptime(stamp, "%Y:%m:%d %H:%M:%S")


@dataclass(frozen=True)
class Photo:
    path: Path
    taken: datetime
    day: int

    @property
    def name(self) -> str:
        return self.path.name


@dataclass(frozen=True)
class Move:
    src: Path
    dest: Path


class Round:
    def __init__(self, folder: Path | str, start: date | None = None):
        self.folder = Path(folder)
        self._start = start

    def _paths(self) -> list[Path]:
        """Photos in the Round folder itself or in its Day folders; nothing else."""
        dirs = [self.folder] + sorted(
            d for d in self.folder.iterdir() if d.is_dir() and DAY_FOLDER.match(d.name)
        )
        return [
            p for d in dirs for p in d.iterdir() if p.is_file() and p.suffix.lower() in PHOTO_SUFFIXES
        ]

    @cached_property
    def _taken(self) -> dict[Path, datetime]:
        return {p: taken_at(p) for p in self._paths()}

    @property
    def start(self) -> date:
        if self._start:
            return self._start
        if not self._taken:
            raise ValueError(f"no Photos in {self.folder}")
        return min(self._taken.values()).date()

    def photos(self) -> list[Photo]:
        """Every Photo in the Round, in shooting order."""
        start = self.start
        return sorted(
            (Photo(p, t, (t.date() - start).days) for p, t in self._taken.items()),
            key=lambda p: (p.taken, p.name),
        )

    def sort(self, dry_run: bool = False) -> list[Move]:
        """Move each Photo into Day_N/. Refuses to overwrite; a sorted Round is left alone."""
        moves = [
            Move(p.path, self.folder / f"Day_{p.day}" / p.name)
            for p in self.photos()
            if p.path.parent != self.folder / f"Day_{p.day}"
        ]
        clashes = [m.dest for m in moves if m.dest.exists()]
        if clashes:
            raise FileExistsError(f"would overwrite {', '.join(map(str, clashes))}")
        if not dry_run:
            for m in moves:
                m.dest.parent.mkdir(exist_ok=True)
                m.src.rename(m.dest)
            self.__dict__.pop("_taken", None)
        return moves
