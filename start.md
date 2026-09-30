# How to Start the Application

You need to run the backend (Python) and the frontend (React) simultaneously in two separate terminals.

## 1. Start the Backend (Terminal 1)
Open a terminal in the project root directory (`d:\capstone`), then run:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```
*(The backend API will run on http://127.0.0.1:8000)*

## 2. Start the Frontend (Terminal 2)
Open a second terminal in the project root directory (`d:\capstone`), then run:

```powershell
cd frontend
npm install
npm run dev
```
*(The frontend will start a local server, usually accessible at http://localhost:5173)*

### Usage
Once both terminals are running without errors, hold `CTRL` and click the local link shown in the frontend terminal (e.g., `http://localhost:5173`) to open the app in your browser!
