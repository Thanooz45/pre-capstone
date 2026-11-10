# How to Start the Application

Run the Python backend and React frontend in two separate terminals. The backend uses Python 3.13 with the built-in `venv` and `pip`.

## macOS

### 1. Install Python and Node.js

Install Python 3.13 using the macOS installer from [python.org](https://www.python.org/downloads/macos/). Install Node.js LTS from [nodejs.org](https://nodejs.org/).

Open Terminal and check the Python installed by python.org:

```bash
"/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13" --version
```

It should print `Python 3.13.x`.

### 2. Set up and run the backend

Open Terminal 1 in the project root folder (`capstone`), then create the virtual environment and install the dependencies:

```bash
cd backend
"/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13" -m venv --clear .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

Start the backend in the same terminal:

```bash
.venv/bin/python -m uvicorn main:app --reload --port 8000
```

For later launches, open Terminal in the project root, run `cd backend`, then run the Uvicorn command above.

The first backend start downloads the MediaPipe task models, so an internet connection is needed.

### 3. Set up and run the frontend

Open Terminal 2 in the project root folder (`capstone`). Install frontend packages the first time, then start the development server:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by the frontend, usually http://localhost:5173.

## Windows

### 1. Install Python and Node.js

Install Python 3.13 from [python.org](https://www.python.org/downloads/windows/) and Node.js LTS from [nodejs.org](https://nodejs.org/). During Python setup, enable the Python Launcher (`py`).

Open PowerShell and check that Python is available:

```powershell
py -3.13 --version
```

It should print `Python 3.13.x`.

### 2. Set up and run the backend

Open PowerShell Terminal 1 in the project root folder (`capstone`), then create the virtual environment and install the dependencies:

```powershell
cd backend
py -3.13 -m venv --clear .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start the backend in the same terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

For later launches, open PowerShell in the project root, run `cd backend`, then run the Uvicorn command above.

The first backend start downloads the MediaPipe task models, so an internet connection is needed.

### 3. Set up and run the frontend

Open PowerShell Terminal 2 in the project root folder (`capstone`). Install frontend packages the first time, then start the development server:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by the frontend, usually http://localhost:5173.

## Stop the application

Press **Ctrl+C** in each terminal running a server.

## Notes

- Run the backend environment setup and `npm install` again only if dependencies change. For later launches, start the backend and frontend using the commands above in separate terminals.
- The backend API is available at http://127.0.0.1:8000. Its interactive API documentation is at http://127.0.0.1:8000/docs.
- In VS Code, reload the window if needed, then select the project environment: `backend/.venv/bin/python` on macOS or `backend\.venv\Scripts\python.exe` on Windows.
