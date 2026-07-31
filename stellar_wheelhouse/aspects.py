"""Every scoreable relationship in a Stellar Wheelhouse chart, translated
into Factor objects. Section references are to the uploaded excerpt.

IMPORTANT - what's an exact book rule vs. an engineering judgment call:
The book gives no numeric weights anywhere; it only ranks importance in
words ("L1 and L7 ... most important", "a strong factor that pulls a lot
of weight", "occasionally the goods are located there"). The `weight`
values below are this engine's own translation of that language into
numbers so factors can be tallied and ranked -- treat them as a
reasonable ordering, not something the book itself states. Anywhere this
module extrapolates beyond a rule the excerpt states outright (e.g.
applying the Rx-motion convention to axis/cusp checks, or the specific
"unless L#" bookkeeping for Mars/Saturn/Uranus/Pluto), it's flagged in a
comment.
"""
from __future__ import annotations

from .constants import (
    FAV, DOG, NORMAL, CHART_BODIES, LORD_WEIGHT, FAV_HOUSES,
    MOON_TRAVEL_ORB, ANGLE_ORB, CUSP_ORB, NODE_ORB,
)
from .factor import Factor, opposite
from .chart_parser import Chart
from .status_engine import (
    body_status, body_status_is_cyclic, pof_final_status, pof_final_status_is_cyclic, combine,
)
from .geometry import best_moon_travel_aspect, applying_delta, axis_relationship, forward_delta


def _cycle_note(chart: Chart, *names: str) -> str:
    flagged = [n for n in names if body_status_is_cyclic(chart, n)]
    if not flagged:
        return ""
    return (
        f"Dispositor chain for {', '.join(flagged)} loops back on itself without any "
        "planet landing in its own sign -- the book never covers this case. Status "
        "defaulted to NORMAL by this engine, not by a stated rule; treat as low-confidence."
    )


def _is_cyclic(chart: Chart, *names: str) -> bool:
    return any(body_status_is_cyclic(chart, n) for n in names)


def _lord_weight_for(chart: Chart, base_name: str) -> float:
    lords = chart.lord_numbers(base_name)
    if not lords:
        return 1.0
    return max(LORD_WEIGHT[n] for n in lords)


def _flip_if_reverse(team: str, status: str) -> str:
    return team if status == NORMAL else opposite(team)


# ---------------------------------------------------------------------
# Moon -> planet/antiscia aspects (p.16-27: the core "gift-giving" rule)
# ---------------------------------------------------------------------

def moon_body_aspects(chart: Chart) -> list[Factor]:
    factors = []
    moon_lon = chart.lon("Moon")
    if moon_lon is None:
        return factors
    moon_status = body_status(chart, "Moon")

    targets = [b for b in CHART_BODIES if b != "Moon"] + [
        "a" + b for b in CHART_BODIES if b != "Moon"
    ]
    for target in targets:
        target_lon = chart.lon(target)
        if target_lon is None:
            continue
        base_name = target[1:] if target.startswith("a") else target
        team = chart.team_of(base_name)
        if team is None:
            continue  # not one of the 10 team-assigned bodies (shouldn't happen for CHART_BODIES)

        hit = best_moon_travel_aspect(moon_lon, target_lon, MOON_TRAVEL_ORB)
        if not hit:
            continue
        aspect_name, fwd = hit

        target_status = body_status(chart, target)
        combined = combine(moon_status, target_status)
        effect_team = team if combined == NORMAL else opposite(team)

        weight = _lord_weight_for(chart, base_name)
        lords = chart.lord_numbers(base_name)
        lord_txt = "/".join(f"L{n}" for n in lords) if lords else "?"
        if len(lords) > 1:
            lord_txt += f", decided by L{chart.deciding_lord(base_name)}"

        factors.append(Factor(
            category="Moon-Planet",
            description=(
                f"Moon {aspect_name} {target} ({lord_txt}, {team}) "
                f"[{moon_status.lower()} Moon x {target_status.lower()} {target} = {combined.lower()}]"
            ),
            team=effect_team,
            weight=weight,
            note=_cycle_note(chart, "Moon", target),
            low_confidence=_is_cyclic(chart, "Moon", target),
            timing_pct=round(fwd / MOON_TRAVEL_ORB * 100, 1),
        ))
    return factors


