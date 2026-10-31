**Working paper title: Same Images, Different Experience: World-Time versus Viewpoint Pretraining**

**Revision 1 — 2026-10-28.** “Bullet-time” remains the repository nickname. This revision adopts the audit fixes and a bounded pilot plan at Joy's request; it is not a final-study freeze or evidence that the pilot works. The original supplied specification is preserved byte-for-byte in Git at `13e951dcbc02d94734241034ff85bbc56d530fa6:SPEC.md`; provenance is in [reports/spec-source.json](reports/spec-source.json). Scientific changes are recorded in [reports/decisions.md](reports/decisions.md). [The pilot plan](docs/pilot-plan.md) and its [planning manifest](configs/pilot-plan.json) make the initial implementation choices and owner handoffs concrete. These selected pilot defaults supersede generic starting suggestions below only for the pilot.

Imagine a game in which a ball is about to hit a stack of boxes. There are two ways to watch the scene. We can leave the camera still and watch the ball knock the boxes over. Or we can pause the game at one moment and move the camera around the frozen scene, as in a bullet-time shot. Both sequences contain visual change, but the change comes from different sources.

Bullet-Time Learning asks whether those two kinds of experience teach a vision model different things. More specifically, if two models see exactly the same images, does the model that sees them connected through time learn something useful that the model seeing them connected through viewpoint does not? A vision model here means a neural network that turns images into internal features, such as information about an object's shape, location, or movement. We judge those features by how useful they are for new tasks.

This is a viable pilot, but it is not yet a fully validated CVPR study. The useful contribution would be a controlled comparison of two ways to organize the same visual experience. The experiment can estimate their effects on learned representations; it cannot, by itself, separate physical understanding from geometry or prove why either representation works. The full study should proceed only after the pilot shows that the comparison is informative, the models learn, and the required precision is affordable.

A benefit from Time, a benefit from View, and a precise finding of practical equivalence could each be useful. They would not automatically be equally important papers. In particular, a tie becomes interesting only when the models use the training relationships, the evaluation needs temporal evidence, and the finding transfers beyond a small synthetic task. If those conditions fail, the result may be valid but too limited for a strong CVPR paper.

The proposed settings below are starting specifications, not completed experiments. The literature assessment covers the papers located and checked through October 28, 2026; it does not establish zero novelty risk.

# 1 The question and why it matters

When a model learns from video, several things change at once. It sees more images of the same objects, sees them from different angles, watches objects become hidden and visible again, and observes events unfolding. An improvement after video training therefore does not, by itself, tell us which part of that experience caused the improvement.

This distinction matters because two plausible explanations lead to different training choices. One is that video mainly teaches correspondence: recognizing that something in one image is the same thing in another image despite changes in its appearance. Another is that relationships between successive world states provide an additional useful signal. For example, seeing a ball before and after a collision could teach something that seeing the same frozen ball from several angles does not.

The experiment asks how much the second kind of relationship adds once the collection of individual images is fixed. The practical decision is how to organize training examples in a controllable visual dataset: spend the same learning budget on viewpoint relationships, temporal relationships, or a mixture. The scientific question is whether a model's useful knowledge depends on those relationships beyond the states and appearances it has already seen.

“Fixed images” is important here. The viewpoint condition will still see pictures of falling boxes, contact, and completed collisions. It will simply encounter each state through a camera sweep rather than through the sequence that connects it to the next state. Therefore a null result would concern the added value of temporal relationships. It would not show that images of dynamic events are unnecessary.

There is also a limit to the gaming claim. Games give us access to world states and camera positions that ordinary recorded video does not provide. However, this experiment does not require the learning model to choose game actions. Scripted gameplay can supply the events. It is a study of visual learning using controllable game worlds, with an optional test of gameplay performance, rather than a benchmark of autonomous computer use. A simulator with equivalent control could also support it.

# 2 What the closest papers already establish

The fair novelty test is whether earlier work has already answered this comparison, rather than whether it contains cameras, time, synthetic data, or related losses. Several papers establish important pieces. They should shape the design rather than become reasons to dismiss it automatically.

## VITO already tests the value of temporal variation

