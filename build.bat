@echo off
echo Building FFastGPU...
echo.

REM Check if PyInstaller is installed
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo Error: PyInstaller is not installed!
    echo Please install it with: pip install pyinstaller
    pause
    exit /b 1
)

REM Auto-increment version number
python increment_version.py
if errorlevel 1 (
    echo Error: Failed to increment version!
    pause
    exit /b 1
)

REM Check if nvidia-smi.exe exists
if not exist "C:\Windows\System32\nvidia-smi.exe" (
    echo Warning: nvidia-smi.exe not found in System32!
    echo The application may not have GPU monitoring functionality.
    echo.
)

REM Run PyInstaller with all parameters
echo Starting PyInstaller build...
pyinstaller --clean --onefile --windowed ^
    --name "FFastGPU" ^
    --add-binary "res/nvidia-smi.exe;." ^
    --version-file version_info.txt ^
    FFastGPU.py

REM Check if build was successful
if errorlevel 1 (
    echo.
    echo Build failed!
    pause
    exit /b 1
) else (
    echo.
    echo Build completed successfully!
    echo Executable: dist\FFastGPU.exe
)

pause