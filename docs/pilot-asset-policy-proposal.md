# Pilot asset-group definition — decision needed

The [current pilot plan](pilot-plan.md) says asset groups never straddle splits.
[The actual request audit](../reports/data/pilot-asset-sharing-audit-20261031.json)
finds that grouping by whole palette configurations does not hold out every
individual rendered asset. The exact target sphere geometry/material appears in
600 train groups, 200 dev groups and 16 groups of the current assessment prefix.
The tracking roof appears in 600 train groups, 200 dev groups and eight assessment
prefix groups. Primitive geometry is also shared; category sharing alone is not
leakage. No model outcomes or assessment labels were inspected for this audit.

This does not invalidate the completed RGB/physics/duplicate checks. It prevents
calling those checks common semantic asset-lineage admission. Full assessment
capture has not started. Implementation and recovery checks can continue while
this definition is resolved; Sudarshan is not a required dependency.

## Option A — explicit shared fixtures in the controlled pilot (recommended)

Keep the current data for the exploratory feasibility pilot. Define an episode's
asset group as its complete procedural appearance configuration. Explicitly list
fixed target/roof components and shared engine primitives as common fixtures,
excluded from a claim of individual-asset holdout. Continue splitting the varying
appearance/configuration/trajectory prototypes and related episodes together.

Proposed addition to SPEC §11 and the pilot data section:

> The exploratory arena pilot shares its fixed target and occlusion-roof fixtures
> across readout splits. Its varying procedural appearance configurations remain
> grouped by split. This pilot tests controlled history sensitivity and training
> feasibility; it does not establish generalization to held-out individual assets
> or layouts. Before the main study's stronger claim, implement and audit separate
> held-out asset/layout groups under SPEC §4.

Also qualify the pilot sentence about asset groups to refer to varying procedural
appearance configurations, with the explicit fixture exception. Record the exact
shared descriptors in the admission report. No counts, frames, labels, H3/H4
thresholds or stored RGB change. Full joint lineage still requires a common
canonical descriptor for the varying groups; this choice alone is not admission.

## Option B — distinct individual asset variants already in the pilot

Keep the stricter interpretation: each individual task asset's geometry/material
combination must be disjoint across pretraining/train/dev/assessment, while base
primitive categories may be common. Add varying, split-grouped target and roof
appearances to the producer before any research fit; retain exact within-pair
matching. Audit every role through a common representation across both producers.

This requires re-rendering the affected train/dev measurement set (all 1,600 groups,
41,200 images), its assessment prefixes and the remaining assessment source. Keep
old artifacts and integration evidence as historical versions; rerun native,
opaque, cross-pool and sensitivity checks on the new data. No research learning
runs need to be discarded because none have occurred. This costs additional local
rendering and still does not by itself prove held-out primitive/mesh-family transfer.

## Pending authority

Neither option is adopted here. The original specification remains in Git and the
current SPEC/pilot files are unchanged. Joy's choice is needed because the existing
asset-group wording and implemented palette grouping admit different scientific
claims. Do not use elapsed time or silence as approval, and do not claim independent
collaborator review. No assessment score or version release has occurred.
