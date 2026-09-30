@echo off
rem JARVIS hands - executes actions confirmed on the hub. Start from Task Scheduler at logon, or double-click.
cd /d C:\Users\kurvh\jarvis-hub
:loop
C:\Users\kurvh\lazo-directory\.venv\Scripts\python.exe jarvis_hands.py >> jarvis_hands.log 2>&1
timeout /t 30 /nobreak >nul
goto loop
