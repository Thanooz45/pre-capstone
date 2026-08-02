"""
services/height_estimator.py — Core AI Pipeline
================================================
Human Height Estimation from a single image.

Pipeline (5 steps):
  1. YOLOv8       → detect person bounding box
  2. MediaPipe    → extract head / nose / ankle / heel keypoints
  3. Pixel height → compute head-top to heel distance in pixels
  4. Pinhole Geo  → convert pixel distance to real-world centimetres
  5. OpenCV       → draw annotated overlays on the image

The models are loaded ONCE via load_models() (called at app startup),
so every subsequent request is fast.
"""

import base64
import logging
import math
import os
from pathlib import Path
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np

# Keep Ultralytics' runtime settings local to this project.  This avoids a
# startup failure when the user's roaming AppData folder is not writable.
os.environ.setdefault("YOLO_CONFIG_DIR", str(Path(__file__).resolve().parents[1] / ".ultralytics"))
from ultralytics import YOLO

from core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level model handles (populated by load_models())
# ---------------------------------------------------------------------------
_yolo_model: Optional[YOLO] = None
_pose: Optional[mp.solutions.pose.Pose] = None


def load_models() -> None:
    """
    Pre-load YOLOv8 and MediaPipe Pose models.
    Called once on application startup via FastAPI lifespan.
    Safe to call multiple times (no-op if already loaded).
    """
    global _yolo_model, _pose

    if _yolo_model is None:
        logger.info("Loading YOLOv8 model: %s", settings.YOLO_MODEL_PATH)
        _yolo_model = YOLO(settings.YOLO_MODEL_PATH)
        logger.info("YOLOv8 loaded.")

    if _pose is None:
        logger.info("Loading MediaPipe Pose (complexity=%d)…", settings.MP_MODEL_COMPLEXITY)
        _pose = mp.solutions.pose.Pose(
            static_image_mode=True,
            model_complexity=settings.MP_MODEL_COMPLEXITY,
            enable_segmentation=False,
            min_detection_confidence=settings.MP_MIN_DETECTION_CONF,
        )
        logger.info("MediaPipe Pose loaded.")


def _ensure_models_loaded() -> None:
    """Lazy-load if load_models() was not called at startup."""
    if _yolo_model is None or _pose is None:
        load_models()


# ---------------------------------------------------------------------------
# Helper: Pinhole Camera Geometry
# ---------------------------------------------------------------------------
def _pixel_to_real_height(
    y_top: float,
    y_bottom: float,
    image_height_px: int,
    distance_cm: float,
    camera_height_cm: float,
) -> float:
    """
    Convert vertical pixel points to real-world height using the pinhole camera model,
    taking into account the camera's height and pitch angle.
    """
    vfov_rad = math.radians(settings.VERTICAL_FOV_DEG)
    f_y = (image_height_px / 2.0) / math.tan(vfov_rad / 2.0)

    # Calculate angles relative to the camera's optical axis
    # Positive alpha means the point is above the center of the image
    dy_top = (image_height_px / 2.0) - y_top
    dy_bottom = (image_height_px / 2.0) - y_bottom

    alpha_top = math.atan(dy_top / f_y)
    alpha_bottom = math.atan(dy_bottom / f_y)

    # Determine camera pitch (theta) based on the feet being on the ground
    # Angle of the ray to the feet below horizontal
    ray_bottom_below_horiz = math.atan(camera_height_cm / distance_cm)
    
    # phi_bottom is the absolute angle of the bottom ray (negative means below horizontal)
    phi_bottom = -ray_bottom_below_horiz
    
    # Camera pitch (theta) = phi_bottom - alpha_bottom
    theta = phi_bottom - alpha_bottom
    
    # Absolute angle of the top ray
    phi_top = theta + alpha_top
    
    # Height of the top point relative to the camera
    h_top_relative = distance_cm * math.tan(phi_top)
    
    # Total height is camera height + relative top height
    total_height = camera_height_cm + h_top_relative
    
    return max(0.0, total_height)


