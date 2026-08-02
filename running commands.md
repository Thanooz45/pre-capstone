# How to Run the Application

This application consists of two parts: a Python FastAPI backend (for the AI processing) and a Vite React frontend (for the user interface). You need to open **two separate terminal windows** to run both simultaneously.

---

## 1. Running the Backend (Terminal 1)

The backend handles the OpenCV, YOLOv8, and MediaPipe processing.

1. Open a new terminal.
2. Navigate to the `backend` folder:
   ```bash
   cd d:\capstone\backend
   ```
3. Activate the virtual environment:
   * **Windows:**
     ```bash
     venv\Scripts\activate
     ```
   * **Mac/Linux:**
     ```bash
     source venv/bin/activate
     ```
4. Install dependencies (if you haven't already):
   ```bash
   pip install -r requirements.txt
   ```
5. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload
   ```
   *(The backend will start running on `http://127.0.0.1:8000`)*

---

## 2. Running the Frontend (Terminal 2)

The frontend is a modern React application built with Vite and TailwindCSS.

1. Open a second terminal window.
2. Navigate to the `frontend` folder:
   ```bash
   cd d:\capstone\frontend
   ```
3. Install the Node modules (only needed the very first time):
   ```bash
   npm install
   ```
4. Start the development server:
   ```bash
   npm run dev
   ```
   *(The frontend will usually be accessible at `http://localhost:5173` or similar, check the terminal output for the exact URL)*

---

### 3. Using the App
Once both terminals are running without errors, hold `CTRL` and click the local link shown in the frontend terminal (e.g., `http://localhost:5173`) to open the app in your browser!
