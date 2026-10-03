@echo off
rem JARVIS watch collector - every 15 minutes (Task Scheduler "JARVIS watch")
cd /d C:\Users\kurvh\jarvis-hub
C:\Users\kurvh\lazo-directory\.venv\Scripts\python.exe collect_watch.py --only social >> collect_watch.log 2>&1
