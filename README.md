# dicedist

A command-line tool that answers one question: given a dice notation
expression like `3d6+2`, what does the actual distribution of results
look like?

Simulating dice with `random.randint` in a loop gives you an
approximation that jitters between runs. `dicedist` computes the exact
probability mass function instead, by convolving one die at a time, so
the numbers it reports (mean, stdev, "chance of rolling at least 15")
are exact fractions, not samples.

## Usage

Pass an expression on stdin:

```
$ echo "3d6+2" | dicedist
3d6+2: min=5 max=20 mean=12.500 stdev=2.958
```

Or put several expressions in a file, one per line, and pass the file:

```
$ cat rolls.txt
2d6
1d20+5
4d4-2
$ dicedist rolls.txt
2d6: min=2 max=12 mean=7.000 stdev=2.415
1d20+5: min=6 max=25 mean=15.500 stdev=5.766
4d4-2: min=2 max=14 mean=8.000 stdev=1.581
```

A bare `-` (or no file at all) means stdin, so the two forms above can
be mixed in a pipeline. Lines that are blank or start with `#` are
skipped.

To ask about a specific target instead of just the summary stats:

```
$ echo "2d20+5" | dicedist --at-least 30
2d20+5: min=7 max=45 mean=26.000 stdev=5.416
  P(at least 30) = 0.3225
```

`--at-most N` and `--exactly N` work the same way. Add `--json` to get
one JSON object per line instead, for feeding into another tool.

Keep-highest/lowest works the same as any other expression:

```
$ echo "4d6kh3" | dicedist
4d6kh3: min=3 max=18 mean=12.245 stdev=2.847
```

## Notation supported so far

`NdM`, `NdM+K`, `NdM-K` -- for example `d20`, `3d6`, `2d8+3`, `4d4-2`.
`N` defaults to 1 if omitted.

Keep-highest/lowest is written `NdMkhJ` or `NdMklJ`, where `J` is how
many of the `N` dice to keep -- for example `4d6kh3` (roll 4d6, keep
the best 3, the classic ability score method) or `2d20kl1`
(disadvantage). A modifier can follow: `4d6kh3+1`. Multi-term
expressions (`2d6+1d4`) aren't parsed yet; see the roadmap below.

## Running it

No dependencies beyond the standard library:

```
python -m dicedist rolls.txt
```

or install it so the `dicedist` command is on your PATH (`pip install
-e .` from this directory).

## Roadmap

- multi-term expressions (`2d6+1d4+3`)
- a text histogram of the full distribution, not just summary stats
- caching distributions for repeated identical expressions in one run
