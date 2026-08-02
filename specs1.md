Build a complete full-stack web application for Estimating Human Height from Images using YOLOv8, MediaPipe Pose, and Pinhole Camera Geometry.

### System Setup & Assumptions:
- Camera Height from Ground: 140 cm
- Distance from Person to Camera: 200 cm
- Tech Stack: Python (FastAPI, OpenCV, Ultralytics YOLOv8, MediaPipe), React (Vite, Tailwind CSS, Axios).

### Backend Requirements (FastAPI):
1. Create a `/api/predict-height` endpoint accepting an uploaded image.
2. Step 1: Pass image through YOLOv8 to detect human bounding boxes.
3. Step 2: Use MediaPipe Pose on the detected crop/person to find head top landmark and ankle keypoints.
4. Step 3: Compute pixel height from top of head to the lowest heel keypoint.
5. Step 4: Apply geometric height calculation using camera height (140 cm) and distance (200 cm) parameters.
6. Step 5: Draw visual overlays on the image:
   - Green bounding box around the person.
   - Red keypoint dots on the top of head and ankles.
   - Blue vertical alignment line from head to toe showing pixel measurement.
7. Return JSON response containing:
   - `estimated_height_cm`
   - `estimated_height_ft`
   - `confidence_score`
   - `annotated_image_base64` (the visual overlay)

### Frontend Requirements (React + Tailwind CSS):
1. Build a clean, modern UI dashboard for Capstone project presentation.
2. Upload dropzone for inputting subject photos.
3. Display real-time image preview alongside the processed output with keypoint/bounding-box overlays.
4. Show a results card with predicted height (in cm and feet/inches).
5. Allow setting custom Distance (default 200 cm) and Camera Height (default 140 cm) via input controls for future dataset expansion.

Please generate the complete codebase with modular backend and frontend folders.