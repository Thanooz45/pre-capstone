# Height and Weight Estimator: Run Guide

## What is complete

- The existing height pipeline remains in place: YOLO detects the person, MediaPipe Pose finds landmarks, and camera distance/height are used for the geometric height estimate.
- A height-calibration model is trained from the labelled heights. It corrects systematic phone-lens, camera-pitch, and landmark bias before height is displayed and before weight is estimated.
- A combined API endpoint, `POST /api/predict-body`, now returns height and weight.
- Weight uses the calculated height plus visible shoulder/hip proportions and a MediaPipe silhouette. The local Random Forest regressor and height calibrator train from the image-level CSV in `model_specification/height_weight_dataset.csv`.
- The feedback form adds labeled images to that same CSV and starts background retraining; the running API reloads the trained models after a successful run.
- The web interface now shows estimated weight in kg/lb and an uncertainty range.
- The dataset browser supports name search and editing names, heights, and weights for records in `model_specification`; saved changes update the CSV and trigger model retraining.
- The trained models are saved at `backend/models/height_calibrator.joblib` and `backend/models/weight_regressor.joblib`.

## Start the application

Open two terminals at the project root.

Terminal 1 – backend:

```bash
cd backend
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

On Windows PowerShell, activate `.\venv\Scripts\Activate.ps1` instead of `source .venv/bin/activate`.

Terminal 2 – frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open the address Vite prints (normally `http://localhost:5173`). Camera height defaults to 100 cm and subject distance defaults to 150 cm; adjust both to the actual measurements for each photo before uploading a clear, straight, full-body image.

## Retrain after changing the dataset

Run this whenever you add, correct, or remove rows/images in `model_specification`:

```bash
cd backend
source .venv/bin/activate
python -m scripts.train_weight_model
```

The CSV has one row per image and includes `person_id`, `image_path`, `subject_distance_cm`, `camera_height_cm`, `height_cm`, and `weight_kg`. Images must exist under `model_specification/images`. Record the actual camera height and subject distance for each image. Validation keeps all images of a person together so the same person cannot appear in both training and evaluation folds. The script reports grouped held-out-person MAE for height and weight.

On Windows PowerShell, activate `.\venv\Scripts\Activate.ps1` and run `python -m scripts.train_weight_model` from `backend`.

## Important limits and your next steps

Weight cannot be measured exactly from one 2D image: body depth, clothing, pose, and muscle/fat composition are not visible reliably. The supplied dataset has 84 images from 22 people, with multiple images of the same person at different distances, so treat the displayed weight and range as a capstone demonstration, not medical or scale-grade output.

The displayed height is not memorised from the CSV. The application first calculates height from camera geometry, then applies a regularised calibration trained on labelled data. The training script reports grouped held-out-person errors after each run. These estimates are from a very small dataset and are not guarantees for a new person or a different phone/camera setup.

For better results, collect many more distinct people (ideally hundreds or thousands), record verified scale weights, include varied body types, use the same full-body front-facing pose and consistent camera measurements, and keep a separate test set of people never used for training. Then retrain with the command above and compare predictions against their known weights.
