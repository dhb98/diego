"""Parser for the plain-text chart export format used by the user's
astrology software (Solar Fire-style "sports chart" report).

Design choice: rather than trying to re-parse the software's own
pre-rendered aspect lines (their line-wrapping/labels are inconsistent),
we pull out the raw longitude/right-ascension numbers the report already
prints for every point, and let stellar_wheelhouse compute every aspect
itself from those numbers. That's the only reliable way to reproduce the
book's rules exactly. The pre-rendered "Planet Aspects" / "Moon to
Planets" / "Planets to Angles" blocks are kept only as free-text context
for the report, never as scoring input.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


SIGN_ABBR = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir",
             "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"]

# Abbreviation -> canonical body name, as used in the "Planet Positions"
# and "Right Ascension" blocks.
ABBR_TO_NAME = {
    "Moon": "Moon", "Sun": "Sun", "Merc": "Mercury", "Ven": "Venus",
    "Mars": "Mars", "Jup": "Jupiter", "Sat": "Saturn", "Ura": "Uranus",
    "Nep": "Neptune", "Plu": "Pluto", "Eris": "Eris", "Ceres": "Ceres",
    "NN": "NorthNode", "POF": "POF",
}

FULL_NAME_ALIASES = {
    "Jupiter": "Jupiter", "Ceres": "Ceres", "Saturn": "Saturn", "Eris": "Eris",
    "Mars": "Mars", "Mercury": "Mercury", "Neptune": "Neptune", "Moon": "Moon",
    "Pluto": "Pluto", "Venus": "Venus", "Sun": "Sun", "Uranus": "Uranus",
}


def _canonical_name(token: str) -> str | None:
    """Map a position-block token (possibly antiscia-prefixed) to a
    canonical body name, e.g. 'aSat' -> 'aSaturn', 'Merc' -> 'Mercury'."""
    antiscia = token.startswith("a") and token != "aPOF" and token not in ABBR_TO_NAME
    # aPOF is its own explicit token; other antiscia tokens are 'a' + abbr.
    if token == "aPOF":
        return "aPOF"
    if token in ABBR_TO_NAME:
        return ABBR_TO_NAME[token]
    if token.startswith("a") and token[1:] in ABBR_TO_NAME:
        return "a" + ABBR_TO_NAME[token[1:]]
    return None


@dataclass
class BodyPosition:
    name: str
    longitude: float          # absolute ecliptic longitude, 0-360
    retrograde: bool = False
    stationary: bool = False
    sign: str = ""
    deg_in_sign: float = 0.0


@dataclass
class HouseCusp:
    number: int
    longitude: float
    ruler: str


@dataclass
class Chart:
    title: str = ""
    meta_lines: list[str] = field(default_factory=list)
    favorite_planets: set[str] = field(default_factory=set)
    underdog_planets: set[str] = field(default_factory=set)
    positions: dict[str, BodyPosition] = field(default_factory=dict)
    houses: dict[int, HouseCusp] = field(default_factory=dict)
    ra: dict[str, float] = field(default_factory=dict)
    extra_angles: dict[str, float] = field(default_factory=dict)
    raw_text: str = ""

    def lon(self, name: str) -> float | None:
        p = self.positions.get(name)
        return p.longitude if p else None

    def is_rx(self, name: str) -> bool:
        p = self.positions.get(name)
        return bool(p and p.retrograde)

    @property
    def asc(self) -> float:
        return self.houses[1].longitude

    @property
    def dsc(self) -> float:
        return (self.houses[1].longitude + 180.0) % 360.0

    @property
    def mc(self) -> float:
        return self.houses[10].longitude

    @property
    def ic(self) -> float:
        return (self.houses[10].longitude + 180.0) % 360.0

    def lord_numbers(self, planet: str) -> list[int]:
        return sorted(h for h, c in self.houses.items() if c.ruler == planet and h not in (3, 9))

    def team_of(self, planet: str) -> str | None:
        base = planet[1:] if planet.startswith("a") and planet != "aPOF" else planet
        if base in self.favorite_planets:
            return "FAV"
        if base in self.underdog_planets:
            return "DOG"
        return None


_POS_LINE = re.compile(
    r"^(?P<name>a?[A-Za-z]+)(?P<rx> Rx)?(?P<st> S)?\s*:\s*"
    r"(?P<d>\d{1,2})[°º]\s*(?P<m>\d{1,2})['’′]\s*"
    r"(?P<sign>[A-Za-z]{3})?\s*\((?P<abs>-?[\d.]+)\)"
)

_HOUSE_LINE = re.compile(
    r"^House\s+(?P<num>\d{1,2})\s*:\s*(?P<d>\d{1,2})[°º]\s*(?P<m>\d{1,2})['’′]\s*"
    r"(?P<sign>[A-Za-z]{3})?\s*\((?P<abs>-?[\d.]+)\)\s*,\s*(?P<ruler>[A-Za-z]+)"
)

_RA_LINE = re.compile(
    r"^RA of (?P<name>[A-Za-z ]+?)\s*:\s*(?P<d>\d{1,3})[°º]\s*(?P<m>\d{1,2})['’′]"
)

_ANGLE_LINE = re.compile(
    r"\b(?P<label>ASC|MC|AX|VX|DSC|IC)\s*:\s*(?P<d>\d{1,2})[°º]\s*(?P<m>\d{1,2})['’′]\s*(?P<sign>[A-Za-z]{3})"
)


def _sign_and_deg(abs_lon: float) -> tuple[str, float]:
    from .constants import SIGNS
    idx = int(abs_lon // 30) % 12
    return SIGNS[idx], abs_lon - idx * 30.0


def parse_chart(text: str) -> Chart:
    chart = Chart(raw_text=text)
    lines = [ln.strip() for ln in text.splitlines()]

    # Title = first non-empty line.
    for ln in lines:
        if ln:
            chart.title = ln
            break

    for ln in lines:
        if not ln:
            continue

        m = re.match(r"^Favorite\s*=\s*(.+)$", ln, re.IGNORECASE)
        if m:
            chart.favorite_planets = {p.strip() for p in m.group(1).split(",") if p.strip()}
            continue
        m = re.match(r"^Underdog\s*=\s*(.+)$", ln, re.IGNORECASE)
        if m:
            chart.underdog_planets = {p.strip() for p in m.group(1).split(",") if p.strip()}
            continue

        m = _HOUSE_LINE.match(ln)
        if m:
            num = int(m.group("num"))
            chart.houses[num] = HouseCusp(number=num, longitude=float(m.group("abs")), ruler=m.group("ruler"))
            continue

        m = _RA_LINE.match(ln)
        if m:
            raw_name = m.group("name").strip()
            tokens = raw_name.split()
            base_token = tokens[0]
            canon = _canonical_name(base_token) or base_token
            deg = int(m.group("d")) + int(m.group("m")) / 60.0
            chart.ra[canon] = deg
            continue

        m = _POS_LINE.match(ln)
        if m:
            raw_name = m.group("name")
            canon = _canonical_name(raw_name)
            if canon is None:
                continue
            abs_lon = float(m.group("abs")) % 360.0
            sign, deg_in_sign = _sign_and_deg(abs_lon)
            chart.positions[canon] = BodyPosition(
                name=canon,
                longitude=abs_lon,
                retrograde=bool(m.group("rx")),
                stationary=bool(m.group("st")),
                sign=sign,
                deg_in_sign=deg_in_sign,
            )
            continue

        chart.meta_lines.append(ln)

    _parse_extra_angles(chart, text)

    return chart


def _parse_extra_angles(chart: Chart, text: str) -> None:
    for m in _ANGLE_LINE.finditer(text):
        label = m.group("label")
        if label in ("ASC", "MC", "DSC", "IC"):
            continue  # derived from house cusps instead, which carry exact decimals
        sign = m.group("sign")
        try:
            idx = SIGN_ABBR.index(sign)
        except ValueError:
            continue
        deg = int(m.group("d")) + int(m.group("m")) / 60.0
        chart.extra_angles[label] = idx * 30.0 + deg