VITO compares its video representation learning method with a same-frame condition, among other ablations. In Section 4.3 and Table 4, its full VideoNet condition outperforms the T = 0 condition on several transfer tasks. This is relevant evidence that relationships across video frames can help. However, those relationships include viewpoint changes, object motion, and other changes together. The ablation does not provide a matched alternative in which the same rendered images are grouped by viewpoint instead of world time. Bullet-Time Learning would ask which kind of relationship supplies the benefit, rather than repeat the claim that temporal variation can help. [VITO paper, Section 4.3 and Table 4](https://arxiv.org/html/2210.06433v3)

## Synthetic motion is a serious alternative explanation

Data Collection-free Masked Video Modeling creates videos by transforming static images. It also tests mixtures with real video in Section 4.4 and relates performance to frame differences in Section 4.7. SMILE adds synthetic local motion and feature targets; its Appendix D studies training without natural videos, while Appendix E.1 controls training iterations across dataset sizes. These results already make “synthetic movement can teach useful video features” an insufficient contribution. [Data Collection-free Masked Video Modeling](https://arxiv.org/html/2409.06665), [SMILE](https://arxiv.org/html/2504.00527)

The remaining question is more specific. Those comparisons change image content, training ingredients, or both. Here, the rendered image collection stays identical while its organization changes. That removes an important alternative explanation for a difference. A tie would establish a bound on the benefit of temporal grouping in this setting; it would not, by itself, identify correspondence learning as the reason.

## The time and viewpoint grid is established

4Real-Video explicitly arranges frames along time and viewpoint axes, including freeze-time and dynamic videos. Its Section 4.3 compares generation architectures, synchronization choices, and training data. The grid itself is therefore not a novel contribution. What differs here is its use as an experimental control for representation learning: train separate models on different traversals of the same grid and measure their transfer to new visual tasks. Generation quality and downstream representation quality are different outcomes. [4Real-Video, Sections 3 and 4.3](https://arxiv.org/html/2412.04462)

## BulletTime and FL4N further limit the novelty claim

BulletTime, a CVPR 2026 video-generation paper, already uses synthetic camera/time variants and disentangled controls. Its name also makes “Bullet-Time Learning” an ambiguous paper title. The working title above emphasizes the actual intervention. Our proposed outcome is frozen representation transfer after retraining with different groupings of the exact same RGB cells, rather than controllable video generation. The camera/time construction alone is not new. [BulletTime author page](https://19reborn.github.io/Bullet4D/), [paper, Sections 3.4–4.3](https://arxiv.org/html/2512.05076v1)

FL4N (October 2026) learns 4D representations with static and dynamic encoders, using pretrained static features and novel-view synthesis with additional supervision described in the method. Its temporal matching, tracking, and depth evaluations overlap our proposed probe categories. Thus “4D representations plus temporal/spatial probes” is not a contribution by itself. The remaining hypothesis is the exact-image, fixed-objective regrouping comparison, with matched update exposure and useful frozen transfer. This is a bounded comparison of located sources, not proof that no equivalent experiment exists; refresh the novelty ledger before substantial training. [FL4N, Sections 3–4.2 and Appendix E](https://arxiv.org/html/2610.35854)

## Camera and object motion have already been separated

The 2026 Structured Dynamics Model paper is especially close. It uses frozen image features, motion extraction from frame pairs, and weak synthetic supervision to structure camera and object motion. Its ProbeMotion suite evaluates these factors separately. Appendix A.1 describes static scenes without foreground objects and dynamic scenes with one moving object; its ablations concern supervision, architecture, data, and related choices. It does not report the exact-image regrouping experiment proposed here. Separating motion types or releasing probes therefore cannot carry our novelty claim. [SDM and ProbeMotion, Sections 2–3, Appendices A.1 and B.5](https://arxiv.org/html/2607.21576)

## Multiview learning and video correspondence are also established

Time-Contrastive Networks use simultaneous viewpoints as positive examples and temporal neighbors as negatives, and compare multiview and single-view variants. This is a substantial precedent for treating viewpoint and time differently. But it changes the learning relationships and their roles in the objective; our main comparison keeps the training rule fixed. [Time-Contrastive Networks, Sections III-A and IV-A](https://arxiv.org/html/1704.06888)

CroCo learns through cross-view completion and studies actual 3D views versus synthetic transformations, including the importance of overlap. SiamMAE learns correspondence from video frame pairs and studies masking, architecture, and sampling gaps. These papers make both endpoints credible. They also warn that a difference could reflect overlap or task difficulty rather than a special understanding of physics. Neither comparison is the proposed common-image, common-training-rule experiment across time and viewpoint. [CroCo, Section 4.1.1 and Appendix C.2](https://arxiv.org/html/2210.10716), [SiamMAE, Section 4.3](https://arxiv.org/html/2305.14344)

## Newer temporal studies narrow the claim further

W2Rep compares same-frame and cross-frame objectives under controlled training settings and tests reversed and shuffled clips. Its same-frame endpoint also changes conditioning, and its order interventions inspect a trained model rather than retrain on the proposed viewpoint alternative. This makes “hold the data fixed and study time” too broad a novelty claim. [W2Rep, Section 4.3 and Appendices C–E](https://arxiv.org/html/2609.35464)

Temporal Difference in Vision models changes between frames and reports component ablations. FOFPred compares static, raw-motion, and disentangled-motion targets. ActiveMimic isolates camera-motion supervision in egocentric pretraining. These establish that the objective and the treatment of motion can matter. Our question concerns the value of the training relationships under a fixed objective and fixed image exposure, not whether motion supervision is useful in general. [TDV, Section 4.3](https://arxiv.org/abs/2606.15956), [FOFPred, Section 4.3 and Table 6](https://arxiv.org/html/2601.10781), [ActiveMimic, Sections 4.1–4.5](https://arxiv.org/html/2606.06194)

V-JEPA is also a close methodological warning. Its masking ablation compares causal masks with masks that predict regions using context from across the clip; its frozen evaluation compares readout designs. Those results show that prediction difficulty and access to learned features matter. They do not compare world motion with camera motion under identical image exposure. Our two objectives are masked prediction methods, not necessarily methods that learn to forecast the future. [V-JEPA, Sections 4.3–4.4](https://arxiv.org/html/2404.08471)

## The claim that survives this comparison

The defensible contribution is a controlled estimate of the effect of grouping identical rendered images by world time, camera position, or both, under a fixed learning rule and training budget. The study also tests whether mixing these experiences helps. The effect includes changes in motion, visibility, and prediction difficulty produced by the grouping.

I did not find that joint experiment in the closest papers examined. That is a reason to proceed to a pilot. It is not a reason to claim that the general idea of learning from time versus viewpoint is new. The project earns significance through the clarity and breadth of the answer, not through inventing the grid.

# 3 The experiment in plain language

Return to the ball and boxes. Save the scene at sixteen moments during the event. At each saved moment, render the scene from sixteen camera positions. This produces 256 images.

The table below shows a smaller version with three moments and three cameras. Each cell is one image.

| World state | Camera A | Camera B | Camera C |
| - | - | - | - |
| Before contact | Before contact from A | Before contact from B | Before contact from C |
| At contact | Contact from A | Contact from B | Contact from C |
| After contact | After contact from A | After contact from B | After contact from C |

Reading across a row produces a camera sweep around a frozen event. Reading down a column produces an event unfolding from a fixed camera. Both ways of reading the table use the same nine images. In the actual dataset, both use the same 256 images.

Call the first condition **View** and the second **Time**. View receives sixteen clips of sixteen camera positions. Time receives sixteen clips of sixteen world states. Neither receives camera coordinates, velocities, object identities, or labels during pretraining. Those records are retained for evaluation and data checks.

The comparison also includes three mixtures: 25%, 50%, and 75% Time. The percentage describes the share of training grids presented as temporal clips. A mixture does not get more images, longer clips, or extra training. It exchanges some viewpoint relationships for temporal relationships.

Include mixtures because an endpoint tie can coexist with a gain from mixed training. Such a gain would show that alternating the two experiences is useful under the chosen recipe. It would be consistent with complementary signals, but could also involve optimization or regularization; the score alone would not identify the mechanism.

Add a **Joint** condition in which the world and camera move together within each clip. This is different from a mixture, which alternates between two kinds of pure clips. Joint tests whether the combination within a single observation supplies useful information that neither pure experience nor their mixture provides.

The intervention changes which images occur together and in what order. It changes motion magnitude, overlap, occlusion, and reconstruction difficulty as well. These are consequences of the intervention, not separate factors that the design has held constant. Therefore, call the result an effect of training experience. Shuffling supplies a useful disruption control, but it also changes local displacement and adjacent-frame content; it is not a clean intervention on chronological knowledge alone.

# 4 Keeping the comparison genuinely matched

The most important implementation rule is to render each image once and reuse the saved file in every condition. Rendering separate copies for View and Time could introduce differences in noise, lighting, or simulation state. A manifest should assign every image an episode identifier, world-state index, camera index, and content hash.

One training unit is a complete sixteen-by-sixteen grid. Construct all sixteen rows for View or all sixteen columns for Time. Accumulate gradients over complete grids and update the model only after the same grid set has been processed in each condition. Normalize the loss over all contributing clips or patches, rather than adding unweighted microbatch means. Advance the optimizer, learning-rate schedule, and feature teacher once per complete update. The backbone must not exchange information between clips through cross-clip attention or batch-dependent normalization.

Joint requires a closed camera path whose positions, orientations, and closing motion are smooth. For each starting camera phase, traverse world time from 0 to 15 while advancing the camera around that loop. Include all sixteen phases, so every state–camera pair appears once. Balance clockwise and counterclockwise traversal across grids using a recorded schedule. World time never wraps. Randomize the starting camera phase and traversal direction for View as well. This is a controlled combined-motion condition; it does not reproduce every camera trajectory found in natural video.

For mixtures, balance orientation assignments over four passes through the dataset. In the 25% Time condition, each grid is temporal on one pass and viewpoint-based on three. In the 50% condition it is temporal on two passes. Randomize the order and balance assignments across scene families and training progress, so a mixture is not accidentally “learn views first, learn time later.” Use a common episode order across conditions.

Augmentation means a training-time change such as cropping or adjusting color. Sample one spatial crop and color transform per complete grid and apply it to every cell. Share that choice across conditions using the grid identifier, pass number, and paired run seed. This preserves the exact transformed image collection as well as the raw image collection.

Share spatial transformations and mask locations across the whole grid and across matched conditions. Use a method-specific mask: VideoMAE uses its spatial tube mask; V-JEPA retains its large spatial blocks repeated through time. Do not give V-JEPA the VideoMAE 90% random mask. Audit visible and target patch indices after the actual mask collator, including any truncation. Start the renderer pilot without cropping; later crops must be shared, and foreground visibility must be measured after cropping.

Identical pixels do not guarantee identical training targets. VideoMAE's released code can normalize a target patch across two adjacent frames. Regrouping those frames would change the target values. For the primary comparison, use raw RGB reconstruction targets with `normlize_target=False` in the official implementation and fixed input normalization. Validate this choice against the native recipe on development data. V-JEPA's feature targets remain context-dependent and its teachers evolve differently across conditions; only its pixel exposure and masking are matched. [VideoMAE training code](https://github.com/MCG-NJU/VideoMAE/blob/main/engine_for_pretraining.py)

Within an objective, match the model, initialization, image resolution, clip length, optimizer, number of updates, effective batch size, mask rate, and augmentation schedule. Select one common configuration per objective using the pooled development results of View, Time, and the 50–50 mixture. Keep it fixed across the main conditions. An equal-budget, separately tuned comparison can be reported as a secondary check, but it answers a different question about each condition's optimized performance. Record actual computation and wall time as well as nominal training steps.

The automated audit must compare image identifiers and exposure counts, transformed pixel hashes, visible and target patch indices, and update boundaries. For pixel reconstruction, also verify identical per-image target values. For feature prediction, log student and teacher image exposure separately. Keep data scheduling, augmentation, and dropout on separate random-number streams so changing the schedule cannot silently change every augmentation. Match the rules and randomization; do not claim that hidden activations or teacher targets are identical.

Record overlap, visible object area, occlusion, and displacement for every condition. Prespecify sensitivity analyses over small and large camera excursions, slow and fast world motion, and different visibility ranges. A subset must retain the same complete grids in every compared condition. Selecting different images for Time and View would break the main control. These analyses can show where an effect occurs; adjusting for consequences such as optical flow does not recover a pure effect of physical knowledge.

# 5 The game worlds and the data to build

Use one instrumented, open-source game project with three scene families. The purpose of the families is to vary the visual and physical demands without turning the project into the development of three commercial games.

| Scene family | Example gameplay | What it contributes |
| - | - | - |
| Projectile arena | Launch balls toward obstacles, targets, and movable stacks | Fast motion, collisions, deflections, and interrupted trajectories |
| Moving-platform course | Traverse platforms and pass through rotating or sliding gates | Articulated movement, periodic motion, and changing support relationships |
| Object-handling room | Push objects into containers and move them behind screens | Occlusion, persistent identity, contact, and multiple independently moving objects |

Use scripted controllers to produce varied successes and failures. The learning model receives RGB images only. Hide scores, timers, text prompts, velocity arrows, and other interface elements that could reveal the answers directly. Randomize textures, lighting, layouts, object sizes, and camera paths independently of task outcomes.

A reasonable starting scale is 4,000 pretraining grids per family, for 12,000 total. Separately generate 600 labeled training episodes, 200 development episodes, and 1,000 final test episodes per family. The labeled episodes train the small downstream prediction heads; they are not extra pretraining data. These are initial collection targets, to be revised using pilot estimates before the final test is opened.

Split whole scene configurations, trajectories, and asset groups rather than individual frames. Put related windows from the same rollout in the same split. Maintain two test partitions: new episodes within familiar scene families, and harder episodes with held-out layouts and asset groups. Also train on two families and test on the third in a smaller replication, so apparent generality is not just texture variation within one mechanic.

For each pretraining grid, save sixteen world states at a fixed interval. Include several interval settings, initially 1/4, 1/8, and 1/16 second, balanced across conditions. Choose sixteen camera poses along a smooth path, with the same poses used at every world state. Camera paths must be sampled independently of event outcomes. Use smooth closed paths so the Joint condition can start at any phase without a camera jump. Include small oval loops, gentle out-and-back excursions, and paths with height variation as well as full orbits. A full 360-degree orbit should not be the only kind of viewpoint experience. Check the closing segment as carefully as the rest of the path.

Randomize event timing within each rollout. A collision must not reliably occur at frame eight, and elapsed time or camera phase must not reveal the answer. Check smooth camera orientation and velocity at the closing segment, not just equal endpoint positions.

Reject a complete grid if its camera path clips through geometry or the intended event is insufficiently visible. Do not rescue individual conditions by choosing different cameras or images. Record all rejection rules and rejection rates. The accepted dataset is then fixed before any comparative model training.

The rendering record should contain scene and asset identifiers, simulation seed, action script, object transforms, velocities, articulation states, camera matrices, timestamps, and RGB hashes. Save contact events and object visibility for evaluation. Dense labels such as depth and object masks can be generated for evaluation episodes and diagnostic subsets rather than stored for every pretraining image.

# 6 The models and training rules

The main study should compare training experiences within established learning methods. Introducing a new architecture at the same time would make it harder to tell what caused the result.

Start with a small video vision transformer, initially ViT-S with sixteen-frame clips at 224 by 224 pixels. A transformer divides an image or clip into small pieces and learns how their information relates. The backbone is the part that produces visual features. During later evaluation, freeze that backbone, meaning its weights cannot change, and train only a small task-specific readout.

Use two main objectives. An objective is the rule that tells the model what it should improve during training.

The first objective is **masked pixel reconstruction**, based on VideoMAE: hide much of a clip and reconstruct its missing image patches. Use the released implementation with a 90% tube mask, the small backbone, grid-shared masks, and raw RGB targets as specified above. Record these departures explicitly and test learning against the native target-normalization recipe before the final protocol is fixed. [VideoMAE](https://arxiv.org/abs/2203.12602)

The second objective is **masked feature prediction**, based on V-JEPA. Predict features of hidden regions using a slowly updated target network trained within the same run. Keep its own block-masking and predictor design, while adapting clip construction and mask sharing to the grid protocol. Record student and teacher computation separately. [V-JEPA](https://arxiv.org/abs/2404.08471)

Both methods can predict missing regions from earlier and later frames. Neither forces the model to infer the future from the past. Agreement between them therefore supports a claim about two masked prediction methods, not all temporal learning. If neither method benefits from coherent grouping over disrupted grouping, a View–Time tie would mainly expose a limit of these objectives or this training regime. It would not establish that temporal information is unnecessary.

For each main objective, train the five Time proportions: 0%, 25%, 50%, 75%, and 100%. Include Joint as a sixth main condition, along with two disruption controls:

1. **Shuffled Time:** use the Time clips, but randomly permute their frame order during training. This preserves each clip's image membership while removing reliable chronological order.

2. **Regrouped images:** randomly divide each complete grid into sixteen clips, each containing sixteen distinct cells. This preserves exact image exposure while disrupting both coherent camera paths and coherent temporal paths.

Regrouped images still come from one event; this control disrupts coherent paths without removing every semantic association. Add a separate framewise image-MAE reference using the same RGB collection and total frame-exposure budget, with a spatial backbone of comparable width and depth. It is an interpretive baseline, not an architecture-matched causal arm. Evaluate a fixed adapter and the same readout family, document unavoidable tokenization differences, and count its compute separately.

Use random initialization for the main causal study, paired across conditions. A shared pretrained-image initialization can be a useful second study if training from scratch proves too expensive, but it changes the question to what additional experience contributes after image pretraining. If that becomes the main study, state that scope in the paper title or abstract rather than quietly inheriting a model's prior knowledge.

Start with three paired seeds in the pilot. For the main study, plan for at least five independent pretraining seeds and determine the final count from pilot variability and the desired precision. A seed identifies a separate randomized training run. The thousands of test images do not replace these independent runs.

Use a common fixed training budget within each objective. As a starting budget study, inspect learning curves at 4, 20, and 80 complete passes through the pretraining grids. Choose the main budget before final testing, using development performance and available resources. If learning is still improving substantially at the affordable budget, a null must be described as budget-specific. It cannot establish that temporal relationships offer no useful signal at sufficient training scale.

Before committing to either objective, compare the controlled recipe with its ordinary recipe on View and Time development runs. Check that grid-shared masks, raw pixel targets where applicable, the small backbone, and the effective number of independent scenes do not destroy learning or reverse the comparison. The native recipe need not satisfy the exact-image control; it is a separate validity check. If a conclusion depends on the controlled adaptation, report that dependence and narrow the claim.

# 7 The evaluation and what each task tells us

The evaluation should separate three questions: whether a model learns useful spatial features, whether it uses motion history, and whether the finding transfers outside the generated game worlds. A single average score would hide these distinctions.

All conditions receive the same downstream training examples, task heads, tuning budget, and test inputs. During the primary evaluation, the pretrained backbone remains frozen. A large head or full fine-tuning could learn the missing temporal information afterward, obscuring what pretraining contributed.

## A task that needs motion history

Create paired episodes in which the final visible image is identical but the preceding movement differs. For example, a ball can occupy the same position while moving toward a barrier in one episode and away from it in another. The next collision outcome differs, but the final picture does not reveal its velocity.

Generate both histories through valid forward simulation or controlled game movement. Do not obtain one merely by reversing footage of an irreversible event. Disable motion blur and trails for this paired test, and check the final images by hash. Matching position alone is insufficient if shadows, particles, animation phase, or other moving objects reveal the branch.

Fix evaluation physics at 64 steps/second and sample RGB every four steps (16 frames/second), independently of the variable pretraining cadence. The sixteen observed frames end at the query time and span 15/16 seconds. Quarter-, half-, and one-second horizons correspond to 16, 32, and 64 future physics steps; contact means any source–target contact in steps 1 through the horizon inclusive. Validate integration stability at this chosen step size before admitting episodes. Give the model those sixteen observed frames and two query points identifying the source object and target in the shared final image. Ask whether they will contact within the next half-second. The readout sees these points, not engine identities, velocities, or state labels. After the query, apply the same specified continuation rule: no new player commands or random draws, with moving platforms and gates continuing their recorded deterministic motion. Record this rule and cadence in the episode manifest. Cadence is fixed by task, not supplied as a variable timing channel; no timestamps or hidden state enter the model. An outcome governed by an unspecified future action is not a valid forecast target. Balance outcomes and report balanced accuracy and Brier score, which measures probability quality.

Repeat at quarter-second and one-second horizons as secondary analyses. Vary speed, contact geometry, and occlusion rather than relying on one left-versus-right rule. Hold out some trajectory families and layouts. The main result should not be explainable by memorizing a few screen positions.

Use fixed physical parameters initially. If later episodes vary hidden properties such as friction, establish that the observed history identifies what is needed for the forecast. A simulator-state oracle can check labels, but only a strong model using the permitted visual history can establish that the visual problem is solvable.

First verify that a final-frame model cannot distinguish the paired cases and that a sufficiently trained visual sequence model can. Add a mandatory diagnostic subset that also matches the unordered collection of images. For example, render an object completing one clockwise or counterclockwise circuit through the same sixteen poses, ending at the same pose, and then release it under a shared rule. Its opposite tangential velocities produce different target contacts. Keep appearance, query points, lighting, and all side information identical. Generate both trajectories forward; do not reverse an irreversible collision.

This subset makes order necessary because a bag of frames cannot distinguish its two cases. Keep each pair together in one split and verify equality of the full input multiset. Require a sequence model to solve it and a permutation-invariant readout to remain at chance. It is a diagnostic of temporal sensitivity, not the entire benchmark; ordinary game trajectories must supply the main evaluation.

## Tracking through occlusion

Mark a visible point on an object and track its identity through an occlusion and reappearance. Include distractors with similar appearances and crossing trajectories, while checking that the permitted visual history resolves the identity. At prediction frame t, supply the current-inclusive window [t−15, …, t] at 16 frames/second, plus one fixed RGB reference frame and its marked coordinate. The reference is the last visible frame before the designated occlusion; it must be in the first reappearance window, precede every scored output, and remains the same for all three predictions. No extra reference history or future RGB is allowed. Score only episodes with all sixteen frames available and with that pre-occlusion reference retained in each of the three scored windows. Use one designated occlusion event per episode; collect all three reappearance labels before admission. The simulator supplies identity, visibility, and the true projected point only for labels.

The primary tracking endpoint is episode-level reacquisition success: on all of the first three visible frames after occlusion, the predicted point is within one quarter of the object's projected bounding-box half-diagonal and visibility is correctly predicted. Weight episodes equally. Report normalized pixel error, visibility accuracy, and success at additional tolerances as supporting measures. Use deterministic resize/letterbox to 224 × 224, with padding excluded from labels and query coordinates transformed identically. Coordinates use x/(W−1), y/(H−1), origin top-left; compute distances and bounding-box diagonals in this 224-pixel coordinate system. The half-diagonal tolerance above is one eighth of the full bounding-box diagonal. Predict visible at probability ≥0.5; the label is visible when the queried surface point passes the renderer depth/occlusion test. An episode whose object diagonal is below 16 pixels on any of the three scored frames belongs to the separately reported small-object stratum, excluded from the primary endpoint by this label-only rule. Report its count and performance rather than silently dropping it. This prevents long stretches of easy visible tracking from hiding failures at reappearance.

This task tests whether a representation supports persistent correspondence under changing visibility. It is not itself a novel tracking benchmark. Its role is to reveal whether an effect found in collision forecasting generalizes to another temporal visual demand.

## A spatial control task

Predict object masks and relative depth from held-out images. For the video backbone, repeat the same RGB image sixteen times, with identical deterministic spatial preprocessing and no temporal augmentation. This adapter supplies one unique image; it cannot use neighboring frames. Use the same adapter for every video condition and record the separate image-only backbone adapter. Masks identify the pixels belonging to each object; relative depth asks which of two queried objects is closer. This reveals whether one training condition trades temporal performance for spatial performance.

A Time advantage on collision forecasting accompanied by a View advantage on geometry would support specialization, not an overall winner. Report both. Spatial scores are important controls but cannot rescue an uninformative null on the temporal tasks.

## Transfer beyond the game renderer

Use Something-Something V2 action recognition as the primary external transfer task with a fixed frozen-backbone readout. Official test labels are withheld: the selected protocol reserves the official validation set for final evaluation, and creates development data only from official training. Call the result “reserved official-validation accuracy,” never official-test accuracy. Within each class, sort official-training video IDs by SHA-256 of `bt-ssv2-dev-v1:20261028:<video_id>` (ID as decimal string, no leading zeroes), breaking hash ties by numeric ID; reserve max(1, floor(0.10 × class count)) for development. The remaining videos are readout training. Select the nested 10% training subset within each remaining class by an independent `bt-ssv2-label-v1:20261028:<video_id>` hash and the same rounding rule. Publish ID manifests and their hashes; audit duplicate/related videos before freezing and keep any related groups together, documenting deviations from these target fractions. The official split has 168,913 training, 24,777 validation and 27,157 test videos. Verify license/access before downloads; no dataset is installed by this plan. [Official dataset/access information](https://www.qualcomm.com/developer/software/something-something-v-2-dataset) The dataset was designed around everyday actions and object interactions. [Something-Something dataset](https://arxiv.org/abs/1706.04261) It provides a different visual domain and actions whose appearance can be similar while their temporal structure differs. Train each readout on the same labeled examples. For this pilot, uniformly select sixteen frames over each entire video using indices round(i × (N−1)/15), i=0…15, with ties rounded down; repeated indices are allowed for short videos. Use deterministic 224-pixel letterboxing and one clip per video for training/development evaluation. Full-video access is permitted for action recognition, unlike causal game tracking. Freeze any later sampling changes before final evaluation.

As a second external check, use a fixed correspondence readout on DAVIS or a TAP-Vid subset, provided the pilot shows that the readout works with the chosen backbone. Lock that choice before the final comparison. The purpose is transfer, not claiming a new state-of-the-art tracker. The released TAPIR work provides a relevant reference for point-tracking evaluation. [TAPIR](https://arxiv.org/abs/2306.08637)

External transfer is a serious feasibility gate. A corpus with millions of rendered images may still contain only twelve thousand independent rollouts and limited semantic variety. PMG's frozen-transfer results explicitly expose this difficulty. If all models remain weak on real videos, equality there adds little; fine-tuning does not substitute for useful frozen transfer. Set a development-data competence threshold against untrained and image-pretrained references before opening the test set. Do not replace a failed primary action task with a successful optional task after seeing the result. [PMG, Appendix H](https://arxiv.org/html/2409.06665)

## The readout protocol

Use the same small attention readout as the primary decoder of frozen features, initially two layers of width 256. Include a linear readout as a secondary check. A weak decoder can hide useful features, while an overly powerful decoder can learn the task itself. Compare identical heads on untrained backbones and on a separate image-only pretraining reference, and inspect low-label learning curves. The image-only reference is diagnostic, not part of the exact architecture-matched causal comparison.

For collision, use the two query points to attend to space-and-time tokens and output one contact probability. For tracking, condition on the fixed reference RGB/point and output the current image coordinate and visibility probability from the current-inclusive causal window defined above. For action recognition, pool clip tokens into class logits. Keep these output heads, their input access, and their tuning budgets identical across pretraining conditions.

For game tasks, train heads on nested sets of 100, 300, and all available labeled training episodes per family. Keep the episode selections identical across conditions. For the external action dataset, use fixed 10% and full-label settings. Choose the primary label budget using development data before final testing.

Run three readout seeds for each pretrained checkpoint and average them within that checkpoint. Retain their variation separately. Full fine-tuning and a frozen-encoder gameplay controller are secondary experiments, after the representation results are established. A controller should use a fixed learning algorithm and demonstration budget; otherwise changes in exploration or optimization could dominate the visual comparison.

# 8 What a positive negative or null result would mean

The sign of the result should determine the conclusion, not whether the study is considered to have worked. However, that only holds if the measurement is sensitive enough to distinguish the competing explanations.

| Result | What it would establish within this experiment | What it would not establish |
| - | - | - |
| Time outperforms View | Temporal grouping provides additional useful supervision at the tested budget despite identical image exposure | That the model has learned physical laws, or that every video-training method benefits |
| View outperforms Time | Replacing viewpoint relationships with temporal relationships has a cost for the tested tasks and methods | That adding extra temporal data would necessarily hurt |
| A mixture outperforms both endpoints | Alternating the two experiences is useful under the tested recipe | A unique mechanism, or an optimal mixture for every dataset or scale |
| Joint outperforms the pure conditions and mixtures | Seeing camera and world motion together supplies a benefit not reproduced by alternating pure clips | That either motion source alone caused the improvement |
| Conditions are practically equivalent to View | Each declared contrast with View is smaller than its prespecified useful effect within the tested setting | That dynamics, video, or interactive experience are generally unnecessary |
| Scores are similar but uncertain or weak | The experiment has not resolved the question | Evidence that the training experiences are interchangeable |

The most useful positive result would survive the matched-image audit, occur on tasks that need history, and transfer outside the renderer. The most useful negative result would show a reproducible tradeoff, such as temporal grouping helping motion prediction while reducing spatial precision. Both would tell us what a fixed learning budget buys.

The null needs more care. “The difference was not statistically significant” means the evidence did not establish a difference. It does not mean the evidence established that any difference is small. For this project, the second statement is the one that matters.

## A concrete null claim

A defensible example would be:

“Under two masked prediction objectives, the tested mixtures of world-time and camera-view sequences, including joint motion, differed from View by less than the prespecified margins on the declared endpoints. Both approaches learned useful features, and coherent grouping supplied benefits over disrupted grouping. This bound applies to the tested corpus, model sizes, training budgets, and readouts.”

That sentence is a template for a possible finding, not a prediction. Each part must be supported. If there is a large effect in one family, a gain from a mixture or Joint, or a failure to transfer, narrow the claim accordingly.

That finding would add a controlled bound beyond demonstrations that synthetic motion can replace natural video. Its significance would come from ruling out a useful incremental effect despite sensitive tasks and useful representations. Exact image matching alone is not enough. If shuffled clips, arbitrary regrouping, and image-only learning all perform equally well, the evidence does not support a special role for viewpoint relationships. The more defensible conclusion would be that these methods did not exploit the tested relationships.

Its practical implication would be that choosing among these coherent training relationships makes little difference within the tested regime once visual states are covered. This could support viewpoint sequences when temporal continuity is unavailable in a comparable synthetic corpus. It would not justify replacing arbitrary real video with unrelated photographs or claim cheaper data generation: View still requires all the dynamic states.

## How to make the null informative

Declare three primary endpoints: collision balanced accuracy, episode-level tracking reacquisition success, and Something-Something V2 top-1 accuracy at one fixed frozen-readout label budget. For the two game endpoints, first average within each family and then weight the three families equally. Report calibration, the same-image-bag diagnostic, spatial controls, other label budgets, and error distributions separately. Choose these definitions and the external label budget on development data before final testing.

Use ±2 percentage points for game endpoints and ±1 point for external action recognition only as provisional planning margins. Two tracking points mean two additional failed reacquisitions per hundred episodes. Before final testing, justify each margin against a meaningful use decision and the gain from pretraining over the untrained reference. Freeze it then. Do not widen a margin because the available runs cannot establish equivalence.

Pair training seeds, average readout seeds within each run, and calculate each between-condition difference. The five comparisons with View are 25%, 50%, 75%, and 100% Time, plus Joint. Across two objectives and three primary endpoints, there are thirty prespecified contrasts. The primary global equivalence claim concerns all thirty, and therefore concerns family averages. A stronger claim covering every game family separately requires all seventy contrasts: five comparisons × two objectives × seven endpoints, where the seven are collision and tracking in each of three families plus external recognition.

For a single claim that every prespecified component is equivalent, use two one-sided tests at α = .05 for each component and require all to pass. This is an intersection–union test: if any component is truly outside its margin, the global claim cannot pass without falsely passing that component. It does not require a Bonferroni correction. This rule does not license selecting favorable individual claims afterward. Correct separately for multiple individual equivalence claims or directional superiority claims, using a prespecified procedure such as Holm's method.

For each component, the two one-sided tests correspond to a 90% confidence interval lying entirely within its equivalence margins. An interval from −0.5 to +0.7 points supports a ±1-point bound; an interval from −4 to +4 does not. Do not label the component intervals as simultaneous 95% intervals. Report conventional uncertainty intervals alongside the equivalence decision. [Lakens, Equivalence Tests](https://doi.org/10.1177/1948550617697177)

Determine the seed count for the intended global claim before final testing. Five seeds are a starting allowance, not a power argument. As a planning calculation, assume independent Gaussian paired run differences, a true difference of zero, and a ±1-point margin. If the paired standard deviation is 0.5 points, five runs give about 95% power for one contrast. At 1 point it is about 29%; roughly eleven runs give 80%. At 2 points it is about 2%; roughly thirty-six runs give 80%. These are calculated scenarios, not measured variance. Requiring thirty or seventy contrasts to pass can need more runs; simulate their joint power using conservative variance and correlation estimates. For illustration only, independent components each with 95% power would yield 0.95^30 ≈ 21% or 0.95^70 ≈ 3% conjunction power; our contrasts share seeds and View, so independence is not an estimate for this study. The pilot must also examine episode-level precision: more training seeds do not repair a too-small evaluation set.

A three-seed pilot estimates variance poorly. Use uncertainty in that estimate when deciding the budget, and fix the sample size or a valid sequential stopping rule in advance. Never add seeds until equivalence happens to pass. Training seeds measure variation conditional on the training corpus. Also assess test-sample uncertainty by resampling paired episode groups or videos, not frames; preserve counterfactual pairs and family structure. A crossed seed-and-episode resampling analysis is a useful sensitivity check, but five seeds do not make its tail estimates reliable.

Report family-level effects and interactions even when the primary family-average claim passes. Opposite effects can cancel. Even if the stronger seventy-component claim passes, describe each condition as equivalent to View in each family; do not claim all pairs are interchangeable at the same margin. Two conditions can each be within ±δ of View yet differ by nearly 2δ from each other. All-pairs equivalence among the six coherent conditions would require 90 primary components or 210 family-specific components and a separately planned power analysis; that is not the selected claim. An independently generated corpus or renderer replication is needed to extend a broad null beyond the one fixed collection used for the main runs.

Require four forms of evidence before treating equivalence as the paper's main result. First, a visual sequence model solves the history and order diagnostics while the restricted controls fail. Second, pretrained models beat untrained references and transfer usefully to real video. Third, coherent grouping produces a prespecified practically meaningful gain over the regrouped control on at least one relevant endpoint for each objective, with multiplicity handled in the protocol; image-only results help interpret that gain. Fourth, precision and development learning curves rule out an unresolved scale or training-budget limitation. If the third check fails, the narrower objective-insensitivity finding remains valid, but the proposed strong null claim does not.

# 9 Whether this is enough for CVPR

I would treat the full version as a plausible CVPR empirical study, rather than a guaranteed main-conference paper. The topic concerns how visual representations acquire useful information, and the intervention addresses a concrete attribution problem. That is a stronger fit than a game-interface study whose main contribution is a novel interaction mechanic.

The closest papers already make a generic null unsurprising: synthetic motion can teach useful features, camera changes can teach correspondence, and masked prediction can exploit static structure. A small, precise View–Time tie would therefore add only a modest control improvement. A stronger result would show that meaningful coherent learning occurred, that temporal evidence was necessary at evaluation, that world-time grouping supplied no useful increment at a defensible margin, and that this pattern survived external transfer and a corpus or scale check. Even then, it is compatible with several mechanisms; it does not prove correspondence is the mechanism.

There is a weaker objection that “the ingredients already exist.” Existing ingredients alone do not settle whether the experiment contributes new knowledge. The more important question is whether its controls let us conclude something that previous results could not. Conversely, merely implementing familiar ingredients together does not create that contribution automatically.

The paper needs the exact-image intervention, genuinely sensitive evaluation, useful external transfer, and evidence that the learning methods actually respond to relationships between frames. The released generator and manifests make that comparison reusable. For a broad null-led paper, include an independent corpus replication and a capacity or budget sensitivity check; a single small-model result should carry a narrower claim.

A paper that only reports “two small models tie on a ball game” would be too weak. So would a large table of statistically uncertain differences. A broad, precise null that constrains the extra value of temporal relationships is substantially more credible, although its ultimate significance still depends on effect bounds, model competence, and scope.

The CVPR 2026 reviewer guidance explicitly treats knowledge advance as important and says that not exceeding existing state-of-the-art accuracy is not grounds for rejection by itself. That supports the type of contribution proposed here; it does not promise acceptance for a null result. [CVPR reviewer guidance](https://cvpr.thecvf.com/Conferences/2026/ReviewerGuidelines)

The official CVPR 2027 deadlines are November 10, 2026 for registration and November 16, 2026 for papers, at 11:59 p.m. AoE. Starting from this unimplemented scaffold on October 28 leaves only nineteen calendar days to the paper deadline. The full study is not a credible commitment for that deadline; select a venue after measured pilot feasibility, rather than compressing validity checks to meet it. The 2026 reviewer guidance above is precedent, not a verified 2027 review rule. [CVPR 2027 dates](https://cvpr.thecvf.com/Conferences/2027/Dates), [call for papers](https://cvpr.thecvf.com/Conferences/2027/CallForPapers)

Proceed with the pilot, not an unconditional eighty-run commitment. A result-independent study is possible; a result-independent promise of CVPR significance is not. Continue when the measurement, learning, transfer, and power gates pass, regardless of which main condition looks better. If coherent and disrupted experiences all tie, or transfer remains weak, report that limitation honestly rather than spending more runs to turn a limited finding into a paper claim.

# 10 Rendering feasibility and the main engineering risks

The basic rendering operation is feasible with existing technology. Kubric combines simulation and rendering with rich annotations, and the public Kubric-5D project includes multiview generation of dynamic scenes. These are precedents for generating the required observations, not implementations of this benchmark. [Kubric](https://github.com/google-research/kubric), [Kubric-5D](https://github.com/TRI-ML/Kubric-5D)

For the gameplay version, use Godot with explicit state capture and replay, plus an independent camera controller. Its pause mechanism stops physics and controls node processing, but a pause button is not a complete guarantee that every visual process is frozen. [Godot pause documentation](https://docs.godotengine.org/en/stable/tutorials/scripting/pausing_games.html)

The simplest reliable approach is to simulate an episode once, record the object transforms and animation states, and render each saved state from all sixteen cameras in a separate rendering pass. This avoids requiring the physics engine to reproduce the entire trajectory every time a camera changes. For the primary dataset, use rigid objects and controlled articulations. Fluids, cloth, smoke, and stochastic particles add state-capture complexity without being necessary for the central question.

Capture everything that can affect the image, including light states and animation phase. Disable motion blur, automatic exposure changes, and history-dependent rendering effects initially. Otherwise the same nominal state could look different depending on the previous camera position. Test repeat rendering of a saved state and camera for pixel identity under the pinned software and hardware setup.

There are three separate feasibility checks:

1. **State fidelity:** rendering a saved state does not advance gameplay or change any relevant visual property.

2. **Camera freedom:** the camera can move without affecting collision, visibility logic, or character behavior.

3. **Throughput:** the renderer and training pipeline can produce and process enough varied examples within the available budget.

Existing engines make these checks plausible, but they still need to pass in the actual project. In particular, a commercial game with a photo mode may hide state, restrict camera access, and complicate redistribution. An instrumented open-source project is the more controllable starting point.

If Godot state export becomes the bottleneck, first implement the grid and training audit with Kubric. That can validate the scientific design, but the final gaming claim should then depend on adding actual game-generated episodes. Do not call a generic pile-of-objects dataset gameplay solely because a physics engine generated it.

# 11 The build plan and resource budget

## Stage one Establish that the images are controlled

Build one projectile-arena scene and export 100 complete grids. Deliver progressively: one grid for format/visual inspection, eight for the first complete optimizer update, then 100 for renderer/audit acceptance. Under the October 30 [ownership reassignment](division-of-labor.md), Joy owns both the producer and consumer plus required scoring; Sudarshan develops a separate independent verifier. The eight-grid drop unblocks real-update integration without waiting for a collaborator or the entire corpus. Implement View, Time, Joint in both directions, the four-pass mixtures, and both disruption controls. Produce an audit report from the real loader before training a model.

Check exact exposure equality, all four-pass schedules, both Joint traversal directions, target-value consistency, frozen world state, deterministic rendering, and split integrity. Inspect contacts, occlusions, camera-loop closure, and post-crop visibility. The indexing rules have been checked in a small standalone enumeration: rows, columns, both diagonal directions, and all five four-pass mixtures use every grid cell equally. This verifies the combinatorics only; the renderer, loader, masks, and optimizer still need end-to-end tests.

## Stage two Establish that the measurements work

Generate paired-history collision cases, the same-image-bag order diagnostic, and a small causal tracking set. Train supervised sequence, final-frame, and permutation-invariant references. Verify label correctness with a state oracle, then verify visual solvability with a model receiving only allowed inputs. Inspect failures before expanding the data.

The concrete pilot uses 1,000 projectile-arena pretraining grids, six VideoMAE conditions (View, Time, Mix50, Joint, Shuffled Time, Regrouped) and paired seeds 17, 29, 43: eighteen controlled runs. Train to twenty complete passes, with a checkpoint at pass four under the same predeclared twenty-pass schedule. Start View/Time/Mix50 at seed 17 through pass four for an early stability screen; these are the first three of eighteen, not extra runs. Resume those exact runs only if code/config/data hashes are unchanged. No eighty-pass pilot extension or V-JEPA matrix is included. The [pilot plan](docs/pilot-plan.md) specifies data units, reference runs, readout workload, development-only thresholds, failure handling, and parallel handoffs. Separately budget native-recipe validation, untrained and image-only references, and readout training. Measure learning stability, throughput, memory, I/O, and paired variance. A scheduler that passes its image-count audit is not yet a working learning experiment.

The exploratory pilot assessment has two prelocked stages on the same 400 episodes per game task: H3 scores all seven supervised diagnostics once; after H3 and early stability pass, H4 scores the 243 declared pass-20/fixed-reference game heads once. Lock both stage inventories, all recipes, seeds, budgets, source/runtime identities and retry/failure rules before any assessment scoring. Bind existing diagnostic checkpoints and early-screen resume points at that lock; append later checkpoint hashes only to their fixed planned identities. H3 outcomes may not select later recipes or substitute failed slots. Early-screen and SSv2 heads remain development-only. Reuse of this pool is exploratory, not independent replication or final-test evidence. Outcome-driven repairs require a new version and a fresh assessment pool, retaining all old results. See the [selected release policy](docs/assessment-release-proposal.md) for exact state and isolation requirements.

Continue regardless of the direction of the View–Time contrast when the experiment passes its validity gates. Repair image shortcuts, ambiguous forecast labels, ineffective learning, or inadequate readouts before interpreting the result. If the objectives learn but ignore grouping, retain that as a narrower outcome and reassess significance; do not silently change the hypothesis to make the observed direction look interesting.

## Stage three Freeze the main protocol

Add the remaining game families and establish separate pretraining, readout-training, development, and test splits. Demonstrate useful real-video transfer on development data. Choose the practical margins, primary readout budget, conjunction of equivalence claims, sample size, and stopping rule. The pilot uses 300 labeled game episodes per task and the fixed 10% external-training subset as its screening budgets, with three readout seeds (101, 102, 103); these are selected pilot defaults, not a freeze of the final-study budget or margins. Plan the independent-corpus and capacity or budget checks before examining the final results, and budget them explicitly.

Test the feature-prediction implementation independently before including it. Save a dated protocol that states all choices. Keep the final test unavailable to the tuning script.

## Stage four Run and explain the full comparison

Run five Time proportions, Joint, and two disruption controls for both objectives. With n paired pretraining seeds this is 16n runs: eighty at n = 5, 176 at n = 11, or 576 at n = 36. These totals exclude pilot work, reference models, native-recipe validation, and replications. A one-objective study costs 8n runs and supports a narrower conclusion. Fix n from the actual power and resource calculation rather than treating eighty runs as sufficient by definition.

Run the prespecified View, Time, and 50–50 replication on an independently generated corpus, and the selected capacity or longer-budget check. Include Joint in the replication if claims about combined motion are central. Report the held-out-family evaluation separately from an independent-corpus replication: they answer different generalization questions. Use the same complete grids for every matched sensitivity contrast.

Report all conditions, including disappointing and uncertain ones. The paper should distinguish a measured effect, practical equivalence, and unresolved uncertainty rather than forcing every comparison into a win or a tie.

## Storage and compute

With 12,000 grids, sixteen times, and sixteen cameras, the pretraining set contains 3,072,000 images. At 224 by 224 pixels with three 8-bit color channels, uncompressed RGB alone occupies about 462 GB in decimal units. A 1,000-grid pilot occupies about 38.5 GB. Compression will reduce RGB storage, while evaluation data, annotations, checkpoints, and caches will add to it. Measure the actual ratio before choosing the storage system.

At the proposed scale, one complete pass contains 192,000 sixteen-frame clips. Twenty passes contain 3.84 million clips per run. If one GPU processes 100 clips per second, a run takes about 10.7 GPU-hours and eighty runs take about 853 GPU-hours, excluding evaluation and overhead. At 20 clips per second, the corresponding total is about 4,267 GPU-hours. These are arithmetic scenarios, not measured speeds. Eighty passes would multiply those totals by four.

Measure each objective separately; feature prediction also runs a teacher. For multiple GPUs, multiply wall time by GPU count. Benchmark rendering as well: 3.072 million images would take roughly 85 hours at ten images per second, or 853 hours at one image per second, per rendering worker. These are arithmetic examples, not measured speeds. Add state export, annotation, storage, loading, native-recipe checks, reference models, replications, readouts, tuning, and failed runs to the resource ledger.

The design is feasible in stages, but no engine implementation or GPU training benchmark has yet been validated for this project. The main risks are weak transfer from limited game diversity, loss of learning quality under the controlled recipe, and the runs needed for a precise global null. Rendering a grid is technically plausible; obtaining an informative, affordable learning comparison is the unresolved feasibility question.

# 12 Implementation details to preserve

Organize the implementation around a small number of independently checkable components.

| Component | Responsibility | Required output |
| - | - | - |
| Episode generator | Run scripts in the game worlds and record states | State traces, action scripts, seeds, and asset records |
| Grid renderer | Render every saved state from every selected camera | Immutable RGB files and camera/state metadata |
| Split builder | Separate related episodes and asset groups | Versioned split manifests |
| Sequence loader | Construct rows, columns, mixtures, Joint, and controls | Clip lists and exposure-audit logs |
| Training runner | Apply paired initialization and matched budgets | Configurations, checkpoints, resource logs, and learning curves |
| Task evaluator | Train common readouts and score held-out episodes | Per-episode predictions and metrics |
| Analysis script | Compare paired runs and test practical equivalence | Effect sizes, intervals, stratified results, and outcome labels |

A grid record includes `grid_id`, `scene_family`, `rollout_id`, `split`, `asset_group`, timestamps, camera poses, camera direction and phase, image paths and hashes, simulator and renderer versions, event phase, random seeds, and state checksums. Evaluation records additionally include the continuation-policy identifier, query points, counterpart-pair identifier, and oracle labels. Keep labels and hidden state outside the pretraining loader's permissions.

The sequence scheduler should take only the manifest, a condition or Time proportion, a pass number, and a seed. It should return sixteen clips per grid, each with sixteen image identifiers. For a grid indexed as `grid[world_time, camera]`, the three coherent constructions are:

```python
view_clips = [grid[t, :] for t in range(16)]
time_clips = [grid[:, c] for c in range(16)]
# direction is +1 or -1, balanced by the recorded schedule.
joint_clips = [
    [grid[t, (direction * t + phase) % 16] for t in range(16)]
    for phase in range(16)
]
```

For each four-pass cycle, each grid uses Time exactly zero, one, two, three, or four times according to its condition. Validate the schedule and inspect checkpoints only after complete cycles, initially at 4, 20, and 80 passes. Shuffle grid order consistently across matched runs.

Start with eight complete grids per optimizer update: 128 clips, but only eight independent scenes. Tune the common learning rate with that correlation structure in mind. Microbatch size can vary with memory; update boundaries, loss normalization, and teacher updates cannot. Finish complete grid units and never discard different partial batches in different conditions.

For an initial small backbone, use twelve transformer blocks, hidden width 384, six attention heads, spatial patches of 16 by 16 pixels, and temporal tubelets of two frames. A tubelet combines a small spatial patch across adjacent frames. Keep the tubelet construction identical across conditions; the input relationships differ by design. Use the published objective-specific decoder or predictor and optimizer defaults, pinned to a recorded code revision. Any small-model adaptation is part of the pilot validation.

Two-frame tubelets combine adjacent images differently after regrouping. That is part of the treatment, so the claim is identical pixel exposure, not identical input tokens. If an effect appears to depend on that early mixing, test one-frame tubelets as a prespecified sensitivity analysis rather than attributing it immediately to temporal understanding.

Record the exact learning rate, warmup, weight decay, mask schedule, initialization, decoder dimensions, precision mode, and software versions in each configuration. Final values should come from the common development procedure, not from separately tuning the favored condition. This is a controlled experiment; copied defaults still need to work at its data scale.

Release a small, fully reproducible example containing one grid, every condition's clip construction, and its audit output. That example should make the central claim easy for another researcher to verify without training a model.

The first deliverable is a rendered grid, an audited training update, and a solvable visual history test. The next is evidence that the controlled objectives learn useful features and that the intended precision is affordable. The full paper is justified only if those pieces support a transferable answer; novelty of the control alone cannot compensate for an uninformative null.
