# BodyVision 2.0 implementation and evaluation audit

## Repository and active pipeline

- `frontend/` contains the React + Vite upload, prediction, feedback, and dataset screens.
- `backend/api/routes.py` exposes `POST /api/predict-body` and dataset/feedback routes.
- `backend/services/height_estimator.py` runs YOLO person detection, MediaPipe Pose and Selfie Segmentation, OpenCV geometry, overlays, and eight image-derived ratios.
- `backend/services/weight_estimator.py` loads the checked-in StandardScaler + Ridge weight model and learned Ridge height calibrator.
- `backend/scripts/train_weight_model.py` performs nested participant-grouped training/evaluation and fits final artifacts.
- `paper/evaluate_grouped.py` writes outer-fold predictions, participant fold assignments, and evaluation metadata.
- `model_specification/` contains the active CSV and images; `backend/models/` contains deployed joblib artifacts.

The height path is a learned Ridge correction to pinhole geometry, not physical camera calibration. Weight features are normalized proportions, including estimated height; they do not represent tape measurements. The legacy API has a fixed ±8 kg range for a Ridge model, which is not a calibrated interval.

## Dataset audit

The active CSV currently has 154 records and 38 participant IDs. The dataset audit found 67 schema-valid front/side pairs across 35 participants, two unpaired captures, 18 rows with an unknown view label, and one CSV image reference that is missing. The remaining image extraction/evaluation scripts either abort on missing files or require `--exclude-missing-images`.

The stored evaluation metadata reports 151 images from 37 participants and the supplied metrics (height MAE 4.143 cm; weight MAE 7.277 kg). Its CSV SHA-256 does not match the current active CSV. Therefore those numbers describe an earlier snapshot, not the present dataset. Re-evaluation of the current CSV (SHA-256 `ad49bc63e7dc87946cb698af6fdb5047760b43031bf54b220b4be032453fd111`) excluded the one missing image and produced the following nested, participant-grouped OOF results:

| Target | Ridge MAE | Training-fold median MAE | Ridge RMSE | Ridge bias |
| --- | ---: | ---: | ---: | ---: |
| Height | 4.092 cm | 6.880 cm | 5.017 cm | +0.646 cm |
| Weight | 7.278 kg | 11.355 kg | 8.667 kg | +0.300 kg |

These are development estimates on 38 participants, not a locked test result. They do not establish improvement over the historical metrics because the CSV snapshot changed. There is no locked external test cohort.

## Participant-safe evaluation

Both grouped evaluation scripts use `GroupKFold` keyed by normalized `person_id`. The paper evaluation now asserts group disjointness for outer and inner boundaries and saves per-image fold assignments, participant-to-fold mapping, feature version, model configuration, and deterministic split method in metadata. The focused leakage test verifies disjoint splits pass and overlapping participant IDs fail.

Height Ridge alpha selection is nested inside the outer participant folds using `StandardScaler` + Ridge and `[0.1, 1, 10, 100]`. Weight uses `StandardScaler` + Ridge(alpha=1) and training-fold out-of-fold calibrated height as its height input. Metrics average predictions and labels by participant. Preprocessing is in scikit-learn pipelines. The current run compares fixed Ridge against a training-fold median and tuned Ridge/Elastic Net searches on identical outer participant folds. Weight MAEs were 7.278 kg for fixed Ridge, 11.355 kg for the median baseline, 7.357 kg for tuned Ridge, and 7.413 kg for Elastic Net. Fixed Ridge remains best among those tested. Tuning uses GroupKFold inside the outer training data. The trainer still aborts on feature-extraction failures, so evaluation does not yet measure an abstention rate. A+C and a properly paired front/side model remain unavailable.

The paper evaluator accepts `--yolo-model` and `--pose-complexity`, records per-image extraction runtime and failure rate, and refuses to report partial-set MAE. YOLO26n was evaluated with Ultralytics 8.4.185 on the same active CSV hash, same five GroupKFold participant splits, 153 available images, and 38 participants as YOLOv8n. Extraction completed with 0/153 failures; mean extraction time was 4.98 s/image in this CPU environment. Grouped height MAE was 4.065 cm and weight MAE was 7.592 kg, versus YOLOv8n's 4.092 cm and 7.278 kg. YOLO26n did not improve weight MAE, so it was not adopted. The 0.027 cm height change does not establish a useful improvement on this small cohort. Candidate weights were not retained. Ultralytics documents YOLO26 under AGPL-3.0 or Enterprise terms; the repository has no project-level license decision, so distribution needs review.

## API and interface changes

`POST /api/predict-body` remains backward compatible by default (`api_version=1`). Version 2 enables upload byte and decoded-dimension limits and heuristic checks for image blur, multiple people, likely truncation, pose visibility, segmentation quality, and likely front/side mismatch. Failures return actionable retry messages. Logs no longer include client filenames.

The experimental `weight_a_only` v2 path still calls the existing single-view Ridge model for each view and averages the two results. It is not a newly trained front/side model and should not be described as a validated BodyVision 2 estimator. Its uncertainty is explicitly uncalibrated. A+C is rejected with HTTP 501 because no participant-grouped model has been trained on consented self-reported inputs; no optional inputs are collected. Height estimation never uses actual height as an input. Heuristic quality thresholds and view checks have not been validated as guarantees.

## Experimental anthropometry proxies

The V2 response now includes `anthropometry-proxy-v1` per-view features: pose-relative chest, waist, abdomen, and hip projected spans divided by detected pixel height, plus shoulder/hip landmark span ratios. Every feature carries a validity flag, stable reason, source view, and normalization. Missing mask bands remain null. These values are explicitly image-space proxies, not tape measurements or physical dimensions, and are not inputs to the deployed Ridge model.

When both views are accepted, the response also includes experimental side-to-front span ratios and a dimensionless elliptical cross-section/body-volume proxy index. Its formula assumes paired, aligned views, elliptical cross-sections, and common pixel-height normalization. It is not physical volume or body composition. The UI shows valid values and states the scale limitation. There is not yet a participant-grouped ablation of these features, so no predictive gain is claimed.

V2 additionally exposes separate detector, view, pose, segmentation, camera calibration, and request status signals. The legacy blended detector/pose score remains only for API V1 compatibility. Camera intrinsics and a known-size reference are not available; height continues to use assumed-FOV geometry with a separate learned Ridge correction.

## Remaining work and limitations

- Collect/verify participant-linked ground truth and view labels, resolve missing images, and preserve consent/provenance.
- The paired-view proxy features are experimental and not included in the trained estimator. Add grouped feature ablations on paired, complete views and train A-only/A+C models only if a suitable, consented labeled dataset exists.
- Run the newly implemented tuned Ridge and Elastic Net candidates on the current snapshot and retain the simplest model only if it improves held-out participants repeatably.
- Validate quality gates and estimate failure coverage; calibrate prediction intervals before returning any interval.
- Obtain a new independent participant cohort for a locked evaluation.
- Finish the MediaPipe Heavy grouped candidate run; benchmark segmentation candidates with an adapter and suitable mask-quality labels. Review Ultralytics licensing before distribution. CatBoost is absent from the environment and is not justified for 38 participants without evidence that it adds value.

No improvement over the stored baseline is claimed. Historical supplied targets remain hypotheses.
