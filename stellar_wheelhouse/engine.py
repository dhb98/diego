from __future__ import annotations

from dataclasses import dataclass

from .chart_parser import parse_chart, Chart
from .scoring import collect_all_factors, summarize, Verdict
from .factor import Factor


@dataclass
class AnalysisResult:
    chart: Chart
    factors: list[Factor]
    verdict: Verdict
    unscored_notes: list[str]


UNSCORED_HINTS = (
    ("Capulus-Algol Alert", "Fixed-star alert flagged by your software; the uploaded book excerpt "
                            "never reaches its Capulus/Algol rule text (only Spica is defined, p.79). Not scored."),
    ("Degree Alert", "Anaretic (29th-degree) flag on the Nodes. Node status itself is explicitly "
                      "ignorable per the book (p.69); shown for awareness only, not scored."),
)


def _unscored_notes(chart: Chart) -> list[str]:
    notes = []
    for line in chart.meta_lines:
        for prefix, explanation in UNSCORED_HINTS:
            if line.startswith(prefix):
                notes.append(f"{line} -- {explanation}")

    from .aspects import unruled_pof_casts
    for cast in unruled_pof_casts(chart):
        notes.append(
            f"{cast} -- the excerpt states planet-to-POF rules only for Mars, "
            "Uranus and Neptune (p.83-84); no rule for this planet survives in "
            "the uploaded pages, so it is left unscored rather than guessed."
        )
    return notes


def analyze(text: str) -> AnalysisResult:
    chart = parse_chart(text)
    factors = collect_all_factors(chart)
    verdict = summarize(factors)
    notes = _unscored_notes(chart)
    return AnalysisResult(chart=chart, factors=factors, verdict=verdict, unscored_notes=notes)
