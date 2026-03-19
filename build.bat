@echo off
echo Building Wuys Edge Manager...
echo.

REM Kiểm tra xem PyInstaller đã được cài đặt chưa
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller chua duoc cai dat. Dang cai dat...
    pip install pyinstaller
)

echo.
echo Dang build ung dung...

REM Build với file spec
pyinstaller build_wuys_manager.spec

echo.
if %errorlevel% equ 0 (
    echo Build thanh cong!
    echo File exe duoc tao tai: dist\WuysEdgeManager.exe
) else (
    echo Build that bai. Vui long kiem tra lai.
)

pause