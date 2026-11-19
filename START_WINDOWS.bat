@echo off
title TRINETRA Setup
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python Launcher was not found. Install 64-bit Python 3.11 from python.org.
  pause
  exit /b 1
)
py -3.11 -c "import struct,sys; assert struct.calcsize('P')*8 == 64; print(sys.version)" >nul 2>nul
if errorlevel 1 (
  echo 64-bit Python 3.11 was not found.
  echo Install Python 3.11 64-bit, then run this file again.
  pause
  exit /b 1
)
if exist .venv\pyvenv.cfg (
  findstr /C:"version = 3.11" .venv\pyvenv.cfg >nul
  if errorlevel 1 (
    echo The existing .venv was made with the wrong Python version.
    echo Delete the .venv folder once, then run this file again.
    pause
    exit /b 1
  )
)
if not exist .venv\Scripts\python.exe (
  echo Creating the TRINETRA environment...
  py -3.11 -m venv .venv
  if errorlevel 1 goto :failed
)
echo Installing or checking required packages...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install --only-binary=:all: -r requirements-dashboard.txt
if errorlevel 1 goto :failed
echo Starting TRINETRA at http://localhost:8501 ...
start "TRINETRA Server - KEEP OPEN" cmd /k "cd /d %~dp0 && .venv\Scripts\python.exe -m streamlit run app.py --server.port 8501 --server.address localhost"
timeout /t 8 >nul
start "" "http://localhost:8501"
echo If the browser does not open, visit http://localhost:8501 manually.
pause
exit /b 0
:failed
echo.
echo Setup failed. Copy the error shown above and send it for correction.
pause
exit /b 1
