# BodyVision 2.0: Implementation-Ready Upgrade Specification

**Purpose:** Upgrade the BodyVision capstone from a single-image geometry and regression prototype into a controlled, measurable, multi-view anthropometry system. This document is a build plan, not a claim that the proposed system can infer clinical measurements or replace a scale or stadiometer.

**Status:** Research specification; implementation and measured status are recorded in [BODYVISION_2_AUDIT.md](BODYVISION_2_AUDIT.md). The cohort-specific implementation is not equivalent to the full aspirational definition of done below.

## 1. Executive summary

BodyVision currently combines React + Vite, a FastAPI service, YOLOv8n person detection, MediaPipe Pose Lite, MediaPipe Selfie Segmentation, OpenCV geometry, Ridge height calibration, and Ridge weight regression. The supplied group-aggregated baseline is **height MAE 4.143 cm** and **weight MAE 7.277 kg**, based on **37 participants and 151 images**.

BodyVision 2.0 should preserve a reproducible baseline while introducing:

- **A — Front/side anthropometry:** controlled front and side captures, pose and silhouette quality checks, normalized dimensions and ratios, and explicit feature provenance.
- **C — Optional user inputs:** user-entered age band and height, plus any other carefully justified, optional inputs. Treat self-reported values as such; do not silently treat them as measured truth. Height can be withheld in a mode that estimates height, since supplying actual height changes the task.
- **Height calibration:** known-size reference or calibrated camera geometry where possible, ground-plane and pose checks, uncertainty, and a fallback calibration model with strict quality gates.
- **Weight benchmarking:** compare transparent linear baselines with regularized and tree-based models using participant-grouped validation; select on held-out participant performance, not training fit.
- **Better data and evaluation:** collect accurate scale/stadiometer labels, repeated controlled captures, participant-level splits, subgroup/error analysis, and a locked test set.
- **Uncertainty and safe UX:** return quality status and a calibrated prediction interval; abstain when input quality or model support is inadequate.

The earlier discussion suggested research targets of **2.5–3.5 cm height MAE** and **4.5–6 kg weight MAE**. These are hypotheses for experiments, not promised results. With only 37 participants, added features may overfit; a robust estimate of improvement requires more unique participants and external testing.

## 2. Current system and baseline

### 2.1 Supplied architecture

| Layer | Current component | Current role |
|---|---|---|
| Web client | React + Vite | Capture/upload and display results |
| API | FastAPI | Receives images and serves estimates |
| Person detection | YOLOv8n | Detects/crops the person |
| Pose | MediaPipe Pose Lite | Locates body landmarks |
| Segmentation | MediaPipe Selfie Segmentation | Produces person silhouette/mask |
| Geometry | OpenCV | Extracts pixel dimensions, ratios, and image geometry |
| Height estimator | Ridge with calibration | Converts visual features into a height estimate |
| Weight estimator | Ridge regression | Maps visual features to weight |

### 2.2 Baseline results supplied

| Target | Current group-aggregated MAE | Dataset |
|---|---:|---|
| Height | 4.143 cm | 37 participants, 151 images |
| Weight | 7.277 kg | 37 participants, 151 images |

Before changing code, create a baseline report that states exactly how these figures were obtained: split method, grouping key, number of unique people in each split, whether duplicate views cross splits, preprocessing, model parameters, units, and treatment of failed predictions. If the current evaluation split images rather than participants, its metrics may be optimistic because images of the same person can appear in both train and test data.

### 2.3 Keep the existing path reproducible

- Tag or record the baseline commit and model artifacts.
- Save the exact feature list, preprocessing parameters, model configuration, random seeds, split manifest, and evaluation script.
- Preserve current API response compatibility during migration where practical.
- Run the new pipeline and the frozen baseline on identical held-out participants.

## 3. Product and modeling scope

### 3.1 Intended use

