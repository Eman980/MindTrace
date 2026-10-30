@echo off
echo ========================================================
echo   Starting MindTrace Localhost Environment
echo ========================================================
echo.
echo Starting Backend (FastAPI on http://127.0.0.1:8000)...
start "MindTrace Backend" cmd /k "cd /d %~dp0backend && .\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"

echo Waiting for backend to initialize...
timeout /t 2 >nul

echo Starting Frontend (Vite on http://localhost:5173)...
start "MindTrace Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo Waiting for frontend...
timeout /t 3 >nul

echo Opening browser...
start http://localhost:5173

echo.
echo ========================================================
echo   MindTrace is starting up!
echo   Frontend : http://localhost:5173
echo   Backend  : http://127.0.0.1:8000
echo   API Docs : http://127.0.0.1:8000/docs
echo ========================================================

