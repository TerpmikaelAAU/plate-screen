from datetime import datetime

from plate_screen.round import Round


def test_reads_local_time_from_exif_not_the_utc_filename(photo, round_dir):
    photo("PXL_20260928_235900000.jpg", datetime(2026, 9, 29, 1, 59))
    (p,) = Round(round_dir).photos()
    assert p.taken == datetime(2026, 9, 29, 1, 59)


def test_day_zero_is_the_date_of_the_earliest_photo(photo, round_dir):
    photo("a.jpg", datetime(2026, 9, 28, 13, 0))
    photo("b.jpg", datetime(2026, 9, 29, 9, 0))
    photo("c.jpg", datetime(2026, 10, 5, 23, 59))
    days = {p.path.name: p.day for p in Round(round_dir).photos()}
    assert days == {"a.jpg": 0, "b.jpg": 1, "c.jpg": 7}


def test_photos_are_listed_in_shooting_order(photo, round_dir):
    photo("late.jpg", datetime(2026, 9, 28, 13, 5))
    photo("early.jpg", datetime(2026, 9, 28, 13, 1))
    assert [p.path.name for p in Round(round_dir).photos()] == ["early.jpg", "late.jpg"]


def test_sort_moves_photos_into_day_folders(photo, round_dir):
    photo("a.jpg", datetime(2026, 9, 28, 13, 0))
    photo("b.jpg", datetime(2026, 9, 30, 9, 0))
    moves = Round(round_dir).sort()
    assert len(moves) == 2
    assert (round_dir / "Day_0" / "a.jpg").exists()
    assert (round_dir / "Day_2" / "b.jpg").exists()
    assert not (round_dir / "a.jpg").exists()


def test_sort_twice_changes_nothing(photo, round_dir):
    photo("a.jpg", datetime(2026, 9, 28, 13, 0))
    photo("b.jpg", datetime(2026, 9, 30, 9, 0))
    Round(round_dir).sort()
    assert Round(round_dir).sort() == []
    days = {p.path.name: p.day for p in Round(round_dir).photos()}
    assert days == {"a.jpg": 0, "b.jpg": 2}


def test_dry_run_moves_nothing(photo, round_dir):
    photo("a.jpg", datetime(2026, 9, 28, 13, 0))
    moves = Round(round_dir).sort(dry_run=True)
    assert [(m.src.name, m.dest.parent.name) for m in moves] == [("a.jpg", "Day_0")]
    assert (round_dir / "a.jpg").exists()


def test_sort_never_overwrites(photo, round_dir):
    photo("a.jpg", datetime(2026, 9, 28, 13, 0))
    photo("Day_0/a.jpg", datetime(2026, 9, 28, 13, 0))
    try:
        Round(round_dir).sort()
    except FileExistsError:
        pass
    else:
        raise AssertionError("expected FileExistsError")
    assert (round_dir / "a.jpg").exists()


def test_ignores_pictures_outside_the_round_and_day_folders(photo, round_dir):
    photo("a.jpg", datetime(2026, 9, 28, 13, 0))
    photo("Tables/St06.jpg", datetime(2026, 10, 9, 13, 0))
    photo("Review/sheet.jpg", datetime(2026, 10, 9, 13, 0))
    assert [p.path.name for p in Round(round_dir).photos()] == ["a.jpg"]


def test_start_date_can_be_given_by_hand(photo, round_dir):
    from datetime import date

    photo("b.jpg", datetime(2026, 9, 29, 9, 0))
    (p,) = Round(round_dir, start=date(2026, 9, 28)).photos()
    assert p.day == 1