A capstone/research prototype that provides approximate estimates under controlled capture conditions and communicates uncertainty. Do not market it as clinical, diagnostic, fitness-grade, or a substitute for direct measurement without independent evidence and appropriate review.

### 3.2 A: anthropometry from front and side views

Require two distinct captures, preferably in one guided session:

1. **Front view:** person faces camera, neutral stance, arms slightly separated from torso, feet visible, fitted non-obstructive clothing, camera level, no severe rotation.
2. **Side view:** person rotates approximately 90 degrees, neutral stance, arms positioned consistently, feet visible, camera and distance unchanged.
3. Capture one view at a time. The client should show alignment guidance and reject blur, truncation, multiple people, severe occlusion, and inconsistent framing.

Candidate measurements, subject to landmark/mask reliability:

- Front silhouette widths at shoulder, chest, waist, pelvis/hip, upper arm, thigh, and calf levels.
- Side silhouette depths at chest, abdomen/waist, pelvis/hip, upper arm, and thigh levels.
- Height-normalized widths/depths; ratios such as waist-to-height and shoulder-to-hip; front/side ratios; limb and torso proportions.
- Silhouette area and vertical profile summaries as exploratory features, only after checking sensitivity to clothing and segmentation.
- Landmark-derived lengths only where the relevant landmarks pass confidence and anatomical plausibility checks.

These are **image-derived proxies**, not tape-measured circumferences. A front width and side depth do not directly equal a circumference. Avoid labeling them as clinical anthropometric measurements. If an experimental volume proxy is used, document its assumptions and validate separately.

### 3.3 C: optional user inputs

Introduce an explicit, versioned input schema. Begin with:

- Age or age band, optional, with a “prefer not to say” option. Exclude minors initially unless the project has appropriate consent, safeguards, and a specific research need.
- User-entered height, optional and labeled **self-reported**. When supplied, weight mode may use it as a feature. Height-estimation mode must also be evaluated without it; never feed the ground-truth height label into its own prediction.
- Optional sex-related physiological input only if the study justifies its collection, explains its use, obtains consent, and tests group performance. Make it optional, do not infer it from images, and document limits. Do not require gender identity as a proxy for physiology.
- Avoid collecting names, exact date of birth, precise location, or unrelated health information.

Store missing values explicitly; do not impute a missing optional input with a fabricated default. Report performance both with and without optional inputs to measure their incremental value and ensure a viable no-input path.

### 3.4 Separate estimation modes

- **Height mode:** image/camera features only, with optional external calibration object or known camera setup. Actual height is the label, never a predictor.
- **Weight mode (A-only):** front/side visual features; no user-entered height or demographic inputs.
- **Weight mode (A+C):** A features plus only consented, available C inputs. Include self-reported height provenance.
- **Optional calibration mode:** if a user provides a measured height for calibration, clearly state that the resulting output is conditional on that input and do not compare it to the no-height mode as though the tasks were identical.

## 4. Height calibration upgrade

### 4.1 Preferred calibration hierarchy

1. **Known-size reference in the capture plane:** a vertical reference of measured length placed near the person and aligned with the same floor plane. Detect its endpoints or have the user mark them with guided review. Reject if tilted, partly hidden, or too far in depth from the person.
2. **Fixed, calibrated camera setup:** known intrinsics, camera height/tilt, distance and floor plane, with repeatable capture position. Use geometric calibration and ground-plane correction. This is viable only when setup constraints are enforceable.
3. **Learned calibration fallback:** use existing Ridge calibration only as a fallback, with participant-grouped training and a clearly defined applicability range. It must not be described as physical calibration if it merely learns from the dataset.

Do not assume pixel-to-centimeter scale is constant across the image. Perspective, camera tilt, subject-camera distance, floor location, footwear, hair, posture, and cropping all affect apparent height.

### 4.2 Processing and quality gates

