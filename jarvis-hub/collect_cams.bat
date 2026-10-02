@echo off
rem JARVIS camera directory - daily (Task Scheduler "JARVIS cameras")
cd /d C:\Users\kurvh\jarvis-hub
C:\Users\kurvh\lazo-directory\.venv\Scripts\python.exe collect_cams.py >> collect_cams.log 2>&1
