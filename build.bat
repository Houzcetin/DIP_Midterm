@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0" || exit /b 1
set "result=1"
if not exist ".venv\Scripts\python.exe" (
    echo Error: .venv\Scripts\python.exe is missing. Run setup.bat first. 1>&2
    goto :done
)

rem The histogram uses QtAgg, which needs the Qt and Agg backend modules.
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --onefile --windowed ^
    --name DIP_Midterm --paths src --additional-hooks-dir tools\pyinstaller_hooks ^
    --exclude-module PySide6.QtWebEngineCore ^
    --exclude-module PySide6.QtWebEngineWidgets ^
    --exclude-module PySide6.QtWebEngineQuick ^
    --exclude-module PySide6.QtQml ^
    --exclude-module PySide6.QtQuick ^
    --exclude-module PySide6.QtQuick3D ^
    --exclude-module PySide6.QtQuickControls2 ^
    --exclude-module PySide6.QtQuickWidgets ^
    --exclude-module PySide6.Qt3DAnimation ^
    --exclude-module PySide6.Qt3DCore ^
    --exclude-module PySide6.Qt3DExtras ^
    --exclude-module PySide6.Qt3DInput ^
    --exclude-module PySide6.Qt3DLogic ^
    --exclude-module PySide6.Qt3DRender ^
    --exclude-module PySide6.QtMultimedia ^
    --exclude-module PySide6.QtMultimediaWidgets ^
    --exclude-module PySide6.QtPdf ^
    --exclude-module PySide6.QtPdfWidgets ^
    --exclude-module tkinter ^
    --exclude-module matplotlib.backends._backend_tk ^
    --exclude-module matplotlib.backends.backend_cairo ^
    --exclude-module matplotlib.backends.backend_macosx ^
    --exclude-module matplotlib.backends.backend_nbagg ^
    --exclude-module matplotlib.backends.backend_pdf ^
    --exclude-module matplotlib.backends.backend_pgf ^
    --exclude-module matplotlib.backends.backend_ps ^
    --exclude-module matplotlib.backends.backend_qt5agg ^
    --exclude-module matplotlib.backends.backend_qt5cairo ^
    --exclude-module matplotlib.backends.backend_qtcairo ^
    --exclude-module matplotlib.backends.backend_svg ^
    --exclude-module matplotlib.backends.backend_webagg ^
    --exclude-module matplotlib.backends.backend_webagg_core ^
    --exclude-module IPython ^
    --exclude-module pytest ^
    src\main.py
set "result=%errorlevel%"
if not "%result%"=="0" (
    echo Error: PyInstaller failed with exit code %result%. 1>&2
    goto :done
)
echo Built dist\DIP_Midterm.exe

:done
if not "%~1"=="" exit /b %result%
rem Explorer uses cmd.exe /c ""full-path\build.bat" " for a double-click.
setlocal EnableDelayedExpansion
set "launch=!cmdcmdline:"=@!"
if not "!launch!"=="!launch: /c @@%~f0@ @=!" pause
exit /b %result%
