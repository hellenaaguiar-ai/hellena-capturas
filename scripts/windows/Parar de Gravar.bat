@echo off
cd /d "C:\hellena-capturas"
.venv\Scripts\python.exe -m voice_capture.desktop.trigger stop
if errorlevel 1 pause