# ---------------------------------------------------------------------
# Moon -> POF / aPOF (p.30-33, refined p.53-58)
# ---------------------------------------------------------------------

def moon_pof_aspects(chart: Chart) -> list[Factor]:
    factors = []
    moon_lon = chart.lon("Moon")
    moon_status = body_status(chart, "Moon")
    if moon_lon is None:
        return factors

    for key, antiscia, label in (("POF", False, "POF"), ("aPOF", True, "aPOF")):
        target_lon = chart.lon(key)
        if target_lon is None:
            continue
        hit = best_moon_travel_aspect(moon_lon, target_lon, MOON_TRAVEL_ORB)
        if not hit:
            continue
        aspect_name, fwd = hit
        pof_status = pof_final_status(chart, antiscia=antiscia)
        combined = combine(moon_status, pof_status)

        # Baseline (p.32): conj/sextile/trine -> fav, square/opposite -> dog.
        baseline = FAV if aspect_name in ("Conjunction", "Sextile", "Trine") else DOG
        effect_team = baseline if combined == NORMAL else opposite(baseline)

        cyclic = _is_cyclic(chart, "Moon") or pof_final_status_is_cyclic(chart, antiscia=antiscia)
        factors.append(Factor(
            category="Moon-POF",
            description=(
                f"Moon {aspect_name} {label} "
                f"[{moon_status.lower()} Moon x {pof_status.lower()} {label} Final = {combined.lower()}]"
            ),
            team=effect_team,
            weight=2.75 if antiscia else 2.5,
            timing_pct=round(fwd / MOON_TRAVEL_ORB * 100, 1),
            note=_cycle_note(chart, "Moon") if cyclic else "",
            low_confidence=cyclic,
        ))
    return factors


# ---------------------------------------------------------------------
# Moon -> Nodes, square only (p.68-69); Moon -> angle (p.19-25)
# ---------------------------------------------------------------------

def moon_node_square(chart: Chart) -> Factor | None:
    moon_lon = chart.lon("Moon")
    nn_lon = chart.lon("NorthNode")
    if moon_lon is None or nn_lon is None:
        return None
    hit = best_moon_travel_aspect(moon_lon, nn_lon, MOON_TRAVEL_ORB)
    if not hit or hit[0] != "Square":
        return None
    moon_status = body_status(chart, "Moon")
    # "Moon normal square Nodes = hurts favorite" (p.69) -> a DOG-leaning
    # factor when normal, flipped to FAV when the Moon is reverse.
    effect_team = DOG if moon_status == NORMAL else FAV
    return Factor(
        category="Moon-Node",
        description=f"Moon square Node axis [{moon_status.lower()} Moon]",
        team=effect_team,
        weight=1.0,
        timing_pct=round(hit[1] / MOON_TRAVEL_ORB * 100, 1),
        note=_cycle_note(chart, "Moon"),
        low_confidence=_is_cyclic(chart, "Moon"),
    )


