@echo off
REM Installation script for Native Messaging Host on Windows
REM Supports Chrome and Microsoft Edge

setlocal EnableDelayedExpansion

REM Get script directory
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

set HOST_NAME=com.videodownloader.host
set MANIFEST_FILE=%SCRIPT_DIR%\%HOST_NAME%.json
set HOST_SCRIPT=%SCRIPT_DIR%\video_downloader_host.py

REM Native Messaging directories
set CHROME_NM_DIR=%LOCALAPPDATA%\Google\Chrome\User Data\NativeMessagingHosts
set EDGE_NM_DIR=%LOCALAPPDATA%\Microsoft\Edge\User Data\NativeMessagingHosts

echo ======================================
echo Video Downloader Native Host Installer
echo ======================================
echo.

REM Check Python installation
echo Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.10 or higher from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python found: %PYTHON_VERSION%
echo.

REM Create directories if they don't exist
echo Creating Native Messaging directories...
if not exist "%CHROME_NM_DIR%" mkdir "%CHROME_NM_DIR%"
if not exist "%EDGE_NM_DIR%" mkdir "%EDGE_NM_DIR%"

REM Copy manifest to Native Messaging directories
REM Windows doesn't support symlinks easily, so we copy the file
echo Installing manifest...
copy /Y "%MANIFEST_FILE%" "%CHROME_NM_DIR%\%HOST_NAME%.json" >nul
copy /Y "%MANIFEST_FILE%" "%EDGE_NM_DIR%\%HOST_NAME%.json" >nul

echo.
echo [SUCCESS] Native Messaging Host installed successfully!
echo.
echo Manifest installed to:
echo   - Chrome: %CHROME_NM_DIR%
echo   - Edge:   %EDGE_NM_DIR%
echo.

echo ======================================
echo IMPORTANT NEXT STEPS:
echo ======================================
echo.
echo 1. Load the extension in Chrome or Edge:
echo    - Open chrome://extensions/ or edge://extensions/
echo    - Enable 'Developer mode'
echo    - Click 'Load unpacked'
echo    - Select the extension folder in your project
echo.
echo 2. Copy the Extension ID
echo    (looks like: abcdefghijklmnopqrstuvwxyz123456)
echo.
echo 3. Update the manifest file:
echo    Edit: %MANIFEST_FILE%
echo    Replace placeholders:
echo      - YOUR_EXTENSION_ID_HERE --^> your Extension ID
echo      - /ABSOLUTE/PATH/TO/YOUR/PROJECT --^> C:\path\to\your\project
echo.
echo    IMPORTANT: Use forward slashes (/) or double backslashes (\\)
echo    Example: C:/Users/YourName/Downloads/Video-Downloader
echo    OR:      C:\\Users\\YourName\\Downloads\\Video-Downloader
echo.
echo 4. Run this installer script again to update:
echo    install_host.bat
echo.
echo 5. Reload the extension in Chrome/Edge
echo.
echo Done!
echo.
pause
