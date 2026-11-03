---
name: plate-screen
description: Turn a folder of daily plate Photos from an antibiotic screening Round (each Plate shot beside a numbered Sticky note) into Tables of cropped plates per Strain. Also measures Colony Diameters and Growth rates. Use when the user has a new Round to sort, label, crop or tabulate, a Key photo to transcribe, or Colonies to measure.
---

# Plate screen

`plate-screen <step> <round-folder>` does the fixed work; you do the reading. Vocabulary (Round, Plate, Key, Label, Crop, Table, Day) is defined in the repo's `CONTEXT.md`. If `plate-screen` is not on PATH, run it as `uv run --project ~/Desktop/Claude/plate-screen plate-screen`.

Work the steps in order. Each ends on its completion criterion; meet it before moving on.

## 1. Key

Skip if the Round folder already has `key.csv`.

Find the photo of the handwritten Key (the user will point at it). Read it and draft `key.csv` with columns `plate,strain,condition,replicate`:

- `strain` as written on the Key, e.g. `St 06`.
- `condition` in full with units: `Vogel`, `Vogel + 0.1 mg/mL Basta`, `Vogel + 200 µg/mL Hyg`.
- `replicate` lettered A, B, … in Plate order within each Strain and Condition.

Show the draft to the user as a table, flagging every reading you are unsure of. **Done when** the user has confirmed or corrected every row and `key.csv` holds the confirmed version.

## 2. Sort

Run `sort --dry-run`, show the user the count per Day, then `sort`. Day 0 is the earliest Photo's local date; pass `--start YYYY-MM-DD` before the step if the user says inoculation was another day. **Done when** a second `sort` reports 0 Photos moved.

## 3. Label

Run `label`. It proposes Plate numbers from shooting order and draws `Review/notes_Day_N.jpg`, one tile per Photo with `#n status: plate` printed above it.

Read every sheet. For each tile, compare the handwritten Sticky note to the printed proposal and edit `labels.csv`:

- Sticky note matches: set `status` to `ok`.
- Sticky note shows another number: set `plate` to it and `status` to `ok`. A missed or extra Photo shifts every proposal after it, so read on carefully past any mismatch.
- No readable Sticky note: clear `plate`, set `status` to `unlabelled`.
- Second Photo of a Plate already seen that Day: set `status` to `duplicate` on the one to leave out.

Never edit a row the user has changed. **Done when** `labels.csv` has no `proposed` rows and every row with status `ok` holds the number on its Sticky note.

## 4. Check

Run `check`. Resolve each problem by re-reading the sheet for that Photo. A gap the Photos genuinely have (Plate not photographed that Day) stays a gap; tell the user. **Done when** `check` reports no problems, or every one left is a real gap reported to the user.

## 5. Crop and table

Run `run`. Look at `Review/crops.jpg`: each row is one Plate across Days, so a wrong Label shows as a dish that jumps, and a bad Crop shows as a dish cut off or off-centre.

- A Photo listed as "no dish found", or a bad Crop: open the Photo, estimate the dish centre and radius in Photo pixels, add `photo,x,y,r` to `crop_overrides.csv`, rerun `run`.
- A dish that jumps: go back to step 3 for that Photo.
- A Photo listed as "no logo found": its Crop keeps the angle it was shot at. Tell the user.

**Done when** `crops.jpg` shows every Plate continuous across Days, and the `Tables/<Strain>.jpg` files are written. Give the user the printed `![[…]]` embed lines and list every `unlabelled` Photo and every gap.

## 6. Measure

Only when the user asks for Colony Diameters or Growth rates. Run `measure`. It writes `Measurements/` and draws every Crop's Outlines into `Review/`: `outlines_<Strain>.jpg` (a Table with Outlines), `flagged_NN.jpg` (Crops waiting for review: plain beside the candidates A, B, C) and `decided_NN.jpg` (Crops the code settled).

Review with subagents, a few sheets each, giving them the brief by path:

- every `flagged_NN.jpg` to a Sonnet subagent with [review-flagged.md](review-flagged.md);
- every `decided_NN.jpg` to a Haiku subagent with [review-decided.md](review-decided.md).

Before fanning out on a new kind of Plate, run one Sonnet subagent on one sheet and compare its answers with your own reading; tighten the brief where it disagrees. Map each answer's `pN DN` to its Photo through `Measurements/diameters.csv` and draft `measure_overrides.csv` (`photo,outline,satellites,note`; `outline` is A, B, C, `empty`, `none`, or blank to give only satellites or a note). After a rerun with more Days, the candidates of a reviewed Crop can change; `measure` stops and names the Photo only if the chosen one vanished, so look over the reviewed Crops on the new sheets. For a decided Crop that Haiku calls wrong, open it yourself and pick the right candidate or `none`.

Show the user the draft with the sheets it refers to, and write it only once they agree. Rerun `measure`: overrides change the shrink and replicate checks of the neighbouring Days, so review only the newly flagged Crops once more, then stop. **Done when** every flagged Crop has a reviewed choice or is reported to the user, and the user has the plots in `Measurements/`.