def moon_angle_aspect(chart: Chart) -> Factor | None:
    """Moon within 2 deg applying to an angle: a whole-game theme
    favoring the favorite, unless the Moon itself is Lord 7 (p.19, p.24-25).

    NOT just conjunctions -- "Not only does a normal Moon benefit a team
    when applying to conjunct an angle within 2 degrees, any normal Moon
    aspect to the ASC, DSC, MC or IC will bring beneficial effect to the
    favorite every time as well... Seeing if the Moon is within 2 degrees
    conjunct or in other major aspect with an angle axis is always among
    the first things to review" (p.19). The book's own example is a Moon
    squaring the Asc-Dsc axis. Judged statically from the chart's start
    (p.20), and the Moon is never retrograde.
    """
    moon_lon = chart.lon("Moon")
    if moon_lon is None:
        return None
    moon_status = body_status(chart, "Moon")

    best = None
    for axis_name, p1 in (("Asc-Dsc", chart.asc), ("Mc-Ic", chart.mc)):
        rel = axis_relationship(moon_lon, False, p1, ANGLE_ORB)
        if rel and (best is None or rel[1] < best[2]):
            best = (axis_name, rel[0], rel[1])
    if not best:
        return None

    axis_name, kind, orb = best
    label = {
        "conjunct_p1": f"conjunct {'ASC' if axis_name == 'Asc-Dsc' else 'MC'}",
        "conjunct_p2": f"conjunct {'DSC' if axis_name == 'Asc-Dsc' else 'IC'}",
        "square": f"square {axis_name}",
        "trine": f"sextile/trine {axis_name}",
    }[kind]
    baseline = DOG if 7 in chart.lord_numbers("Moon") else FAV
    effect_team = _flip_if_reverse(baseline, moon_status)
    cyclic = _is_cyclic(chart, "Moon")
    note = "Whole-game theme, not tied to a specific scoring moment."
    if cyclic:
        note = _cycle_note(chart, "Moon") + " " + note
    return Factor(
        category="Moon-Angle",
        description=f"Moon {label} within {orb:.2f} deg [{moon_status.lower()} Moon]",
        team=effect_team,
        weight=2.0,
        note=note,
        low_confidence=cyclic,
    )


# ---------------------------------------------------------------------
# Planet/antiscia -> house cusp proximity (p.26-29), incl. aPOF -> angle
# special case (p.77) and POF -> angle ignored (p.33, p.57).
# ---------------------------------------------------------------------



def planet_cusp_aspects(chart: Chart) -> list[Factor]:
    factors = []
    # The Moon itself is excluded: its angle behaviour is the dedicated
    # whole-game Moon-Angle rule above, and the book never demonstrates a
    # Moon-on-minor-cusp case. Its ANTISCIA (aMoon) has no such special
    # rule and is an ordinary point -- antiscia "operate exactly like we
    # already learned from planets ... for antiscia planets to be near
    # angles, and for antiscia planets to cast aspects" (p.75) -- so it
    # stays in.
    bodies = [b for b in CHART_BODIES if b != "Moon"] + [
        "a" + b for b in CHART_BODIES
    ]
    for body in bodies:
        lon = chart.lon(body)
        if lon is None:
            continue
        base_name = body[1:] if body.startswith("a") else body
        body_team = chart.team_of(base_name)
        if body_team is None:
            continue
        status = body_status(chart, body)

        for house_num, cusp in chart.houses.items():
            if house_num in (3, 9):
                continue
            if base_name == "Neptune" and house_num in (1, 4, 7, 10):
                continue  # Neptune's angle behavior is status-independent and handled by neptune_angle_aspects()
            signed = ((lon - cusp.longitude + 180) % 360) - 180  # + = just inside house, - = just outside
            if abs(signed) > CUSP_ORB:
                continue
            house_team = FAV if house_num in FAV_HOUSES else DOG
            key_house = house_num in (1, 7)

            if body_team == house_team:
                effect_team = body_team
                strength = "own"
            elif signed < 0:
                effect_team = body_team  # just outside opponent's cusp: dominates (p.28)
                strength = "outside"
            else:
                effect_team = house_team  # just inside opponent's cusp: weakens body's team (p.28-29)
                strength = "inside"

            effect_team = _flip_if_reverse(effect_team, status)
            base_weight = LORD_WEIGHT[house_num] * (0.5 if strength == "own" else 1.0)
            if key_house:
                base_weight *= 1.5

            factors.append(Factor(
                category="Planet-Cusp",
                description=(
                    f"{body} ({status.lower()}) {abs(signed):.2f} deg "
                    f"{'inside' if signed >= 0 else 'outside'} House {house_num} cusp "
                    f"({'own' if strength == 'own' else house_team} house)"
                ),
                team=effect_team,
                weight=base_weight,
                note=_cycle_note(chart, body),
                low_confidence=_is_cyclic(chart, body),
            ))
    return factors


