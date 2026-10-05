@echo off
rem JARVIS wake - every minute (Task Scheduler "JARVIS wake"): opens JARVIS in a kiosk window when the hub's alarm fires
cd /d C:\Users\kurvh\jarvis-hub
C:\Users\kurvh\lazo-directory\.venv\Scripts\python.exe jarvis_wake.py >> jarvis_wake.log 2>&1
