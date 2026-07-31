"""Constants derived from David Sloan's "Stellar Wheelhouse" (2022/2026).

Only what is explicitly stated in the uploaded excerpt (Foreword through the
opening of "A Most Helpful List", book pages ~1-84) is encoded here. See
README.md for exactly what is and is not covered.
"""

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

# Stellar Wheelhouse's final rulership table (p.83): Eris rules Taurus,
# Ceres rules Virgo -- Venus and Mercury do NOT rule those signs in this
# system.
SIGN_RULER = {
    "Aries": "Mars",
    "Taurus": "Eris",
    "Gemini": "Mercury",
    "Cancer": "Moon",
    "Leo": "Sun",
    "Virgo": "Ceres",
    "Libra": "Venus",
    "Scorpio": "Pluto",
    "Sagittarius": "Jupiter",
    "Capricorn": "Saturn",
    "Aquarius": "Uranus",
    "Pisces": "Neptune",
}

TRADITIONAL_PLANETS = {"Moon", "Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}

# Inverse of SIGN_RULER: the one sign each body rules in this system.
PLANET_RULES = {planet: sign for sign, planet in SIGN_RULER.items()}


def opposite_sign(sign: str) -> str:
    idx = SIGNS.index(sign)
    return SIGNS[(idx + 6) % 12]

# Planets/points whose dispositor chain and Rx/29th-degree status we track.
CHART_BODIES = [
    "Moon", "Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
    "Uranus", "Neptune", "Pluto", "Eris", "Ceres",
]

# Major aspects used throughout the book.
ASPECT_ANGLES = {
    "Conjunction": 0,
    "Sextile": 60,
    "Square": 90,
    "Trine": 120,
    "Opposition": 180,
}

# House Lords used for prediction; L3/L9 are deliberately omitted (p.16).
FAVORITE_LORDS = [1, 10, 2, 6, 5]
UNDERDOG_LORDS = [7, 4, 8, 12, 11]

FAV_HOUSES = set(FAVORITE_LORDS)
DOG_HOUSES = set(UNDERDOG_LORDS)

# Relative importance/weight of each Lord within its side, in the order
# given in the book ("L1 and L7 ... most important, followed by L10 and
# L4 ... remaining Lords listed roughly in order of strength", p.17,
# p.26 for the dog side parallel).
LORD_WEIGHT = {
    1: 3.0, 7: 3.0,
    10: 2.0, 4: 2.0,
    2: 1.5, 8: 1.5,
    6: 1.2, 12: 1.2,
    5: 1.0, 11: 1.0,
}

# Anaretic ("29th") degree threshold (p.77).
ANARETIC_DEGREE = 29.0

# Via Combusta range used in this book: 14 Libra - 14 Scorpio (p.78),
# i.e. absolute ecliptic longitude 194.0 to 224.0 (Libra starts at 180).
VIA_COMBUSTA_START = 180.0 + 14.0
VIA_COMBUSTA_END = 210.0 + 14.0

# Fixed star Spica, "24 11' Libra as of 2026" (p.79) -> absolute longitude.
SPICA_LONGITUDE = 180.0 + 24.0 + 11.0 / 60.0
SPICA_ORB = 1.0

# Orbs used by the book.
MOON_TRAVEL_ORB = 5.0      # Moon-to-planet / Moon-to-POF window (p.16-17)
ANGLE_ORB = 2.0            # Moon/planet-to-angle window (p.19, p.83)
CUSP_ORB = 2.0             # planet-on-house-cusp window (p.26-27)
NODE_ORB = 2.0             # planet/POF conjunct Node window (p.68-69)

ANTISCIA_PAIRS = {
    "Aries": "Virgo", "Virgo": "Aries",
    "Taurus": "Leo", "Leo": "Taurus",
    "Gemini": "Cancer", "Cancer": "Gemini",
    "Libra": "Pisces", "Pisces": "Libra",
    "Scorpio": "Aquarius", "Aquarius": "Scorpio",
    "Sagittarius": "Capricorn", "Capricorn": "Sagittarius",
}

FAV = "FAV"
DOG = "DOG"
NORMAL = "NORMAL"
REVERSE = "REVERSE"
