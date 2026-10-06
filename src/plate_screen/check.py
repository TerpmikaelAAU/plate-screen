"""Checks run on the Labels before a Table is built. They warn; they never block."""

from collections import defaultdict
from itertools import groupby

from .key import Key
from .labels import STATUSES, Label

COUNTED = ("proposed", "ok")


def check(key: Key, labels: list[Label]) -> list[str]:
    problems = []
    for day, day_rows in groupby(sorted(labels, key=lambda r: r.day), key=lambda r: r.day):
        day_rows = list(day_rows)
        seen = defaultdict(list)
        last = None
        for r in day_rows:
            if r.status not in STATUSES:
                problems.append(f"Day {day}: {r.photo} has status '{r.status}'; use one of {', '.join(STATUSES)}")
                continue
            if r.status not in COUNTED:
                continue
            if r.plate is None:
                problems.append(f"Day {day}: {r.photo} is {r.status} but has no Plate number")
                continue
            if r.plate not in key:
                problems.append(f"Day {day}: {r.photo} is labelled Plate {r.plate}, which is not in the Key")
                continue
            if r.status == "proposed":
                problems.append(f"Day {day}: {r.photo} is still proposed; check its Sticky note")
            if last is not None and r.plate < last:
                problems.append(f"Day {day}: {r.photo} (Plate {r.plate}) was shot after Plate {last}; worth a second look")
            last = r.plate
            seen[r.plate].append(r.photo)
        for plate in key.plates():
            photos = seen.get(plate, [])
            if not photos:
                problems.append(f"Day {day}: no Photo of Plate {plate}")
            elif len(photos) > 1:
                problems.append(f"Day {day}: Plate {plate} is on {', '.join(photos)}; mark all but one as duplicate")
    return problems
