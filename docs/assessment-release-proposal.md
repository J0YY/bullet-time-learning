# Selected pilot assessment release policy

This resolves a timing conflict in [pilot v1](pilot-plan.md): H3 must pass before
expansion, while H4 measures later pass-20/fixed-reference outputs, and the current
text permits only one assessment inspection per version. Joy selected the two-stage option on October 31, 2026. This policy is a
protocol amendment, not an actual version lock or data-release receipt.
No assessment data or scores have been produced or opened.

## Selected: two locked stages using the existing pilot pool

Keep the current 400 assessment episodes per game task: 200 complete collision
pairs, 200 complete order pairs and 400 tracking episodes. Both stages use this
same pool; this is explicitly a reused exploratory pilot assessment, never an
independent replication or a final confirmatory test.

1. Finish development selection, including the three-slot early screen and the
   seven supervised diagnostic recipes. Use only training/internal-development
   outcomes. Count all tuning/failed attempts. H1/H2, the complete pretraining
   corpus and resources are still required for the early screen.
2. Before any assessment predictions are scored, lock the whole pilot version:
   code/runtime, data/split/admission hashes, all pretraining and head recipes,
   seeds, budgets, thresholds, expected slots, failure/retry policy and both stage
   inventories. Bind the already-trained diagnostic checkpoints and early-screen
   resume points. Future checkpoint bytes cannot be known yet: bind their exact
   planned recipe/seed/pass/source identities now, then append their actual hashes
   without changing slots or recipes. Record failure instead of substituting a model.
3. **H3 release, once:** infer and score all seven locked supervised diagnostics
   on the complete declared assessment examples. Apply the existing collision,
   order and tracking thresholds. Missing/failed predictions mean incomplete;
   an unsuccessful/incomplete H3 prevents expansion. Retain results. Repairs or
   outcome-driven changes require a new version and a fresh assessment pool.
4. **Fixed execution:** if H3 and early stability pass, run the already-locked
   remaining training and frozen-head fits. No capacity, hyperparameter, seed,
   task, subset or budget selection may use H3 outputs. Fitting jobs cannot read
   assessment inputs/labels, original reconstruction material or prior scores.
   Exact infrastructure retries use the declared recovery policy and same bytes.
5. **H4 release, once:** score all declared pass-20/fixed-reference game heads on
   the complete pool. This is 243 game head slots: 162 controlled, 18 native,
   27 image-MAE, 27 untrained and 9 external-image reference heads. Early-screen
   heads and every SSv2 head remain development-only. Keep all failed/missing slots
   and the existing H4 interpretation/exit rules. No repeated assessment tuning.

This changes release timing, not the 360 frozen-head fits, seven diagnostic fits,
400 assessment episodes/task, gate thresholds, seeds or training exposure. The 243
H4 game slots are a subset of the existing 360 fits: the remaining fits are 36
early-screen heads plus 81 pass-20/fixed-reference SSv2 heads. Reusing a fitted
reference by exact hash does not create another fit.

The implementation must enforce monotonic states: development → locked → H3
released → H3 passed → H4 released → closed. A failed H3 closes the version without
H4. Each stage needs its own immutable expected-key inventory, frozen prediction
bytes, score receipt and one-time release record; repeat commands may retrieve an
identical receipt but cannot reveal another set of predictions. Interrupted jobs
do not reset release state. The assessment scorer remains disabled until this
policy is implemented and tested, with real data/execution prerequisites admitted.

## Unselected alternative: separate H3 and H4 pools

Use 400 episodes/task for H3 and a separate 400/task for H4, with disjoint lineage,
assets/trajectories and actual pixel admission across both pools and every other
split. This keeps the H4 pool uninspected after H3, but adds 1,200 game assessment
episodes plus rendering, admission and storage. It requires an explicit count-plan
version; do not silently split the existing 400 into smaller, less precise pools.
The same recipe/slot lock and fresh-pool rule after repairs still apply.

## Common boundaries

Joy operates the workflow; Sudarshan's review is nonblocking and grants no release
authority. Preserve private nonces and opaque IDs, deny every private/reconstruction
copy, validate the actual execution boundary, and keep labels only in scoring.
Same-person operation is not human blinding. Neither option changes eventual
final-test isolation or establishes CVPR novelty, sensitivity or useful learning.
