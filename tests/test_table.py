import numpy as np
from PIL import Image

from plate_screen.key import Key, Plate
from plate_screen.table import CELL, render_table, table_name

KEY = Key(
    [
        Plate(1, "St 06", "Vogel", "A"),
        Plate(2, "St 06", "Vogel", "B"),
        Plate(3, "St 07", "Vogel", "A"),
    ]
)


def crop(colour):
    return Image.new("RGB", (CELL, CELL), colour)


def test_one_row_per_plate_of_the_strain_and_one_column_per_day():
    crops = {(1, 0): crop("red"), (2, 0): crop("red"), (1, 1): crop("red"), (2, 1): crop("red")}
    two_rows = render_table(KEY, "St 06", crops, days=[0, 1], title="St 06")
    one_row = render_table(KEY, "St 07", {}, days=[0, 1], title="St 07")
    three_days = render_table(KEY, "St 06", crops, days=[0, 1, 2], title="St 06")
    assert two_rows.height - one_row.height >= CELL
    assert three_days.width - two_rows.width >= CELL


def test_cells_hold_the_crop_and_a_missing_photo_is_left_black():
    table = render_table(KEY, "St 06", {(1, 0): crop((255, 0, 0))}, days=[0], title="St 06")
    a = np.asarray(table).reshape(-1, 3)
    red = ((a[:, 0] > 200) & (a[:, 1] < 50)).sum()
    assert CELL * CELL * 0.9 <= red <= CELL * CELL * 1.1  # one cell red, the other blank


def test_table_file_name_drops_spaces():
    assert table_name("St 06") == "St06.jpg"


def test_a_long_condition_widens_the_label_column_instead_of_running_into_the_crops():
    short = render_table(KEY, "St 07", {}, days=[0], title="t")
    long = Key([Plate(3, "St 07", "Vogel + 0.1 mg/mL Basta + 500 µg/mL Hyg + a long note", "A")])
    assert render_table(long, "St 07", {}, days=[0], title="t").width > short.width
