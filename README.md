# plate-screen

Turns daily phone photos of an antibiotic screening into one image per strain: a table with a row per plate (condition × replicate) and a column per day, each cell the dish cropped onto black.

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
  Day_0/ … Day_7/    the photos, moved here by `sort`
  Review/            notes_Day_N.jpg sheets for checking labels, crops.jpg for checking crops
  Tables/            St06.jpg, St07.jpg
```

## Steps

```bash
plate-screen sort --dry-run ROUND   # see where photos would go
plate-screen sort ROUND             # move photos into Day_N/ by EXIF date (Day 0 = earliest; --start to override)
plate-screen label ROUND            # propose plate numbers from shooting order, draw review sheets
plate-screen check ROUND            # missing, doubled, unknown or out-of-order plates
plate-screen run ROUND              # check, crop, table
```

Label statuses: `proposed` (not yet checked), `ok`, `unlabelled` (no readable note), `duplicate` (extra photo of a plate that day). Only `proposed` and `ok` photos reach the tables. Re-running `label` never changes an existing row.

In Claude Code, ask for the plate screen on a Round folder and the `plate-screen` skill walks through the same steps, reading the sticky notes for you.

## Develop

```bash
uv run pytest
```

Tests draw their own synthetic photos; no real photos live in this repo.