# ---------------------------------------------------------------------
# Planet/antiscia -> Asc-Dsc / Mc-Ic / Ax-Vx / EQD-EQA axis square+trine
# (p.19-20 general rule, p.65-67 for Ax-Vx/EQD-EQA, p.83-85 for the
# Mars/Saturn/Uranus/Pluto special-case table). Conjunctions to
# ASC/DSC/MC/IC are handled by planet_cusp_aspects (those points ARE
# house cusps 1/7/10/4); conjunctions to AX/VX/EQD/EQA are handled here
# since they have no house-cusp equivalent.
#
# "(unless L#)" bookkeeping: when the aspecting planet itself holds that
# Lord number, the book says to fall back to the plain team-based
# baseline instead of the planet's stated bias.
#
# GENERIC BASELINE: for any planet without a special-case entry below, a
# normal planet aspecting an angle helps ITS OWN team -- for squares just
# as much as for trines. The aspect type does not flip the side, exactly
# as it doesn't for Moon-planet aspects ("the type of aspect is
# irrelevant", p.25). Both worked examples in the excerpt confirm it:
# normal L7 Mercury square the MC "must really help that team [the dog]"
# and only hurts the dog once Rx makes it reverse (p.59-60), and normal
# L1 Jupiter square the Ax-Vx is "a huge boost" for the favorite (p.65).
# Only Mars/Saturn/Uranus/Pluto carry an inherent fav/dog bias that
# overrides the planet's own side.
# ---------------------------------------------------------------------

# name -> {(axis, kind): (baseline_team, unless_lord_or_None)}
SPECIAL_AXIS_RULES = {
    "Mars": {
        ("Asc-Dsc", "trine"): (FAV, 7),
        ("Asc-Dsc", "square"): (DOG, 1),
        ("Mc-Ic", "trine"): (DOG, 1),
        ("Mc-Ic", "square"): (FAV, 7),
    },
    "Saturn": {
        ("Asc-Dsc", "trine"): (FAV, 7),
        ("Asc-Dsc", "square"): (DOG, 1),
        ("Mc-Ic", "trine"): (DOG, 7),
        ("Mc-Ic", "square"): (FAV, 1),
    },
    "Uranus": {
        # Uranus's Asc-Dsc trine team was not legible in the excerpt
        # (only "(unless L7)" survived); inferred as DOG from "Uranus is
        # normally dog biased" (p.84) and the symmetry of the other
        # entries. Mc-Ic trine for Uranus is not stated at all and is
        # left out (falls through to the generic baseline below).
        ("Asc-Dsc", "trine"): (DOG, 7),
        ("Asc-Dsc", "square"): (DOG, 1),
        ("Mc-Ic", "square"): (FAV, 7),
    },
    "Pluto": {
        ("Asc-Dsc", "trine"): (FAV, 7),
        ("Asc-Dsc", "square"): (DOG, None),
        ("Mc-Ic", "trine"): (DOG, 7),
        ("Mc-Ic", "square"): (FAV, 1),
    },
}

AXES = {
    "Asc-Dsc": lambda chart: chart.asc,
    "Mc-Ic": lambda chart: chart.mc,
}


