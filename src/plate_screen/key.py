"""The Key: which Strain, Condition and Replicate each Plate number stands for."""

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Plate:
    number: int
    strain: str
    condition: str
    replicate: str


class Key:
    def __init__(self, plates: list[Plate]):
        self._plates = {p.number: p for p in plates}

    @classmethod
    def load(cls, path: Path) -> "Key":
        with open(path, newline="") as f:
            return cls(
                [
                    Plate(int(r["plate"]), r["strain"].strip(), r["condition"].strip(), r["replicate"].strip())
                    for r in csv.DictReader(f)
                ]
            )

    def __getitem__(self, number: int) -> Plate:
        return self._plates[number]

    def __contains__(self, number: int) -> bool:
        return number in self._plates

    def plates(self) -> list[int]:
        return sorted(self._plates)

    def strains(self) -> list[str]:
        return list(dict.fromkeys(self[n].strain for n in self.plates()))

    def rows(self, strain: str) -> list[Plate]:
        """The Plates of one Strain, in Key order: one Table row each."""
        return [self[n] for n in self.plates() if self[n].strain == strain]
