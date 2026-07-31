from __future__ import annotations

import re
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


# Alerts the chart software emits as *asterisked* flags. Anything matched
# here is explained; anything unrecognised is still surfaced verbatim by
# _unscored_notes below, so a flag never disappears just because this
# engine has no rule for it.
ASTERISK_ALERTS = {
    "Can in 7th house": (
        "Cancer falls inside the 7th house. The book's rule is specifically about "
        "Cancer being ON the 7th cusp, which would make the Moon L7 and flip the "
        "Moon-to-angle reading toward the dog (p.19). Here the Moon is not L7, so "
        "the rule does not fire -- flagged in case your template means something "
        "broader by it."
    ),
    "Moon 25-29 degrees": (
        "Late-degree Moon flag from your software. The excerpt only defines a rule "
        "for exactly 29 degrees (p.77), not a 25-29 band, so nothing is scored for "
        "it; any such rule would be in the truncated pages 85-193."
    ),
}


def _unscored_notes(chart: Chart) -> list[str]:
    notes = []
    seen = set()
    for line in chart.meta_lines:
        for prefix, explanation in UNSCORED_HINTS:
            if line.startswith(prefix):
                notes.append(f"{line} -- {explanation}")

        # Standalone asterisked flag lines, e.g.
        # "*Can in 7th house**Moon 25-29 degrees*". Lines that merely
        # CONTAIN asterisked planet names (the "... Midpoint Alert: *Jup*
        # 0deg40'" rows) are their own labelled category and are skipped
        # here so individual planet names don't leak in as pseudo-flags.
        if not line.startswith("*"):
            continue
        for flag in re.findall(r"\*([^*]+)\*", line):
            flag = flag.strip()
            if not flag or flag in seen:
                continue
            seen.add(flag)
            explanation = ASTERISK_ALERTS.get(
                flag,
                "Flag from your chart software with no matching rule in the uploaded "
                "book excerpt; surfaced here rather than dropped, but not scored.",
            )
            notes.append(f"{flag} -- {explanation}")

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
