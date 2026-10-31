# Operational scoring and paired analysis

Joy owns `evaluation/metrics.py`, `scoring.py`, `statistics.py`, `score_plan.py` and
`scripts/scoring/`. Sudarshan's independent implementation remains separate under
`analysis/`; neither implementation imports the other. This first increment supports
synthetic and train/development scoring. Assessment scoring is rejected before
label access until the release/isolation workflow is implemented and verified.

## Run a declared plan

```sh
.venv/bin/python scripts/scoring/score.py --plan PATH/plan.json --output NEW-report.json
```

The plan (`bullet-time.scoring-plan.v1`) declares `scope` (`synthetic` or
`development`), `split`, expected `families`, `classes`, the three `readout_seeds`,
paired `pretraining_seeds`, `slots`, `contrasts`, and bootstrap `replicates`/`seed`.
`labels` and `groups` each contain a relative `path` and actual file `sha256`.
Paths resolve within the plan directory; symlink/parent escapes fail. Arrange an
immutable analysis snapshot under that root rather than reaching outside it.

Each slot declares `slot_id`, `condition`, `objective`, `task_id`, `horizon`,
`label_budget`, `checkpoint_pass`, `model_kind`, `corpus_sha256`,
`readout_recipe_sha256`, `pretraining_seed`, `readout_seed`, an `expected` path/hash,
and a relative `predictions` directory. A development slot also binds the actual
`fit` report path/hash when a prediction export is delivered. The common readout
recipe hash is the canonical fit configuration with only `seed` removed.

Learned slots derive seed, condition, objective, corpus and completed pass from the
actual backbone binding. Frozen references use `model_kind`/`condition`/`objective`
`untrained` or `external`, pass zero and a zero-filled corpus hash. Supervised
models use kind `diagnostic`, objective `supervised`, their actual mode as condition,
pass zero and zero-filled corpus hash; their run/checkpoint identity is the fitted
diagnostic identity. None of these references is counted as an extra independent
pretraining seed. Inference metadata must bind the actual fit/config/source and
prediction IDs; a plan cannot relabel a checkpoint's seed, budget or fitted horizon.
Seed zero is valid. Separate horizon heads may share the same frozen backbone ID.

An unfitted slot may have `expected: null`; it remains explicitly incomplete, with
no invented checkpoint keys. A missing prediction directory or failed-fit receipt
also keeps the planned slot and missing/failed examples. Delivered exports must
contain all expected CSV rows, including explicit failures, and their coverage
counters/hashes must agree. A corrupt export is a validation error, not a failed
arm that can be quietly omitted. Missing slots or predictions cannot yield a
complete contrast or a favorable successful-subset score.

A contrast declares the same objective/task/horizon/budget/pass/model-kind/corpus/
recipe fields, plus `contrast_id`, `condition`, `reference` and a positive `margin`
in score fractions (0.02 = two percentage points). All planned paired training
seeds × three readout seeds must exist on both sides. Actual labels, related groups,
queries and family inventories must match. Three readouts within a condition/seed
must share the actual backbone run/checkpoint; different pretraining seeds cannot
reuse that same backbone. Delivered development fits must also agree on training
episode IDs, input/image/label hashes, selection and development inventory binding.
Matching counts alone do not establish matching examples. Actual model, training
and runtime bindings must agree except for condition, seed, permitted microbatch
size and seed-specific initialization; initialization must match within each paired
pretraining seed. Failures before a fit exists retain their receipt hash and reason.
Pairing also checks the fit/inference source-runtime records and actual inference
input/RGB-catalog hashes; shared episode IDs alone do not establish shared inputs.
The configuration is trusted as the
predeclared analysis inventory; it is not proof of a prospective final freeze.
Full pilot gate admission and its required run matrix remain separate work.

## Metric and inference rules

- Collision/order: class-balanced accuracy at probability ≥0.5 and mean Brier score.
  Require opposite labels in each primary-horizon pair. Secondary horizons are
  separate heads and need both classes for balanced accuracy.
- Tracking: exactly three consecutive visible primary reappearance frames per
  episode; all three must satisfy visibility ≥0.5 and distance ≤full projected-box
  diagonal/8, in 224-pixel coordinates. The tiny numerical boundary allowance is
  1e-12 pixels. Any primary diagonal below 16 pixels moves the entire episode to
  the separately reported small-object stratum. Episode weights are equal.
  Supporting error/visibility summarize primary windows; auxiliary visibility is
  separate. The producer must still establish actual surface visibility and first
  reappearance from physical/rendered evidence.
- SSv2: top-1 accuracy over videos. Accept the existing video-ID→related-group map
  and require complete selected groups. Actual official-training partition/access
  validation remains necessary outside scoring.