def planet_axis_aspects(chart: Chart) -> list[Factor]:
    factors = []
    # Neptune and aNeptune are both handled by neptune_angle_aspects
    # (status-independent rule). The Moon has its own whole-game angle
    # rule, but aMoon is an ordinary antiscia point and belongs here.
    bodies = [b for b in CHART_BODIES if b not in ("Moon", "Neptune")] + [
        "a" + b for b in CHART_BODIES if b != "Neptune"
    ]
    extra_axes = {}
    ax = chart.extra_angles.get("AX")
    if ax is not None:
        extra_axes["Ax-Vx"] = ax
    eqd = chart.ra.get("EQD")

    for body in bodies:
        lon = chart.lon(body)
        if lon is None:
            continue
        base_name = body[1:] if body.startswith("a") else body
        team = chart.team_of(base_name)
        has_special = base_name in SPECIAL_AXIS_RULES
        # A planet that rules only house 3 and/or 9 has no side, because
        # L3/L9 are dropped from the method entirely (p.16). Such a planet
        # still counts when it carries one of the absolute fav/dog angle
        # biases -- "Mars trine Asc-Dsc = fav" holds whatever Lord Mars
        # happens to be, the "(unless L7)" clause being the only carve-out
        # -- but a planet falling through to the generic own-team baseline
        # has no team to score for and drops out.
        if team is None and not has_special:
            continue
        status = body_status(chart, body)
        retro = chart.is_rx(base_name)
        weight = _lord_weight_for(chart, base_name)

        for axis_name, getter in AXES.items():
            p1 = getter(chart)
            rel = axis_relationship(lon, retro, p1, ANGLE_ORB)
            if not rel or rel[0] not in ("square", "trine"):
                continue
            kind, orb = rel
            special = SPECIAL_AXIS_RULES.get(base_name, {}).get((axis_name, kind))
            if special:
                baseline, unless_lord = special
                # "(unless L7)" etc: the planet's inherent bias yields to
                # its own side when it holds that Lord.
                result_team = team if (
                    unless_lord is not None and unless_lord in chart.lord_numbers(base_name)
                ) else baseline
            else:
                if team is None:
                    continue
                result_team = team
            effect_team = _flip_if_reverse(result_team, status)
            factors.append(Factor(
                category="Planet-Axis",
                description=f"{body} ({status.lower()}) {kind} {axis_name} within {orb:.2f} deg",
                team=effect_team,
                weight=weight * 1.3,
                note=_cycle_note(chart, body),
                low_confidence=_is_cyclic(chart, body),
            ))

        # Ax-Vx and (RA-based) EQD-EQA: no team-anchored named points, so
        # conjunction also uses the generic own-team/opposite-team baseline.
        for axis_name, p1 in extra_axes.items():
            if team is None:
                break  # no absolute rule covers Ax-Vx; nothing to score for
            rel = axis_relationship(lon, retro, p1, ANGLE_ORB)
            if not rel:
                continue
            kind, orb = rel
            result_team = team  # generic baseline: aspect type does not flip the side
            effect_team = _flip_if_reverse(result_team, status)
            factors.append(Factor(
                category="Planet-Axis",
                description=f"{body} ({status.lower()}) {kind.replace('_', ' ')} {axis_name} within {orb:.2f} deg",
                team=effect_team,
                weight=weight * 0.8,
                note=(_cycle_note(chart, body) + " Ax-Vx/EQD-EQA: supplementary angle set (p.65-67).").strip(),
                low_confidence=_is_cyclic(chart, body),
            ))

        if eqd is not None and team is not None:
            ra_val = chart.ra.get(base_name)
            if ra_val is not None:
                rel = axis_relationship(ra_val, retro, eqd, ANGLE_ORB)
                if rel:
                    kind, orb = rel
                    result_team = team  # generic baseline: aspect type does not flip the side
                    effect_team = _flip_if_reverse(result_team, status)
                    factors.append(Factor(
                        category="Planet-Axis",
                        description=f"{body} ({status.lower()}) {kind.replace('_', ' ')} EQD-EQA (RA) within {orb:.2f} deg",
                        team=effect_team,
                        weight=weight * 0.8,
                        note=(_cycle_note(chart, body) + " Ax-Vx/EQD-EQA: supplementary angle set (p.65-67).").strip(),
                        low_confidence=_is_cyclic(chart, body),
                    ))
    return factors


