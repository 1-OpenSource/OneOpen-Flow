@echo off
REM OneOpen Flow local development helper (Windows)
cd /d "%~dp0"

echo Starting backend on :8000 ...
start "oneopen-flow-backend" cmd /c "cd backend && set DATABASE_URL=sqlite:///./oneopen_flow.db && .venv\Scripts\uvicorn app.main:app --reload --port 8000"

echo Starting frontend on :5173 ...
start "oneopen-flow-frontend" cmd /c "cd frontend && npm run dev"

echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo Seed user: owner@oneopen.local / ChangeMe123!
echo.
pause