- Detect exactly one person and ensure head and feet are visible.
- Estimate body axis and floor contact from pose and mask; reject excessive lean, bent knees, cropped hair/feet, strong occlusion, or inconsistent stance.
- Use a consistent definition of measured height (barefoot stadiometer ground truth; top of head to floor in a straight posture). Record footwear for captures and exclude or correct only with a predefined method.
- Estimate height using calibrated scale and geometry where available; record all intermediate values (pixel height, reference pixel height, scale, tilt/position checks, pose confidence).
- Return a quality score and interval. Abstain if reference detection, pose, or segmentation quality fails thresholds selected on development data.
- For learned calibration, compare Ridge to a simple calibrated geometric estimator and other candidates. Use a nested/grouped validation procedure so any calibration tuning happens without test participant leakage.

### 4.3 Calibration study

Collect repeated captures across a range of distances, camera heights, camera models, lighting, and body sizes. Compare within-person repeatability and error against stadiometer readings. Report MAE, median absolute error, RMSE, signed bias, limits/quantiles of error, failure/abstention rate, and subgroup results. Do not select thresholds using the locked test set.

## 5. Weight features and model benchmarking

### 5.1 Feature engineering

Create a feature pipeline with a versioned, named feature vector. Candidate blocks:

- **Front geometry:** normalized widths and width profile at fixed relative heights; shoulder/waist/hip ratios; silhouette width summaries.
- **Side geometry:** normalized depths and depth profile; chest/abdomen/hip depth ratios.
- **Cross-view features:** paired front-width/side-depth products or ratios as experimental body-size proxies; front/side alignment and capture consistency.
- **Proportions:** limb-to-torso ratios and landmark-derived segment lengths, gated on confidence.
- **Input C:** optional self-reported height, age/age band, and any separately justified optional variable, each with missingness and provenance indicators as needed.
- **Quality covariates:** confidence and capture-quality fields should primarily drive rejection/uncertainty; test whether including them as predictive inputs creates spurious relationships.

All visual dimensions should be normalized using a legitimate scale source (known-size reference, fixed calibrated setup, or an input height explicitly supplied in weight mode). Avoid using estimated height as a hidden shortcut without separately measuring error propagation. Fit imputers, scalers, feature selection, and all transforms on training folds only.

### 5.2 Benchmark ladder

Use identical participant splits and compare:

1. Training-fold median predictor (sanity baseline).
2. Existing Ridge model with its original features and with engineered A / A+C features.
3. Regularized linear models such as Ridge and Elastic Net, with tuned regularization inside grouped CV.
4. Random Forest or ExtraTrees with constrained depth/leaf size.
5. Gradient-boosted trees such as HistGradientBoosting or CatBoost only if dependency and dataset size justify them; use strong regularization and grouped tuning.
6. Optional simple physics-inspired regression on proxy volume/size features, treated as a baseline rather than ground truth.

Do not assume a more complex model is better. For 37 participants, tree models can overfit badly. Feature/model choice must be made using development data and a locked participant test set.

### 5.3 Weight endpoints and reporting

Primary metric: MAE in kilograms, reported per participant, with a participant-level bootstrap confidence interval. Also report median absolute error, RMSE, signed bias, error quantiles, calibration of intervals, and the proportion abstained. Report performance by relevant, adequately sized groups and by capture-quality bands; suppress conclusions for tiny groups. Show baseline and candidate results on the same participants.

Investigate systematic error over body-size range and input combinations. Check for leakage (participant identifiers, filenames, repeated images, label-derived features, target-derived transformations). Do not tune to individual participants in the test set.

## 6. Dataset collection plan and schema

### 6.1 Participant count and study design

The current 37-person dataset is a useful prototype but too small to support strong generalization claims or many predictors. Prioritize **unique participants**, not extra images from existing people. A practical staged goal is:

- **Stage 1:** audit and recapture/standardize the existing cohort where consent and records permit; prove the capture and evaluation pipeline.
- **Stage 2:** target at least 100–150 unique adults for a stronger internal feasibility study, with balanced coverage across the intended population and body-size range.
- **Stage 3:** target 300–500 unique participants as a longer-term research goal, with an independently recruited external test cohort if feasible.

These are planning targets, not guarantees of statistical power. The final sample size should be justified from expected error variability, desired confidence interval width, recruitment feasibility, and subgroup analysis needs. More photos of one participant do not replace more participants.

### 6.2 Collection protocol

- Measure **ground-truth height** using a stadiometer and **ground-truth weight** using a calibrated scale. Record device type, resolution/calibration date where available, measurement time, and repeated reading procedure.
- Use a consistent clothing, footwear, pose, camera, distance, lighting, and background protocol. Record deviations rather than silently mixing conditions.
- Capture front and side images within a short interval of weighing; use a random study ID. Avoid public-facing storage of identifiable images.
- Take repeat captures for a subset to quantify technical repeatability, not to inflate independent sample size.
- Obtain informed consent, define retention/deletion policy, restrict access, encrypt storage, and separate identifying consent/contact records from research data. Follow institutional review and applicable privacy requirements before collecting data.
- Include voluntary optional fields only when justified. Track missingness and consent scope.

### 6.3 Suggested data schema

Use one participant table, one session/measurement table, and one image/capture table; store images separately under randomized IDs. Example logical fields:

**Participant**

- `participant_id` (random, pseudonymous; never use as a model feature)
- `consent_version`, `consent_timestamp` (access-controlled)
- `age_years` or `age_band` (nullable; prefer band if exact age is unnecessary)
- `optional_physiology_input` (nullable, only if approved and justified)
- `self_reported_height_cm` (nullable)
- `input_provenance` (e.g., self-reported; measurement source if available)

**Measurement session**

- `session_id`, `participant_id`, `measurement_timestamp`
- `weight_kg`, `weight_device_id/type`, `weight_repeat_values_kg`
- `height_cm`, `height_device_id/type`, `height_repeat_values_cm`
- `ground_truth_protocol_version`, `operator_id` (pseudonymous)
- relevant protocol deviations, clothing/footwear flags, consent status

**Capture/image record**

- `capture_id`, `session_id`, `view` (`front`/`side`), secure image URI
- camera/device model if available, image dimensions, capture distance/setup metadata
- blur/exposure/occlusion/truncation checks, person/pose/segmentation model versions
- preprocessing version, feature schema version, quality flags, rejection reason
- never store names or contact details alongside image paths

**Derived prediction/evaluation record**

- `model_version`, `feature_version`, `prediction_mode`, input feature provenance
- estimate, interval lower/upper, confidence/quality outputs, abstention reason
- evaluation split/fold, target value access restricted to evaluation tooling

Keep raw, derived, and target label data separable so the production inference service cannot accidentally read ground-truth labels.

## 7. API changes (FastAPI)

Keep endpoint names aligned with the existing service where possible; version the contract if breaking changes are required. Proposed logical request:

```json
{
  "front_image": "multipart file",
  "side_image": "multipart file",
  "mode": "weight_a_plus_c",
  "user_inputs": {
    "self_reported_height_cm": 170.0,
    "age_band": "30-39",
    "optional_physiology_input": null
  },
  "calibration": {
    "reference_length_cm": 100.0,
    "reference_type": "vertical_reference"
  }
}
```

Use multipart uploads or secure object references rather than base64 JSON unless existing architecture requires otherwise. Validate image type, size, dimensions, and count; do not trust client MIME type alone. Enforce upload limits, timeouts, safe temporary-file handling, and deletion/retention policy.

Proposed response:

