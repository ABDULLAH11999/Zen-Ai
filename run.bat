@echo off
title Z.E.N. Autonomous System & Mobile Cloud Portal
color 0b
cls

:: Switch to Zen Ai directory
cd /d "F:\Zen Agent\Zen Ai"

echo ======================================================================
echo          Z.E.N. (Zero-latency Executive Neural-network) 2.0           
echo              Master Unified System for Sir Abdullah Irfan             
echo ======================================================================
echo.
echo [*] Directory: %CD%
echo.

:: Clear any stale process on Port 5050 to prevent WinError 10048
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5050" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo [1/2] Starting Mobile Web Audio Portal (Port 5050 + Tailscale SSL)...
start "ZEN Mobile Web Portal (Port 5050)" cmd /k "cd /d "F:\Zen Agent\Zen Ai" && color 0a && title ZEN Mobile Web Portal (Port 5050) && set PYTHONIOENCODING=utf-8 && "C:\laragon\bin\python\python-3.13\python.exe" zen_web_portal.py"

timeout /t 2 /nobreak >nul

echo [2/2] Starting Desktop AI Assistant & Voice Engine (GUI)...
echo.
set PYTHONIOENCODING=utf-8
"C:\laragon\bin\python\python-3.13\python.exe" main.py

pause
