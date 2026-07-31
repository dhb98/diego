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
    factors += aspects.outer_planet_angle_conjunctions(chart)
    factors += aspects.asc_mc_midpoint_factors(chart)
    factors += aspects.apof_angle_aspects(chart)
    factors += aspects.planet_pof_aspects(chart)
    factors += aspects.apof_planet_conjunctions(chart)
    factors += aspects.node_aspects(chart)

    factors.sort(key=lambda f: f.weight, reverse=True)
    return factors


@dataclass
class KeyLordRead:
    """The chart read using ONLY factors that involve Lord 1 or Lord 7 --
    the favourite's and the underdog's main planets.

    Restricted to MOON aspects, because that is the context in which the
    book states the ranking: "the Lord that is being aspected by the Moon
    does matter. It is a fact that generally speaking, a Moon aspect to
    L1 or L10 is stronger than an aspect to L2, L6, with L5 being the
    weakest" (p.25), alongside "L1 and L7 ... are the most important"
    (p.17). When neither main planet takes a Moon aspect, this read stays
    silent rather than manufacturing a verdict out of the Lords the book
    itself calls weakest.

    STATUS: UNVALIDATED. Over the fifteen test charts: 7/9 correct with
    six no-calls (78%, p=0.090) -- not significant, and one of roughly
    fifteen variants tried during development, so the apparent edge is
    within what chance produces. Widening it to every factor touching
    L1/L7 drops it to 7/12 (58%), which shows how fragile the number is.
    Do not treat this as a proven edge; it is a pre-registered hypothesis
    awaiting an out-of-sample test on 30-50 unseen charts.
    """
    lean: str                 # FAV, DOG, "silent" (no key-lord aspect) or "tied"
    fav_score: float
    dog_score: float
    factors: list[Factor]

    @property
    def is_silent(self) -> bool:
        """No call. Either main planet never took a Moon aspect, or both
        did and they cancel exactly -- very different situations that
        must not be reported with the same sentence."""
        return self.lean in ("silent", "tied")


def key_lord_read(factors: list[Factor]) -> KeyLordRead:
    kf = [f for f in factors
          if f.is_key_lord and not f.low_confidence and f.category == "Moon-Planet"]
    fav = sum(f.weight for f in kf if f.team == FAV)
    dog = sum(f.weight for f in kf if f.team == DOG)
    if not kf:
        return KeyLordRead("silent", fav, dog, kf)
    if abs(fav - dog) < 1e-9:
        return KeyLordRead("tied", fav, dog, kf)
    return KeyLordRead(FAV if fav > dog else DOG, fav, dog, kf)


@dataclass
class Verdict:
    fav_score: float
    dog_score: float
    fav_count: int
    dog_count: int
    lean: str
    confidence: str
    excluded_low_confidence: int
    clearness: float = 0.0   # 0-10, how one-sided AND well-evidenced the chart is
    suggestion: str = ""     # what the book's own betting discipline implies


def _clearness(fav: float, dog: float, n_factors: int, excluded: int) -> float:
    """A 0-10 reading of how decisively the chart speaks.

    Combines how lopsided the tally is with how much evidence produced
    it -- the book wants BOTH ("lots of marbles heavy on one side of the
    scale with only a light smattering on the other", p.22, and it warns
    that one tiny Moon aspect is not enough to back a big underdog).
    A one-sided split resting on a single factor is not a clear chart.

    NOTE: this measures clarity of the SIGNAL, not likelihood of winning.
    On the ten charts run so far the two have not correlated.
    """
    total = fav + dog
    if total == 0 or n_factors == 0:
        return 0.0
    ratio = abs(fav - dog) / total                 # 0 = tied, 1 = one-sided
    margin = min(abs(fav - dog) / 6.0, 1.0)        # absolute gap, saturating at 6 pts
    evidence = min(n_factors / 8.0, 1.0)           # saturates at 8 scored factors
    score = 10.0 * (0.5 * ratio + 0.3 * margin + 0.2 * evidence)
    if excluded:                                    # unresolved factors dilute confidence
        score *= max(0.5, 1.0 - 0.1 * excluded)
    return round(score, 1)


def _suggestion(lean: str, clearness: float) -> str:
    if lean == "no lean" or clearness < 3.0:
        return "PASS"
    if clearness < 5.0:
        return f"pass / watch only ({lean} lean, too thin)"
    if clearness < 7.0:
        return f"small stake on {lean}"
    return f"strongest available: {lean}"


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

    clearness = _clearness(fav_score, dog_score, fav_count + dog_count, excluded)
    return Verdict(
        fav_score, dog_score, fav_count, dog_count, lean, confidence, excluded,
        clearness=clearness,
        suggestion=_suggestion(lean, clearness),
    )
