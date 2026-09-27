@echo off
REM ===================================================================
REM  Atavia Weddings — venue directory: fetch, generate, build.
REM  Double-click to run. Requires GOOGLE_PLACES_API_KEY to be set once:
REM
REM    [Environment]::SetEnvironmentVariable("GOOGLE_PLACES_API_KEY","AIza...","User")
REM
REM  ...then reopen PowerShell. Verify with:  echo %GOOGLE_PLACES_API_KEY%
REM ===================================================================
cd /d "%~dp0"

if "%GOOGLE_PLACES_API_KEY%"=="" (
  echo.
  echo   GOOGLE_PLACES_API_KEY is not set.
  echo   Run this once in PowerShell, then reopen it:
  echo.
  echo     [Environment]::SetEnvironmentVariable^("GOOGLE_PLACES_API_KEY","AIza...","User"^)
  echo.
  pause
  exit /b 1
)

echo.
echo  [1/3] Fetching venues from Google Places...
python _src\fetch_venues.py
if errorlevel 1 goto :err

echo.
echo  [2/3] Generating venue directory pages...
python _src\gen_venues.py
if errorlevel 1 goto :err

echo.
echo  [3/3] Building site + sitemaps...
python _src\build.py
if errorlevel 1 goto :err

echo.
echo  ================================================
echo   DONE. Now redeploy to Cloudflare Pages:
echo   drag this folder's contents (WITHOUT _src)
echo   into Pages ^> atavia ^> Create deployment
echo  ================================================
echo.
pause
exit /b 0

:err
echo.
echo   Something failed above. Read the error, fix, re-run.
pause
exit /b 1
