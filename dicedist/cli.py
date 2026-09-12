"""Command line interface for dicedist.

Reads dice notation expressions, one per line, from files given as
arguments, or from stdin when no files are given (or a file is "-").
This lets the tool sit at either end of a pipeline: `echo "3d6+2" |
dicedist` works the same as `dicedist rolls.txt`.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from typing import Iterable, TextIO

from . import core


def _lines_from(stream: TextIO) -> Iterable[str]:
    for raw_line in stream:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        yield line


def _read_expressions(paths: list[str]) -> Iterable[str]:
    if not paths:
        yield from _lines_from(sys.stdin)
        return
    for path in paths:
        if path == "-":
            yield from _lines_from(sys.stdin)
        else:
            with open(path, encoding="utf-8") as handle:
                yield from _lines_from(handle)


def _report(text: str, args: argparse.Namespace) -> dict:
    expr = core.parse(text)
    pmf = core.distribution(expr)
    totals = pmf.keys()
    result = {
        "expression": str(expr),
        "min": min(totals),
        "max": max(totals),
        "mean": core.mean(pmf),
        "stdev": math.sqrt(core.variance(pmf)),
    }
    if args.at_least is not None:
        result["at_least"] = {"target": args.at_least, "probability": core.at_least(pmf, args.at_least)}
    if args.at_most is not None:
        result["at_most"] = {"target": args.at_most, "probability": core.at_most(pmf, args.at_most)}
    if args.exactly is not None:
        result["exactly"] = {"target": args.exactly, "probability": core.exactly(pmf, args.exactly)}
    return result


def _print_human(result: dict) -> None:
    print(
        f"{result['expression']}: min={result['min']} max={result['max']} "
        f"mean={result['mean']:.3f} stdev={result['stdev']:.3f}"
    )
    for key in ("at_least", "at_most", "exactly"):
        if key in result:
            target = result[key]["target"]
            prob = result[key]["probability"]
            label = key.replace("_", " ")
            print(f"  P({label} {target}) = {prob:.4f}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dicedist",
        description="Compute exact probability statistics for dice notation expressions.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="files with one dice expression per line; omit, or pass -, to read stdin",
    )
    parser.add_argument("--at-least", type=int, default=None, metavar="N", help="report P(total >= N)")
    parser.add_argument("--at-most", type=int, default=None, metavar="N", help="report P(total <= N)")
    parser.add_argument("--exactly", type=int, default=None, metavar="N", help="report P(total == N)")
    parser.add_argument("--json", action="store_true", help="emit one JSON object per line instead of text")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    saw_any = False
    had_error = False
    for text in _read_expressions(args.files):
        saw_any = True
        try:
            result = _report(text, args)
        except core.DiceSyntaxError as exc:
            print(f"error: {exc}", file=sys.stderr)
            had_error = True
            continue
        if args.json:
            print(json.dumps(result))
        else:
            _print_human(result)
    if not saw_any:
        print("error: no expressions given", file=sys.stderr)
        return 1
    return 1 if had_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
