# Joy implementation completion audit

Scope: implement Joy's pilot work until real producer data/validation is the
remaining dependency. Base `c10b678`; original SPEC and Sudarshan-owned code/log
remain intact. Fixtures are synthetic, not game/research evidence. The review-loop
baseline stays fixed across cumulative reviews; only the reviewer is delegated.

| Requirement | Current evidence | Remaining proof |
| --- | --- | --- |
| Strict RGB manifest, hashes, input allowlist and confinement | Consumer and malformed-data tests | Real S1/S2 bundle acceptance |
| Eight schedules, per-family/progress balance, all-cell exposure | Enumeration tests including 100-grid tail | Independent producer audit |
| Shared transforms/masks, actual source-coordinate raw targets | Real collator tensor tests on PNG fixtures | Real render/post-crop visibility |
| Released VideoMAE and controlled/native validation path | Pinned upstream wrapper; full 224 model forward and native crop/mask/target tests | Empirical learning on real data later |
| Complete-grid weighted updates, deterministic resume and provenance | Actual optimizer/tail/microbatch-equivalence and dropout-resume tests pass | Real S2 update/audit and intended hardware benchmark |
| Runnable pretraining/reference configuration and CLI | Fixture CLI creates/validates 8 grids, updates and resumes; slot/resource tools | Documented operator smoke, source/readout end-to-end checks, real admission |
| Causal evaluation assembly and all seven diagnostic modes | v2 input checks, final-frame access and arbitrary bag permutation tests | Full seven-mode runnable handoff and S3 visual solvability |
| Frozen attention heads, readout training and prediction exports | Fit/predict/export tests; backbone unchanged; explicit missing rows | CLI fit/predict integration and label-budget/horizon checks |
| SSv2 internal partitions and frame/image adapters | Deterministic partitions/group check and frame assembly tests | Decoder and pinned external model path; real S split agreement later |
| Pilot slots/coverage/admission guards and handoff commands | Exact 360-head/23-training/7-diagnostic inventory and bounded admission | More negative admission tests and complete producer-facing guide |
| Independent implementation/research review and CI | Pending | Cumulative baseline review/fix loop, final local/remote checks |

V-JEPA, extra families, independent corpus and capacity replication are main-stage
work after the pilot, not silently counted as implemented by the VideoMAE path.
A passing fixture pipeline cannot establish visual solvability, useful transfer,
renderer fidelity, or statistical power. Those need the real H1–H4 evidence.
