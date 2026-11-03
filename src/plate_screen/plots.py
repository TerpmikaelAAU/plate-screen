"""Plots of Diameters and Growth rates: one figure per Strain, and one comparing every Strain with its Vogel control."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from .growth import CONTROL, Growth, Reading, Summary  # noqa: E402

# Categorical slots in fixed order; a Condition keeps its colour in every figure of a Round
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SURFACE, INK, INK_2, RULE = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"


def colours(conditions: list[str]) -> dict[str, str]:
    """Vogel first, then the rest in Key order; past eight, Conditions share the last slot."""
    order = sorted(dict.fromkeys(conditions), key=lambda c: c != CONTROL)
    return {c: SERIES[min(i, len(SERIES) - 1)] for i, c in enumerate(order)}


def short(condition: str) -> str:
    return condition.removeprefix(f"{CONTROL} + ") or condition


def _style(ax) -> None:
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(RULE)
    ax.tick_params(colors=INK_2, labelsize=9, length=0)
    ax.grid(axis="y", color=RULE, linewidth=0.8)
    ax.set_axisbelow(True)


def _wrap(label: str) -> str:
    """The last word on a line of its own, so neighbouring tick labels don't run into each other."""
    head, _, tail = label.rpartition(" ")
    return f"{head}\n{tail}" if head else label


def _label_ends(ax, ends: list) -> None:
    """Label each line where it stops, nudging labels that would overlap apart."""
    gap = 0.06 * (ax.get_ylim()[1] - ax.get_ylim()[0])
    ends.sort(key=lambda e: e[1])
    for i, end in enumerate(ends):
        for below in ends[:i]:  # a label reaches about two Days to the right of where it starts
            if abs(end[0] - below[0]) <= 2 and end[1] - below[1] < gap:
                end[1] = below[1] + gap
    for x, y, text in ends:
        ax.annotate(text, (x, y), xytext=(6, 0), textcoords="offset points", va="center", fontsize=9, color=INK)


def strain_figure(strain: str, readings: list[Reading], growth: list[Growth], summary: list[Summary], colour: dict) -> plt.Figure:
    """Left: each Plate's Diameter by Day (thin) and the mean per Condition (thick) on Days with every Replicate. Right: each Plate's Growth rate
    by Condition, the mean as a bar across, and the mean as a percentage of Vogel."""
    fig, (left, right) = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [3, 2]}, facecolor=SURFACE)
    conditions = list(dict.fromkeys(r.cell.plate.condition for r in readings if r.cell.plate.strain == strain))
    ends = []  # where each mean line stops, for its label

    for condition in conditions:
        mine = [r for r in readings if r.cell.plate.strain == strain and r.cell.plate.condition == condition]
        by_plate: dict[int, list[Reading]] = {}
        for r in mine:
            if r.diameter is not None:
                by_plate.setdefault(r.cell.plate.number, []).append(r)
        for rs in by_plate.values():
            rs.sort(key=lambda r: r.cell.day)
            left.plot([r.cell.day for r in rs], [r.diameter for r in rs], color=colour[condition], linewidth=1, alpha=0.35)
        # The mean only on Days every Replicate has a Diameter, so a missing one doesn't make it jump
        plates = {r.cell.plate.number for r in mine}
        on = {}
        for rs in by_plate.values():
            for r in rs:
                on.setdefault(r.cell.day, []).append(r.diameter)
        days = sorted(d for d, ds in on.items() if len(ds) == len(plates))
        means = [sum(on[d]) / len(on[d]) for d in days]
        if days:
            left.plot(days, means, color=colour[condition], linewidth=2, marker="o", markersize=5)
            ends.append([days[-1], means[-1], short(condition)])
    _style(left)
    left.set_xlabel("Day", color=INK_2)
    left.set_ylabel("Diameter (mm)", color=INK_2)
    left.set_ylim(bottom=0)
    _label_ends(left, ends)
    left.xaxis.get_major_locator().set_params(integer=True)
    left.margins(x=0.15)

    rates = {s.condition: s for s in summary if s.strain == strain}
    for i, condition in enumerate(conditions):
        values = [g.rate for g in growth if g.plate.strain == strain and g.plate.condition == condition and g.rate is not None]
        right.scatter([i] * len(values), values, s=36, color=colour[condition], edgecolor=SURFACE, linewidth=1.5, zorder=3)
        s = rates.get(condition)
        if s is not None and s.rate is not None:
            right.hlines(s.rate, i - 0.25, i + 0.25, color=INK, linewidth=2, zorder=2)
            if s.percent_of_vogel is not None and condition != CONTROL:
                right.annotate(f"{s.percent_of_vogel:.0f}%", (i + 0.25, s.rate), xytext=(4, 0), textcoords="offset points",
                               va="center", fontsize=9, color=INK)
    _style(right)
    right.set_xticks(range(len(conditions)), [_wrap(short(c)) for c in conditions], fontsize=9)
    right.set_xlim(-0.6, len(conditions) - 0.4)
    right.set_ylabel("Growth rate (mm/Day)", color=INK_2)
    right.set_ylim(bottom=min([0] + [g.rate for g in growth if g.plate.strain == strain and g.rate is not None]))

    fig.suptitle(strain, x=0.06, ha="left", fontsize=13, color=INK)
    # Every Condition in the legend, also one with no Day where all its Replicates have a Diameter
    handles = [Line2D([], [], color=colour[c], linewidth=2, marker="o", markersize=5) for c in conditions]
    if handles:
        fig.legend(handles, conditions, loc="upper right", ncol=len(handles), frameon=False, fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    return fig


def summary_figure(title: str, summary: list[Summary], colour: dict) -> plt.Figure:
    """Each Strain's Growth rate per Condition as a percentage of its Vogel control: a dot per Condition."""
    strains = list(dict.fromkeys(s.strain for s in summary if s.percent_of_vogel is not None))
    fig, ax = plt.subplots(figsize=(8, 0.45 * len(strains) + 1.6), facecolor=SURFACE)
    seen = set()
    for y, strain in enumerate(strains):
        for s in summary:
            if s.strain == strain and s.condition != CONTROL and s.percent_of_vogel is not None:
                ax.scatter(s.percent_of_vogel, y, s=60, color=colour[s.condition], edgecolor=SURFACE, linewidth=2, zorder=3,
                           label=None if s.condition in seen else s.condition)
                seen.add(s.condition)
    _style(ax)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=RULE, linewidth=0.8)
    ax.axvline(100, color=INK_2, linewidth=1)
    ax.annotate(CONTROL, (100, len(strains) - 0.4), xytext=(4, 0), textcoords="offset points", fontsize=9, color=INK_2)
    ax.set_yticks(range(len(strains)), strains, fontsize=9)
    ax.set_ylim(len(strains) - 0.3, -0.7)
    ax.set_xlim(left=min([0] + [s.percent_of_vogel for s in summary if s.percent_of_vogel is not None]))
    ax.set_xlabel("Growth rate, % of the same Strain on Vogel", color=INK_2)
    if seen:
        ax.legend(loc="lower left", bbox_to_anchor=(0, 1.02), ncol=len(seen), frameon=False, fontsize=9)
    ax.set_title(title, loc="left", fontsize=13, color=INK, pad=28)
    fig.tight_layout()
    return fig


def save(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
