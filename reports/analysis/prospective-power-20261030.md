# Prospective conjunction power scenarios

The [54-scenario calculation](prospective-power-20261030.json) extends the original
single-contrast arithmetic to the future 30- and 70-component conjunctions. It uses
5,000 seeded Gaussian simulations per scenario and records Monte Carlo intervals.
These are assumptions, not empirical variance estimates, a chosen sample size, or
an H4 pass. All true effects are zero, so this is favorable to equivalence.

Each endpoint is divided by its future practical margin. An SD/margin ratio of one
means, for example, a paired SD of 2 percentage points with a 2-point margin. It
does not choose those values. Component correlation is a sensitivity parameter;
sharing View and datasets makes independence an implausible universal assumption,
while perfect correlation is another extreme.

For SD/margin = 1, the simulated probability that **every** component passes is:

| Components | Paired seeds | Correlation 0 | Correlation 0.5 | Correlation 1 |
| --- | --- | --- | --- | --- |
| 30 | 5 | 0/5,000 | 0/5,000 | 29.2% |
| 30 | 11 | 0.56% | 10.7% | 85.0% |
| 30 | 36 | 99.86% | 99.96% | 100% observed |
| 70 | 5 | 0/5,000 | 0/5,000 | 28.4% |
| 70 | 11 | 0/5,000 | 2.28% | 85.2% |
| 70 | 36 | 99.90% | 99.88% | 100% observed |

Zero observed successes is not zero true power, and 100% observed is not certainty;
the JSON contains the Monte Carlo intervals. Differences between the two perfectly
correlated rows reflect simulation sampling, not an effect of component count.
The report also includes SD/margin ratios 0.5 and 2. Neither five nor thirty-six
seeds should be adopted from this table: actual variance, effects, dependence,
precision, model competence and resources must determine the later freeze.

Reproduce with:

```sh
.venv/bin/python scripts/scoring/power_scenarios.py --output NEW-power.json
```

The implementation uses the same independently checked one-sided Student-t/TOST
rules described in [operational scoring](../../docs/operational-scoring.md). Existing
tests compare the p-values to SciPy's one-sample tests and check seeded power against
a known single-component probability. The 54 output cells and probability bounds
were checked without needlessly repeating the simulations.
