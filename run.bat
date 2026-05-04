@echo off
echo ==============================================
echo Indian Stock Analysis API - Startup Script
echo ==============================================

echo [1/3] Installing Backend Dependencies...
cd backend
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install backend dependencies. Please check your Python installation.
    pause
    exit /b %errorlevel%
)
cd ..

echo [2/3] Installing Frontend Dependencies...
cd frontend
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install frontend dependencies. Please check your Python installation.
    pause
    exit /b %errorlevel%
)
cd ..

echo [3/3] Starting Services...

echo Starting FastAPI Backend on Port 8000...
start cmd /k "cd backend && uvicorn main:app --host 0.0.0.0 --port 8000"

echo Starting Streamlit Frontend on Port 8501...
start cmd /k "cd frontend && streamlit run app.py"

echo Both services have been started in new windows.
echo - Backend API: https://ai-project-1-ooli.onrender.com/docs
echo - Frontend UI: https://ai-project-1-qe2sp8spvczl8w6yqkg8sa.streamlit.app/
pause
