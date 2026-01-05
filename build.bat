@echo off
chcp 65001 >nul
echo ========================================
echo   Product Price Finder - EXE Build
echo ========================================
echo.

REM Install dependencies
echo [1/2] Installing dependencies...
pip install -r requirements.txt

echo.
echo [2/2] Building EXE file...
pyinstaller --onefile --windowed --name "PriceFinder" price_finder_gui.py

echo.
echo ========================================
echo   Build complete!
echo   Use: dist\PriceFinder.exe
echo.
echo   * API key settings will appear on first run.
echo   * Get API key from Naver Developer Center.
echo ========================================
pause
