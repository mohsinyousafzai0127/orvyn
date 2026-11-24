@echo off
rem Orvyn launcher: double-click this file to start Orvyn in its own console window.
title Orvyn
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONUTF8=1

if exist ".venv\Scripts\activate.bat" goto start

echo.
echo   Orvyn cannot start: the virtual environment .venv was not found.
echo   Create it once, in this folder, with these commands:
echo.
echo       python -m venv .venv
echo       .venv\Scripts\activate.bat
echo       python -m pip install -r requirements.txt
echo       copy .env.example .env
echo.
echo   Then put your GOOGLE_API_KEY into the .env file and double-click orvyn.bat again.
echo.
pause
exit /b 1

:start
call ".venv\Scripts\activate.bat"
python -m src.main
set EXITCODE=%ERRORLEVEL%
echo.
if not "%EXITCODE%"=="0" echo   Orvyn stopped with exit code %EXITCODE%.
pause
