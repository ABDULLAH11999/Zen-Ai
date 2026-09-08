@echo off
:: Batch script to set Windows Hello PIN as the Default Credential Provider on Windows 11
echo ==========================================================
echo Setting Windows Hello PIN as Primary Sign-In Option...
echo ==========================================================

:: Check for Administrator permissions
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Administrator privileges required.
    echo Right-click this file and select 'Run as Administrator'.
    pause
    exit /b 1
)

:: Set NGC PIN Credential Provider as Default
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\System" /v DefaultCredentialProvider /t REG_SZ /d "{D6886603-9D2F-4EB2-B667-1971041FA96B}" /f

if %errorlevel% equ 0 (
    echo.
    echo [SUCCESS] Windows Hello PIN is now configured as the Default/Primary Sign-In option!
    echo Fingerprint remains active as secondary option in the background.
    echo.
) else (
    echo.
    echo [ERROR] Failed to update registry. Please ensure you ran as Administrator.
    echo.
)

pause