# ---------------------------------------------------------------------------
# Helper: Unit conversion
# ---------------------------------------------------------------------------
def _cm_to_feet_inches(cm: float) -> tuple[int, float]:
    total_inches = cm / 2.54
    feet = int(total_inches // 12)
    inches = round(total_inches % 12, 1)
    return feet, inches


# ---------------------------------------------------------------------------
# Helper: Draw overlays
# ---------------------------------------------------------------------------
def _draw_overlays(
    overlay: np.ndarray,
    x1: int, y1: int, x2: int, y2: int,
    det_conf: float,
    landmarks: dict,
    head_top: tuple[int, int],
    heel: tuple[int, int],
    estimated_cm: float,
    feet: int,
    inches: float,
) -> None:
    """
    Draws all visual overlays directly onto `overlay` (in-place).
    """
    # --- Green bounding box ---
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 210, 0), 3)
    cv2.putText(
        overlay,
        f"Person  {det_conf:.0%}",
        (x1, max(y1 - 12, 20)),
        cv2.FONT_HERSHEY_DUPLEX, 0.75, (0, 210, 0), 2, cv2.LINE_AA,
    )

    # --- Full skeleton pose wireframe ---
    skeleton_connections = [
        ('left_shoulder', 'right_shoulder'),
        ('left_shoulder', 'left_hip'),
        ('right_shoulder', 'right_hip'),
        ('left_hip', 'right_hip'),
        ('left_hip', 'left_knee'),
        ('right_hip', 'right_knee'),
        ('left_knee', 'left_ankle'),
        ('right_knee', 'right_ankle'),
        ('left_ankle', 'left_heel'),
        ('right_ankle', 'right_heel'),
        ('left_ankle', 'left_toe'),
        ('right_ankle', 'right_toe'),
    ]
    for p1_name, p2_name in skeleton_connections:
        if p1_name in landmarks and p2_name in landmarks:
            p1 = landmarks[p1_name]
            p2 = landmarks[p2_name]
            cv2.line(overlay, p1, p2, (0, 255, 255), 2, cv2.LINE_AA)
            cv2.circle(overlay, p1, 4, (0, 165, 255), -1, cv2.LINE_AA)
            cv2.circle(overlay, p2, 4, (0, 165, 255), -1, cv2.LINE_AA)

    # --- Highlight Y_top and Y_bottom ---
    mid_x = (head_top[0] + heel[0]) // 2
    # Red dot with horizontal marker line for Y_top
    cv2.circle(overlay, head_top, 6, (0, 0, 255), -1, cv2.LINE_AA)
    cv2.line(overlay, (mid_x - 30, head_top[1]), (mid_x + 30, head_top[1]), (0, 0, 255), 2, cv2.LINE_AA)
    
    # Green dot with horizontal marker line for Y_bottom
    cv2.circle(overlay, heel, 6, (0, 255, 0), -1, cv2.LINE_AA)
    cv2.line(overlay, (mid_x - 30, heel[1]), (mid_x + 30, heel[1]), (0, 255, 0), 2, cv2.LINE_AA)

    # --- Blue bounding vertical line ---
    cv2.line(overlay, (mid_x, head_top[1]), (mid_x, heel[1]), (255, 100, 0), 2, cv2.LINE_AA)

    # --- Height label (shadow + text) ---
    label = f"{estimated_cm:.1f} cm  ({feet}' {inches}\")"
    text_x = mid_x + 14
    text_y = head_top[1] + (heel[1] - head_top[1]) // 2

    # Drop shadow
    cv2.putText(overlay, label, (text_x + 2, text_y + 2),
                cv2.FONT_HERSHEY_DUPLEX, 0.85, (0, 0, 0), 3, cv2.LINE_AA)
    # Foreground
    cv2.putText(overlay, label, (text_x, text_y),
                cv2.FONT_HERSHEY_DUPLEX, 0.85, (255, 120, 30), 2, cv2.LINE_AA)


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------
def estimate_height(
    image_path: str,
    camera_height_cm: float = settings.DEFAULT_CAMERA_HEIGHT_CM,
    distance_cm: float = settings.DEFAULT_DISTANCE_CM,
) -> dict:
    """
    Run the full height-estimation pipeline on a single image file.

    Parameters
    ----------
    image_path      : Absolute path to the input image (JPG / PNG / WEBP).
    camera_height_cm: Height of the camera above the ground in centimetres.
    distance_cm     : Horizontal distance from the camera to the subject in cm.

    Returns
    -------
    dict with keys:
        estimated_height_cm     (float)
        estimated_height_ft     (str)
        confidence_score        (float, 0–1)
        pixel_height            (int)
        bounding_box            (dict: x1, y1, x2, y2)
        camera_height_cm        (float, echo of input)
        distance_cm             (float, echo of input)
        annotated_image_base64  (str, base64-encoded JPEG)

    Raises
    ------
    ValueError  — if the image cannot be read, no person is found, or
                  MediaPipe fails to detect any pose landmarks.
    """
    _ensure_models_loaded()

    # =========================================================
    # STEP 0 — Load image
    # =========================================================
    image_bgr = cv2.imread(image_path)
    if image_bgr is None:
        raise ValueError(f"Cannot read image at path: {image_path}")

    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    img_h, img_w = image_bgr.shape[:2]
    overlay = image_bgr.copy()  # work on a copy; original stays clean

    logger.debug("Image loaded: %dx%d px", img_w, img_h)

    # =========================================================
    # STEP 1 — YOLOv8: person detection
    # =========================================================
    yolo_results = _yolo_model(image_rgb, verbose=False)[0]
    boxes = yolo_results.boxes

    person_boxes: list[tuple[int, int, int, int, float]] = []
    if boxes is not None:
        for box in boxes:
            cls_id = int(box.cls[0].item())
            conf   = float(box.conf[0].item())
            if cls_id == settings.YOLO_PERSON_CLASS_ID and conf >= settings.YOLO_CONF_THRESHOLD:
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                person_boxes.append((x1, y1, x2, y2, conf))

    if not person_boxes:
        raise ValueError(
            "No person detected in the image. "
            "Please use a clear, well-lit, full-body photo. "
            f"(YOLO confidence threshold: {settings.YOLO_CONF_THRESHOLD:.0%})"
        )

    # Select the largest bounding box (dominant / closest person)
    person_boxes.sort(key=lambda b: (b[2] - b[0]) * (b[3] - b[1]), reverse=True)
    x1, y1, x2, y2, det_conf = person_boxes[0]
    logger.debug("Best person box: (%d,%d)→(%d,%d)  conf=%.2f", x1, y1, x2, y2, det_conf)

    # =========================================================
    # STEP 2 — MediaPipe Pose: keypoint extraction
    # =========================================================
    pad = 15  # px padding around the detected crop
    cx1 = max(0,     x1 - pad)
    cy1 = max(0,     y1 - pad)
    cx2 = min(img_w, x2 + pad)
    cy2 = min(img_h, y2 + pad)

    crop_rgb  = image_rgb[cy1:cy2, cx1:cx2]
    crop_h, crop_w = crop_rgb.shape[:2]

    pose_result = _pose.process(crop_rgb)

    if not pose_result.pose_landmarks:
        raise ValueError(
            "MediaPipe Pose could not detect any keypoints in the image. "
            "Try a well-lit photo where the full body is visible."
        )

    lms = pose_result.pose_landmarks.landmark

    # MediaPipe landmark indices used:
    #   0  = Nose
    #   7  = Left ear,    8  = Right ear
    #  11  = Left shoulder, 12 = Right shoulder
    #  23  = Left hip,    24 = Right hip
    #  25  = Left knee,   26 = Right knee
    #  27  = Left ankle,  28 = Right ankle
    #  29  = Left heel,   30 = Right heel
    #  31  = Left toe,    32 = Right toe
    def lm_abs(lm) -> tuple[int, int]:
        """Convert normalised landmark → absolute image coordinates."""
        return (
            int(lm.x * crop_w) + cx1,
            int(lm.y * crop_h) + cy1,
        )

    landmarks_dict = {
        'nose': lm_abs(lms[0]),
        'left_ear': lm_abs(lms[7]),
        'right_ear': lm_abs(lms[8]),
        'left_shoulder': lm_abs(lms[11]),
        'right_shoulder': lm_abs(lms[12]),
        'left_hip': lm_abs(lms[23]),
        'right_hip': lm_abs(lms[24]),
        'left_knee': lm_abs(lms[25]),
        'right_knee': lm_abs(lms[26]),
        'left_ankle': lm_abs(lms[27]),
        'right_ankle': lm_abs(lms[28]),
        'left_heel': lm_abs(lms[29]),
        'right_heel': lm_abs(lms[30]),
        'left_toe': lm_abs(lms[31]),
        'right_toe': lm_abs(lms[32]),
    }

    # =========================================================
    # STEP 3 — Pixel boundary logic
    # =========================================================
    # Head Apex (Top Point):
    y_ears = (landmarks_dict['left_ear'][1] + landmarks_dict['right_ear'][1]) / 2.0
    y_shoulders = (landmarks_dict['left_shoulder'][1] + landmarks_dict['right_shoulder'][1]) / 2.0
    h_head = abs(y_shoulders - y_ears) * 1.2
    y_top = int(y_ears - h_head)
    
    mid_x = int((landmarks_dict['left_shoulder'][0] + landmarks_dict['right_shoulder'][0]) / 2.0)
    head_top = (mid_x, y_top)

    # Ground Contact (Bottom Point):
    y_bottom = max(
        landmarks_dict['left_heel'][1],
        landmarks_dict['right_heel'][1],
        landmarks_dict['left_toe'][1],
        landmarks_dict['right_toe'][1]
    )
    # Find x for bottom by picking the lowest point's x
    bottom_points = [
        landmarks_dict['left_heel'], landmarks_dict['right_heel'], 
        landmarks_dict['left_toe'], landmarks_dict['right_toe']
    ]
    bottom_pt = max(bottom_points, key=lambda p: p[1])
    heel = (bottom_pt[0], int(y_bottom))
    
    pixel_height = abs(y_bottom - y_top)
    if pixel_height < 10:
        raise ValueError(
            "Detected person is too small in the frame. "
            "Please use a photo where the full body is clearly visible."
        )

    # Posture warning (knee angles)
    def angle(p1, p2, p3):
        # angle at p2
        v1 = np.array(p1) - np.array(p2)
        v2 = np.array(p3) - np.array(p2)
        cosine_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
        return np.degrees(np.arccos(np.clip(cosine_angle, -1.0, 1.0)))
    
    left_knee_angle = angle(landmarks_dict['left_hip'], landmarks_dict['left_knee'], landmarks_dict['left_ankle'])
    right_knee_angle = angle(landmarks_dict['right_hip'], landmarks_dict['right_knee'], landmarks_dict['right_ankle'])
    posture_warning = left_knee_angle < 160 or right_knee_angle < 160

    logger.debug("Pixel height: %d px  (head_top_y=%d, heel_y=%d)", pixel_height, y_top, y_bottom)

    # =========================================================
    # STEP 4 — Geometric height calculation
    # =========================================================
    estimated_cm = _pixel_to_real_height(float(y_top), float(y_bottom), img_h, distance_cm, camera_height_cm)
    feet, inches = _cm_to_feet_inches(estimated_cm)

    # Confidence: weighted blend of YOLOv8 box confidence + nose visibility
    pose_visibility = float(lms[0].visibility)
    confidence = round(det_conf * 0.6 + pose_visibility * 0.4, 3)

    logger.info(
        "Result: %.1f cm (%d'%.1f\")  confidence=%.2f",
        estimated_cm, feet, inches, confidence,
    )

    # =========================================================
    # STEP 5 — Draw overlays
    # =========================================================
    _draw_overlays(
        overlay=overlay,
        x1=x1, y1=y1, x2=x2, y2=y2,
        det_conf=det_conf,
        landmarks=landmarks_dict,
        head_top=head_top,
        heel=heel,
        estimated_cm=estimated_cm,
        feet=feet,
        inches=inches,
    )

    # =========================================================
    # STEP 6 — Encode annotated image → base64 JPEG
    # =========================================================
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, settings.JPEG_QUALITY]
    success, buffer = cv2.imencode(".jpg", overlay, encode_params)
    if not success:
        raise RuntimeError("Failed to encode annotated image to JPEG.")

    annotated_b64 = base64.b64encode(buffer).decode("utf-8")

    return {
        "estimated_height_cm": round(estimated_cm, 1),
        "estimated_height_ft": f"{feet}' {inches}\"",
        "confidence_score":    confidence,
        "pixel_height":        pixel_height,
        "bounding_box":        {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
        "camera_height_cm":    camera_height_cm,
        "distance_cm":         distance_cm,
        "posture_warning":     bool(posture_warning),
        "annotated_image_base64": annotated_b64,
    }
