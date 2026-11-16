import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import BackgroundTasks, HTTPException

from api.routes import (
    delete_dataset_image,
    delete_dataset_person,
    download_dataset_csv,
)
from core.models import DatasetPersonDelete
from services.dataset_catalog import DATASETS


class DeleteDatasetPersonTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.dataset_directory = Path(self.temporary_directory.name)
        (self.dataset_directory / "images").mkdir()
        self.csv_path = self.dataset_directory / "height_weight_dataset.csv"
        self.original_dataset = DATASETS["model_specification"]
        self.datasets_patch = patch.dict(
            DATASETS,
            {
                "model_specification": {
                    **self.original_dataset,
                    "directory": self.dataset_directory,
                    "csv": self.csv_path.name,
                }
            },
        )
        self.datasets_patch.start()
        self.addCleanup(self.datasets_patch.stop)
        self.addCleanup(self.temporary_directory.cleanup)

    def _write_rows(self, rows):
        with self.csv_path.open("w", newline="", encoding="utf-8") as destination:
            writer = csv.DictWriter(
                destination, fieldnames=["person_name", "image_path"]
            )
            writer.writeheader()
            writer.writerows(rows)

    def _read_rows(self):
        with self.csv_path.open(newline="", encoding="utf-8") as source:
            return list(csv.DictReader(source))

    def test_removes_person_records_and_unshared_images(self):
        image_directory = self.dataset_directory / "images"
        (image_directory / "first.jpg").write_bytes(b"first")
        (image_directory / "shared.jpg").write_bytes(b"shared")
        self._write_rows(
            [
                {"person_name": "Avery", "image_path": "images/first.jpg"},
                {"person_name": "Avery", "image_path": "images/shared.jpg"},
                {"person_name": "Morgan", "image_path": "images/./shared.jpg"},
            ]
        )
        background_tasks = BackgroundTasks()

        result = delete_dataset_person(
            DatasetPersonDelete(current_name=" aVeRy "),
            background_tasks,
        )

        self.assertEqual(result["deleted_records"], 2)
        self.assertEqual(result["deleted_images"], 1)
        self.assertEqual(self._read_rows(), [
            {"person_name": "Morgan", "image_path": "images/./shared.jpg"}
        ])
        self.assertFalse((image_directory / "first.jpg").exists())
        self.assertTrue((image_directory / "shared.jpg").exists())
        self.assertEqual(len(background_tasks.tasks), 1)

    def test_missing_person_does_not_change_training_data(self):
        rows = [{"person_name": "Morgan", "image_path": "images/morgan.jpg"}]
        self._write_rows(rows)

        with self.assertRaises(HTTPException) as raised:
            delete_dataset_person(
                DatasetPersonDelete(current_name="Unknown"),
                BackgroundTasks(),
            )

        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(self._read_rows(), rows)

    def test_deletes_image_and_all_records_that_reference_it(self):
        image_directory = self.dataset_directory / "images"
        (image_directory / "remove.jpg").write_bytes(b"remove")
        (image_directory / "keep.jpg").write_bytes(b"keep")
        self._write_rows(
            [
                {"person_name": "Avery", "image_path": "images/remove.jpg"},
                {"person_name": "Morgan", "image_path": "images/./remove.jpg"},
                {"person_name": "Morgan", "image_path": "images/keep.jpg"},
            ]
        )
        background_tasks = BackgroundTasks()

        result = delete_dataset_image(
            "model_specification",
            "remove.jpg",
            background_tasks,
        )

        self.assertEqual(result["deleted_records"], 2)
        self.assertEqual(
            self._read_rows(),
            [{"person_name": "Morgan", "image_path": "images/keep.jpg"}],
        )
        self.assertFalse((image_directory / "remove.jpg").exists())
        self.assertTrue((image_directory / "keep.jpg").exists())
        self.assertEqual(len(background_tasks.tasks), 1)

    def test_download_returns_training_csv_attachment(self):
        self._write_rows(
            [{"person_name": "Morgan", "image_path": "images/morgan.jpg"}]
        )

        response = download_dataset_csv()

        self.assertEqual(Path(response.path), self.csv_path)
        self.assertIn("attachment", response.headers["content-disposition"])
        self.assertIn("text/csv", response.media_type)


if __name__ == "__main__":
    unittest.main()
