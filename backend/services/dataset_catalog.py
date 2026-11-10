"""SQLite search index for the project's CSV-backed image datasets."""

import csv
import hashlib
import re
import sqlite3
from pathlib import Path
from urllib.parse import quote

PROJECT = Path(__file__).resolve().parents[2]
BACKEND = PROJECT / "backend"
DATABASE_PATH = BACKEND / ".ultralytics" / "dataset_index.sqlite3"

DATASETS = {
    "primary": {
        "directory": PROJECT / "dataset_of_height_weight_updated",
        "csv": "Output_data.csv",
        "images": (
            ("Image Name", "front"),
        ),
        "name": "Name",
        "height": "Height (cm)",
        "weight": "Weight (kg)",
        "distance": "Distance from camera (cm)",
        "camera_height": "Camera height from ground (cm)",
    },
    "paired": {
        "directory": PROJECT / "height_weight_dataset_updated",
        "csv": "height_weight_dataset.csv",
        "images": (
            ("Image 1 Name", "Image 1 View"),
            ("Image 2 Name", "Image 2 View"),
        ),
        "name": "Person Name",
        "height": None,
        "weight": "Weight (kg)",
        "distance": "Distance from Camera (cm)",
        "camera_height": "Camera Height from Ground (cm)",
    },
    "model_specification": {
        "directory": PROJECT / "model_specification",
        "csv": "height_weight_dataset.csv",
        "images": (
            ("image_path", "view"),
        ),
        "image_paths": True,
        "name": "person_name",
        "height": "height_cm",
        "weight": "weight_kg",
        "distance": "subject_distance_cm",
        "camera_height": "camera_height_cm",
    },
}


def _normalise_name(name: str) -> str:
    return " ".join(name.casefold().split())


def _number(row: dict, column: str | None) -> float | None:
    value = row.get(column) if column else None
    if value is None or not str(value).strip():
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS image_records (
            dataset_key TEXT NOT NULL,
            image_name TEXT NOT NULL,
            name TEXT NOT NULL,
            normalized_name TEXT NOT NULL,
            view TEXT,
            height_cm REAL,
            weight_kg REAL,
            distance_cm REAL,
            camera_height_cm REAL,
            image_sha256 TEXT,
            image_size INTEGER,
            image_mtime_ns INTEGER,
            PRIMARY KEY (dataset_key, image_name)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_image_records_name
        ON image_records(normalized_name)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_image_records_hash
        ON image_records(image_sha256)
        """
    )
    connection.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS people_name_fts
        USING fts5(name_key UNINDEXED, normalized_name, tokenize='unicode61')
        """
    )
    return connection


def _read_records() -> list[dict]:
    records = []
    for dataset_key, config in DATASETS.items():
        csv_path = config["directory"] / config["csv"]
        if not csv_path.is_file():
            continue
        with csv_path.open(encoding="utf-8-sig", newline="") as source:
            for row in csv.DictReader(source):
                name = (row.get(config["name"]) or "").strip()
                if not name:
                    continue
                for image_column, view_column in config["images"]:
                    image_reference = (row.get(image_column) or "").strip()
                    if config.get("image_paths"):
                        relative_path = Path(image_reference)
                        if (
                            relative_path.is_absolute()
                            or len(relative_path.parts) != 2
                            or relative_path.parts[0] != "images"
                        ):
                            continue
                        image_name = relative_path.name
                    else:
                        image_name = image_reference
                        if not image_name or Path(image_name).name != image_name:
                            continue
                    image_path = config["directory"] / "images" / image_name
                    try:
                        image_stat = image_path.stat()
                        image_size = image_stat.st_size
                        image_mtime_ns = image_stat.st_mtime_ns
                    except OSError:
                        image_size = None
                        image_mtime_ns = None
                    records.append(
                        {
                            "dataset_key": dataset_key,
                            "image_name": image_name,
                            "name": name,
                            "normalized_name": _normalise_name(name),
                            "view": (row.get(view_column) or "").strip() or None,
                            "height_cm": _number(row, config["height"]),
                            "weight_kg": _number(row, config["weight"]),
                            "distance_cm": _number(row, config["distance"]),
                            "camera_height_cm": _number(row, config["camera_height"]),
                            "image_size": image_size,
                            "image_mtime_ns": image_mtime_ns,
                        }
                    )
    return records


