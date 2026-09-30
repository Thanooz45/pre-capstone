# Height and Weight Estimator: Run Guide

## What is complete

- The existing height pipeline remains in place: YOLO detects the person, MediaPipe Pose finds landmarks, and camera distance/height are used for the geometric height estimate.
- A height-calibration model is trained from the labelled heights. It corrects systematic phone-lens, camera-pitch, and landmark bias before height is displayed and before weight is estimated.
- A combined API endpoint, `POST /api/predict-body`, now returns height and weight.
- Weight uses the calculated height plus visible shoulder/hip proportions and a MediaPipe silhouette. A local Random Forest regressor was trained from all 36 records in `dataset_of_height_weight_updated`.
- The web interface now shows estimated weight in kg/lb and an uncertainty range.
- The trained models are saved at `backend/models/height_calibrator.joblib` and `backend/models/weight_regressor.joblib`.

## Start the application

Open two terminals at the project root (`D:\capstone`).

Terminal 1 – backend:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Terminal 2 – frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open the address Vite prints (normally `http://localhost:5173`). Enter the real camera height and subject distance used when the photo was taken, then upload a clear, straight, full-body image.

## Retrain after changing the dataset

Run this whenever you add, correct, or remove rows/images in `dataset_of_height_weight_updated`:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python scripts\train_weight_model.py
```

The CSV must keep these columns: image name, height, weight, distance from camera, and camera height. Images must be inside `dataset_of_height_weight_updated/images`.

## Important limits and your next steps

Weight cannot be measured exactly from one 2D image: body depth, clothing, pose, and muscle/fat composition are not visible reliably. The supplied dataset has only 36 images and several are the same people at different distances, so treat the displayed weight and range as a capstone demonstration, not medical or scale-grade output.

The displayed height is not memorised from the CSV. The application first calculates height from camera geometry, then applies a regularised calibration trained on labelled data. In five-fold validation during the latest training run, calibrated height had a mean absolute error of **5.7 cm**. This is an estimate from a very small data set, not a guarantee for a new person or a different phone/camera setup.

For better results, collect many more distinct people (ideally hundreds or thousands), record verified scale weights, include varied body types, use the same full-body front-facing pose and consistent camera measurements, and keep a separate test set of people never used for training. Then retrain with the command above and compare predictions against their known weights.
