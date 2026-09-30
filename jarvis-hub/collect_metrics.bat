@echo off
rem JARVIS metrics collector - scheduled hourly (Task Scheduler task "JARVIS metrics")
cd /d C:\Users\kurvh\jarvis-hub
C:\Users\kurvh\lazo-directory\.venv\Scripts\python.exe collect_metrics.py >> collect_metrics.log 2>&1
