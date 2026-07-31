from __future__ import annotations

from dataclasses import dataclass

from .constants import FAV, DOG


def opposite(team: str) -> str:
    return DOG if team == FAV else FAV


@dataclass
class Factor:
    category: str
    description: str
    team: str | None       # FAV, DOG, or None if not scored/informational
    weight: float
    timing_pct: float | None = None
    note: str = ""
    low_confidence: bool = False  # e.g. status depends on an unresolved dispositor loop
    lords: tuple[int, ...] = ()   # houses ruled by the planet involved, if any

    @property
    def is_key_lord(self) -> bool:
        """Does this factor involve Lord 1 or Lord 7 -- the favourite's and
        the underdog's main planets? "L1 and L7, followed by L10 and L4,
        are the most important" (p.17).

        Read from structured lord numbers, never from the description
        text: substring matching on "L1" also catches L10/L11/L12.
        """
        return any(n in (1, 7) for n in self.lords)