```json
{
  "request_id": "opaque-id",
  "model_version": "bodyvision-2.0-candidate-1",
  "mode": "weight_a_plus_c",
  "status": "ok",
  "estimate": {"value": 72.4, "unit": "kg"},
  "uncertainty": {"lower": 64.1, "upper": 80.7, "level": 0.90, "method": "conformal"},
  "quality": {"score": 0.91, "flags": []},
  "features_used": ["front_waist_width_norm", "side_abdomen_depth_norm", "self_reported_height_cm"],
  "notice": "Approximate estimate; verify with a scale for an accurate measurement."
}
```

Define stable error codes for `NO_PERSON`, `MULTIPLE_PEOPLE`, `VIEW_MISMATCH`, `BODY_TRUNCATED`, `POSE_QUALITY_LOW`, `SEGMENTATION_QUALITY_LOW`, `CALIBRATION_REQUIRED`, `INPUT_INVALID`, `OUT_OF_SUPPORTED_RANGE`, and `INFERENCE_UNAVAILABLE`. Do not return a numeric estimate when required inputs fail. Avoid logging images, raw sensitive inputs, or labels. Add request IDs and model/version metadata for supportability.

## 8. Frontend changes (React + Vite)

- Add a guided two-step capture flow with clear front/side illustrations, camera positioning, distance and lighting prompts, privacy notice, and consent where required.
- Provide manual file upload as a fallback; preview each view and allow retake/remove before submission.
- Validate view order and capture quality client-side when possible, but treat server validation as authoritative.
- Add an optional-input screen with plain explanations, purpose, provenance labels, skip choices, and no preselected sensitive option.
- Explain that self-reported height is optional and changes the weight model mode; let users choose A-only or A+C and show which inputs were used.
- Present estimate, interval, quality status, and a short explanation. Avoid false precision: round to a sensible unit and do not display a narrow interval if calibration does not support it.
- Show actionable retry guidance on abstention (e.g., include head/feet, improve lighting, stand side-on), without implying the person caused a model failure.
- Provide a clear “delete this session” path if images are stored, and state retention accurately.
- Keep accessibility in scope: keyboard support, screen-reader labels, contrast, and alternatives to camera capture.

## 9. Validation protocol

### 9.1 Split strategy

- Split by `participant_id`; all images, sessions, and repeats for one person remain in one partition.
- Reserve a locked test cohort before feature/model tuning. If sample size is too small for a stable fixed test, use nested GroupKFold or leave-group-out development estimates and clearly label uncertainty; recruit a separate final cohort for confirmatory evaluation.
- Perform preprocessing, feature selection, calibration tuning, and hyperparameter selection inside training folds only.
- Maintain a written split manifest and verify participant disjointness automatically.

### 9.2 Comparisons

Evaluate, on identical test participants:

- Frozen current baseline.
- Height geometry/calibration candidates.
- Weight A-only candidates.
- Weight A+C candidates, plus ablations for each optional input and feature block.
- Quality-gated result including both error and abstention coverage.

Report confidence intervals at the participant level. For paired model comparisons, bootstrap participants and compute paired MAE differences. Document failed processing cases and count them in coverage reporting; do not silently drop difficult participants.

### 9.3 Calibration and uncertainty

- For regression intervals, start with split conformal or cross-conformal calibration on participant-independent calibration data, preserving group structure. Estimate coverage and interval width on untouched test data.
- Calibrate height and weight separately, and by mode if A-only versus A+C materially changes residuals.
- Report nominal versus observed coverage (e.g., 90%), mean/median interval width, and coverage by supported subgroup/quality level.
- A confidence score is not a probability of correctness unless calibrated and validated as such. Prefer interpretable quality flags plus an empirically calibrated prediction interval.
- Establish an out-of-distribution/support check based on training feature ranges or validated distance methods; abstain or widen uncertainty outside supported ranges.

## 10. Quality controls and responsible use

