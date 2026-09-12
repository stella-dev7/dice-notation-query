"""Parsing and probability computation for dice notation.

Supported notation for this first pass: "NdM" or "NdM+K" / "NdM-K",
e.g. "3d6", "d20", "2d8+3". Keep-highest/lowest and multi-term
expressions ("2d6+1d4") are not handled yet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_DICE_RE = re.compile(r"^\s*(\d*)d(\d+)\s*([+-]\s*\d+)?\s*$", re.IGNORECASE)


class DiceSyntaxError(ValueError):
    """Raised when a string is not valid dice notation."""


@dataclass(frozen=True)
class DiceExpr:
    count: int
    sides: int
    modifier: int

    def __str__(self) -> str:
        base = f"{self.count}d{self.sides}"
        if self.modifier > 0:
            return f"{base}+{self.modifier}"
        if self.modifier < 0:
            return f"{base}{self.modifier}"
        return base


def parse(text: str) -> DiceExpr:
    match = _DICE_RE.match(text)
    if not match:
        raise DiceSyntaxError(f"not valid dice notation: {text!r}")
    count_str, sides_str, modifier_str = match.groups()
    count = int(count_str) if count_str else 1
    sides = int(sides_str)
    if count < 1:
        raise DiceSyntaxError(f"dice count must be at least 1: {text!r}")
    if sides < 2:
        raise DiceSyntaxError(f"a die needs at least 2 sides: {text!r}")
    modifier = int(modifier_str.replace(" ", "")) if modifier_str else 0
    return DiceExpr(count=count, sides=sides, modifier=modifier)


def distribution(expr: DiceExpr) -> dict[int, float]:
    """Exact probability mass function, built by convolving one die at a time.

    Enumerating every N**count outcome directly would be wasteful (and
    infeasible once count or sides gets large), so the running total's
    distribution is folded in one die at a time instead.
    """
    pmf: dict[int, float] = {0: 1.0}
    die_pmf = {face: 1.0 / expr.sides for face in range(1, expr.sides + 1)}
    for _ in range(expr.count):
        next_pmf: dict[int, float] = {}
        for total, prob in pmf.items():
            for face, face_prob in die_pmf.items():
                key = total + face
                next_pmf[key] = next_pmf.get(key, 0.0) + prob * face_prob
        pmf = next_pmf
    if expr.modifier:
        pmf = {total + expr.modifier: prob for total, prob in pmf.items()}
    return pmf


def mean(pmf: dict[int, float]) -> float:
    return sum(total * prob for total, prob in pmf.items())


def variance(pmf: dict[int, float]) -> float:
    mu = mean(pmf)
    return sum(prob * (total - mu) ** 2 for total, prob in pmf.items())


def at_least(pmf: dict[int, float], target: int) -> float:
    return sum(prob for total, prob in pmf.items() if total >= target)


def at_most(pmf: dict[int, float], target: int) -> float:
    return sum(prob for total, prob in pmf.items() if total <= target)


def exactly(pmf: dict[int, float], target: int) -> float:
    return pmf.get(target, 0.0)
