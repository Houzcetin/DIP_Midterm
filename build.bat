@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
pyinstaller --noconfirm --onefile --windowed --name DIP_Midterm src\main.py
echo.
echo Exe hazir: dist\DIP_Midterm.exe
pause
