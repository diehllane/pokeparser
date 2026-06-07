@echo off
setlocal EnableDelayedExpansion
title PokeParser Installer

echo.
echo  ============================================
echo   PokeParser Installer for Windows
echo  ============================================
echo.

:: ── Check Python ──────────────────────────────────────────────────────────────
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found.
    echo.
    echo  Install Python from https://python.org
    echo  On the first screen, check "Add Python to PATH" before clicking Install.
    echo.
    goto :error
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  [OK] Python %PYVER%

:: ── Check/Install Tesseract ───────────────────────────────────────────────────
where tesseract >nul 2>&1
if %errorlevel% equ 0 (
    echo  [OK] Tesseract already on PATH.
    goto :pip
)

if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo  [OK] Tesseract found at default location.
    set "PATH=%PATH%;C:\Program Files\Tesseract-OCR"
    goto :pip
)

echo.
echo  ============================================
echo   STEP 1 OF 2: Install Tesseract OCR
echo  ============================================
echo.
echo  Downloading Tesseract installer...
echo.

set "TESS_EXE=%TEMP%\tesseract_setup.exe"
set "TESS_URL=https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3.20231005/tesseract-ocr-w64-setup-5.3.3.20231005.exe"

curl -L --progress-bar -o "%TESS_EXE%" "%TESS_URL%" 2>&1
if %errorlevel% neq 0 (
    powershell -NoProfile -Command "Invoke-WebRequest -Uri '%TESS_URL%' -OutFile '%TESS_EXE%' -UseBasicParsing"
)

if not exist "%TESS_EXE%" (
    echo.
    echo  [ERROR] Could not download Tesseract automatically.
    echo  Install it manually from: https://github.com/UB-Mannheim/tesseract/wiki
    echo  Keep the default install path, then run this script again.
    goto :error
)

echo.
echo  Running Tesseract installer...
echo  Keep the default install path: C:\Program Files\Tesseract-OCR\
echo.
"%TESS_EXE%"
del "%TESS_EXE%" >nul 2>&1

set "PATH=%PATH%;C:\Program Files\Tesseract-OCR"
setx TESSDATA_PREFIX "C:\Program Files\Tesseract-OCR\tessdata" >nul 2>&1

if not exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo  [ERROR] Tesseract install could not be verified.
    echo  Try installing manually from https://github.com/UB-Mannheim/tesseract/wiki
    goto :error
)
echo  [OK] Tesseract installed.

:: ── Python packages ───────────────────────────────────────────────────────────
:pip
echo.
echo  ============================================
echo   STEP 2 OF 2: Install Python packages
echo  ============================================
echo.

python -m pip install --upgrade pip --quiet

python -m pip install ^
    pillow ^
    pytesseract ^
    numpy ^
    openpyxl ^
    google-api-python-client ^
    google-auth-httplib2 ^
    google-auth-oauthlib ^
    requests ^
    tkinterdnd2 ^
    pyinstaller

if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Package install failed.
    echo  Try right-clicking install_windows.bat and "Run as administrator".
    goto :error
)
echo.
echo  [OK] All packages installed.

:: ── Build ─────────────────────────────────────────────────────────────────────
echo.
echo  ============================================
echo   Building PokeParser.exe
echo  ============================================
echo.
echo  Takes 60-120 seconds. Window may look frozen - that is normal.
echo.

set "SCRIPT_DIR=%~dp0"
:: Remove trailing backslash
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

cd /d "%SCRIPT_DIR%"

:: Remove stale build artifacts to guarantee fresh compile
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
echo  [OK] Cleaned previous build files.

python -m PyInstaller pokeparser.spec --noconfirm --clean

if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Build failed. See output above for details.
    goto :error
)

set "APP_DIR=%SCRIPT_DIR%\dist\PokeParser"
set "EXE=%APP_DIR%\PokeParser.exe"

echo.
echo  [OK] Build complete.
echo  App location: %APP_DIR%
echo.

:: ── Desktop shortcut (3 methods, first that works wins) ───────────────────────
set "DESKTOP=%USERPROFILE%\Desktop"
set "LNK=%DESKTOP%\PokeParser.lnk"

echo  Creating Desktop shortcut...

:: Method 1: VBScript (most reliable, no PowerShell policy needed)
set "VBS=%TEMP%\make_shortcut.vbs"
(
    echo Set oShell = CreateObject("WScript.Shell"^)
    echo Set oLink = oShell.CreateShortcut("%LNK%"^)
    echo oLink.TargetPath = "%EXE%"
    echo oLink.WorkingDirectory = "%APP_DIR%"
    echo oLink.Description = "PokeParser OCR Tool"
    echo oLink.Save
) > "%VBS%"
cscript //nologo "%VBS%"
del "%VBS%" >nul 2>&1

if exist "%LNK%" (
    echo  [OK] Shortcut created on Desktop.
) else (
    :: Method 2: PowerShell with bypass flag
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$s=(New-Object -COM WScript.Shell).CreateShortcut('%LNK%'); $s.TargetPath='%EXE%'; $s.WorkingDirectory='%APP_DIR%'; $s.Save()" >nul 2>&1

    if exist "%LNK%" (
        echo  [OK] Shortcut created on Desktop.
    ) else (
        :: Method 3: Just copy the exe to Desktop as fallback
        copy "%EXE%" "%DESKTOP%\PokeParser.exe" >nul 2>&1
        if exist "%DESKTOP%\PokeParser.exe" (
            echo  [OK] Copied PokeParser.exe directly to Desktop.
        ) else (
            echo  [WARN] Could not create Desktop shortcut automatically.
            echo  You can find the app here:
            echo  %EXE%
        )
    )
)

:: ── Done ──────────────────────────────────────────────────────────────────────
echo.
echo  ============================================
echo   Installation Complete!
echo  ============================================
echo.
echo  App is at:
echo  %EXE%
echo.
echo  To share with other players:
echo  Zip this folder and send it:
echo  %APP_DIR%
echo  (They will need Tesseract installed - see README.md)
echo.
pause
exit /b 0

:error
echo.
pause
exit /b 1
