@echo off
rem JARVIS traffic collector - every 5 minutes (Task Scheduler "JARVIS traffic")
cd /d C:\Users\kurvh\jarvis-hub
C:\Users\kurvh\lazo-directory\.venv\Scripts\python.exe collect_traffic.py >> collect_traffic.log 2>&1
