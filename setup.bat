@echo off
cd /d "%~dp0"
echo [1/3] Sanal ortam olusturuluyor (.venv)...
rem Anaconda python'u kullanma: eski msvcp140.dll yuzunden PySide6 (QtCore) yuklenemiyor.
py -3.11 -m venv .venv 2>nul || python -m venv .venv || (echo Python bulunamadi. python.org'dan kurup "Add to PATH" secin. & pause & exit /b 1)
echo [2/3] Paketler kuruluyor...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt || (echo Paket kurulumu basarisiz. & pause & exit /b 1)
echo [3/3] Kurulum tamam. Uygulama aciliyor...
python src\main.py
pause
