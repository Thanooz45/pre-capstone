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
import sys
from pathlib import Path
from typing import Literal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse, JSONResponse

from core.config import settings
from core.models import (
    DatasetPersonDelete,
    DatasetPersonUpdate,
    HeightResponse,
    ErrorResponse,
)
from services.dataset_catalog import (
    DATASETS,
    find_image_records_by_hash,
    find_people_by_name,
    find_people_by_normalized_names,
    list_people,
)
from services.height_estimator import estimate_height
from services.weight_estimator import (
    calibrate_height,
    estimate_weight,
    reload_trained_models,
)

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
        "2. **MediaPipe Pose** — extracts body landmarks for posture and shape features\n"
        "3. **Pixel height** — computed from the person-box top → lowest visible heel/toe\n"
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
            height_calibrator=calibrate_height,
        )
        features = result.pop("_weight_features")
        segmented_image = result.pop("_segmented_image_base64")
        detection_image = result.pop("_detection_image_base64")
        pose_image = result.pop("_pose_image_base64")
        geometric_height = result["geometric_height_cm"]
        calibrated_height = result["estimated_height_cm"]
        
        # Base result
        features["estimated_height_cm"] = calibrated_height
        result["geometric_height_cm"] = geometric_height
        
        # Estimate weight (Front)
        front_weight_est = estimate_weight(features)
        side_weight_estimate = None
        side_segmented_image = None
        side_detection_image = None
        side_pose_image = None
        
        # If side image provided, average the weight estimates
        if tmp_path_side:
            side_result = estimate_height(
                image_path=tmp_path_side,
                camera_height_cm=camera_height_cm,
                distance_cm=distance_cm,
                height_calibrator=calibrate_height,
            )
            side_features = side_result.pop("_weight_features")
            side_segmented_image = side_result.pop("_segmented_image_base64")
            side_detection_image = side_result.pop("_detection_image_base64")
            side_pose_image = side_result.pop("_pose_image_base64")
            side_features["estimated_height_cm"] = side_result["estimated_height_cm"]
            side_weight_est = estimate_weight(side_features)
            side_weight_estimate = side_weight_est["estimated_weight_kg"]
            
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

        result["pipeline"] = {
            "geometric_height_cm": geometric_height,
            "calibrated_height_cm": calibrated_height,
            "front_weight_estimate_kg": front_weight_est["estimated_weight_kg"],
            "side_weight_estimate_kg": side_weight_estimate,
            "feature_values": features,
            "detection_image_base64": detection_image,
            "pose_image_base64": pose_image,
            "detection_image_base64_side": side_detection_image,
            "pose_image_base64_side": side_pose_image,
            "segmented_image_base64": segmented_image,
            "segmented_image_base64_side": side_segmented_image,
        }

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


