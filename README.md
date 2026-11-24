# BodyVision: Camera-Based Human Height and Weight Estimation

BodyVision is a capstone project that estimates a person's height and weight from
full-body photographs. It combines person detection and pose/segmentation models
with camera geometry and locally trained regression models. A React web
application provides image upload, prediction, dataset review, and feedback
workflows; a FastAPI service runs the computer-vision pipeline and exposes the
training-cohort API.

> **Important:** These are experimental visual estimates, not medical
> measurements. Do not use them in place of a calibrated scale or stadiometer,
> or for medical, employment, eligibility, or other high-stakes decisions.

## What the application does

- Accepts a front-view, full-body image and camera setup measurements.
- Estimates height in centimetres and feet/inches, returning both a raw
  camera-geometry estimate and a dataset-calibrated estimate.
- Estimates weight in kilograms and pounds from visible body proportions. The
  web app's height-and-weight mode requests both front and side images and
  averages their weight predictions; the API also accepts a front image alone.
- Produces annotated images with the detected person box, pose landmarks,
  measurement line, and estimate. Result images can be opened larger for
  inspection.
- After a prediction, the **View prediction pipeline** window shows the raw
  image, separate YOLOv8 detection and MediaPipe pose views (including labeled
  elbow and wrist landmarks), a cleaned person segmentation preview, all eight
  weight-model factors, and geometric/calibrated measurement values.
- Shows a posture warning when the detected knee angles suggest bent knees.
- Supports browsing, searching, correcting, adding, and deleting training
  cohort records through the web app. Dataset edits and feedback can trigger
  model retraining.
- Offers an opt-in v2 visual-only upload path with front/side capture checks.
  It still uses the existing per-image Ridge artifacts and averages two legacy
  predictions; it is not a newly trained multi-view model.

## How estimation works

1. **Person detection:** YOLOv8 detects people (COCO class `0`). The pipeline
   uses the largest detected person whose confidence is at least `0.4`.
2. **Pose and body shape:** MediaPipe Pose estimates body landmarks, including
   shoulders, hips, knees, ankles, heels, and toes. MediaPipe Selfie
   Segmentation supplies silhouette measurements used by the weight model.
3. **Pixel height:** The top of the detected person box and the lowest visible
   heel/toe landmark define the image-space height.
4. **Geometric height:** A pinhole-camera calculation converts the pixel span
   to centimetres using the configured vertical field of view (55 degrees by
   default), camera height, and subject distance. The feet are assumed to be on
   the ground.
5. **Height calibration:** A StandardScaler + Ridge model, trained on the
   project cohort, corrects the geometric estimate for patterns in the
   collected images.
6. **Weight regression:** Eight normalized height/body-proportion features are
   passed to a StandardScaler + Ridge model. When front and side images are
   supplied, their weight predictions and reported ranges are averaged.
7. **Visualization:** OpenCV draws the detection and measurement overlays and
   encodes the result image for the browser.

YOLOv8, MediaPipe Pose, and MediaPipe Selfie Segmentation are learned
deep-learning models. The height geometry and final Ridge regressors are
separate classical calculations/models; the project does not use a deep neural
network to directly regress weight from pixels.

API V1 retains a legacy weighted blend of detector score and MediaPipe nose
visibility. It is not a calibrated probability that a result is correct. V2
reports detector, view, pose, segmentation, and camera-calibration status
separately. Camera intrinsics are not calibrated: geometry uses configured
field of view, camera height and distance, followed by a separate learned Ridge
correction. The V2 weight interval is omitted because there is no validated
uncertainty interval.

V2 returns experimental pose-relative chest, waist, abdomen and hip image spans
normalized by detected pixel height. Paired front/side requests also return
side-to-front span ratios and a dimensionless elliptical cross-section proxy
index. Features include validity and source metadata; invalid mask bands remain
missing. They are not tape measurements, physical dimensions, body volume, or
body composition, and are excluded from the deployed weight model pending
participant-grouped ablation results.

