@echo off
REM lazo-outreach-daily.bat - JC-LAZO-OUTREACH-1019
REM Task Scheduler runs this every morning: sync Smartlead results into Firestore, then feed the next slice of
REM vendors into the claim campaign. Logs to generate\data\outreach\_daily.log plus a per-day console log.
setlocal
set ROOT=C:\Users\kurvh\lazo-directory
set LOGDIR=%ROOT%\deploy\logs
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set D=%%i
cd /d "%ROOT%"
"%ROOT%\.venv\Scripts\python.exe" "%ROOT%\generate\outreach_daily.py" %* >> "%LOGDIR%\outreach-%D%.log" 2>&1
exit /b %ERRORLEVEL%
