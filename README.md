# Stellar Wheelhouse Engine

A rules engine that scores sports-event astrology charts according to
David Sloan's *Stellar Wheelhouse* (2022, revised 2026 edition). Paste in
a chart report from your astrology software and get a itemized,
weighted breakdown of every scoreable factor plus a favorite/underdog
lean.

## Quick start

```bash
python3 -m stellar_wheelhouse.cli path/to/chart.txt
# or pipe it in:
cat chart.txt | python3 -m stellar_wheelhouse.cli
```

No third-party dependencies -- pure Python 3.10+ standard library.

See `tests/fixtures/example_chart.txt` for the exact input format expected
(a plain-text chart export with a `Favorite = ...` / `Underdog = ...` line,
a `Planet Positions:` block, a `House 1:`...`House 12:` block, and a
`Right Ascension:` block -- these four sections are all this engine
actually reads; the pre-rendered "Planet Aspects" / "Moon to Planets" /
"Planets to Angles" blocks your software prints are ignored, because this
engine recomputes every aspect itself from the raw longitudes for
consistency with the book's rules).

## Running the tests

```bash
python3 tests/test_engine.py     # no dependencies
# or, if you have pytest installed:
python3 -m pytest tests/
```

## What it implements

Everything in the uploaded book excerpt that states a mechanical rule:

- House-Lord team assignment (favorite = L1/L10/L2/L6/L5, underdog =
  L7/L4/L8/L12/L11), read directly from your software's `House N:` lines.
- Normal/Reverse status via the dispositor chain (own sign / detriment /
  neutral-recurse, p.42-43), including Rx, the 29th-degree ("anaretic")
  flip, Via Combusta, and the Spica exception.
- Moon-to-planet and Moon-to-antiscia aspects across the 5-degree travel
  window, with in-game timing percentage.
- Part of Fortune and Antiscia Part of Fortune, including the 3-part
  (Sun x Moon x POF-in-sign) Final status calculation and Moon-POF
  aspect rules.
- Moon-to-angle (ASC/DSC/MC/IC) and planet-to-angle/axis relationships,
  including the Mars/Saturn/Uranus/Neptune/Pluto special-case table and
  the extra Antivertex-Vertex and (right-ascension-based) EQD-EQA axes.
- Planet-on-house-cusp proximity (inside/outside/own-house effects).
- Node conjunctions and the planet/Moon/POF-square-Nodes rules.
- aPOF's explicit angle rule (valuable) vs. plain POF near an angle
  (explicitly ignored by the book).

## Rule coverage

Every rule stated in the available pages has been catalogued (41 of
them) and audited against the code. All 41 are implemented. The
audit table lives in the commit history; the short version is that the
engine covers Lord assignment and interception, the full dispositor
status system (own sign / detriment with both stated escape routes /
neutral recursion, Rx, 29th degree with propagation, Via Combusta,
Spica), Moon travel aspects and timing, Moon-to-angle in every aspect,
POF and aPOF including the three-part Final status, antiscia
throughout, house-cusp proximity, the four angle axes, the
Mars/Saturn/Uranus/Neptune/Pluto special tables, the Asc-Mc midpoint
rule, and the Node rules.

## What it does NOT implement (and says so in its output)

The uploaded PDF is a 42-page excerpt; it runs out mid-sentence partway
through "A Most Helpful List" (around book page 84) and never reaches
book pages 85-193: the rest of that rules list (Jupiter/Ceres/Eris/inner-
planet specifics), the Capulus-Algol fixed-star rule, and every worked
example chapter ("Serious Practice", "10 Super Bowls", "A Few World
Cups", "More Detailed Practice", "Final Notes/Addendum"). Anything only
explained there isn't in this engine. When your chart data includes a
Capulus-Algol alert, the report says so explicitly rather than silently
ignoring it.

## Honesty features worth knowing about

- **No numeric weights exist in the book.** It only ranks importance in
  words ("L1 and L7 most important", "a strong factor"). The `weight`
  values in `aspects.py` are this engine's own translation into numbers
  so factors can be tallied -- treat the resulting score as a reasonable
  ordering, not a book-stated value.
- **Closed dispositor loops are reasoned through, not guessed.** The
  book only ever demonstrates chains that terminate at a planet in its
  own sign, but that is not guaranteed — through June–July 2026, for
  instance, no planet is in its own sign *or* its detriment, so every
  chain necessarily closes into a loop. That turns out to be resolvable
  from the book's own wording: REVERSE only ever *originates* at a
  detriment placement, and neutral planets merely *inherit* it, so a
  loop with no detriment member has no source of reverse and is
  provably NORMAL. The sole exception is the 29th degree, which does
  propagate down the chain (p.77) — an odd number of 29-degree members
  inside a loop is genuinely self-contradictory, and only that case is
  flagged `low_confidence` and held out of the scored verdict.
- **Thin evidence is labeled as such.** A "lopsided" score built from
  one surviving factor is not the same as one built from a dozen, and
  the verdict line says so explicitly.
- Every non-obvious extrapolation beyond what the excerpt states
  outright is called out in a code comment where it happens (see
  `aspects.py`'s module docstring and `status_engine.py`'s docstring for
  the two clearest examples, including one place where the book's own
  worked example appears to contradict its own stated rule).

## Project layout

```
stellar_wheelhouse/
  constants.py      sign rulerships, orbs, Lord weights
  chart_parser.py    parses the plain-text chart report
  geometry.py        angle/orb arithmetic
  status_engine.py   Normal/Reverse dispositor-chain logic
  aspects.py         every scoreable relationship -> Factor objects
  scoring.py         tallies factors into a Verdict
  factor.py          the Factor dataclass
  engine.py          analyze(text) -> AnalysisResult
  report.py          renders a text report
  cli.py             command-line entry point
tests/
  test_engine.py
  fixtures/example_chart.txt
```
