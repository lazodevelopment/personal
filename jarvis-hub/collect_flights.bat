@echo off
rem JARVIS flights feed - every minute (Task Scheduler "JARVIS flights")
cd /d C:\Users\kurvh\jarvis-hub
rem keep the log under ~1 MB: start over from the last 2000 lines once it passes that
for %%F in (collect_flights.log) do if %%~zF GTR 1000000 powershell -NoProfile -Command "$l = Get-Content collect_flights.log -Tail 2000; Set-Content collect_flights.log $l"
C:\Users\kurvh\lazo-directory\.venv\Scripts\python.exe collect_flights.py --global-only >> collect_flights.log 2>&1
exit /b %errorlevel%
