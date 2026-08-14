@echo off
cd /d "%~dp0..\.."
.venv\Scripts\python.exe -m voice_capture.desktop.trigger idea
if errorlevel 1 pause
