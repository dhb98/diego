from __future__ import annotations

from .constants import FAV, DOG, CHART_BODIES
from .engine import AnalysisResult
from .status_engine import body_status_is_cyclic


def _cyclic_bodies(result: AnalysisResult) -> list[str]:
    found = []
    for b in CHART_BODIES:
        if body_status_is_cyclic(result.chart, b):
            found.append(b)
    return found


def render(result: AnalysisResult) -> str:
    chart = result.chart
    lines = []
    lines.append("=" * 72)
    lines.append("STELLAR WHEELHOUSE ANALYSIS")
    lines.append("=" * 72)
    lines.append(chart.title)
    for m in chart.meta_lines:
        if m.startswith(("Date:", "Time:", "Location:")):
            lines.append(m)
    lines.append("")
    lines.append(f"Favorite planets: {', '.join(sorted(chart.favorite_planets))}")
    lines.append(f"Underdog planets: {', '.join(sorted(chart.underdog_planets))}")
    lines.append("")

    cyclic = _cyclic_bodies(result)
    if cyclic:
        lines.append("-" * 72)
        lines.append("UNRESOLVED DISPOSITOR LOOP DETECTED")
        lines.append("-" * 72)
        lines.append(
            "The following bodies sit in a chain of dispositors that never reaches "
            "a planet standing in its own sign -- a scenario the book never "
            "addresses. Every factor touching them is marked [LOW-CONF] below and "
            "excluded from the scored verdict:"
        )
        lines.append("  " + ", ".join(cyclic))
        lines.append("")

    scored = [f for f in result.factors if not f.low_confidence]
    low_conf = [f for f in result.factors if f.low_confidence]

    lines.append("-" * 72)
    lines.append(f"SCORED FACTORS ({len(scored)})")
    lines.append("-" * 72)
    if not scored:
        lines.append("(none -- see low-confidence factors below, or this chart is genuinely quiet)")
    for f in scored:
        timing = f" @ {f.timing_pct:.0f}% through the game" if f.timing_pct is not None else ""
        lines.append(f"[{f.team:>3}] w={f.weight:<5.2f} {f.category:<16} {f.description}{timing}")
        if f.note:
            lines.append(f"        note: {f.note}")

    if low_conf:
        lines.append("")
        lines.append("-" * 72)
        lines.append(f"LOW-CONFIDENCE / EXCLUDED FACTORS ({len(low_conf)})")
        lines.append("-" * 72)
        for f in low_conf:
            lines.append(f"[{f.team:>3}] w={f.weight:<5.2f} {f.category:<16} {f.description}")

    if result.unscored_notes:
        lines.append("")
        lines.append("-" * 72)
        lines.append("FLAGGED BUT NOT SCORED")
        lines.append("-" * 72)
        for n in result.unscored_notes:
            lines.append(f"- {n}")

    v = result.verdict
    lines.append("")
    lines.append("=" * 72)
    lines.append("VERDICT")
    lines.append("=" * 72)
    lines.append(f"Favorite score: {v.fav_score:.2f}  ({v.fav_count} factors)")
    lines.append(f"Underdog score: {v.dog_score:.2f}  ({v.dog_count} factors)")
    if v.excluded_low_confidence:
        lines.append(f"Excluded (low-confidence): {v.excluded_low_confidence} factors")
    lines.append(f"Lean: {v.lean}")
    lines.append(f"Read: {v.confidence}")
    lines.append("")
    lines.append(
        "Reminder: weights are this engine's own numeric translation of the "
        "book's qualitative importance language, not values the book states. "
        "Treat this as a structured first pass, not a final answer -- the book "
        "itself calls this ~80% technique, ~20% feel."
    )
    return "\n".join(lines)
