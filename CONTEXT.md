# Plate Screen

Turns daily phone photos of an antibiotic screening into a Table of cropped plates per Strain, so growth can be compared across Conditions and Days.

## Language

### The experiment

**Round**:
One screening experiment: a fixed set of Plates inoculated on the same day and photographed once a day afterwards. Its Photos live in one folder in the notebook.
_Avoid_: Screen, batch, run

**Strain**:
The organism being screened, written `St 06`, `St 07`.
_Avoid_: Sample, isolate

**Condition**:
The medium a Plate is poured with: Vogel alone, or Vogel plus one antibiotic at one concentration (e.g. Vogel + 200 µg/mL Hyg).
_Avoid_: Treatment, media

**Plate**:
One physical dish in a Round, inoculated with one Strain on one Condition.
_Avoid_: Dish, sample

**Plate number**:
The number that identifies a Plate within a Round, written on the Sticky note in every Photo of it.
_Avoid_: ID, index

**Replicate**:
One of the Plates sharing the same Strain and Condition in a Round, lettered A, B, …
_Avoid_: Copy, duplicate

**Key**:
The mapping from each Plate number in a Round to its Strain, Condition and Replicate.
_Avoid_: Legend, plate map, layout

**Day**:
The number of calendar days since inoculation; Day 0 is the date of the Round's earliest Photo, in local time.
_Avoid_: Timepoint

### The pictures

**Photo**:
One phone picture of a single Plate next to its Sticky note.
_Avoid_: Image, picture

**Sticky note**:
The paper note beside the Plate in a Photo, carrying its handwritten Plate number.
_Avoid_: Tag

**Label**:
The Plate number read from a Photo's Sticky note, recorded so a person can check and correct it.
_Avoid_: Classification, tag

**Unlabelled photo**:
A Photo with no readable Sticky note; left out of the Table until someone labels it.

**Duplicate photo**:
A second Photo of the same Plate on the same Day; left out of the Table until someone picks one.

**Crop**:
The part of a Photo showing just the Plate, turned so the logo moulded into the dish sits at the bottom, where one is found.

**Table**:
The composite image for one Strain: one row per Condition and Replicate, one column per Day, each cell a Crop.
_Avoid_: Matrix, composite, grid

### Growth

**Colony**:
The mycelium growing out from the inoculation point of a Plate. A pigment halo in the agar around it is not part of the Colony.
_Avoid_: Growth, spot

**Satellite**:
A separate small colony on a Plate, away from the Colony; counted, not measured.

**Outline**:
The traced edge of the Colony in one Crop. Each Crop gets three candidate Outlines, A (traced from the last Day back, reluctant to grow past the next Day's), B (traced on its own Day only) and C (as A, but only where the agar outside is unchanged), and review chooses one, or none.

**Diameter**:
The diameter of the circle with the same area as the Colony's Outline, in mm. Measured from Day 1; Day 0 shows only the inoculum.
_Avoid_: Size, width

**Growth rate**:
How fast the Diameter of one Plate increases, in mm per Day, over the same early Days for every Plate of a Round (up to Day 4, and only before it reaches the rim or 80% of the dish; Days before the Colony first shows count at the size it first shows at), timed by when each Photo was taken.