- Gate on person count, view orientation, body visibility, landmark confidence, mask quality, reference detection, capture distance/pose and image integrity.
- Persist a reason code for every abstention; monitor abstention rates by capture condition and participant group.
- Do not infer sensitive attributes from pixels. Make optional demographic features transparent and test whether they create unequal error or exclude users who decline them.
- Provide a mode without optional sensitive inputs. Compare its performance and communicate any limitation honestly.
- Use error and coverage analysis across age bands, skin tones if ethically and lawfully collected, body sizes, clothing, camera devices, and other relevant factors. Collect only variables justified for bias evaluation, with consent and safeguards.
- Restrict outputs to supported ranges; mark unsupported estimates rather than extrapolating confidently.
- State that image-based weight estimation is indirect and can be wrong because body composition, clothing, posture, and shape are not fully observable from RGB images.

## 11. Phased implementation plan

### Phase 0 — Audit and freeze baseline

- Map current routes, request/response schemas, feature extraction, model artifacts, and evaluation code.
- Reproduce the 4.143 cm and 7.277 kg MAE figures or document why exact reproduction is not possible.
- Confirm participant IDs, image/label mapping, duplicates, consent, and split integrity.
- Deliverable: baseline card, data audit, and frozen artifacts.

### Phase 1 — Dataset and capture protocol

- Finalize measurement protocol and consent/data handling before new recruitment.
- Add participant/session/capture schema and stable pseudonymous IDs.
- Build front/side capture guidance and collect a pilot set; measure repeatability and failure modes.
- Deliverable: versioned dataset, quality report, and capture protocol.

### Phase 2 — Geometry and height calibration

- Refactor features into versioned front/side extraction modules with diagnostics.
- Add reference/camera calibration path, ground-plane checks, and rejection reasons.
- Compare against existing Ridge height estimator with participant splits.
- Deliverable: height candidate report including MAE, bias, interval coverage, and abstention rate.

### Phase 3 — Weight A and A+C benchmark

- Build A-only and A+C feature matrices with provenance and missing-input handling.
- Benchmark models using nested participant-level validation; run feature ablations and leakage checks.
- Select the simplest model that provides a repeatable held-out gain and acceptable subgroup performance.
- Deliverable: model card and locked candidate artifact.

### Phase 4 — API and UI integration

- Add versioned request/response contracts, input validation, quality codes, uncertainty and mode metadata.
- Add guided multi-view UI, optional input choices, result interval, and retake/abstention flows.
- Confirm privacy, storage, logging, deletion and retention behavior end to end.
- Deliverable: integrated staging build.

### Phase 5 — Independent validation and release decision

- Evaluate once on the locked participant test cohort or newly recruited external cohort.
- Review errors, intervals, coverage, abstention, subgroup results and usability feedback.
- Release only claims supported by the final evaluation; keep model and data versions traceable.
- Deliverable: final evaluation report and go/no-go record.

## 12. Acceptance criteria

A BodyVision 2.0 implementation is ready for capstone demonstration when all applicable items below are met:

### Data and evaluation

- Every sample has a stable pseudonymous participant ID and measurement provenance.
- No participant, repeat session, or image from one participant crosses train/validation/test partitions.
- The baseline metric is reproducible or its evaluation limitations are documented.
- Model preprocessing and tuning occur only inside grouped training folds; the locked test set is not used for model selection.

### Height

- The estimator documents its calibration source and rejects invalid or missing calibration when required.
- Head and feet visibility, pose, and calibration quality are checked; failures return reason codes.
- Height evaluation reports MAE, bias, error distribution, participant-level confidence intervals, interval coverage, and abstention rate against stadiometer labels.

### Weight

- A-only and A+C modes are both evaluated on identical held-out participants, with feature ablations and provenance.
- Model choice beats or matches the baseline on held-out participants without unacceptable subgroup regressions; all uncertainty in the comparison is reported.
- The system does not claim a target MAE unless the locked test results support it.

### Product/API

