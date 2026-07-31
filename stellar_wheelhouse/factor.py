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