Version 2 upload checks limit each image to 12 MB and 30 megapixels and apply
heuristics for blur, multiple people, likely edge truncation, pose visibility,
segmentation quality, and likely front/side mismatch. These checks are not
calibrated guarantees. Version 2 removes the uncalibrated weight range from its
response. A+C is unavailable because no participant-grouped model has been
trained with self-reported inputs; the application does not ask for those
inputs.

## Technology

- **Frontend:** React, Vite, JavaScript, Axios, Tailwind CSS
- **Backend:** Python 3.13, FastAPI, Uvicorn, Pydantic
- **Vision and models:** OpenCV, Ultralytics YOLOv8, MediaPipe, NumPy,
  scikit-learn, joblib
- **Dataset catalog:** CSV cohort and a local SQLite search index

## Repository layout

```text
backend/
  api/routes.py                 FastAPI prediction and dataset endpoints
  core/config.py                Camera, model, and API settings
  core/models.py                API request/response data models
  models/                       Trained height and weight model artifacts
  scripts/train_weight_model.py Grouped evaluation and model training
  services/height_estimator.py  YOLO, MediaPipe, geometry, and overlays
  services/weight_estimator.py  Model loading, height calibration, and weight inference
  tests/                        Backend unit tests
  requirements.txt             Python dependencies
frontend/
  src/App.jsx                   Web interface
  src/services/api.js           Browser-to-API requests
  package.json                  Frontend scripts and dependencies
model_specification/
  height_weight_dataset.csv     Training labels and camera metadata
  images/                       Referenced training images
report_codes.txt                Source excerpts prepared for the project report
```

Generated caches and environments (including the local dataset search index)
are kept under ignored paths such as `backend/.ultralytics/` and are not needed
in version control.

## Requirements

- Python **3.13** (the repository pins this in `backend/.python-version`)
- Node.js **20.19+** or **22.12+**, and npm (required by the Vite version in
  `frontend/package-lock.json`)
- Internet access on first backend startup so YOLOv8 and MediaPipe model assets
  can be downloaded if they are not already cached

The checked-in trained artifacts are `backend/models/height_calibrator.joblib`
and `backend/models/weight_regressor.joblib`. Ultralytics can download
`yolov8n.pt` automatically when it is not present. MediaPipe Pose and
Selfie-Segmentation task files are also downloaded into the backend cache when
needed.

## Run locally

Open two terminals from the repository root.

### 1. Start the backend

macOS / Linux:

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Windows PowerShell:

```powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The first startup may take longer while model assets are downloaded and loaded.
Keep this terminal running.

### 2. Start the frontend

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open the local URL printed by Vite (normally
[`http://localhost:5173`](http://localhost:5173)). The backend's interactive
API documentation is at [`http://localhost:8000/docs`](http://localhost:8000/docs);
ReDoc is at [`http://localhost:8000/redoc`](http://localhost:8000/redoc).

The frontend defaults to `http://localhost:8000/api`. To use another backend,
create `frontend/.env.local` and set:

```dotenv
VITE_API_URL=http://localhost:8000/api
```

Restart Vite after changing the environment file. The API's allowed development
origins are configured in `backend/core/config.py`.

## Using the application

### Predict measurements

1. Open **Predict Measurements** and upload a clear, well-lit front-view image
   showing the person's full body, including both feet.
2. For the web app's height-and-weight mode, upload a side-view image as well.
   The backend accepts a side image optionally; the browser asks for it when
   weight estimation is selected.
3. Enter the camera height above the ground and the horizontal camera-to-person
   distance. Defaults are 100 cm and 150 cm.
4. Run the prediction and inspect the estimates, posture warning, and annotated
   image. Click an image to inspect it at a larger size.

Use the actual capture setup values when possible. The defaults and assumed
55-degree vertical field of view are approximations; inaccurate camera height,
distance, lens field of view, camera pitch, occlusion, or pose can affect the
result. Stand upright with the entire body visible and feet on the ground.

### Training data and feedback

The **Add Training Data** and **Training Dataset** areas let the user submit
verified measurements, search records, edit participant labels, download the
CSV, and remove participants or images. These operations change the local
`model_specification/height_weight_dataset.csv` and/or its image files.
Successful feedback or relevant edits/deletions start background retraining.
Deleting dataset records or images is destructive; keep a backup before making
bulk changes.

The cohort contains participant names and photographs. Obtain consent and follow
applicable privacy requirements before collecting, sharing, or publishing
images or labels. Do not commit additional private images or identifying
measurements to a public repository without authorization.

## Dataset and model training

The active training cohort is in `model_specification/`. Its CSV contains these
columns:

| Column | Meaning |
| --- | --- |
| `image_id` | Unique image-record identifier |
| `person_id` | Participant group used to keep one person's images together during validation |
| `person_name` | Display name used by dataset-management features |
| `image_path` | Image path relative to `model_specification/`, normally `images/<filename>` |
| `view` | Image view, such as `front` or `side` |
| `subject_distance_cm` | Horizontal camera-to-subject distance |
| `camera_height_cm` | Camera height above the floor |
| `height_cm` | Measured height label |
| `weight_kg` | Measured weight label; blank values are permitted by the trainer |

The trainer checks that image paths stay inside the dataset directory and that
all referenced image files exist. The current repository snapshot has 154 CSV
rows and 38 participant IDs, with one referenced image missing. The audit also
found 18 unknown view labels, 67 valid front/side pairs, and two unpaired
captures. Resolve the missing image or correct/remove its CSV row before
retraining.
Training also requires at least five participant groups with usable data.

To train and replace the default artifacts:

```bash
cd backend
source .venv/bin/activate       # Windows: .\.venv\Scripts\Activate.ps1
python -m scripts.train_weight_model
```

The script extracts image features, evaluates by participant-grouped nested
cross-validation, tunes the height-calibration Ridge alpha over
`[0.1, 1.0, 10.0, 100.0]`, and trains the weight model with Ridge alpha `1.0`.
It prints participant-averaged MAE values and median-baseline comparisons, then
saves both artifacts in `backend/models/`. Since this default overwrites the
existing models, save a candidate elsewhere first if you want to compare it:

```bash
python -m scripts.train_weight_model --model-output-dir ./candidate-models
```

To run evaluation without replacing deployed model files, use:

```bash
cd backend
.venv/bin/python ../paper/evaluate_grouped.py --exclude-missing-images
```

The evaluator writes participant fold assignments, per-image OOF predictions,
feature/model metadata, and grouped metrics to `paper/evaluation_results/`.
It also evaluates nested tuned-Ridge and Elastic Net candidates on the same
participant folds. The current run reports 7.357 kg MAE for tuned Ridge and
7.413 kg for Elastic Net, both worse than the fixed Ridge result, so the fixed
Ridge remains the simplest tested weight model.
On the current CSV snapshot (154 rows, 38 participant IDs, one missing image
excluded), the latest run reported 4.092 cm height MAE and 7.278 kg weight MAE;
the median baselines were 6.880 cm and 11.355 kg. These are grouped
development estimates, not a locked external test result. The historical
4.143/7.277 metrics used a different CSV snapshot and cannot establish that
the model improved or regressed.

To benchmark detector or pose candidates on the same participant folds, pass
`--yolo-model` and/or `--pose-complexity 0|1|2`. The evaluator records per-image
feature-extraction runtime and failure rate, and refuses to publish partial
MAE if any image fails. On the active snapshot, YOLO26n produced height MAE
4.065 cm and weight MAE 7.592 kg, versus the YOLOv8n baseline 4.092 cm and
7.278 kg. It was not adopted. Its mean extraction time was 4.98 seconds per
image in the CPU environment used for that run. Ultralytics licensing should
be reviewed before distributing either model. See [BODYVISION_2_AUDIT.md](BODYVISION_2_AUDIT.md)
for detailed status and remaining limitations.

After training to the default directory while the API is already running,
restart the backend to load the new artifacts. The API's background retraining
workflow reloads models after successful training.

## API reference

The backend exposes interactive request schemas at `/docs`.

| Method and path | Purpose |
| --- | --- |
| `GET /` | Service name, version, status, and docs path |
| `GET /health` | Health check |
| `POST /api/predict-body` | Estimate height and weight from multipart image upload |
| `GET /api/models/info` | Model and camera default information |
| `GET /api/dataset/people` | Search/browse cohort (`search`, `limit`, `offset`) |
| `GET /api/dataset/download` | Download the active training CSV |
| `POST /api/dataset/lookup` | Search by participant name or identical image |
| `POST /api/submit-feedback` | Add verified measurements and images to the cohort |
| `PUT /api/dataset/people` | Update a participant's dataset labels |
| `DELETE /api/dataset/people` | Remove a participant and unshared image files |
| `GET /api/dataset/images/{dataset_key}/{image_name}` | View a cohort image |
| `DELETE /api/dataset/images/{dataset_key}/{image_name}` | Remove an image and its CSV records |

### Prediction request

`POST /api/predict-body` accepts `multipart/form-data`:

| Field | Requirement | Details |
| --- | --- | --- |
| `file` | Required | Front/full-body image: JPG, JPEG, PNG, WEBP, or BMP |
| `file_side` | Optional | Side-view image used to improve/average weight prediction |
| `camera_height_cm` | Optional | Camera height; default 100, allowed 30–500 |
| `distance_cm` | Optional | Subject distance; default 150, allowed 30–2000 |
| `api_version` | Optional | `1` (default compatibility behavior) or `2` (quality-gated behavior) |
| `prediction_mode` | Optional | For v2, `height` or `weight_a_only`; weight requires `file_side` |

The response includes `estimated_height_cm`, `estimated_height_ft`,
`geometric_height_cm`, YOLOv8 `detection_confidence_score`,
`estimated_weight_kg`, `estimated_weight_lb`,
`weight_estimate_range_kg`, `confidence_score`, `posture_warning`, camera
measurements, the person bounding box, and the annotated image as a base64 JPEG.
When a side image is supplied, `annotated_image_base64_side` contains its
annotated result. The `pipeline` object includes the raw and calibrated height,
front/side weight-model estimates, the eight model input factors, distinct
detection/pose overlays, and base64-encoded foreground segmentation previews.
Invalid images or failed person/pose detection return an error response.
V2 responses include `model_version`, `feature_version`, `prediction_mode`,
`features_used`, `quality_flags`, and an approximation notice. V2 A+C returns
HTTP 501 until an appropriate grouped model is available. Version 2 image
limits are 12 MB and 30 megapixels per upload.

## Tests and frontend build

Run the backend unit tests from `backend/` with the virtual environment active:

```bash
python -m unittest discover -s tests -v
```

Type-check and build the frontend from `frontend/`:

```bash
npm ci
npm run build
```

## Troubleshooting

- **The web page cannot reach the API:** Confirm both servers are running and
  that `VITE_API_URL` points to the backend's `/api` base URL. Check the browser
  console and backend terminal for errors.
- **Startup fails while loading model assets:** Check internet access and
  retry. YOLOv8 and MediaPipe assets may need to download the first time.
- **No person or pose is detected:** Use a well-lit, upright, full-body photo
  with the head, legs, and feet unobstructed.
- **Training reports a missing image:** Check every `image_path` in
  `model_specification/height_weight_dataset.csv`; paths are relative to that
  directory and referenced files must exist.
- **Training data changes but model files do not update:** Check the backend
  logs for background training errors. Retraining requires valid CSV rows,
  available images, and enough participant groups.

## Limitations

- The camera model uses a fixed vertical field of view and depends on user
  supplied camera height and subject distance.
- The method assumes one dominant, upright person with feet on the ground and
  visible body landmarks. Cropping, occlusion, unusual poses, perspective, and
  lens distortion can degrade estimates.
- Weight is inferred from visible shape features and a relatively small
  participant cohort; clothing and body composition are not directly measured.
- A high detection/landmark confidence does not guarantee a small height or
  weight error. Treat results as research prototypes, not ground truth.
