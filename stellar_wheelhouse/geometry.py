"""Small angle-arithmetic helpers shared by aspects.py."""
from __future__ import annotations

from .constants import ASPECT_ANGLES, MOON_TRAVEL_ORB


def norm360(x: float) -> float:
    return x % 360.0


def forward_delta(frm: float, to: float) -> float:
    """Degrees you must move forward (increasing longitude) from `frm`
    to reach `to`, in [0, 360)."""
    return (to - frm) % 360.0


def applying_delta(body_lon: float, target_lon: float, retrograde: bool) -> float:
    """How far `body_lon` is from *approaching* `target_lon`, respecting
    direction of motion (p.47: an Rx planet applies "backward"). Smaller
    is closer to exact; the caller compares against an orb."""
    if retrograde:
        return forward_delta(target_lon, body_lon)
    return forward_delta(body_lon, target_lon)


def aspect_points(target_lon: float, angle: float) -> list[float]:
    if angle == 0:
        return [norm360(target_lon)]
    if angle == 180:
        return [norm360(target_lon + 180)]
    return [norm360(target_lon + angle), norm360(target_lon - angle)]


def best_moon_travel_aspect(moon_lon: float, target_lon: float, max_orb: float):
    """Search all 5 major aspects for the nearest one the (always-direct)
    Moon will make to `target_lon` within the next `max_orb` degrees of
    forward travel. Returns (aspect_name, forward_degrees) or None."""
    best = None
    for aspect_name, angle in ASPECT_ANGLES.items():
        for pt in aspect_points(target_lon, angle):
            fwd = forward_delta(moon_lon, pt)
            if fwd <= max_orb and (best is None or fwd < best[1]):
                best = (aspect_name, fwd)
    return best


def in_game_timing(forward_degrees: float, window: float = MOON_TRAVEL_ORB) -> float:
    """In-game timing ("IT") of a Moon factor, as a percentage of the game.

    The book treats the Moon's 5-degree travel window as spanning the whole
    game (p.16-17), so an aspect that perfects after `forward_degrees` of
    forward travel lands `forward_degrees / window` of the way through it:
    0.0 means exact at the opening whistle, 100.0 at the very end. Rounded
    to one decimal, matching how the report prints it.
    """
    return round(forward_degrees / window * 100.0, 1)


def is_applying_within(body_lon: float, target_lon: float, retrograde: bool, orb: float) -> float | None:
    """Returns the applying orb if `body_lon` is applying to `target_lon`
    within `orb` degrees (conjunction only), else None."""
    d = applying_delta(body_lon, target_lon, retrograde)
    return d if d <= orb else None


def axis_relationship(body_lon: float, retrograde: bool, p1: float, orb: float) -> tuple[str, float] | None:
    """Classify `body_lon`'s applying relationship to the two-point axis
    anchored at `p1` (and p1+180): 'conjunct_p1', 'conjunct_p2', 'square',
    or 'trine' (book's shorthand for sextile-or-trine to an axis, p.24).
    Returns (kind, orb) for the closest applying match, else None.
    """
    p2 = norm360(p1 + 180)
    candidates = [
        ("conjunct_p1", p1),
        ("conjunct_p2", p2),
        ("square", norm360(p1 + 90)),
        ("square", norm360(p1 - 90)),
        ("trine", norm360(p1 + 60)),
        ("trine", norm360(p1 - 60)),
        ("trine", norm360(p1 + 120)),
        ("trine", norm360(p1 - 120)),
    ]
    best = None
    for kind, pt in candidates:
        d = applying_delta(body_lon, pt, retrograde)
        if d <= orb and (best is None or d < best[1]):
            best = (kind, d)
    return best