- Front and side views are validated independently and jointly; invalid inputs return clear actionable errors.
- Optional inputs can be skipped; the selected mode and features used are visible to the user.
- A prediction response includes model version, estimate, unit, uncertainty interval, quality flags and applicable notice, or abstains.
- Logs exclude raw images and unnecessary sensitive inputs; storage/deletion behavior matches the stated policy.

### Claims and usability

- All public performance statements cite the test cohort, protocol, date, metrics and limitations.
- No clinical-grade, guaranteed, or scale-replacement claims are made without appropriate independent evidence and review.
- Capture flow and retry guidance are usable with keyboard and assistive technology, and a non-camera upload path is available where appropriate.

## 13. Risks and mitigations

| Risk | Why it matters | Mitigation |
|---|---|---|
| Small participant cohort | High variance and overfitting; image count exaggerates sample size | Recruit more unique participants; participant-grouped validation; bootstrap intervals |
| Train/test leakage | Inflated performance if views of the same person cross splits | Group by participant; automate disjointness checks |
| Perspective and camera variation | Pixel scale changes with distance, tilt, and device | Reference object/fixed geometry; quality gates; collect device/setup diversity |
| Clothing, pose, occlusion | Alters silhouette and apparent dimensions | Capture protocol; retries; quality flags; test clothing sensitivity |
| Weight not visually identifiable | Similar silhouettes can have different body composition and mass | Set realistic scope; use A+C as optional predictors; interval and abstention; avoid guarantees |
| Optional input bias/privacy | Sensitive fields can create harm or exclusion | Data minimization, consent, skip option, ablations, subgroup review |
| More complex model overfits | Current cohort is too small for many parameters | Benchmark simple baselines; tune within grouped CV; prefer simpler model absent clear gain |
| Misleading calibration language | Learned regression may be mistaken for physical measurement | Distinguish camera/scale calibration from statistical correction in UI and report |
| Dataset/label mismatch | Scale readings may not align with image session | Record times, repeated readings, protocol deviations and device provenance |
| False certainty in intervals | Miscalibrated uncertainty can mislead users | Independent conformal calibration; coverage checks; suppress unsupported predictions |

## 14. MAE targets: hypotheses, not guarantees

The referenced discussion proposed the following planning ranges:

| Target | Supplied baseline | Research hypothesis for upgraded system | Interpretation |
|---|---:|---:|---|
| Height MAE | 4.143 cm | 2.5–3.5 cm | Possible only if capture/calibration and labels improve; must be measured on unseen participants |
| Weight MAE | 7.277 kg | 4.5–6.0 kg | Ambitious; depends on sample size, representativeness, label quality, and held-out performance |

These ranges are **not guaranteed**, not acceptance promises, and not suitable as marketing claims before independent validation. A stronger camera calibration may improve height; front/side features and optional inputs may help weight, but the improvement could be small, absent, or negative. Small data, distribution shift, and participant diversity all affect results. Report the measured result with uncertainty, including if it misses the hypothesis.

## 15. Recommended first engineering tasks

1. Locate the current feature extraction and evaluation code; document the exact baseline protocol.
2. Audit participant identity and split construction before adding any features.
3. Create the versioned dataset schema and standardized capture/measurement checklist.
4. Implement front/side quality validation and save diagnostics for each feature.
5. Build A-only and A+C feature tables with provenance and missingness handling.
6. Add grouped benchmarking and ablation reports; keep a locked participant test set.
7. Evaluate height calibration paths separately from learned height prediction.
8. Integrate API and UI only after model contracts, failure states, and uncertainty format are settled.
9. Publish a model card and final report with measured test results and limitations.

## 16. Definition of done

The upgrade is complete when BodyVision can collect two controlled views, optionally accept clearly labeled user inputs, return a versioned estimate with validated uncertainty or a meaningful abstention, and demonstrate its performance on participants not used for training or tuning. The final report must compare against the current baseline using the same held-out participants, state the participant count and protocol, disclose uncertainty and limitations, and describe the MAE targets as hypotheses unless the results establish them.