def _sync(connection: sqlite3.Connection) -> None:
    records = _read_records()
    connection.execute(
        """
        CREATE TEMP TABLE IF NOT EXISTS current_image_records (
            dataset_key TEXT NOT NULL,
            image_name TEXT NOT NULL,
            PRIMARY KEY (dataset_key, image_name)
        )
        """
    )
    connection.execute("DELETE FROM current_image_records")
    for record in records:
        connection.execute(
            "INSERT OR IGNORE INTO current_image_records VALUES (?, ?)",
            (record["dataset_key"], record["image_name"]),
        )
        previous = connection.execute(
            """
            SELECT image_sha256, image_size, image_mtime_ns
            FROM image_records
            WHERE dataset_key = ? AND image_name = ?
            """,
            (record["dataset_key"], record["image_name"]),
        ).fetchone()
        sha256 = None
        if (
            previous
            and previous["image_size"] == record["image_size"]
            and previous["image_mtime_ns"] == record["image_mtime_ns"]
        ):
            sha256 = previous["image_sha256"]
        elif record["image_size"] is not None:
            image_path = (
                DATASETS[record["dataset_key"]]["directory"]
                / "images"
                / record["image_name"]
            )
            try:
                with image_path.open("rb") as image_file:
                    sha256 = hashlib.file_digest(image_file, "sha256").hexdigest()
            except OSError:
                sha256 = None

        connection.execute(
            """
            INSERT INTO image_records (
                dataset_key, image_name, name, normalized_name, view, height_cm,
                weight_kg, distance_cm, camera_height_cm, image_sha256,
                image_size, image_mtime_ns
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(dataset_key, image_name) DO UPDATE SET
                name = excluded.name,
                normalized_name = excluded.normalized_name,
                view = excluded.view,
                height_cm = excluded.height_cm,
                weight_kg = excluded.weight_kg,
                distance_cm = excluded.distance_cm,
                camera_height_cm = excluded.camera_height_cm,
                image_sha256 = excluded.image_sha256,
                image_size = excluded.image_size,
                image_mtime_ns = excluded.image_mtime_ns
            """,
            (
                record["dataset_key"],
                record["image_name"],
                record["name"],
                record["normalized_name"],
                record["view"],
                record["height_cm"],
                record["weight_kg"],
                record["distance_cm"],
                record["camera_height_cm"],
                sha256,
                record["image_size"],
                record["image_mtime_ns"],
            ),
        )

    connection.execute(
        """
        DELETE FROM image_records
        WHERE NOT EXISTS (
            SELECT 1
            FROM current_image_records
            WHERE current_image_records.dataset_key = image_records.dataset_key
              AND current_image_records.image_name = image_records.image_name
        )
        """
    )

    connection.execute("DELETE FROM people_name_fts")
    connection.execute(
        """
        INSERT INTO people_name_fts (name_key, normalized_name)
        SELECT normalized_name, normalized_name
        FROM image_records
        GROUP BY normalized_name
        """
    )
    connection.commit()


def _search_keys(
    connection: sqlite3.Connection, search: str | None, limit: int, offset: int
) -> tuple[list[str], int]:
    if search and search.strip():
        tokens = re.findall(r"[^\W_]+", _normalise_name(search), flags=re.UNICODE)
        if not tokens:
            return [], 0
        expression = " AND ".join(f'"{token}"*' for token in tokens)
        total = connection.execute(
            """
            SELECT COUNT(*)
            FROM people_name_fts
            WHERE people_name_fts MATCH ?
            """,
            (expression,),
        ).fetchone()[0]
        rows = connection.execute(
            """
            SELECT name_key
            FROM people_name_fts
            WHERE people_name_fts MATCH ?
            ORDER BY normalized_name
            LIMIT ? OFFSET ?
            """,
            (expression, limit, offset),
        ).fetchall()
    else:
        total = connection.execute(
            "SELECT COUNT(DISTINCT normalized_name) FROM image_records"
        ).fetchone()[0]
        rows = connection.execute(
            """
            SELECT normalized_name AS name_key
            FROM image_records
            GROUP BY normalized_name
            ORDER BY normalized_name
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
    return [row["name_key"] for row in rows], total


def _group_people(
    connection: sqlite3.Connection, name_keys: list[str]
) -> list[dict]:
    people = []
    for name_key in name_keys:
        rows = connection.execute(
            """
            SELECT *
            FROM image_records
            WHERE normalized_name = ?
            ORDER BY dataset_key, image_name
            """,
            (name_key,),
        ).fetchall()
        if not rows:
            continue

        measurements = []
        images = []
        for row in rows:
            measurement = next(
                (
                    existing
                    for existing in measurements
                    if existing["distance_cm"] == row["distance_cm"]
                    and existing["camera_height_cm"] == row["camera_height_cm"]
                    and all(
                        row[field] is None
                        or existing[field] is None
                        or existing[field] == row[field]
                        for field in ("height_cm", "weight_kg")
                    )
                ),
                None,
            )
            if measurement is None:
                measurements.append(
                    {
                        "height_cm": row["height_cm"],
                        "weight_kg": row["weight_kg"],
                        "distance_cm": row["distance_cm"],
                        "camera_height_cm": row["camera_height_cm"],
                    }
                )
            else:
                for field in ("height_cm", "weight_kg"):
                    if measurement[field] is None:
                        measurement[field] = row[field]
            images.append(
                {
                    "name": row["image_name"],
                    "view": row["view"],
                    "dataset": row["dataset_key"],
                    "height_cm": row["height_cm"],
                    "weight_kg": row["weight_kg"],
                    "distance_cm": row["distance_cm"],
                    "camera_height_cm": row["camera_height_cm"],
                    "url": (
                        f"/api/dataset/images/{row['dataset_key']}/"
                        f"{quote(row['image_name'], safe='')}"
                    ),
                }
            )
        people.append(
            {
                "name": rows[0]["name"],
                "normalized_name": name_key,
                "measurements": measurements,
                "images": images,
            }
        )
    return people


def list_people(
    search: str | None = None, limit: int = 50, offset: int = 0
) -> dict:
    connection = _connect()
    try:
        _sync(connection)
        name_keys, total = _search_keys(connection, search, limit, offset)
        return {
            "people": _group_people(connection, name_keys),
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    finally:
        connection.close()


def find_people_by_name(
    name: str, limit: int = 50, offset: int = 0
) -> list[dict]:
    return list_people(search=name, limit=limit, offset=offset)["people"]


def find_people_by_normalized_names(name_keys: list[str]) -> list[dict]:
    if not name_keys:
        return []
    connection = _connect()
    try:
        _sync(connection)
        return _group_people(connection, name_keys)
    finally:
        connection.close()


def find_image_records_by_hash(image_bytes: bytes) -> list[dict]:
    image_hash = hashlib.sha256(image_bytes).hexdigest()
    connection = _connect()
    try:
        _sync(connection)
        rows = connection.execute(
            """
            SELECT name, image_name, dataset_key, normalized_name
            FROM image_records
            WHERE image_sha256 = ?
            """,
            (image_hash,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()
