"""Normal/Reverse status calculation (Part II: "Arrangement and Order",
p.35-51, plus the anaretic-degree and Via Combusta refinements from
Part III, p.77-79).

Core rule, stated precisely on p.42-43:
    - A planet standing in the sign IT rules is NORMAL (own sign).
    - A planet standing in its DETRIMENT (the sign opposite the one it
      rules) is REVERSE in a single hop -- UNLESS that sign's ruler (the
      planet's dispositor) is itself standing in its own ruling sign, in
      which case the exception saves it back to NORMAL. Either way, this
      does NOT recurse any further up the chain (confirmed by the p.39-40
      Venus/Mars worked example, which stops at Mars's sign placement
      without chasing Mars's own dispositor).
    - A planet standing in a NEUTRAL sign (neither its own nor its
      detriment) takes on the FULL status of that sign's ruler,
      recursively (the Mars-in-Gemini -> Mercury -> Sun chain example,
      p.38, and confirmed by practice examples 1/2/4/5/7 on p.43) --
      EXCEPT when that dispositor is itself standing in the first
      planet's own sign (mutual reception), in which case both are
      treated as NORMAL. This exception is not in the excerpt; it's
      standard traditional-astrology practice (see the p.5 credit to
      John Frawley) added here because Eris/Ceres each rule exactly one
      sign, which makes a permanent two-planet reception loop physically
      possible (e.g. Mars transiting Taurus while Eris sits in Aries,
      which it does for decades at a stretch) in a way the old two-
      sign-per-planet rulership table never allowed.

    A dispositor's own Rx/29th-degree state does NOT propagate down the
    chain -- only its sign placement does (p.48-49); Rx/29th-degree are
    applied only to the specific planet whose status is being resolved,
    as the very last step.

    Rx present            -> flips status once.
    At 29 degrees of sign -> flips status once, UNLESS the planet is
                              standing in the sign it itself rules (p.79).
    Via Combusta (Moon/POF/aPOF only, 14 Lib-14 Sco) -> flips status once.
    Within 1 degree of Spica (Moon or POF only) -> forces NORMAL.

Combining two or more statuses (Moon-Planet aspects, Moon-POF-Sun trio,
etc.) follows the "distributive property" from p.45-46: normal=+1,
reverse=-1, multiply.

Note on p.43 practice example 3 ("Sun in Libra... normally reverse"):
that example contradicts the book's own explicit rule above (Libra is
not the Sun's detriment -- Aquarius, opposite Leo, is; Libra is opposite
Aries, the Sun's traditional *exaltation*, i.e. its classical "fall",
which the book never names or defines as a status trigger). Examples 4,
5 and 7 all match the stated rule exactly, so this implementation
follows the rule as written and treats example 3 as an inconsistency in
the source text rather than a fourth, unstated case.
"""
from __future__ import annotations

from .constants import (
    SIGN_RULER, PLANET_RULES, NORMAL, REVERSE, ANARETIC_DEGREE,
    VIA_COMBUSTA_START, VIA_COMBUSTA_END, SPICA_LONGITUDE, SPICA_ORB,
    opposite_sign,
)
from .chart_parser import Chart, _sign_and_deg


def flip(status: str) -> str:
    return REVERSE if status == NORMAL else NORMAL


def combine(*statuses: str) -> str:
    sign = 1
    for s in statuses:
        sign *= -1 if s == REVERSE else 1
    return NORMAL if sign > 0 else REVERSE


def _dispositor_in_own_sign(chart: Chart, dispositor: str) -> bool:
    disp_lon = chart.lon(dispositor)
    if disp_lon is None:
        return False
    disp_sign, _ = _sign_and_deg(disp_lon)
    return PLANET_RULES.get(dispositor) == disp_sign


def _status_for_placement(chart: Chart, planet: str, sign: str, _visited: frozenset[str] = frozenset()) -> tuple[str, bool]:
    """Own/detriment/neutral status for `planet`'s identity (its
    rulership/detriment) AS IF standing in `sign`. For a real planet,
    `sign` is just its actual current sign; for an antiscia point,
    `planet` is the BASE planet's identity but `sign` is the antiscia
    POINT's own sign (p.76: "Use the regular planet[']s ... status to
    determine the antiscia planet's status ... If the antiscia planet is
    in its own sign, it is normal there"). Returns (status, cyclic).
    """
    if planet in _visited or planet not in PLANET_RULES:
        return NORMAL, planet in _visited
    ruled_sign = PLANET_RULES[planet]

    if sign == ruled_sign:
        return NORMAL, False  # own sign

    dispositor = SIGN_RULER[sign]
    if sign == opposite_sign(ruled_sign):
        # Detriment: one-hop exception check only, no further recursion.
        if _dispositor_in_own_sign(chart, dispositor):
            return NORMAL, False
        return REVERSE, False

    # Neutral sign: take on the dispositor's full status at its actual position.
    disp_lon = chart.lon(dispositor)
    if disp_lon is None:
        return NORMAL, False
    disp_sign, _ = _sign_and_deg(disp_lon)

    # Mutual reception (not stated in the excerpt, but standard practice
    # in the traditional astrology this method is built on -- see p.5's
    # credit to John Frawley): if the dispositor is itself standing in
    # THIS planet's own sign, each is "visiting the other's house" and
    # both are treated as home/NORMAL. Without this, a single-ruler body
    # like Eris (fixed in Aries for decades) and Mars (which transits
    # Taurus, Eris's sign, every ~2 years) can lock into a permanent
    # two-planet loop that never existed when Venus/Mercury ruled Taurus/
    # Virgo with two signs each to fall back on.
    if disp_sign == ruled_sign:
        return NORMAL, False

    return _status_for_placement(chart, dispositor, disp_sign, _visited | {planet})


