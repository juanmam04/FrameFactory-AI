@echo off
cd /d "%~dp0"
echo FrameFactory Documentary Studio
echo Open http://127.0.0.1:8787
if exist "venv\Scripts\python.exe" (
  "venv\Scripts\python.exe" -m uvicorn studio.app:app --reload --host 127.0.0.1 --port 8787
  exit /b %ERRORLEVEL%
)
python -m uvicorn studio.app:app --reload --host 127.0.0.1 --port 8787
