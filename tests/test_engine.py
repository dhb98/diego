import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stellar_wheelhouse.chart_parser import parse_chart, Chart, BodyPosition, HouseCusp
from stellar_wheelhouse.status_engine import (
    combine, flip, body_status, body_status_is_cyclic, is_via_combusta, is_near_spica,
)
from stellar_wheelhouse.constants import NORMAL, REVERSE
from stellar_wheelhouse.engine import analyze

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "example_chart.txt")


def _chart_with(**signs_and_flags) -> Chart:
    """Build a minimal Chart for dispositor-chain unit tests. Each kwarg
    is planet_name=(longitude, retrograde)."""
    chart = Chart()
    for name, (lon, rx) in signs_and_flags.items():
        from stellar_wheelhouse.chart_parser import _sign_and_deg
        sign, deg = _sign_and_deg(lon)
        chart.positions[name] = BodyPosition(name=name, longitude=lon, retrograde=rx, sign=sign, deg_in_sign=deg)
    return chart


def test_combine_distributive_property():
    assert combine(NORMAL, NORMAL) == NORMAL
    assert combine(NORMAL, REVERSE) == REVERSE
    assert combine(REVERSE, REVERSE) == NORMAL
    assert combine(NORMAL, NORMAL, REVERSE) == REVERSE
    assert combine(REVERSE, REVERSE, REVERSE) == REVERSE
    assert flip(NORMAL) == REVERSE
    assert flip(REVERSE) == NORMAL


def test_dispositor_chain_normal_example_p38():
    # Mars in Gemini -> Mercury in Leo -> Sun in Leo (own sign) = all normal.
    chart = _chart_with(
        Mars=(65.0, False),     # 5 Gemini
        Mercury=(125.0, False), # 5 Leo
        Sun=(128.0, False),     # 8 Leo
    )
    assert body_status(chart, "Sun") == NORMAL
    assert body_status(chart, "Mercury") == NORMAL
    assert body_status(chart, "Mars") == NORMAL


def test_dispositor_detriment_examples_p43():
    # Practice example 5 (p.43): Moon at 0 Aries, Mars in 25 Libra (Mars's
    # detriment -- opposite its own sign Aries), Venus in Leo (not Libra,
    # so the exception doesn't save Mars), Sun in Sagittarius.
    # "Mars is in bad shape in his worst sign. The Moon is REVERSE."
    chart = _chart_with(
        Moon=(0.0, False),      # 0 Aries
        Mars=(205.0, False),    # 25 Libra = Mars's detriment
        Venus=(125.0, False),   # 5 Leo -- Venus rules Libra but isn't standing in it
        Sun=(250.0, False),     # 10 Sagittarius
    )
    assert body_status(chart, "Mars") == REVERSE
    assert body_status(chart, "Moon") == REVERSE

    # Practice example 7 (p.43): Moon in 09 Capricorn (Moon's detriment,
    # opposite Cancer), Saturn in Capricorn (its own sign) saves it.
    # "This is Saturn's best sign and 'saves' the Moon. Moon here is NORMAL."
    chart2 = _chart_with(
        Moon=(279.0, False),    # 9 Capricorn
        Saturn=(280.0, False),  # 10 Capricorn -- Saturn's own sign
    )
    assert body_status(chart2, "Moon") == NORMAL


def test_rx_and_29th_degree_flip():
    # Neptune in Pisces (own sign) but Rx -> reverse (p.44-45).
    chart = _chart_with(Neptune=(340.0, True))  # 10 Pisces, Rx
    assert body_status(chart, "Neptune") == REVERSE

    # A planet at 29 degrees of a sign it doesn't rule gets an extra flip.
    chart2 = _chart_with(
        Mars=(65.0, False),
        Mercury=(125.0, False),
        Sun=(128.0, False),
        Jupiter=(29.5, False),  # 29.5 Aries, ruled by Mars (normal) -> would be normal, but 29th degree flips it
    )
    assert body_status(chart2, "Jupiter") == REVERSE

    # Exception (p.79): a planet at 29 degrees of the sign IT rules stays normal.
    chart3 = _chart_with(Neptune=(359.9, False))  # 29.9 Pisces, own sign
    assert body_status(chart3, "Neptune") == NORMAL