def neptune_angle_aspects(chart: Chart) -> list[Factor]:
    """Neptune's blanket rule (p.84): ANY aspect -- normal or reverse --
    from Neptune/aNeptune to ASC, MC, DSC or IC helps the favorite,
    unless Neptune itself is Lord 7 (then it helps the dog). Status is
    explicitly ignored here, unlike every other rule in this module."""
    factors = []
    baseline = DOG if 7 in chart.lord_numbers("Neptune") else FAV
    retro = chart.is_rx("Neptune")
    angle_points = {"ASC": chart.asc, "MC": chart.mc, "DSC": chart.dsc, "IC": chart.ic}
    for body in ("Neptune", "aNeptune"):
        lon = chart.lon(body)
        if lon is None:
            continue
        for name, alon in angle_points.items():
            d = min(applying_delta(lon, alon, retro), applying_delta(alon, lon, False))
            if d <= ANGLE_ORB:
                factors.append(Factor(
                    category="Neptune-Angle",
                    description=f"{body} conjunct {name} (status-independent)",
                    team=baseline, weight=2.25,
                ))
        for axis_name, p1 in (("Asc-Dsc", chart.asc), ("Mc-Ic", chart.mc)):
            rel = axis_relationship(lon, retro, p1, ANGLE_ORB)
            if rel and rel[0] in ("square", "trine"):
                factors.append(Factor(
                    category="Neptune-Angle",
                    description=f"{body} {rel[0]} {axis_name} (status-independent)",
                    team=baseline, weight=1.75,
                ))
    return factors


def apof_angle_aspects(chart: Chart) -> list[Factor]:
    """aPOF conjunct ASC/MC/DSC/IC is explicitly valuable (p.77); plain
    POF near an angle is explicitly ignored."""
    factors = []
    lon = chart.lon("aPOF")
    if lon is None:
        return factors
    status = pof_final_status(chart, antiscia=True)
    cyclic = pof_final_status_is_cyclic(chart, antiscia=True)
    angle_rules = {
        "ASC": (FAV, 2.5), "MC": (FAV, 1.75), "DSC": (DOG, 2.5), "IC": (DOG, 1.75),
    }
    angles = {"ASC": chart.asc, "MC": chart.mc, "DSC": chart.dsc, "IC": chart.ic}
    for name, angle_lon in angles.items():
        d = forward_delta(lon, angle_lon)
        d = min(d, forward_delta(angle_lon, lon))  # aPOF isn't retrograde; treat as a static proximity check
        if d > ANGLE_ORB:
            continue
        baseline, weight = angle_rules[name]
        effect_team = _flip_if_reverse(baseline, status)
        factors.append(Factor(
            category="aPOF-Angle",
            description=f"aPOF within {d:.2f} deg of {name} [{status.lower()}]",
            team=effect_team,
            weight=weight,
            low_confidence=cyclic,
        ))
    return factors


# ---------------------------------------------------------------------
# Planet -> POF / aPOF casts (p.83-84). "The POF does also CAST aspects.
# Treat it just like a planet" (p.57), and the p.83 list header scopes
# these to "Planets and aPlanets (all with NORMAL status within 2
# degrees applying)".
#
# The excerpt states these for Mars, Uranus and Neptune ONLY. Saturn,
# Venus, Ceres, Jupiter etc. casting to the POF get no stated rule -- any
# such rule would be in the truncated pages 85-193 -- so those are
# reported as unscored rather than guessed at.
# ---------------------------------------------------------------------

# planet -> (aspects_favoring_fav, aspects_favoring_dog)
POF_CAST_RULES = {
    "Mars": ({"Sextile", "Trine"}, {"Conjunction", "Square", "Opposition"}),
    "Uranus": ({"Conjunction", "Sextile", "Trine"}, {"Square", "Opposition"}),
    "Neptune": ({"Conjunction", "Sextile", "Trine"}, {"Square", "Opposition"}),
}

POF_CAST_UNRULED = ("Sun", "Mercury", "Venus", "Jupiter", "Saturn", "Pluto", "Eris", "Ceres")


