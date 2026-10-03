@echo off
rem JARVIS flights feed - every minute (Task Scheduler "JARVIS flights")
cd /d C:\Users\kurvh\jarvis-hub
C:\Users\kurvh\lazo-directory\.venv\Scripts\python.exe collect_flights.py --global-only >> collect_flights.log 2>&1
