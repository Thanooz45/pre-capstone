"""
api/routes.py — API Route Definitions
======================================
Exposes:
  POST /api/predict-height   — main height estimation endpoint
  GET  /api/models/info      — info about loaded models
"""

import os
import shutil
import tempfile
import logging
import csv
import subprocess
import asyncio
import time
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from core.config import settings
from core.models import HeightResponse, ErrorResponse
from services.height_estimator import estimate_height
from services.weight_estimator import calibrate_height, estimate_weight

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Height & Weight Estimation"])


# ---------------------------------------------------------------------------
# POST /api/predict-height
# ---------------------------------------------------------------------------
@router.post(
    "/predict-body",
    response_model=HeightResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request (no person detected, invalid image, etc.)"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Estimate human height and weight from an uploaded image",
    description=(
        "**Pipeline:**\n\n"
        "1. **YOLOv8** — detects the person bounding box (COCO class 0)\n"
        "2. **MediaPipe Pose** — extracts head, nose, ankle, and heel landmarks\n"
        "3. **Pixel height** — computed from estimated head-top → lowest heel\n"
        "4. **Pinhole Camera Geometry** — converts pixel height to real-world cm\n"
        "5. **OpenCV** — draws green bounding box, red keypoints, blue measurement line\n\n"
        "Returns height in **cm** and **feet/inches**, a confidence score, "
        "and the annotated image as **base64 JPEG**."
    ),
)
async def predict_body(
    file: UploadFile = File(..., description="Full-body image of the person (JPG / PNG / WEBP)."),
    file_side: UploadFile = File(None, description="Optional side-view image for better weight estimation."),
    camera_height_cm: float = Form(
        default=settings.DEFAULT_CAMERA_HEIGHT_CM,
        ge=30.0,
        le=500.0,
        description="Height of the camera above the ground in centimetres.",
    ),
    distance_cm: float = Form(
        default=settings.DEFAULT_DISTANCE_CM,
        ge=30.0,
        le=2000.0,
        description="Horizontal distance from the camera to the person in centimetres.",
    ),
):
    # --- Validate file type ---
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Uploaded file must be an image (JPG, PNG, or WEBP).",
        )

    # --- Save to temp file ---
    suffix = os.path.splitext(file.filename or "upload.jpg")[-1].lower() or ".jpg"
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    if suffix not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{suffix}'. Use JPG, PNG, or WEBP.",
        )

    tmp_path = None
    tmp_path_side = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        if file_side:
            side_suffix = os.path.splitext(file_side.filename or "upload_side.jpg")[-1].lower() or ".jpg"
            with tempfile.NamedTemporaryFile(delete=False, suffix=side_suffix) as tmp_side:
                shutil.copyfileobj(file_side.file, tmp_side)
                tmp_path_side = tmp_side.name

        logger.info(
            "predict-body called | file=%s side_file=%s camera_h=%.1f dist=%.1f",
            file.filename,
            file_side.filename if file_side else "None",
            camera_height_cm,
            distance_cm,
        )

        result = estimate_height(
            image_path=tmp_path,
            camera_height_cm=camera_height_cm,
            distance_cm=distance_cm,
        )
        features = result.pop("_weight_features")
        geometric_height = result["estimated_height_cm"]
        calibrated_height = calibrate_height(features)
        
        # Base result
        features["estimated_height_cm"] = calibrated_height
        result["geometric_height_cm"] = geometric_height
        result["estimated_height_cm"] = round(calibrated_height, 1)
        total_inches = calibrated_height / 2.54
        result["estimated_height_ft"] = f"{int(total_inches // 12)}' {round(total_inches % 12, 1)}\""
        
        # Estimate weight (Front)
        front_weight_est = estimate_weight(features)
        
        # If side image provided, average the weight estimates
        if tmp_path_side:
            side_result = estimate_height(
                image_path=tmp_path_side,
                camera_height_cm=camera_height_cm,
                distance_cm=distance_cm,
            )
            side_features = side_result.pop("_weight_features")
            side_features["estimated_height_cm"] = calibrate_height(side_features)
            side_weight_est = estimate_weight(side_features)
            
            # Average the predictions
            front_kg = front_weight_est["estimated_weight_kg"]
            side_kg = side_weight_est["estimated_weight_kg"]
            avg_kg = (front_kg + side_kg) / 2
            
            front_range = front_weight_est["weight_estimate_range_kg"]
            side_range = side_weight_est["weight_estimate_range_kg"]
            
            result["estimated_weight_kg"] = round(avg_kg, 1)
            result["estimated_weight_lb"] = round(avg_kg * 2.20462, 1)
            result["weight_estimate_range_kg"] = [
                round((front_range[0] + side_range[0]) / 2, 1),
                round((front_range[1] + side_range[1]) / 2, 1)
            ]
            result["weight_model_available"] = front_weight_est["weight_model_available"]
            result["annotated_image_base64_side"] = side_result["annotated_image_base64"]
        else:
            result.update(front_weight_est)
            result["annotated_image_base64_side"] = None

        return JSONResponse(content=result)

    except ValueError as exc:
        # Known pipeline errors (no person, no pose, etc.)
        logger.warning("Pipeline error: %s", exc)
        return JSONResponse(
            status_code=400,
            content={"error": str(exc), "detail": None},
        )
    except Exception as exc:
        logger.exception("Unexpected error in predict_height")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error.", "detail": str(exc)},
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        if tmp_path_side and os.path.exists(tmp_path_side):
            os.remove(tmp_path_side)


