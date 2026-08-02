"""
core/models.py — Pydantic Response Models
==========================================
Defines the typed data contracts returned by the API.
"""

from pydantic import BaseModel, Field


class HeightResponse(BaseModel):
    """Response payload for POST /api/predict-height."""

    estimated_height_cm: float = Field(
        ...,
        description="Estimated real-world height in centimetres.",
        example=174.5,
    )
    estimated_height_ft: str = Field(
        ...,
        description="Height formatted as feet and inches (e.g. 5'8.7\").",
        example="5'8.7\"",
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Composite confidence score [0–1] derived from YOLOv8 "
            "detection confidence (60%) and MediaPipe nose visibility (40%)."
        ),
        example=0.87,
    )
    pixel_height: int = Field(
        ...,
        description="Vertical pixel distance from estimated head-top to heel.",
        example=412,
    )
    bounding_box: dict = Field(
        ...,
        description="YOLOv8 person bounding box coordinates {x1, y1, x2, y2}.",
        example={"x1": 50, "y1": 10, "x2": 300, "y2": 620},
    )
    camera_height_cm: float = Field(
        ...,
        description="Camera height used for calculation (echo of input).",
        example=140.0,
    )
    distance_cm: float = Field(
        ...,
        description="Distance from camera used for calculation (echo of input).",
        example=200.0,
    )
    annotated_image_base64: str = Field(
        ...,
        description=(
            "JPEG image encoded in base64 with overlays: "
            "green bounding box, red keypoint dots, blue measurement line, "
            "and height label."
        ),
    )
    posture_warning: bool = Field(
        False,
        description="True if bent knees are detected, indicating incorrect posture.",
    )


class ErrorResponse(BaseModel):
    """Standard error payload."""
    error: str = Field(..., description="Human-readable error message.")
    detail: str | None = Field(None, description="Optional technical detail.")