- Average within each expected family, then equally across those families. One
  arena is labeled a single-family pilot result, never a three-family estimate.
- Average three readout scores within each checkpoint, retain their SD, and form
  paired pretraining-seed differences. TOST uses component 90% Student-t intervals;
  conventional 95% intervals and variance uncertainty are also reported. Zero
  observed paired variance is reported as unavailable t inference, not automatic
  equivalence. A component interval touching a margin does not pass.
- Paired group bootstrap preserves counterfactual pairs/videos, family structure,
  and label-outcome strata where necessary. The same sampled groups are used by
  all arms/readout/training seeds. Crossed sensitivity additionally resamples
  training seeds. Neither sensitivity interval substitutes for primary TOST;
  few training seeds limit tail reliability.
- The global conjunction helper requires exactly the declared 30/70 View-relative
  components; every component must pass at alpha .05. Individual equivalence and
  two-sided superiority use separate Holm families. Missing components cannot be
  silently omitted. Statistical calculations alone never certify a scientific claim.

`statistics.simulate_joint_power` provides seeded Gaussian equicorrelation scenarios
with Monte Carlo uncertainty, explicitly prospective. Its SDs/correlations/margins
are assumptions, not estimates or a sample-size freeze. Numerical distributions use
pinned [SciPy 1.16.3](https://pypi.org/project/scipy/1.16.3/) and its
[Student-t distribution](https://docs.scipy.org/doc/scipy-1.16.2/reference/generated/scipy.stats.t.html).
The protocol's [TOST source](https://doi.org/10.1177/1948550617697177) supplies the
scientific interpretation; future sample size/stopping and margins still need freezing.

## Check the implementation

```sh
.venv/bin/python -m pytest tests/scoring -q
```

Known-answer wires live in `tests/fixtures/scoring/`; they are deliberately synthetic.
Tests cover chance/Brier values, family macro weighting, failed/missing rows/runs,
hash/identity/group corruption, tracking tolerance/visibility/size boundaries,
seed hierarchy, missing experiment cells, pairing, exact conjunction coverage,
Holm calculations and independently evaluated SciPy one-sided tests. Real J7
producer integration and locked assessment are still required before research use.
Scoring records its source/runtime and input hashes. Unimported scoring modules
are excluded from the training/inference fingerprint so analysis work does not
invalidate fits; shared export/provenance and actual model/input code stay bound.

The [October 30 prospective power scenarios](../reports/analysis/prospective-power-20261030.md)
record 30/70-component conjunction sensitivity to paired SD, margin, correlation and
seed count. They are planning calculations, not empirical power or a protocol freeze.
The [real readout integration](../reports/data/readout-integration-20261030.md) records
actual native-image fit, prediction and scoring execution, without claiming H3.

## Fixed H4 numerical screens

`assessment_policy.h4_verdict` checks exactly 324 pass-20/fixed-reference heads:
243 game assessment heads plus 81 SSv2 internal-development heads. Each report must
already have its slot-to-fit, actual execution and release bindings validated by
the staged adapter. This calculation does not provide those bindings or release
assessment; the direct scorer still refuses assessment.

It recomputes metrics from complete rows, requires matching task pools/targets and
label budgets, checks the fixed game counts/pairs and predictor consistency, and
retains explicit failed slots. Missing/failed predictions in any arm (including
image-only or external references) make the whole numerical screen incomplete.
It averages three readout seeds within checkpoint, then pretraining seeds, then
the predeclared View/Time/Mix50 arms. It reports every arm and checkpoint alongside
the learning, per-task native-recipe, external-competence and grouping comparisons.
The order diagnostic is reported but cannot substitute for a primary endpoint in
the learning/grouping rules. Thresholds are the unchanged pilot-plan defaults.

A plan has schema `bullet-time.h4-numerical-plan.v1` and `reports`, a map from each
ID in `h4_inventory()` to `{ "path": "relative/report.json", "sha256": "..." }`.
A report is a validated `bullet-time.score.v1` score, or
`{ "status": "failed", "error": "concrete retained failure" }` for an undelivered
slot. Paths resolve within the plan directory. Keep real assessment reports private
under the existing staged release policy; this is not a way to inspect them early.

```bash
.venv/bin/python scripts/scoring/pilot_h4.py \
  --plan /absolute/private/h4-report-plan.json \
  --output /absolute/private/new-h4-numerical-report.json
```

The command checks actual report bytes and code before/after calculation, emits
source/input hashes, and requires a new output. A numerical `pass` is not full H4:
precision, paired uncertainty, prospective power, measured total resource costs,
H1/H2/H3, early stability and actual locked execution remain separate. All outputs
retain `assessment_authorized=false`, `scientific_gate_pass=false` and
`main_launch_allowed=false`. Synthetic threshold/failure tests are not pilot results.
