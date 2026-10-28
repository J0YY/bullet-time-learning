# Bullet-time: specification and CVPR feasibility audit

**Date:** 2026-10-28, America/New_York. **Reviewer:** Joy's coding agent, at the
user's request. **Base:** `d9ec3a8`. This is a source-backed self-review, not an
independent collaborator review, empirical result, or acceptance prediction.

## Judgment

**Proceed with a bounded validity pilot. Do not commit to the full study or promise
CVPR 2027 from the present state.** The question is coherent and the exact-image
control is useful. Novelty is narrower than the title suggests, and success depends
on showing that the comparison teaches us something beyond synthetic-motion and
multiview learning already established in the literature.

The original spec is unusually careful about many failure modes: per-update
exposure, contextual targets, valid history pairs, order-required diagnostics,
frozen readouts, weak nulls, and power. Those strengths survive this audit. The
largest risks are useful frozen transfer from a small synthetic corpus, learning
under the controlled recipe, and the breadth/cost of the global null claim.

For the immediate cycle, the official CVPR 2027 registration and paper deadlines
are **November 10 and November 16, 2026, 11:59 PM AoE**, respectively. November 16
is 19 calendar dates after October 28. There is currently no game scene, corpus,
training runner, measured throughput, transfer result, or power estimate. Completing
all scientific gates, replications, analysis, and writing in that interval is not
a credible planning assumption. This is an execution judgment, not proof that an
exceptionally fast narrower study is impossible. [Official dates](https://cvpr.thecvf.com/Conferences/2027/Dates),
[call for papers](https://cvpr.thecvf.com/Conferences/2027/CallForPapers).

The topic fits CVPR's representation learning, video understanding, and vision/
graphics scope. The 2026 reviewer guidance supports knowledge advances without
requiring a new benchmark record; it does not guarantee significance for this
particular null. The 2027 reviewer-guideline URL was inaccessible during this
audit, so 2026 guidance is treated as precedent, not a verified 2027 review rule.
[2027 scope](https://cvpr.thecvf.com/Conferences/2027/CallForPapers),
[2026 reviewer guidance](https://cvpr.thecvf.com/Conferences/2026/ReviewerGuidelines).

## What was checked

Read all 12 SPEC sections and every tracked scaffold file; rechecked ownership,
startup/log attribution, contracts, CI, provenance, and ignore behavior. The spec
remains byte-identical to the supplied original. Reviewed primary sources for the
closest work, searched for additional overlap, recomputed workload/TOST arithmetic,
and enumerated grid partitions independently of the nonexistent production loader.

Literature search is bounded, not a proof of absence. Queries included combinations
of exact/same images, camera/object motion, world time/viewpoint, frozen time,
multiview/temporal representation learning, and BulletTime. Relevant findings below
are supported by author papers, code, project pages, and official venue/dataset
pages; third-party search summaries were only leads.

## Findings requiring attention

### 1. Missing close work and a title collision — newly identified

**BulletTime: Decoupled Control of Time and Camera Pose for Video Generation** is
already a CVPR 2026 paper. It decouples world-time and camera control for diffusion
generation, including synthetic data with independently varied factors. Its
experiments concern generation/control, rather than the proposed fixed-objective,
identical-image regrouping effect on frozen downstream representations. It does
not eliminate the proposed study, but omitting it would make the novelty review
look incomplete and the current title confusing. [Paper, §§3.4–4.3](https://arxiv.org/html/2512.05076v1),
[author project page](https://19reborn.github.io/Bullet4D/).

Also add **FL4N**, posted October 26, 2026. It adds a dynamic encoder to a pretrained
static representation for 4D novel-view synthesis and probes temporal matching,
tracking, and depth. Thus “4D learning plus downstream probes” is also insufficient
as our distinguishing claim. Its architecture, supervision, initialization and
comparison differ from our experiment. [FL4N, §§3–4.2 and Appendix E](https://arxiv.org/html/2610.35854).

**Recommendation:** use a working manuscript title such as *Same Images, Different
Experience: World-Time versus Viewpoint Pretraining*. Keep the repository name if
convenient. Cite both papers and explain the experiment-level difference. This audit
does not silently rename the original spec or treat a title change as new science.

### 2. Reference-relative equivalence is not all-pairs interchangeability — wording gap

The spec's concrete null sentence is correctly relative to View. Its broader
“choosing among” / “all families as interchangeable” language needs the same scope.
If A is −0.9 points from View and B is +0.9, both are within ±1 of View, but they
differ by 1.8. Neither 30 nor 70 View-relative contrasts establishes that every pair
is within the same margin.

Keep the proposed claim explicitly **equivalence to View**. If all-pairs equivalence
is desired instead, six coherent arms produce 15 pairwise contrasts, yielding 90
components across objectives/primary endpoints, or 210 for the all-family version.
That is a different preregistered claim with a different power burden; do not add
it after results. The current counts remain correct for their original scope.

The intersection–union rule itself is sound: if the global claim is false, at
least one component null is true, and passing every component entails rejecting
that true null. Therefore no Bonferroni correction is needed for this one global
conjunction. Individual selected equivalence/superiority claims are separate.
TOST at alpha .05 uses component 90% intervals. [Lakens, 2017](https://pmc.ncbi.nlm.nih.gov/articles/PMC5502906/).

### 3. External evaluation partition is underspecified — newly verified dependency

Something-Something V2 provides 168,913 training and 24,777 validation videos;
its 27,157 test videos have no released labels on the official page. “Standard
split” plus “choose on development before opening test” is not yet an executable
protocol for per-video analysis. [Official dataset information](https://www.qualcomm.com/developer/software/something-something-v-2-dataset).

Before readout tuning, choose and hash a concrete arrangement. One option is a
development holdout inside official training, with official validation reserved
for final evaluation; describe it accurately as official-validation evaluation,
not official test. Alternatively verify a usable official-test evaluation service
and its outputs. Keep label budgets, competence thresholds and tuning separate
from the final set. Do not use official validation for both model selection and
the supposedly untouched confirmation result. No partition was chosen in this audit.

### 4. Forecast time and tracking access need precise contracts — implementation gaps

SPEC §5 varies the interval for **pretraining**. It does not fix the evaluation
cadence for the half-second forecast in §7. Do not silently reuse variable cadence
while providing only RGB: the same displacement per frame can imply different
physical speeds at different intervals. Identical permitted image histories could
then require different half-second labels. Fix evaluation cadence, or explicitly
revise allowed inputs to provide timing. This is a risk to prevent, not a claim
that the currently nonexistent evaluation set is already invalid.

Define whether the tracking window ending at prediction time includes the current
RGB frame. Standard online tracking can use that frame without future leakage;
literal “preceding frames” could instead implement forecasting. Pin query-reference
access, the three reappearance frames, point/bounding-box coordinates, visibility
threshold, and small-object exclusion/strata before generation and scoring.
Likewise fix how a video backbone receives a single-image spatial-control input.

### 5. Learning and frozen transfer are the largest scientific risks — already recognized

Three million views do not provide three million independent scenes. The plan has
12,000 grids, potentially fewer independent rollouts if windows are reused, from
three related mechanics. Its action-transfer domain includes human-object actions
not directly covered by those worlds. Large labeled readouts may also learn motion
from untrained features; that is why the spec's identical-head references matter.

PMG reports weak frozen linear transfer and discusses limited semantic features;
SMILE shows that synthetic motion can train useful representations, but its
reported synthetic-data results do not guarantee our frozen-transfer protocol.
These are motivation for early testing, not predictions of failure.
[PMG, Appendix H](https://arxiv.org/html/2409.06665),
[SMILE, Appendix D](https://arxiv.org/html/2504.00527).

Test native versus controlled VideoMAE early, including readout competence and
background/foreground contribution. Raw reconstruction can reward easy background
pixels; inspect that before interpreting a temporal tie. Check V-JEPA separately;
success of one objective does not validate the other. Its original masking ablation
shows that substituting random tubes for its block masks can materially harm
features. [V-JEPA, §4.4](https://arxiv.org/html/2404.08471).

### 6. Statistical scope is expensive even though the arithmetic is correct

Recomputed exact Gaussian paired-TOST power at true difference zero and ±1 point:

| Paired run SD | Power with five seeds | First n reaching at least 80% for one contrast |
| --- | --- | --- |
| 0.5 pp | 94.996% | 4 (82.777%) |
| 1 pp | 29.385% | 11 (84.900%) |
| 2 pp | 2.028% | 36 (80.515%) |

The original rounded examples are correct. They do not establish power for the
30/70-component conjunction. As an illustration only, 30 independent components
each with 95% power all pass with probability 21.46%; for 70 it is 2.76%. Actual
contrasts share View, seeds and tasks, so independence is not their forecast.
Estimate/simulate the joint distribution conservatively before choosing a budget.

Test-set precision matters separately. For a simplified paired binary success
comparison with zero mean difference, 20% discordant outcomes and 1,000 independent
episodes, a normal-approximation 90% interval has half-width about 2.33 pp. That is
already wider than a ±2 pp per-family target, before additional clustering. This
illustration is not a measured discordance or the full balanced-accuracy analysis.
Increasing training seeds does not eliminate limited test-sample information.

### 7. Compute scenarios are not a capacity plan — already recognized

Verified: 3,072,000 RGB images, 462.422 decimal GB raw RGB; 38.535 GB for 1,000
grids; 192,000 clips/pass; 3.84 million clips/run at 20 passes. Eighty main runs
require 853.33 GPU-hours at 100 clips/s or 4,266.67 at 20 clips/s. These rates are
hypothetical. With eight perfectly utilized GPUs those correspond to roughly
4.44 or 22.22 days of main training alone; rendering, tuning, readouts, references,
replications, failures and writing are additional. V-JEPA and VideoMAE need their
own measurements. Render arithmetic is 85.33 hours at 10 images/s or 853.33 at 1.

No resource allocation or throughput was validated. Even plentiful GPUs would
not remove sequential data-validity, learning, transfer and protocol decisions.

## Novelty audit: what remains after the closest comparisons

| Primary source inspected | What overlaps | What differs in the proposed study |
| --- | --- | --- |
| [VITO, §4.3/Table 4](https://arxiv.org/html/2210.06433v3) | Same-frame versus temporal-deformation learning | No exact common RGB grid regrouped into camera versus world-time clips |
| [PMG, §§4.4/4.7 and H](https://arxiv.org/html/2409.06665) | Synthetic motion, mixing, limitations of frozen transfer | Image content and construction differ between its alternatives |
| [SMILE, D/E.1](https://arxiv.org/html/2504.00527) | Synthetic local motion, feature/pixel targets and budget checks | Not the proposed common-image traversal intervention |
| [4Real-Video, §§3–4.3](https://arxiv.org/html/2412.04462v1) | Explicit time/view grid and frozen-time generation | Generative architecture/synchronization study rather than this representation-learning intervention |
| [BulletTime, §§3.4–4.3](https://arxiv.org/html/2512.05076v1) | Separate world-time/camera controls and synthetic data | Generation/control objective and metrics; important missing citation/title collision |
| [SDM/ProbeMotion, §§2–3, A.1](https://arxiv.org/html/2607.21576v1) | Camera/object dynamics, synthetic supervision, separate probes | Frozen image backbone and structured model; static/dynamic scenes differ in content |
| [TCN, III-A/IV-A](https://arxiv.org/html/1704.06888) | Simultaneous views and temporal relationships | Different positive/negative roles and multiview/single-view objectives |
| [CroCo, §4.1.1/C.2](https://arxiv.org/html/2210.10716) | Cross-view completion and overlap sensitivity | Supports View as a plausible endpoint; not this matched time/view training comparison |
| [SiamMAE, §4.3](https://arxiv.org/html/2305.14344) | Video-pair correspondence, gap and masking ablations | Different asymmetric pair objective; no same-grid viewpoint alternative |
| [W2Rep, §4.3/C–E](https://arxiv.org/html/2609.35464v1) | Common-budget same/cross-frame objectives and order diagnostics | Same-frame endpoint also removes context; no proposed camera grouping retraining |
| [TDV, §4.3](https://arxiv.org/abs/2606.15956) | Dynamics-based representation objective | Different learning rule; no evidence here of this exact comparison |
| [FOFPred, Table 6](https://arxiv.org/html/2601.10781) | Static, raw-motion and separated-motion targets | Changes supervision/targets in a language-conditioned forecasting system |
| [ActiveMimic, §§4.1–4.5](https://arxiv.org/html/2606.06194) | Camera-motion supervision and robotic transfer | Active perception/action learning, not fixed-RGB masked pretraining arms |
| [FL4N, §§3–4.2/E](https://arxiv.org/html/2610.35854) | Static/dynamic representations with downstream motion/geometry probes | Pretrained static model plus dynamic architecture/supervision; not this controlled traversal comparison |

**Defensible novelty:** an empirical estimate of changing the relationships among
identical rendered observations under a fixed objective and matched exposure,
including mixtures and joint motion. I did not find an exact duplicate in the
comparisons inspected. That is a scoped search conclusion, not certification that
no such work exists. The broad concepts and ingredients are established.

The controlled treatment changes motion, overlap, occlusion, token pairing and
prediction difficulty together. That does not invalidate its total effect; those
are part of the treatment. It prevents a conclusion that the effect uniquely
measures physical understanding. A weak tie or an obvious task-specific advantage
on one tiny world would have limited significance even if technically new.

The strongest useful outcomes would be reproducible effects or tradeoffs that
change how one allocates a fixed training budget, or a precise reference-relative
bound after demonstrated grouping sensitivity and useful external transfer. The
spec already gives the null more demanding validity gates. Preserve them instead
of treating all possible outcomes as equally strong papers.

## Recommended next decision and work order

1. **Keep the controlled question; narrow the initial commitment.** One scene,
   one objective, an audited real update, valid history/order/tracking data.
   A small engineering screen may precede the declared 18-run pilot but cannot
   support final superiority/equivalence claims or replace its paired-seed design.
2. **Resolve inputs and external partitions before labels/tuning.** Joy defines
   readout timing and final-evaluation access; Sudarshan binds them to generation,
   split and label manifests. Explicitly state reference-relative claim scope.
3. **Measure learning and transfer before expanding the matrix.** Compare controlled
   and native recipes, common-head untrained/image-only references, coherent and
   disrupted arms, and development transfer. Keep thresholds fixed before checking
   the corresponding confirmation set; record failures without changing the question.
4. **Calculate affordable precision from measured variability and throughput.**
   Include test episodes, paired runs, references, readouts, replication and failed
   work. Do not set n=5 because the resulting 80-run matrix looks manageable.
5. **Make a venue decision from evidence.** If the first gates fail, repair or stop
   expansion. If they pass, freeze the affordable claim and proceed regardless of
   which arm wins. For a broad null, retain independent-corpus and budget/capacity
   checks. Do not schedule the full unbuilt program around November 16 by assumption.

No new protocol, final split, numeric competence threshold, budget, title, compute
host or submission commitment is adopted by these recommendations. The original
spec is preserved; this report records what needs clarification before execution.

## Repository verification and reproducibility

No material ownership/collaboration defect or imported research policy was found.
The original spec SHA-256 remains
`e543446ddf6466e07cbf545a402092ebe2f5d6a6a43465472bd41c4e693fb9de`.
The setup checker passed at audit start: 18 required files, 13 Markdown files,
50 local links and 32 ignore checks. New report links are checked again at completion.

[audit_spec.py](../scripts/audit_spec.py) reproduces 163 valid partition checks,
including all 16 four-pass orientation assignments, both Joint directions and
sampled disruption partitions; it also computes workload/contrast counts. Optional
`--power` integrates the exact Gaussian TOST power with SciPy. Results and source/
script hashes are in [spec-math-audit.json](spec-math-audit.json).

```bash
python3 scripts/check_scaffold.py
python3 scripts/audit_spec.py
python3 scripts/audit_spec.py --power
git diff --check
```

Power calculation was run with Python 3.14.3 / SciPy 1.17.1 already available
locally. No dependencies were installed and no model/GPU/renderer experiment was
run. Enumeration does not test a production loader, mask collator, renderer replay,
distributed gradients, or teacher updates. Original VideoMAE code does confirm
two-frame target normalization; disabling it needs real learning validation.
[Official target code](https://github.com/MCG-NJU/VideoMAE/blob/main/engine_for_pretraining.py).

Completion checks at substantive audit commit `af32b16`: clean-clone scaffold
validation passed (14 Markdown files, 60 local links, 32 ignore cases); regenerated
standard-library calculations match the stored JSON; SPEC and Sudarshan's log
match their pre-audit bytes. A separate direct Gaussian Monte Carlo check with
200,000 draws per SD and RNG seed 20261028 yielded powers 0.95003, 0.29303 and
0.01955, agreeing with quadrature within 0.004. This is mathematical simulation,
not empirical training. Python parsing, tracked-size/credential-pattern checks and
full-tree whitespace validation passed.
[GitHub CI 40758307456](https://github.com/J0YY/bullet-time-learning/actions/runs/40758307456)
passed both scaffold and arithmetic checks on Linux/Python 3.12. Final completion
documentation receives another exact-commit CI/remote check before handoff.