def _closest_aspect(body_lon: float, target_lon: float, retro: bool, orb: float):
    """Nearest applying major aspect between two points within `orb`."""
    from .constants import ASPECT_ANGLES
    from .geometry import aspect_points
    best = None
    for name, angle in ASPECT_ANGLES.items():
        for pt in aspect_points(target_lon, angle):
            d = applying_delta(body_lon, pt, retro)
            if d <= orb and (best is None or d < best[1]):
                best = (name, d)
    return best


def planet_pof_aspects(chart: Chart) -> list[Factor]:
    factors = []
    for planet, (fav_aspects, dog_aspects) in POF_CAST_RULES.items():
        retro = chart.is_rx(planet)
        for body in (planet, "a" + planet):
            lon = chart.lon(body)
            if lon is None:
                continue
            status = body_status(chart, body)
            for key, antiscia, label in (("POF", False, "POF"), ("aPOF", True, "aPOF")):
                pof_lon = chart.lon(key)
                if pof_lon is None:
                    continue
                hit = _closest_aspect(lon, pof_lon, retro, ANGLE_ORB)
                if not hit:
                    continue
                aspect_name, orb = hit
                baseline = FAV if aspect_name in fav_aspects else DOG if aspect_name in dog_aspects else None
                if baseline is None:
                    continue
                pof_status = pof_final_status(chart, antiscia=antiscia)
                # The book states these rules for a normal planet and is
                # silent on whether the POF's own Final status also flips
                # them. Combining both matches how every other paired
                # rule in the method works (p.45-46, p.57).
                combined = combine(status, pof_status)
                effect_team = baseline if combined == NORMAL else opposite(baseline)
                factors.append(Factor(
                    category="Planet-POF",
                    description=(
                        f"{body} ({status.lower()}) {aspect_name} {label} within {orb:.2f} deg "
                        f"[x {pof_status.lower()} {label} Final = {combined.lower()}]"
                    ),
                    team=effect_team,
                    weight=1.75,
                    note=_cycle_note(chart, body),
                    low_confidence=_is_cyclic(chart, body) or pof_final_status_is_cyclic(chart, antiscia=antiscia),
                ))
    return factors


def moon_extra_axis_contacts(chart: Chart) -> list[str]:
    """Moon within orb of the Ax-Vx or EQD-EQA axis.

    Deliberately NOT scored. The book's Moon-to-angle rule names only
    "the ASC, DSC, MC or IC" (p.19), yet it also says the supplementary
    axes are "treated identically to the Asc-Dsc" (p.65) -- which would
    pull the Moon in. The excerpt never resolves which reading wins and
    never shows a worked Moon/Ax-Vx example, so these are surfaced for
    the reader to judge rather than guessed at either way.
    """
    found = []
    moon_lon = chart.lon("Moon")
    if moon_lon is None:
        return found

    ax = chart.extra_angles.get("AX")
    if ax is not None:
        rel = axis_relationship(moon_lon, False, ax, ANGLE_ORB)
        if rel:
            found.append(f"Moon {rel[0].replace('_', ' ')} Ax-Vx within {rel[1]:.2f} deg")

    eqd = chart.ra.get("EQD")
    moon_ra = chart.ra.get("Moon")
    if eqd is not None and moon_ra is not None:
        rel = axis_relationship(moon_ra, False, eqd, ANGLE_ORB)
        if rel:
            found.append(f"Moon {rel[0].replace('_', ' ')} EQD-EQA (RA) within {rel[1]:.2f} deg")
    return found


def unruled_pof_casts(chart: Chart) -> list[str]:
    """Planet->POF aspects the excerpt gives no rule for, so the report
    can name them instead of silently dropping them."""
    found = []
    for planet in POF_CAST_UNRULED:
        retro = chart.is_rx(planet)
        for body in (planet, "a" + planet):
            lon = chart.lon(body)
            if lon is None:
                continue
            for key, label in (("POF", "POF"), ("aPOF", "aPOF")):
                pof_lon = chart.lon(key)
                if pof_lon is None:
                    continue
                hit = _closest_aspect(lon, pof_lon, retro, ANGLE_ORB)
                if hit:
                    found.append(f"{body} {hit[0]} {label} within {hit[1]:.2f} deg")
    return found


