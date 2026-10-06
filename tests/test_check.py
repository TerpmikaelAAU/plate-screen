from plate_screen.check import check
from plate_screen.key import Key, Plate
from plate_screen.labels import Label

KEY = Key([Plate(n, "St 06", "Vogel", "AB"[n % 2]) for n in (1, 2, 3)])


def rows(*spec):
    """spec: (day, plate, status) in shooting order."""
    return [Label(f"{i}.jpg", d, p, s) for i, (d, p, s) in enumerate(spec)]


def test_a_complete_round_has_no_problems():
    assert check(KEY, rows((0, 1, "ok"), (0, 2, "ok"), (0, 3, "ok"))) == []


def test_reports_missing_plates():
    assert check(KEY, rows((0, 1, "ok"), (0, 3, "ok"))) == ["Day 0: no Photo of Plate 2"]


def test_reports_a_plate_photographed_twice():
    problems = check(KEY, rows((0, 1, "ok"), (0, 2, "ok"), (0, 2, "ok"), (0, 3, "ok")))
    assert problems == ["Day 0: Plate 2 is on 1.jpg, 2.jpg; mark all but one as duplicate"]


def test_reports_plate_numbers_not_in_the_key():
    problems = check(KEY, rows((0, 1, "ok"), (0, 2, "ok"), (0, 3, "ok"), (0, 9, "ok")))
    assert problems == ["Day 0: 3.jpg is labelled Plate 9, which is not in the Key"]


def test_flags_labels_out_of_shooting_order():
    problems = check(KEY, rows((0, 1, "ok"), (0, 3, "ok"), (0, 2, "ok")))
    assert problems == ["Day 0: 2.jpg (Plate 2) was shot after Plate 3; worth a second look"]


def test_reports_unchecked_proposals():
    problems = check(KEY, rows((0, 1, "ok"), (0, 2, "proposed"), (0, 3, "ok")))
    assert problems == ["Day 0: 1.jpg is still proposed; check its Sticky note"]


def test_unlabelled_and_duplicate_photos_are_left_out_quietly():
    spec = ((0, 1, "ok"), (0, None, "unlabelled"), (0, 2, "ok"), (0, 2, "duplicate"), (0, 3, "ok"))
    assert check(KEY, rows(*spec)) == []


def test_reports_unknown_status_and_missing_plate_number():
    problems = check(KEY, rows((0, 1, "ok"), (0, 2, "fine"), (0, None, "ok"), (0, 3, "ok")))
    assert problems == [
        "Day 0: 1.jpg has status 'fine'; use one of proposed, ok, unlabelled, duplicate",
        "Day 0: 2.jpg is ok but has no Plate number",
        "Day 0: no Photo of Plate 2",
    ]