def run_training_task():
    try:
        script_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "train_weight_model.py")
        subprocess.run(["python", script_path], check=True)
        logger.info("Background model training completed successfully.")
    except Exception as e:
        logger.error(f"Background model training failed: {e}")


@router.post(
    "/submit-feedback",
    summary="Submit accurate user height/weight data and retrain model",
)
async def submit_feedback(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Front view image."),
    file_side: UploadFile = File(None, description="Side view image (optional)."),
    actual_height_cm: float = Form(...),
    actual_weight_kg: float = Form(...),
    camera_height_cm: float = Form(default=140.0),
    distance_cm: float = Form(default=200.0),
):
    try:
        dataset_dir = Path(__file__).resolve().parents[2] / "dataset_of_height_weight_updated"
        images_dir = dataset_dir / "images"
        csv_path = dataset_dir / "Output_data.csv"
        
        images_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = int(time.time())
        front_filename = f"user_front_{timestamp}_{file.filename}"
        
        with open(images_dir / front_filename, "wb") as f:
            shutil.copyfileobj(file.file, f)
            
        new_rows = []
        new_rows.append({
            "Image Name": front_filename,
            "Name": f"User_{timestamp}",
            "Height (cm)": actual_height_cm,
            "Weight (kg)": actual_weight_kg,
            "Distance from camera (cm)": distance_cm,
            "Camera height from ground (cm)": camera_height_cm
        })
        
        if file_side:
            side_filename = f"user_side_{timestamp}_{file_side.filename}"
            with open(images_dir / side_filename, "wb") as f:
                shutil.copyfileobj(file_side.file, f)
            new_rows.append({
                "Image Name": side_filename,
                "Name": f"User_{timestamp}_Side",
                "Height (cm)": actual_height_cm,
                "Weight (kg)": actual_weight_kg,
                "Distance from camera (cm)": distance_cm,
                "Camera height from ground (cm)": camera_height_cm
            })
            
        file_exists = csv_path.exists()
        with open(csv_path, "a", newline="", encoding="utf-8-sig") as csvfile:
            fieldnames = [
                "Image Name", "Name", "Height (ft-in)", "Height (cm)", 
                "Weight (kg)", "Distance from camera (cm)", "Camera height from ground (cm)"
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            for row in new_rows:
                # Add dummy ft-in if needed
                total_inches = row["Height (cm)"] / 2.54
                row["Height (ft-in)"] = f"{int(total_inches // 12)}'{round(total_inches % 12, 1)}\""
                writer.writerow(row)
                
        # Trigger background training
        background_tasks.add_task(run_training_task)
        
        return JSONResponse(content={"message": "Feedback submitted successfully! The model will retrain in the background."})
    except Exception as exc:
        logger.exception("Error in submit-feedback")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error.", "detail": str(exc)},
        )


# ---------------------------------------------------------------------------
# GET /api/models/info
# ---------------------------------------------------------------------------
@router.get(
    "/models/info",
    summary="Get information about the loaded AI models",
    tags=["Meta"],
)
def models_info():
    """Returns which models are loaded and the current camera parameter defaults."""
    return {
        "yolo_model": settings.YOLO_MODEL_PATH,
        "yolo_conf_threshold": settings.YOLO_CONF_THRESHOLD,
        "mediapipe_complexity": settings.MP_MODEL_COMPLEXITY,
        "mediapipe_min_detection_conf": settings.MP_MIN_DETECTION_CONF,
        "default_camera_height_cm": settings.DEFAULT_CAMERA_HEIGHT_CM,
        "default_distance_cm": settings.DEFAULT_DISTANCE_CM,
        "vertical_fov_deg": settings.VERTICAL_FOV_DEG,
        "weight_prediction": "Train scripts/train_weight_model.py with the supplied dataset before use.",
    }