# ---------------------------------------------------------------------
# Nodes (p.68-69): conjunctions to planets/POF/aPOF, and the separate
# 1-degree "planet square Nodes" rule. Outer planets (Uranus, Neptune,
# Pluto) are explicitly excluded ("not relevant to this in my
# experience... they stay connected much longer due to their slow
# speed").
# ---------------------------------------------------------------------

NODE_ELIGIBLE = {"Moon", "Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Eris", "Ceres"}


def node_aspects(chart: Chart) -> list[Factor]:
    factors = []
    nn = chart.lon("NorthNode")
    if nn is None:
        return factors
    sn = (nn + 180.0) % 360.0

    for base_name in NODE_ELIGIBLE:
        lon = chart.lon(base_name)
        if lon is None:
            continue
        team = chart.team_of(base_name)
        if team is None:
            continue
        status = body_status(chart, base_name)
        retro = chart.is_rx(base_name)

        cyclic = _is_cyclic(chart, base_name)
        for node_name, node_lon, helps in (("North Node", nn, True), ("South Node", sn, False)):
            d = applying_delta(lon, node_lon, retro)
            if d <= NODE_ORB:
                baseline = team if helps else opposite(team)
                factors.append(Factor(
                    category="Node-Conjunction",
                    description=f"{base_name} ({status.lower()}) conjunct {node_name} within {d:.2f} deg",
                    team=_flip_if_reverse(baseline, status),
                    weight=1.25,
                    note=_cycle_note(chart, base_name),
                    low_confidence=cyclic,
                ))

        d_sq = min(applying_delta(lon, (nn + 90) % 360, retro), applying_delta(lon, (nn - 90) % 360, retro))
        if d_sq <= 1.0:
            factors.append(Factor(
                category="Node-Square",
                description=f"{base_name} ({status.lower()}) square Node axis within {d_sq:.2f} deg",
                team=_flip_if_reverse(opposite(team), status),
                weight=1.0,
                note=_cycle_note(chart, base_name),
                low_confidence=cyclic,
            ))

    for key, antiscia, label in (("POF", False, "POF"), ("aPOF", True, "aPOF")):
        lon = chart.lon(key)
        if lon is None:
            continue
        status = pof_final_status(chart, antiscia=antiscia)
        pof_cyclic = pof_final_status_is_cyclic(chart, antiscia=antiscia)
        for node_name, node_lon, helps_fav in (("North Node", nn, True), ("South Node", sn, False)):
            d = min(forward_delta(lon, node_lon), forward_delta(node_lon, lon))
            if d <= NODE_ORB:
                baseline = FAV if helps_fav else DOG
                factors.append(Factor(
                    category="Node-Conjunction",
                    description=f"{label} conjunct {node_name} within {d:.2f} deg [{status.lower()}]",
                    team=_flip_if_reverse(baseline, status),
                    weight=1.5 if antiscia else 1.25,
                    low_confidence=pof_cyclic,
                ))
        d_sq = min(forward_delta(lon, (nn + 90) % 360), forward_delta((nn + 90) % 360, lon),
                   forward_delta(lon, (nn - 90) % 360), forward_delta((nn - 90) % 360, lon))
        if not antiscia and d_sq <= ANGLE_ORB:
            factors.append(Factor(
                category="Node-Square",
                description=f"POF square Node axis within {d_sq:.2f} deg [{status.lower()}]",
                team=_flip_if_reverse(DOG, status),
                weight=1.0,
                note="POF-square-Node orb inferred at 2 deg; the book gives no explicit orb here.",
                low_confidence=pof_cyclic,
            ))
    return factors
