from __future__ import annotations

from dataclasses import dataclass

from .constants import FAV, DOG
from .factor import Factor
from .chart_parser import Chart
from . import aspects


def collect_all_factors(chart: Chart) -> list[Factor]:
    factors: list[Factor] = []
    factors += aspects.moon_body_aspects(chart)
    factors += aspects.moon_pof_aspects(chart)

    node_sq = aspects.moon_node_square(chart)
    if node_sq:
        factors.append(node_sq)

    angle = aspects.moon_angle_aspect(chart)
    if angle:
        factors.append(angle)

    factors += aspects.planet_cusp_aspects(chart)
    factors += aspects.planet_axis_aspects(chart)
    factors += aspects.neptune_angle_aspects(chart)
    factors += aspects.apof_angle_aspects(chart)
    factors += aspects.planet_pof_aspects(chart)
    factors += aspects.node_aspects(chart)

    factors.sort(key=lambda f: f.weight, reverse=True)
    return factors


@dataclass
class Verdict:
    fav_score: float
    dog_score: float
    fav_count: int
    dog_count: int
    lean: str
    confidence: str
    excluded_low_confidence: int


def summarize(factors: list[Factor]) -> Verdict:
    # Factors whose status depends on an unresolved dispositor loop (see
    # aspects._cycle_note) are not a book rule's output -- they're this
    # engine's coin flip. Keep them visible in the report but don't let
    # them silently sway the tallied verdict.
    scored = [f for f in factors if not f.low_confidence]
    excluded = len(factors) - len(scored)

    fav_score = sum(f.weight for f in scored if f.team == FAV)
    dog_score = sum(f.weight for f in scored if f.team == DOG)
    fav_count = sum(1 for f in scored if f.team == FAV)
    dog_count = sum(1 for f in scored if f.team == DOG)

    diff = fav_score - dog_score
    total = fav_score + dog_score
    if total == 0:
        lean, confidence = "no lean", "no factors found -- pass"
    else:
        ratio = abs(diff) / total
        lean = FAV if diff > 0 else DOG if diff < 0 else "no lean"
        if abs(diff) < 1.0:
            confidence = "razor-thin margin -- book says pass on games like this"
        elif ratio < 0.25:
            confidence = "mild lean -- book wants a clearer pile before betting"
        elif ratio < 0.55:
            confidence = "solid lean"
        else:
            confidence = "lopsided -- the kind of setup the book calls a strong bet"

        # A lopsided *score* built from almost no scoreable factors is not
        # the same as a chart stacked with evidence -- say so, otherwise
        # "1 factor found, 7 excluded" reads identically to a chart with
        # 12 clean factors pointing the same way.
        scored_count = fav_count + dog_count
        if excluded and scored_count and excluded >= 2 * scored_count:
            confidence += (
                f"; but thin evidence -- only {scored_count} of {scored_count + excluded} "
                "factors resolved cleanly, the rest sit in an unresolved dispositor loop"
            )

    return Verdict(fav_score, dog_score, fav_count, dog_count, lean, confidence, excluded)
