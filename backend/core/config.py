"""
core/config.py — Application Settings
======================================
Central place for all configurable constants.
Change values here; everything else reads from this module.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Settings:
    # ---- Project metadata ----
    PROJECT_NAME: str = "Human Height Estimator API"
    VERSION: str = "1.0.0"

    # ---- CORS ----
    CORS_ORIGINS: List[str] = field(default_factory=lambda: [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
    ])

    # ---- Camera defaults ----
    DEFAULT_CAMERA_HEIGHT_CM: float = 140.0   # camera mounted at 140 cm from ground
    DEFAULT_DISTANCE_CM: float = 200.0         # person is 200 cm from the camera

    # ---- Camera geometry ----
    VERTICAL_FOV_DEG: float = 55.0            # vertical field-of-view (typical webcam/phone)

    # ---- YOLOv8 ----
    YOLO_MODEL_PATH: str = "yolov8n.pt"       # swap to yolov8s.pt / yolov8m.pt for accuracy
    YOLO_PERSON_CLASS_ID: int = 0             # COCO class 0 = person
    YOLO_CONF_THRESHOLD: float = 0.4          # min detection confidence

    # ---- MediaPipe ----
    MP_MODEL_COMPLEXITY: int = 2              # 0=lite, 1=full, 2=heavy
    MP_MIN_DETECTION_CONF: float = 0.5

    # ---- Output image quality ----
    JPEG_QUALITY: int = 88                    # JPEG encoding quality (0–100)


settings = Settings()
