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

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from core.config import settings
from core.models import HeightResponse, ErrorResponse
from services.height_estimator import estimate_height

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Height Estimation"])


# ---------------------------------------------------------------------------
# POST /api/predict-height
# ---------------------------------------------------------------------------
@router.post(
    "/predict-height",
    response_model=HeightResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request (no person detected, invalid image, etc.)"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Estimate human height from an uploaded image",
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
async def predict_height(
    file: UploadFile = File(..., description="Full-body image of the person (JPG / PNG / WEBP)."),
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
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        logger.info(
            "predict-height called | file=%s size=%d camera_h=%.1f dist=%.1f",
            file.filename,
            os.path.getsize(tmp_path),
            camera_height_cm,
            distance_cm,
        )

        result = estimate_height(
            image_path=tmp_path,
            camera_height_cm=camera_height_cm,
            distance_cm=distance_cm,
        )
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
    }
