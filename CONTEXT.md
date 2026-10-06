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
The part of a Photo showing just the Plate.

**Table**:
The composite image for one Strain: one row per Condition and Replicate, one column per Day, each cell a Crop.
_Avoid_: Matrix, composite, grid
