"""
core/models.py — Pydantic Response Models
==========================================
Defines the typed data contracts returned by the API.
"""

from pydantic import BaseModel, Field


class PredictionPipelineDetails(BaseModel):
    """Intermediate measurements and images shown in the prediction pipeline."""

    geometric_height_cm: float = Field(
        ..., description="Camera-geometry height before dataset calibration."
    )
    calibrated_height_cm: float = Field(
        ..., description="Height after applying the trained calibration model."
    )
    front_weight_estimate_kg: float = Field(
        ..., description="Weight model estimate from the front image."
    )
    side_weight_estimate_kg: float | None = Field(
        None, description="Weight model estimate from the side image, when supplied."
    )
    feature_values: dict[str, float] = Field(
        ..., description="The eight values supplied to the weight regression model."
    )
    side_feature_values: dict[str, float] | None = Field(
        None, description="The legacy feature schema extracted from the side image, when supplied."
    )
    feature_metadata: dict[str, dict[str, str]] = Field(
        default_factory=dict, description="Feature names, units, kinds, and proxy descriptions."
    )
    front_quality_details: dict[str, float | int | bool | str | None] | None = Field(
        None, description="Front-view image and pose quality checks."
    )
    side_quality_details: dict[str, float | int | bool | str | None] | None = Field(
        None, description="Side-view image and pose quality checks."
    )
    anthropometric_features: dict | None = Field(
        None, description="Versioned image-derived front/side measurement proxies, with per-feature validity and provenance."
    )
    quality_assessment: dict | None = Field(
        None, description="Separate detection, pose, segmentation, view, calibration, and request quality signals."
    )
    detection_image_base64: str = Field(
        ..., description="JPEG with only the YOLOv8 person box and confidence overlay."
    )
    pose_image_base64: str = Field(
        ..., description="JPEG with MediaPipe pose joints, elbow/wrist labels, and height markers."
    )
    detection_image_base64_side: str | None = Field(
        None, description="YOLOv8 detection view for the side image, when supplied."
    )
    pose_image_base64_side: str | None = Field(
        None, description="MediaPipe pose view for the side image, when supplied."
    )
    segmented_image_base64: str = Field(
        ..., description="PNG with the segmented person visible and background transparent."
    )
    segmented_image_base64_side: str | None = Field(
        None, description="Transparent-background segmentation for the side image, when supplied."
    )


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
    geometric_height_cm: float = Field(
        ..., description="Uncalibrated height from camera geometry before dataset calibration.", example=169.2
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Legacy composite score retained for API V1 compatibility; not a probability of accuracy. V2 provides separate quality signals in pipeline.quality_assessment.",
        example=0.87,
    )
    pixel_height: int = Field(
        ...,
        description=(
            "Vertical pixel distance from the detected person box's top edge "
            "to the lowest visible heel/toe landmark."
        ),
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
        example=100.0,
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
    detection_confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Raw detector score for the selected person bounding box; not an accuracy probability."
    )
    annotated_image_base64_side: str | None = Field(
        None,
        description="JPEG image encoded in base64 with overlays for the side view (if provided)."
    )
    posture_warning: bool = Field(
        False,
        description="True if bent knees are detected, indicating incorrect posture.",
    )
    estimated_weight_kg: float | None = Field(None, description="Visual weight estimate in kilograms, when requested.", example=68.4)
    estimated_weight_lb: float | None = Field(None, description="Visual weight estimate in pounds, when requested.", example=150.8)
    weight_estimate_range_kg: list[float] | None = Field(
        None, description="Legacy uncalibrated range in kg. Version 2 omits it because it is not a validated prediction interval.", example=[61.2, 75.6]
    )
    weight_model_available: bool | None = Field(None, description="Whether the locally trained weight model was used.")
    api_version: str | None = Field(None, description="Prediction response schema version.")
    model_version: str | None = Field(None, description="Model artifact/version identifier.")
    feature_version: str | None = Field(None, description="Feature schema version.")
    prediction_mode: str | None = Field(None, description="Requested estimation mode.")
    estimate_value: float | None = Field(None, description="Primary estimate selected by prediction mode.")
    estimate_unit: str | None = Field(None, description="Unit for the primary estimate (cm or kg).")
    features_used: list[str] = Field(default_factory=list, description="Feature groups used by the selected mode.")
    quality_flags: list[str] = Field(default_factory=list, description="Quality and limitation flags for the result.")
    notice: str | None = Field(None, description="Research-prototype notice for version 2 results.")
    pipeline: PredictionPipelineDetails = Field(
        ..., description="Intermediate values and visual outputs for the prediction pipeline."
    )


class ErrorResponse(BaseModel):
    """Standard error payload."""
    error: str = Field(..., description="Human-readable error message.")
    detail: str | None = Field(None, description="Optional technical detail.")


class DatasetPersonUpdate(BaseModel):
    """Updated participant labels applied to all images in the training cohort."""

    current_name: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)
    height_cm: float = Field(..., gt=0, le=300)
    weight_kg: float = Field(..., gt=0, le=500)


class DatasetPersonDelete(BaseModel):
    """Participant to remove from the training cohort."""

    current_name: str = Field(..., min_length=1, max_length=100)
