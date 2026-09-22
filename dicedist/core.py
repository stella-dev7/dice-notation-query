"""Parsing and probability computation for dice notation.

Supported notation: "NdM", "NdM+K" / "NdM-K", and keep-highest/lowest
("NdMkhJ", "NdMklJ", each optionally followed by a +K/-K modifier),
e.g. "3d6", "d20", "2d8+3", "4d6kh3". Multi-term expressions
("2d6+1d4") are not handled yet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from math import comb

_DICE_RE = re.compile(
    r"^\s*(\d*)d(\d+)(?:k([hl])(\d+))?\s*([+-]\s*\d+)?\s*$", re.IGNORECASE
)


class DiceSyntaxError(ValueError):
    """Raised when a string is not valid dice notation."""


@dataclass(frozen=True)
class DiceExpr:
    count: int
    sides: int
    modifier: int
    keep: int | None = None
    keep_highest: bool = True

    def __str__(self) -> str:
        base = f"{self.count}d{self.sides}"
        if self.keep is not None:
            base += f"k{'h' if self.keep_highest else 'l'}{self.keep}"
        if self.modifier > 0:
            return f"{base}+{self.modifier}"
        if self.modifier < 0:
            return f"{base}{self.modifier}"
        return base


def parse(text: str) -> DiceExpr:
    match = _DICE_RE.match(text)
    if not match:
        raise DiceSyntaxError(f"not valid dice notation: {text!r}")
    count_str, sides_str, keep_which, keep_str, modifier_str = match.groups()
    count = int(count_str) if count_str else 1
    sides = int(sides_str)
    if count < 1:
        raise DiceSyntaxError(f"dice count must be at least 1: {text!r}")
    if sides < 2:
        raise DiceSyntaxError(f"a die needs at least 2 sides: {text!r}")
    modifier = int(modifier_str.replace(" ", "")) if modifier_str else 0
    keep = None
    keep_highest = True
    if keep_str is not None:
        keep = int(keep_str)
        keep_highest = keep_which.lower() == "h"
        if keep < 1:
            raise DiceSyntaxError(f"keep count must be at least 1: {text!r}")
        if keep > count:
            raise DiceSyntaxError(f"cannot keep more dice than are rolled: {text!r}")
    return DiceExpr(count=count, sides=sides, modifier=modifier, keep=keep, keep_highest=keep_highest)


def _full_distribution(count: int, sides: int) -> dict[int, float]:
    """PMF of the sum of `count` dSides dice, by convolving one die at a time.

    Enumerating every N**count outcome directly would be wasteful (and
    infeasible once count or sides gets large), so the running total's
    distribution is folded in one die at a time instead.
    """
    pmf: dict[int, float] = {0: 1.0}
    die_pmf = {face: 1.0 / sides for face in range(1, sides + 1)}
    for _ in range(count):
        next_pmf: dict[int, float] = {}
        for total, prob in pmf.items():
            for face, face_prob in die_pmf.items():
                key = total + face
                next_pmf[key] = next_pmf.get(key, 0.0) + prob * face_prob
        pmf = next_pmf
    return pmf


def _keep_distribution(count: int, sides: int, keep: int, keep_highest: bool) -> dict[int, float]:
    """PMF of the sum of the `keep` highest (or lowest) of `count` dSides dice.

    Processes face values from the kept extreme inward (sides down to 1
    for keep-highest, 1 up to sides for keep-lowest). At each step the
    unassigned dice are exchangeable and uniform over the faces not yet
    ruled out, so the count of them landing on the current extreme face
    is binomial; conditioned on missing it, they're uniform over the
    remaining faces, which is what lets the recursion continue.
    """
    order = range(sides, 0, -1) if keep_highest else range(1, sides + 1)
    # state key: (dice not yet assigned a face, dice kept so far, running total)
    state: dict[tuple[int, int, int], float] = {(count, 0, 0): 1.0}
    for v in order:
        span = v if keep_highest else sides - v + 1
        p = 1.0 / span
        next_state: dict[tuple[int, int, int], float] = {}
        for (remaining, kept, total), prob in state.items():
            if remaining == 0 or kept == keep:
                key = (remaining, kept, total)
                next_state[key] = next_state.get(key, 0.0) + prob
                continue
            for c in range(remaining + 1):
                branch_prob = comb(remaining, c) * (p**c) * ((1 - p) ** (remaining - c))
                if branch_prob == 0.0:
                    continue
                taken = min(c, keep - kept)
                key = (remaining - c, kept + taken, total + taken * v)
                next_state[key] = next_state.get(key, 0.0) + prob * branch_prob
        state = next_state
    pmf: dict[int, float] = {}
    for (_remaining, _kept, total), prob in state.items():
        pmf[total] = pmf.get(total, 0.0) + prob
    return pmf


def distribution(expr: DiceExpr) -> dict[int, float]:
    """Exact probability mass function for a dice expression."""
    if expr.keep is not None:
        pmf = _keep_distribution(expr.count, expr.sides, expr.keep, expr.keep_highest)
    else:
        pmf = _full_distribution(expr.count, expr.sides)
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