@router.get("/dataset/people", summary="Search or browse the participant-ID training cohort")
def dataset_people(
    search: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    try:
        return list_people(search=search, limit=limit, offset=offset)
    except Exception as exc:
        logger.exception("Unable to load the dataset catalog")
        raise HTTPException(
            status_code=500, detail="Unable to load the dataset catalog."
        ) from exc


@router.get("/dataset/download", summary="Download the active training cohort as CSV")
def download_dataset_csv():
    dataset = DATASETS["model_specification"]
    csv_path = dataset["directory"] / dataset["csv"]
    if not csv_path.is_file():
        raise HTTPException(status_code=404, detail="The training cohort was not found.")
    return FileResponse(
        csv_path,
        media_type="text/csv",
        filename=dataset["csv"],
    )


@router.put("/dataset/people", summary="Update a participant in the training cohort")
def update_dataset_person(
    update: DatasetPersonUpdate,
    background_tasks: BackgroundTasks,
):
    dataset_dir = Path(__file__).resolve().parents[2] / "model_specification"
    csv_path = dataset_dir / "height_weight_dataset.csv"
    if not csv_path.is_file():
        raise HTTPException(status_code=404, detail="The training cohort was not found.")

    current_name = " ".join(update.current_name.split())
    updated_name = " ".join(update.name.split())
    current_key = " ".join(current_name.casefold().split())
    updated_key = " ".join(updated_name.casefold().split())
    if not current_key or not updated_key:
        raise HTTPException(status_code=422, detail="Person name cannot be empty.")

    temporary_csv_path = None
    try:
        with csv_path.open(newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source)
            fieldnames = reader.fieldnames or []
            required_fields = {
                "person_name",
                "height_cm",
                "weight_kg",
            }
            if required_fields - set(fieldnames):
                raise ValueError("The training-cohort table has an invalid schema.")
            rows = list(reader)

        matching_rows = [
            row
            for row in rows
            if " ".join(row["person_name"].casefold().split()) == current_key
        ]
        if not matching_rows:
            raise HTTPException(
                status_code=404,
                detail="No editable training-cohort records were found for that participant.",
            )
        if any(
            " ".join(row["person_name"].casefold().split()) == updated_key
            and " ".join(row["person_name"].casefold().split()) != current_key
            for row in rows
        ):
            raise HTTPException(
                status_code=409,
                detail="Another dataset person already uses that name.",
            )

        for row in matching_rows:
            row["person_name"] = updated_name
            row["height_cm"] = update.height_cm
            row["weight_kg"] = update.weight_kg

        with tempfile.NamedTemporaryFile(
            mode="w",
            newline="",
            encoding="utf-8",
            dir=dataset_dir,
            prefix=".height-weight-dataset-",
            suffix=".tmp",
            delete=False,
        ) as destination:
            temporary_csv_path = Path(destination.name)
            writer = csv.DictWriter(destination, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary_csv_path, csv_path)
        temporary_csv_path = None

        background_tasks.add_task(run_training_task)
        return {
            "message": "Person records updated; model retraining has started.",
            "person_name": updated_name,
            "updated_images": len(matching_rows),
            "training_started": True,
        }
    except HTTPException:
        if temporary_csv_path:
            temporary_csv_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        if temporary_csv_path:
            temporary_csv_path.unlink(missing_ok=True)
        logger.exception("Unable to update training-cohort participant")
        raise HTTPException(
            status_code=500,
            detail="Unable to update the person's dataset records.",
        ) from exc


@router.delete("/dataset/people", summary="Delete a participant from the training cohort")
def delete_dataset_person(
    deletion: DatasetPersonDelete,
    background_tasks: BackgroundTasks,
):
    dataset = DATASETS["model_specification"]
    dataset_dir = dataset["directory"]
    csv_path = dataset_dir / dataset["csv"]
    if not csv_path.is_file():
        raise HTTPException(status_code=404, detail="The training cohort was not found.")

    current_name = " ".join(deletion.current_name.split())
    current_key = " ".join(current_name.casefold().split())
    if not current_key:
        raise HTTPException(status_code=422, detail="Person name cannot be empty.")

    temporary_csv_path = None
    try:
        with csv_path.open(newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source)
            fieldnames = reader.fieldnames or []
            if {"person_name", "image_path"} - set(fieldnames):
                raise ValueError("The training-cohort table has an invalid schema.")
            rows = list(reader)

        matching_rows = [
            row
            for row in rows
            if " ".join(row["person_name"].casefold().split()) == current_key
        ]
        if not matching_rows:
            raise HTTPException(
                status_code=404,
                detail="No training-cohort records were found for that participant.",
            )

        remaining_rows = [
            row
            for row in rows
            if " ".join(row["person_name"].casefold().split()) != current_key
        ]
        images_dir = (dataset_dir / "images").resolve()

        def image_path_for_row(row):
            image_reference = row.get("image_path", "").strip()
            if not image_reference:
                return None
            image_path = (dataset_dir / image_reference).resolve()
            if image_path == images_dir or not image_path.is_relative_to(images_dir):
                return None
            return image_path

        remaining_image_paths = {
            image_path
            for row in remaining_rows
            if (image_path := image_path_for_row(row)) is not None
        }
        image_paths_to_remove = {
            image_path
            for row in matching_rows
            if (image_path := image_path_for_row(row)) is not None
            and image_path not in remaining_image_paths
        }

        with tempfile.NamedTemporaryFile(
            mode="w",
            newline="",
            encoding="utf-8",
            dir=dataset_dir,
            prefix=".height-weight-dataset-",
            suffix=".tmp",
            delete=False,
        ) as destination:
            temporary_csv_path = Path(destination.name)
            writer = csv.DictWriter(destination, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(remaining_rows)
        os.replace(temporary_csv_path, csv_path)
        temporary_csv_path = None

        deleted_images = 0
        image_cleanup_errors = 0
        for image_path in image_paths_to_remove:
            try:
                if image_path.is_file():
                    image_path.unlink()
                    deleted_images += 1
            except OSError:
                image_cleanup_errors += 1
                logger.exception("Unable to remove a deleted participant's image")

        background_tasks.add_task(run_training_task)
        return {
            "message": "Person records deleted; model retraining has started.",
            "person_name": current_name,
            "deleted_records": len(matching_rows),
            "deleted_images": deleted_images,
            "image_cleanup_errors": image_cleanup_errors,
            "training_started": True,
        }
    except HTTPException:
        if temporary_csv_path:
            temporary_csv_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        if temporary_csv_path:
            temporary_csv_path.unlink(missing_ok=True)
        logger.exception("Unable to delete training-cohort participant")
        raise HTTPException(
            status_code=500,
            detail="Unable to delete the person's dataset records.",
        ) from exc


@router.delete(
    "/dataset/images/{dataset_key}/{image_name}",
    summary="Delete an image and its training records",
)
def delete_dataset_image(
    dataset_key: str,
    image_name: str,
    background_tasks: BackgroundTasks,
):
    dataset = DATASETS.get(dataset_key)
    if dataset is None or Path(image_name).name != image_name:
        raise HTTPException(status_code=404, detail="Dataset image not found.")

    dataset_dir = dataset["directory"]
    images_dir = (dataset_dir / "images").resolve()
    image_path = (images_dir / image_name).resolve()
    if not image_path.is_relative_to(images_dir) or not image_path.is_file():
        raise HTTPException(status_code=404, detail="Dataset image not found.")

    csv_path = dataset_dir / dataset["csv"]
    if not csv_path.is_file():
        raise HTTPException(status_code=404, detail="The training cohort was not found.")

    temporary_csv_path = None
    try:
        with csv_path.open(newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source)
            fieldnames = reader.fieldnames or []
            image_columns = [column for column, _ in dataset["images"]]
            if not image_columns or set(image_columns) - set(fieldnames):
                raise ValueError("The training-cohort table has an invalid schema.")
            rows = list(reader)

        def references_image(row):
            for column in image_columns:
                image_reference = row.get(column, "").strip()
                if not image_reference:
                    continue
                if dataset.get("image_paths"):
                    row_image_path = (dataset_dir / image_reference).resolve()
                else:
                    if Path(image_reference).name != image_reference:
                        continue
                    row_image_path = (images_dir / image_reference).resolve()
                if (
                    row_image_path.is_relative_to(images_dir)
                    and row_image_path == image_path
                ):
                    return True
            return False

        matching_rows = [row for row in rows if references_image(row)]
        if not matching_rows:
            raise HTTPException(
                status_code=404,
                detail="No training-cohort records were found for that image.",
            )
        remaining_rows = [row for row in rows if not references_image(row)]

        with tempfile.NamedTemporaryFile(
            mode="w",
            newline="",
            encoding="utf-8",
            dir=dataset_dir,
            prefix=".height-weight-dataset-",
            suffix=".tmp",
            delete=False,
        ) as destination:
            temporary_csv_path = Path(destination.name)
            writer = csv.DictWriter(destination, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(remaining_rows)
        os.replace(temporary_csv_path, csv_path)
        temporary_csv_path = None

        image_cleanup_error = False
        try:
            image_path.unlink()
        except OSError:
            image_cleanup_error = True
            logger.exception("Unable to remove deleted training image %s", image_name)

        background_tasks.add_task(run_training_task)
        return {
            "message": "Image records deleted; model retraining has started.",
            "image_name": image_name,
            "deleted_records": len(matching_rows),
            "image_cleanup_error": image_cleanup_error,
            "training_started": True,
        }
    except HTTPException:
        if temporary_csv_path:
            temporary_csv_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        if temporary_csv_path:
            temporary_csv_path.unlink(missing_ok=True)
        logger.exception("Unable to delete training-cohort image")
        raise HTTPException(
            status_code=500,
            detail="Unable to delete the image's dataset records.",
        ) from exc


@router.get(
    "/dataset/images/{dataset_key}/{image_name}",
    summary="View an image from the participant-ID training cohort",
)
def dataset_image(dataset_key: str, image_name: str):
    dataset = DATASETS.get(dataset_key)
    if dataset is None or Path(image_name).name != image_name:
        raise HTTPException(status_code=404, detail="Dataset image not found.")
    image_path = dataset["directory"] / "images" / image_name
    if not image_path.is_file():
        raise HTTPException(status_code=404, detail="Dataset image not found.")
    return FileResponse(image_path)


@router.post(
    "/dataset/lookup",
    summary="Find training-cohort records by name or an identical image file",
)
async def dataset_lookup(
    file: UploadFile = File(...),
    person_name: str = Form(default="", max_length=100),
):
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload an image file.")
    image_bytes = await file.read(15 * 1024 * 1024 + 1)
    if len(image_bytes) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image must be 15 MB or smaller.")

    try:
        exact_records = find_image_records_by_hash(image_bytes)
        exact_names = {record["normalized_name"] for record in exact_records}
        matches_by_name = {}
        for person in find_people_by_name(person_name.strip()) if person_name.strip() else []:
            matches_by_name[person["normalized_name"]] = person

        if exact_names:
            for person in find_people_by_normalized_names(sorted(exact_names)):
                matches_by_name[person["normalized_name"]] = person

        matches = []
        for person in matches_by_name.values():
            person["match_type"] = (
                "identical_image"
                if person["normalized_name"] in exact_names
                else "name"
            )
            matches.append(person)
        matches.sort(key=lambda person: person["name"].casefold())
        return {
            "matches": matches,
            "exact_image_match": bool(exact_records),
        }
    except Exception as exc:
        logger.exception("Unable to look up existing dataset records")
        raise HTTPException(
            status_code=500, detail="Unable to look up existing dataset records."
        ) from exc


def run_training_task():
    try:
        backend_dir = Path(__file__).resolve().parents[1]
        subprocess.run(
            [sys.executable, "-m", "scripts.train_weight_model"],
            check=True,
            cwd=backend_dir,
        )
        reload_trained_models()
        logger.info("Background model training completed successfully.")
    except (subprocess.CalledProcessError, OSError, FileNotFoundError):
        logger.exception("Background model training failed.")


@router.post(
    "/submit-feedback",
    summary="Submit verified user measurements and retrain the applicable model",
)
async def submit_feedback(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Front view image."),
    file_side: UploadFile = File(None, description="Side view image (optional)."),
    person_name: str = Form(..., min_length=1, max_length=100),
    actual_height_cm: float = Form(..., gt=0, le=300),
    actual_weight_kg: float | None = Form(default=None, gt=0, le=500),
    feedback_mode: Literal["height_only", "height_weight"] = Form(default="height_weight"),
    camera_height_cm: float = Form(default=settings.DEFAULT_CAMERA_HEIGHT_CM, ge=30.0, le=500.0),
    distance_cm: float = Form(default=settings.DEFAULT_DISTANCE_CM, ge=30.0, le=2000.0),
):
    saved_images = []
    temporary_csv_path = None
    try:
        dataset_dir = Path(__file__).resolve().parents[2] / "model_specification"
        images_dir = dataset_dir / "images"
        csv_path = dataset_dir / "height_weight_dataset.csv"
        dataset_dir.mkdir(parents=True, exist_ok=True)
        images_dir.mkdir(parents=True, exist_ok=True)
        clean_name = " ".join(person_name.split())
        if not clean_name:
            raise HTTPException(status_code=422, detail="Person name is required.")
        if feedback_mode == "height_weight" and actual_weight_kg is None:
            raise HTTPException(
                status_code=422,
                detail="Actual weight is required for height-and-weight feedback.",
            )
        if feedback_mode == "height_only":
            actual_weight_kg = None

        if csv_path.exists():
            with csv_path.open(newline="", encoding="utf-8-sig") as csvfile:
                reader = csv.DictReader(csvfile)
                fieldnames = reader.fieldnames or []
                required_fields = {
                    "image_id",
                    "person_id",
                    "person_name",
                    "image_path",
                    "view",
                    "subject_distance_cm",
                    "camera_height_cm",
                    "height_cm",
                    "weight_kg",
                }
                if required_fields - set(fieldnames):
                    raise ValueError("The model specification CSV has an invalid schema.")
                existing_rows = list(reader)
        else:
            fieldnames = [
                "image_id",
                "person_id",
                "person_name",
                "image_path",
                "view",
                "subject_distance_cm",
                "camera_height_cm",
                "height_cm",
                "weight_kg",
            ]
            existing_rows = []

        normalized_name = " ".join(clean_name.casefold().split())
        matching_person = next(
            (
                row
                for row in existing_rows
                if " ".join(row["person_name"].casefold().split()) == normalized_name
            ),
            None,
        )
        if matching_person:
            person_id = matching_person["person_id"]
        else:
            next_person_number = max(
                (
                    int(row["person_id"].removeprefix("person_"))
                    for row in existing_rows
                ),
                default=0,
            ) + 1
            person_id = f"person_{next_person_number:03d}"

        image_slug = "_".join(
            "".join(
                char.lower() if char.isascii() and char.isalnum() else "_"
                for char in clean_name
            ).split("_")
        ).strip("_") or "person"
        next_image_number = max(
            (
                int(row["image_id"].removeprefix("img_"))
                for row in existing_rows
            ),
            default=0,
        ) + 1
        used_image_paths = {row["image_path"] for row in existing_rows}

        allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        new_rows = []
        for upload, view in ((file, "front"), (file_side, "side")):
            if upload is None:
                continue
            if not (upload.content_type or "").startswith("image/"):
                raise HTTPException(status_code=400, detail="Uploaded files must be images.")
            suffix = Path(upload.filename or "").suffix.lower()
            if suffix not in allowed_extensions:
                raise HTTPException(
                    status_code=400,
                    detail="Use a JPG, PNG, WEBP, or BMP image.",
                )
            image_bytes = await upload.read(15 * 1024 * 1024 + 1)
            if len(image_bytes) > 15 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="Each image must be 15 MB or smaller.")

            distance_label = f"{distance_cm:g}"
            view_code = "F" if view == "front" else "S"
            filename_stem = f"{image_slug}_{distance_label}{view_code}"
            image_filename = f"{filename_stem}{suffix}"
            duplicate_number = 2
            while f"images/{image_filename}" in used_image_paths:
                image_filename = f"{filename_stem}_{duplicate_number}{suffix}"
                duplicate_number += 1
            used_image_paths.add(f"images/{image_filename}")
            image_path = images_dir / image_filename
            image_path.write_bytes(image_bytes)
            saved_images.append(image_path)
            new_rows.append(
                {
                    "image_id": f"img_{next_image_number:03d}",
                    "person_id": person_id,
                    "person_name": clean_name,
                    "image_path": f"images/{image_filename}",
                    "view": view,
                    "subject_distance_cm": distance_cm,
                    "camera_height_cm": camera_height_cm,
                    "height_cm": actual_height_cm,
                    "weight_kg": actual_weight_kg if actual_weight_kg is not None else "",
                }
            )
            next_image_number += 1

        with tempfile.NamedTemporaryFile(
            mode="w",
            newline="",
            encoding="utf-8",
            dir=dataset_dir,
            prefix=".height-weight-dataset-",
            suffix=".tmp",
            delete=False,
        ) as csvfile:
            temporary_csv_path = Path(csvfile.name)
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(existing_rows)
            writer.writerows(new_rows)
        os.replace(temporary_csv_path, csv_path)
        temporary_csv_path = None

        background_tasks.add_task(run_training_task)
        return JSONResponse(
            content={
                "message": (
                    "Height feedback added to the training dataset."
                    if feedback_mode == "height_only"
                    else "Height and weight feedback added to the training dataset."
                ),
                "person_name": clean_name,
                "images": [path.name for path in saved_images],
                "feedback_mode": feedback_mode,
                "training_started": True,
            }
        )
    except HTTPException:
        for image_path in saved_images:
            image_path.unlink(missing_ok=True)
        if temporary_csv_path:
            temporary_csv_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        for image_path in saved_images:
            image_path.unlink(missing_ok=True)
        if temporary_csv_path:
            temporary_csv_path.unlink(missing_ok=True)
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
        "weight_prediction": "Trained from the participant-ID image cohort.",
        "camera_height_cm": "Variable; provide the measured height for each image.",
    }
