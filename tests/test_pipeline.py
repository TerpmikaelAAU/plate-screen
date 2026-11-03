import csv
from datetime import datetime

from PIL import Image

from plate_screen import pipeline
from plate_screen.round import Round

KEY = """plate,strain,condition,replicate
1,St 06,Vogel,A
2,St 06,Vogel,B
3,St 07,Vogel + 200 µg/mL Hyg,A
"""


def make_round(photo, round_dir, days=2):
    for day in range(days):
        for plate in range(3):
            photo(f"d{day}_p{plate + 1}.jpg", datetime(2026, 9, 28 + day, 13, plate))
    (round_dir / "key.csv").write_text(KEY)
    return Round(round_dir)


def test_label_writes_a_review_sheet_per_day(photo, round_dir):
    r = make_round(photo, round_dir)
    pipeline.label(r)
    assert (round_dir / "labels.csv").exists()
    assert sorted(p.name for p in (round_dir / "Review").glob("notes_*.jpg")) == [
        "notes_Day_0.jpg",
        "notes_Day_1.jpg",
    ]


def test_full_run_writes_a_table_per_strain(photo, round_dir):
    r = make_round(photo, round_dir)
    pipeline.label(r)
    problems = pipeline.check(r)
    assert all("still proposed" in p for p in problems)
    failed = pipeline.crop(r)
    assert failed == []
    assert (round_dir / "Review" / "crops.jpg").exists()
    written = pipeline.table(r)
    assert [p.name for p in written] == ["St06.jpg", "St07.jpg"]
    assert Image.open(round_dir / "Tables" / "St06.jpg").width > 0


def test_a_photo_with_no_dish_is_reported_and_can_be_cropped_by_hand(photo, round_dir):
    r = make_round(photo, round_dir, days=1)
    blank = round_dir / "d0_p2.jpg"
    Image.new("RGB", (600, 800), (60, 62, 66)).save(blank, exif=Image.open(round_dir / "d0_p1.jpg").getexif())
    pipeline.label(r)
    assert pipeline.crop(r) == ["d0_p2.jpg"]
    (round_dir / "crop_overrides.csv").write_text("photo,x,y,r\nd0_p2.jpg,300,400,100\n")
    assert pipeline.crop(r) == []


def test_crops_with_no_logo_found_are_reported(photo, round_dir):
    r = make_round(photo, round_dir, days=1)
    pipeline.label(r)
    pipeline.crop(r)
    assert pipeline.unturned(r) == ["d0_p1.jpg", "d0_p2.jpg", "d0_p3.jpg"]


def test_unlabelled_photos_are_not_cropped(photo, round_dir):
    r = make_round(photo, round_dir, days=1)
    pipeline.label(r)
    csv = round_dir / "labels.csv"
    csv.write_text(csv.read_text().replace("d0_p2.jpg,0,2,proposed", "d0_p2.jpg,0,,unlabelled"))
    pipeline.crop(r)
    assert sorted(p.name for p in (round_dir / "Review" / "crops").iterdir()) == ["d0_p1.jpg", "d0_p3.jpg"]


def test_notebook_embed_is_relative_to_the_notebook(tmp_path, photo, round_dir):
    (tmp_path / ".terpnotes").mkdir()
    assert pipeline.embed(round_dir / "Tables" / "St06.jpg") == "![[round/Tables/St06.jpg]]"


def test_measure_writes_diameters_review_sheets_and_plots(photo, round_dir):
    r = make_round(photo, round_dir, days=3)
    pipeline.label(r)
    pipeline.crop(r)
    pipeline.measure(r)
    out = round_dir / "Measurements"
    assert sorted(p.name for p in out.iterdir()) == [
        "St06.png", "St07.png", "diameters.csv", "growth.csv", "summary.csv", "summary.png",
    ]
    rows = list(csv.DictReader(open(out / "diameters.csv")))
    assert [(x["plate"], x["day"]) for x in rows] == [(p, d) for p in "123" for d in "12"]  # Day 0 is the reference
    assert {(p.name) for p in (round_dir / "Review").glob("outlines_*.jpg")} == {"outlines_St06.jpg", "outlines_St07.jpg"}


def test_a_reviewed_outline_and_satellites_are_kept(photo, round_dir):
    r = make_round(photo, round_dir, days=2)
    pipeline.label(r)
    pipeline.crop(r)
    (round_dir / "measure_overrides.csv").write_text("photo,outline,satellites,note\nd1_p2.jpg,none,2,smudge\n")
    rows = {x["photo"]: x for x in csv.DictReader(open(pipeline.measure(r).diameters))}
    assert (rows["d1_p2.jpg"]["outline"], rows["d1_p2.jpg"]["diameter_mm"]) == ("none", "")
    assert (rows["d1_p2.jpg"]["satellites"], rows["d1_p2.jpg"]["note"]) == ("2", "smudge")