def _planet_chain_status(chart: Chart, planet: str) -> tuple[str, bool]:
    """Full own/detriment/neutral dispositor status for one of the 12
    ruling bodies at its actual position (p.42-43)."""
    lon = chart.lon(planet)
    if lon is None:
        return NORMAL, False
    sign, _ = _sign_and_deg(lon)
    return _status_for_placement(chart, planet, sign)


def _pof_sign_status(chart: Chart, sign: str) -> tuple[str, bool]:
    """POF/aPOF-in-sign status (p.55-57): a mathematical point rules
    nothing and has no detriment, so it always simply takes on the full
    status of that sign's ruler -- equivalent to always hitting the
    "neutral" branch of _status_for_placement."""
    ruler = SIGN_RULER[sign]
    ruler_lon = chart.lon(ruler)
    if ruler_lon is None:
        return NORMAL, False
    ruler_sign, _ = _sign_and_deg(ruler_lon)
    return _status_for_placement(chart, ruler, ruler_sign)


def is_via_combusta(longitude: float) -> bool:
    return VIA_COMBUSTA_START <= longitude <= VIA_COMBUSTA_END


def is_near_spica(longitude: float) -> bool:
    diff = min((longitude - SPICA_LONGITUDE) % 360, (SPICA_LONGITUDE - longitude) % 360)
    return diff <= SPICA_ORB


def body_status_detail(chart: Chart, name: str) -> tuple[str, bool]:
    """Like body_status(), but also reports whether the dispositor chain
    hit an unresolved loop (see _status_for_placement)."""
    pos = chart.positions.get(name)
    if pos is None:
        return NORMAL, False

    # Antiscia points are read via the base planet's identity, standing
    # at the ANTISCIA point's own sign ("that is a reverse sign for Mars;
    # therefore aMars is reverse", p.76), and inherit the base planet's
    # own retrograde motion (this software's chart export never tags
    # antiscia lines with Rx directly).
    is_antiscia = name.startswith("a") and name != "aPOF"
    base_name = name[1:] if is_antiscia else name
    retrograde = chart.is_rx(base_name) if is_antiscia else pos.retrograde

    base, cyclic = _status_for_placement(chart, base_name, pos.sign)

    is_own_sign = PLANET_RULES.get(base_name) == pos.sign
    if pos.deg_in_sign >= ANARETIC_DEGREE and not is_own_sign:
        base = flip(base)

    if retrograde:
        base = flip(base)

    return base, cyclic


def body_status(chart: Chart, name: str) -> str:
    """Full Normal/Reverse status of a chart body (planet or antiscia
    point), including its own Rx and 29th-degree flags."""
    return body_status_detail(chart, name)[0]


def body_status_is_cyclic(chart: Chart, name: str) -> bool:
    return body_status_detail(chart, name)[1]


def pof_final_status_detail(chart: Chart, antiscia: bool = False) -> tuple[str, bool]:
    """Like pof_final_status(), but also reports whether the Sun, Moon,
    or (a)POF-in-sign chain hit an unresolved dispositor loop."""
    key = "aPOF" if antiscia else "POF"
    pos = chart.positions.get(key)
    if pos is None:
        return NORMAL, False

    sun_status, sun_cyclic = body_status_detail(chart, "Sun")
    moon_status, moon_cyclic = body_status_detail(chart, "Moon")

    in_sign_status, in_sign_cyclic = _pof_sign_status(chart, pos.sign)
    cyclic = sun_cyclic or moon_cyclic or in_sign_cyclic
    # POF never rules a sign, so the 29th-degree own-sign exception never applies.
    if pos.deg_in_sign >= ANARETIC_DEGREE:
        in_sign_status = flip(in_sign_status)

    statuses = [sun_status, moon_status, in_sign_status]

    if is_via_combusta(pos.longitude):
        # Exception (p.79): skip the flip if the POF's immediate
        # dispositor is itself standing in its own ruling sign (a
        # "very happy" dispositor) -- the clearest reading of the
        # text's stated exception.
        immediate_ruler = SIGN_RULER[pos.sign]
        ruler_lon = chart.lon(immediate_ruler)
        dispositor_very_happy = False
        if ruler_lon is not None:
            ruler_sign, _ = _sign_and_deg(ruler_lon)
            dispositor_very_happy = SIGN_RULER[ruler_sign] == immediate_ruler
        skip_flip = dispositor_very_happy or (not antiscia and is_near_spica(pos.longitude))
        if not skip_flip:
            statuses.append(REVERSE)

    return combine(*statuses), cyclic


def pof_final_status(chart: Chart, antiscia: bool = False) -> str:
    """The 3-part (or 4-part, with Via Combusta) POF/aPOF Final status
    described on p.55-57 and p.78."""
    return pof_final_status_detail(chart, antiscia)[0]


def pof_final_status_is_cyclic(chart: Chart, antiscia: bool = False) -> bool:
    return pof_final_status_detail(chart, antiscia)[1]
