from datetime import datetime

from plate_screen.key import Key
from plate_screen.labels import Labels
from plate_screen.round import Round

KEY = """plate,strain,condition,replicate
1,St 06,Vogel,A
2,St 06,Vogel,B
3,St 07,Vogel,A
"""


def write_key(round_dir, text=KEY):
    round_dir.mkdir(parents=True, exist_ok=True)
    (round_dir / "key.csv").write_text(text)
    return Key.load(round_dir / "key.csv")


def test_key_reads_strain_condition_and_replicate(round_dir):
    key = write_key(round_dir)
    assert key[2].strain == "St 06" and key[2].condition == "Vogel" and key[2].replicate == "B"
    assert key.strains() == ["St 06", "St 07"]
    assert key.plates() == [1, 2, 3]


def test_proposes_plate_numbers_from_shooting_order_each_day(photo, round_dir):
    for i, minute in enumerate([1, 2, 3]):
        photo(f"d0_{i}.jpg", datetime(2026, 9, 28, 13, minute))
        photo(f"d1_{i}.jpg", datetime(2026, 9, 29, 10, minute))
    key = write_key(round_dir)
    labels = Labels.update(Round(round_dir), key)
    assert [(r.photo, r.day, r.plate, r.status) for r in labels.rows[:4]] == [
        ("d0_0.jpg", 0, 1, "proposed"),
        ("d0_1.jpg", 0, 2, "proposed"),
        ("d0_2.jpg", 0, 3, "proposed"),
        ("d1_0.jpg", 1, 1, "proposed"),
    ]


def test_extra_photos_get_no_proposal(photo, round_dir):
    for minute in range(4):
        photo(f"{minute}.jpg", datetime(2026, 9, 28, 13, minute))
    labels = Labels.update(Round(round_dir), write_key(round_dir))
    assert labels.rows[3].plate is None


def test_labels_are_saved_and_edits_survive_a_rerun(photo, round_dir):
    photo("a.jpg", datetime(2026, 9, 28, 13, 1))
    key = write_key(round_dir)
    Labels.update(Round(round_dir), key)
    csv = round_dir / "labels.csv"
    assert csv.read_text().splitlines()[0] == "photo,day,plate,status"
    csv.write_text("photo,day,plate,status\na.jpg,0,3,ok\n")
    photo("b.jpg", datetime(2026, 9, 28, 13, 2))
    labels = Labels.update(Round(round_dir), key)
    assert [(r.photo, r.plate, r.status) for r in labels.rows] == [
        ("a.jpg", 3, "ok"),
        ("b.jpg", None, "proposed"),
    ]


def test_a_new_photo_is_proposed_the_plate_after_the_last_one_before_it(photo, round_dir):
    photo("a.jpg", datetime(2026, 9, 28, 13, 1))
    key = write_key(round_dir)
    Labels.update(Round(round_dir), key)
    (round_dir / "labels.csv").write_text("photo,day,plate,status\na.jpg,0,2,ok\n")
    photo("b.jpg", datetime(2026, 9, 28, 13, 2))
    labels = Labels.update(Round(round_dir), key)
    assert labels.rows[1].plate == 3


def test_label_rows_follow_photos_into_day_folders(photo, round_dir):
    photo("a.jpg", datetime(2026, 9, 28, 13, 1))
    key = write_key(round_dir)
    Labels.update(Round(round_dir), key)
    Round(round_dir).sort()
    labels = Labels.update(Round(round_dir), key)
    assert [(r.photo, r.plate) for r in labels.rows] == [("a.jpg", 1)]
