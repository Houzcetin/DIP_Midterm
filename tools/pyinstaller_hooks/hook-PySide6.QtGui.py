"""Keep QtGui's regular plugins without bundling PDF and touch-keyboard stacks."""

from pathlib import Path

from PyInstaller.utils.hooks.qt import add_qt6_dependencies

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
# These plugins pull in native QtPdf, QtQuick, and QtQml even when their Python
# modules are excluded. The desktop app reads images with OpenCV.
binaries = [entry for entry in binaries
            if Path(entry[0]).name.lower() not in {"qpdf.dll", "qtvirtualkeyboardplugin.dll"}]
