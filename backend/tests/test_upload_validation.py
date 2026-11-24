import asyncio
import os
from io import BytesIO
import unittest

import cv2
import numpy as np
from fastapi import HTTPException, UploadFile

from api.routes import _save_image_upload


class UploadValidationTests(unittest.TestCase):
    def test_accepts_decodable_image_and_removes_temp_file(self):
        ok, encoded = cv2.imencode(".jpg", np.zeros((120, 120, 3), dtype=np.uint8))
        self.assertTrue(ok)
        upload = UploadFile(filename="capture.jpg", file=BytesIO(encoded.tobytes()))

        path = asyncio.run(_save_image_upload(upload, ".jpg"))
        try:
            self.assertTrue(os.path.isfile(path))
        finally:
            os.remove(path)

    def test_rejects_non_image_bytes(self):
        upload = UploadFile(filename="capture.jpg", file=BytesIO(b"not an image"))
        with self.assertRaises(HTTPException) as error:
            asyncio.run(_save_image_upload(upload, ".jpg"))
        self.assertEqual(error.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
