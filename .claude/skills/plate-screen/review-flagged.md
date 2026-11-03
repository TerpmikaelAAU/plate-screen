You are reviewing traced Colony outlines on photos of fungal plates (Petri dishes, seen from above, logo "SARSTEDT" at the bottom). Change no files; zoomed crops go in a scratch folder.

Each tile on the sheet is one Plate on one Day, labelled "pN DN" (Plate N, Day N) followed by why it was flagged. The left image is the plain Crop; the right one has the candidate Outlines drawn on it: A green, B magenta, C cyan. "A=B" means A and B are the same within 0.5 mm, drawn once. The line at the top gives each candidate's Diameter in mm ("-" means that candidate found nothing).

What counts as the Colony:
- All the mycelium growing out from the middle, including the white or pale-yellow fluffy margin at its edge. The margin counts even when it is thin and faint.
- Not a pigment halo: colour that has diffused into the agar beyond the mycelium (smooth, no fluffy texture).
- Not a Satellite: a separate small colony elsewhere on the plate. Count Satellites instead.
- Not the dish wall, reflections, condensation, the logo or numbers written on the lid.

How the candidates usually go wrong:
- A and B often stop at the inner, darker zone and leave out the pale margin. That is wrong.
- C often follows the margin well, but on late Days it can run out to the limit near the wall; a Diameter of about 77 mm is that limit, not a measurement.
- A sometimes cuts a chord across the Colony on one side.

For each tile, choose:
- A, B or C: that Outline follows the Colony's edge all the way round, within about 1-2 mm. If two fit, pick the closer one. Be strict: an Outline that cuts across the margin or runs into the agar along any stretch longer than about a tenth of the way round is wrong, even if the rest is perfect.
- empty: there is no Colony, only the inoculum spot at most (a small pale disc, about 10-18 mm, already there on Day 0).
- none: no candidate follows the edge (each misses the margin, cuts across, or runs into the agar).

Faint tiles (flag "faint"): a pale disc that may be a thin Colony or just the inoculum spot. Leave the choice blank and say in the note which you think it is and why.

Zoom in on every tile before you decide (crop and enlarge it with Python/PIL into a scratch folder); the sheet at full size is too small to judge a 1-2 mm margin.

Answer with one line per tile, every tile on the sheet, in the order shown, and nothing else:
pN DN | choice | satellites | note
where satellites is a whole number (0 if none) and note is a few words (why, especially for none; may be blank).
