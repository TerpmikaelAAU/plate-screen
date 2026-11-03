# plate-screen

Turns daily phone photos of an antibiotic screening into one image per strain: a table with a row per plate (condition × replicate) and a column per day, each cell the dish cropped onto black and turned so the logo moulded into the dish sits at the bottom.

Each plate is photographed every day beside a sticky note with its plate number; a key maps plate numbers to strain, condition and replicate. The fixed work (sorting by date, finding the dish, drawing tables) is code. Reading handwriting is done by Claude Code through the bundled skill, with every reading written to a CSV a person can check.

Vocabulary is in [CONTEXT.md](CONTEXT.md).

## Install

```bash
uv tool install -e .
ln -s "$PWD/.claude/skills/plate-screen" ~/.claude/skills/plate-screen
```

## A Round folder

```
ST_06_ST_07/
  key.csv            plate,strain,condition,replicate   (you write this, or Claude drafts it from the key photo)
  labels.csv         photo,day,plate,status             (proposed by `label`, checked by Claude, corrected by you)
  crop_overrides.csv photo,x,y,r                        (optional: dish centre and radius when detection fails)
  measure_overrides.csv photo,outline,satellites,note   (review's choice of Outline per photo: A, B, C, empty, none, or blank for a note only)
  Day_0/ … Day_7/    the photos, moved here by `sort`
  Review/            notes_Day_N.jpg sheets for checking labels, crops.jpg for checking crops
  Tables/            St06.jpg, St07.jpg
  Measurements/      diameters.csv, growth.csv, summary.csv, a plot per strain and summary.png (from `measure`)
```

## Steps

```bash
plate-screen sort --dry-run ROUND   # see where photos would go
plate-screen sort ROUND             # move photos into Day_N/ by EXIF date (Day 0 = earliest; --start to override)
plate-screen label ROUND            # propose plate numbers from shooting order, draw review sheets
plate-screen check ROUND            # missing, doubled, unknown or out-of-order plates
plate-screen run ROUND              # check, crop, table
plate-screen measure ROUND          # colony diameters per photo, growth rates, plots; outlines drawn into Review/
```

`measure` traces three candidate outlines per photo and only fills in a diameter where they agree and nothing looks off; the rest are flagged for review (see the skill). Millimetres assume the dish rim is 92 mm across (`DISH_MM` in `measure.py`). Growth rates are fitted on Days 1–4 (`FIT_DAYS` in `growth.py`) against the time each photo was taken, so every plate of a Round is compared over the same time.

Label statuses: `proposed` (not yet checked), `ok`, `unlabelled` (no readable note), `duplicate` (extra photo of a plate that day). Only `proposed` and `ok` photos reach the tables. Re-running `label` never changes an existing row.

In Claude Code, ask for the plate screen on a Round folder and the `plate-screen` skill walks through the same steps, reading the sticky notes for you.

## Develop

```bash
uv run pytest
```

Tests draw their own synthetic photos; no real photos live in this repo.