def test_via_combusta_and_spica_range():
    assert is_via_combusta(200.0) is True   # 20 Libra
    assert is_via_combusta(190.0) is False  # 10 Libra, outside 14-14 range
    assert is_near_spica(204.18) is True
    assert is_near_spica(210.0) is False


def test_fixture_dispositor_chains_all_resolve():
    # With the corrected own/detriment/neutral algorithm, every chain in
    # the example chart terminates -- Moon's detriment placement in
    # Capricorn (p.43 example 7's mirror image: Saturn is NOT in Capricorn
    # here, so the exception does not save it) short-circuits what would
    # otherwise have looped Mars-Mercury-Moon-Saturn forever.
    with open(FIXTURE) as f:
        chart = parse_chart(f.read())
    from stellar_wheelhouse.constants import CHART_BODIES
    for b in CHART_BODIES:
        assert body_status_is_cyclic(chart, b) is False, b


def test_synthetic_neutral_dispositor_loop_is_detected():
    # A genuine 3-way neutral loop with nobody in their own sign or
    # detriment (Mercury-in-Scorpio -> Pluto-in-Aquarius -> Uranus-in-
    # Gemini -> Mercury-in-Scorpio...) is a scenario the book never
    # addresses; the engine must flag it rather than silently guess.
    chart = _chart_with(
        Mercury=(215.0, False),  # 5 Scorpio
        Pluto=(305.0, False),    # 5 Aquarius
        Uranus=(65.0, False),    # 5 Gemini
    )
    assert body_status_is_cyclic(chart, "Mercury") is True
    assert body_status_is_cyclic(chart, "Pluto") is True
    assert body_status_is_cyclic(chart, "Uranus") is True


def test_fixture_parses_key_positions():
    with open(FIXTURE) as f:
        chart = parse_chart(f.read())
    assert chart.favorite_planets == {"Jupiter", "Ceres", "Saturn", "Eris", "Mars"}
    assert chart.underdog_planets == {"Mercury", "Neptune", "Moon", "Pluto", "Venus"}
    assert round(chart.asc, 2) == 262.07
    assert round(chart.mc, 2) == 161.98
    assert round(chart.dsc, 2) == 82.07
    assert round(chart.ic, 2) == 341.98
    assert round(chart.lon("POF"), 2) == 61.86
    assert chart.houses[7].ruler == "Mercury"
    assert chart.lord_numbers("Jupiter") == [1]
    assert chart.lord_numbers("Saturn") == [2]


def test_dual_rulership_resolves_to_strongest_lord():
    # Pisces on both the 6th and 7th cusps makes Neptune L6 (fav, nearly
    # the weakest fav Lord) and L7 (dog, the dog's strongest). The dog
    # must win that tie-break; naively trusting the report's
    # "Favorite = ...Neptune..." line gets it backwards.
    chart = parse_chart(
        "Favorite = Ceres, Mercury, Venus, Neptune, Uranus\n"
        "Underdog = Neptune, Jupiter, Mars, Ceres, Sun\n"
        "House 1: 27°52' Vir  (177.87), Ceres\n"
        "House 6: 0°34' Pis  (330.56), Neptune\n"
        "House 7: 27°52' Pis  (357.87), Neptune\n"
        "House 12: 0°34' Vir  (150.56), Ceres\n"
    )
    assert chart.lord_numbers("Neptune") == [6, 7]
    assert chart.deciding_lord("Neptune") == 7
    assert chart.team_of("Neptune") == "DOG"
    assert chart.team_of("aNeptune") == "DOG"

    # Ceres is L1 (fav, strongest) and L12 (dog, weak) -> favorite.
    assert chart.lord_numbers("Ceres") == [1, 12]
    assert chart.deciding_lord("Ceres") == 1
    assert chart.team_of("Ceres") == "FAV"


def test_analyze_fixture_end_to_end():
    with open(FIXTURE) as f:
        result = analyze(f.read())
    assert len(result.factors) > 0
    assert not any(f.low_confidence for f in result.factors)  # no dispositor loop in this chart
    assert result.verdict.fav_score > 0
    assert result.verdict.dog_score > 0
    assert result.verdict.lean in ("FAV", "DOG")
    assert len(result.unscored_notes) == 2  # Capulus-Algol + Degree Alert, flagged but not scored


if __name__ == "__main__":
    import traceback
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
