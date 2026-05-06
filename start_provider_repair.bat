@echo off
setlocal
cd /d "%~dp0"
python "%~dp0provider_repair_gui.py"
if errorlevel 1 (
  echo.
  echo Failed to start the tool. Make sure Python with Tkinter is installed.
  pause
)
