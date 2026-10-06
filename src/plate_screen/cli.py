"""plate-screen <step> <round-folder>"""

import argparse
import sys
from datetime import date
from pathlib import Path

from . import pipeline
from .round import Round


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="plate-screen", description="Turn daily Photos of a screening Round into Tables.")
    parser.add_argument("--start", type=date.fromisoformat, help="Day 0 (YYYY-MM-DD), if not the earliest Photo's date")
    steps = parser.add_subparsers(dest="step", required=True)
    for name, help in [
        ("sort", "move Photos into Day_N/ folders by the date they were taken"),
        ("label", "propose Plate numbers in labels.csv and draw Review/notes_Day_N.jpg sheets"),
        ("check", "report missing, doubled or out-of-order Labels"),
        ("crop", "cut each dish out onto black and draw Review/crops.jpg"),
        ("table", "write Tables/<Strain>.jpg"),
        ("run", "check, crop and table in one go"),
    ]:
        step = steps.add_parser(name, help=help)
        step.add_argument("round", type=Path, help="the Round folder")
        if name == "sort":
            step.add_argument("--dry-run", action="store_true", help="print the moves without making them")
    args = parser.parse_args(argv)
    round = Round(args.round, start=args.start)

    if args.step == "sort":
        moves = pipeline.sort(round, dry_run=args.dry_run)
        for m in moves:
            print(f"{'would move' if args.dry_run else 'moved'} {m.src.relative_to(round.folder)} -> {m.dest.relative_to(round.folder)}")
        print(f"{len(moves)} Photos {'to move' if args.dry_run else 'moved'}")
        return 0
    if args.step == "label":
        labels = pipeline.label(round)
        proposed = sum(r.status == "proposed" for r in labels.rows)
        print(f"{len(labels.rows)} Photos in {labels.path.name}, {proposed} still proposed; sheets in {pipeline.REVIEW}/")
        return 0

    problems = pipeline.check(round)
    for p in problems:
        print(f"! {p}")
    if args.step == "check":
        print("no problems" if not problems else f"{len(problems)} problems")
        return 1 if problems else 0
    failed = pipeline.crop(round)
    for f in failed:
        print(f"! no dish found in {f}; add it to {pipeline.OVERRIDES_FILE} (photo,x,y,r)")
    print(f"look over the Crops in {round.folder / pipeline.REVIEW / 'crops.jpg'}")
    if args.step == "crop":
        return 1 if failed else 0
    for path in pipeline.table(round):
        print(f"wrote {path}\n  {pipeline.embed(path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
