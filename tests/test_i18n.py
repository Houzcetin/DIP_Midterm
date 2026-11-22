"""Exercise runtime translation through the application's visible UI."""

import re

import pytest
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractButton, QApplication, QComboBox, QDialog, QFileDialog, QGroupBox,
    QLabel, QListWidget, QMenu, QSpinBox, QToolBox, QWidget,
)

from ops.registry import OPERATIONS, get_op
from ui.i18n import TURKISH, current_language, missing_keys, set_language
from ui.image_view import ImageView
from ui.main_window import MainWindow
from ui.ops_panel import GROUPS


@pytest.fixture
def settings(tmp_path):
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


@pytest.fixture
def create_window(qapp):
    windows = []

    def create(settings):
        window = MainWindow(settings)
        windows.append(window)
        window.show()
        qapp.processEvents()
        return window

    yield create
    for window in windows:
        window.close()
        window.deleteLater()
    set_language("en")
    missing_keys.clear()


def widget_texts(root):
    texts = []
    for widget in (root, *root.findChildren(QWidget)):
        texts.extend((widget.windowTitle(), widget.toolTip(), widget.statusTip()))
        if isinstance(widget, (QLabel, QAbstractButton, ImageView)):
            texts.append(widget.text())
        if isinstance(widget, (QGroupBox, QMenu)):
            texts.append(widget.title())
        if isinstance(widget, (QToolBox, QComboBox)):
            texts.extend(widget.itemText(i) for i in range(widget.count()))
        if isinstance(widget, QListWidget):
            for row in range(widget.count()):
                texts.extend((widget.item(row).text(), widget.item(row).toolTip()))
    for action in root.findChildren(QAction):
        if action.isVisible():
            texts.extend((action.text(), action.toolTip(), action.statusTip()))
    return sorted(text for text in texts if text)


def plot_texts(view):
    return [text for ax in view.axes for text in (
        ax.get_title(), ax.get_xlabel(), ax.get_ylabel(), *(label.get_text() for label in ax.texts)
    ) if text]


def without_mnemonics(text):
    return re.sub(r"(?<!&)&(?![ &])", "", text).replace("&&", "&")


def assert_turkish(texts):
    english = {without_mnemonics(source) for source, translation in TURKISH.items()
               if source != translation}
    untranslated = english & {without_mnemonics(text) for text in texts}
    assert not untranslated


def modal_texts(show):
    entries = []

    def inspect():
        dialog = QApplication.activeModalWidget()
        if isinstance(dialog, QDialog):
            entries.extend(widget_texts(dialog))
            if isinstance(dialog, QFileDialog):
                entries.extend(dialog.nameFilters())
            dialog.reject()

    QTimer.singleShot(0, inspect)
    show()
    assert entries
    assert_turkish(entries)
    return entries


def test_turkish_catalog_covers_window_dialogs_and_views(create_window, settings, tmp_path, monkeypatch):
    missing_keys.clear()
    settings.setValue("language", "tr")
    window = create_window(settings)
    window.show_histogram_window()
    window.show_frequency_inspector()
    assert window.original_view.text() == window.result_view.text() == "Görüntü yok"
    assert window.info_label.text() == "Başlamak için bir görüntü açın (Ctrl+O)"
    assert "Başlamak için bir görüntü açın" in plot_texts(window._frequency_dialog)
    assert "Piksel sayısı" in plot_texts(window.histogram_view)
    open_dialog = modal_texts(window.open_image)
    assert "Görüntü Aç" in open_dialog
    assert "Görüntüler (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)" in open_dialog
    assert {"Konum:", "Dosya türü:", "İptal"} <= {without_mnemonics(text) for text in open_dialog}
    assert "Lütfen önce bir görüntü açın." in modal_texts(window.save_image)
    assert "Sayısal Görüntü İşleme" in "\n".join(modal_texts(window.show_about))
    assert "Fare tekerleği" in "\n".join(modal_texts(window.show_shortcuts))
    assert "Dosya bulunamadı" in "\n".join(modal_texts(lambda: window._open_path(str(tmp_path / "missing.png"))))
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"invalid image")
    assert "Görüntü açılamadı" in "\n".join(modal_texts(lambda: window._open_path(str(broken))))
    assert_turkish(widget_texts(window) + plot_texts(window.histogram_view)
                   + plot_texts(window._dialog_histogram) + plot_texts(window._frequency_dialog))

    window.open_sample_image()
    assert window.statusBar().currentMessage().startswith("Gri tonlama")
    assert "Sonucu Kaydet" in modal_texts(window.save_image)
    saved = tmp_path / "sonuç.png"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_: (str(saved), ""))
    window.save_image()
    assert saved.is_file()
    assert window.statusBar().currentMessage() == f"Kaydedildi: {saved}"
    for error, message in ((ValueError, "Görüntü kaydedilemedi"), (PermissionError, "Erişim izni yok")):
        with monkeypatch.context() as patch:
            def fail_save(_):
                raise error()

            patch.setattr(window.state, "save", fail_save)
            assert message in "\n".join(modal_texts(window.save_image))

    for op in OPERATIONS:
        window.apply_operation(op.id, {p.name: p.default for p in op.params})
        window.undo()
    window.apply_operation("rotate", {"angle_deg": 25, "expand": False})
    assert "Tuvali genişlet=Hayır" in window.history_panel.item(1).text()
    assert "İşlem başarısız" in modal_texts(lambda: window.apply_operation("add_noise", {"kind": "invalid"}))
    window.preview_operation("flip", {"mode": "invalid"})
    assert window.statusBar().currentMessage() == "Önizleme oluşturulamadı: Çevirme"
    window._show_pixel(1, 2, 42)
    assert window.statusBar().currentMessage() == "x=1, y=2 | Gri=42"
    window._show_pixel(1, 2, (3, 4, 5))
    assert window.statusBar().currentMessage() == "x=1, y=2 | R,G,B=5,4,3"
    window.apply_operation("scale", {"sx": 0.5, "sy": 0.5})
    window.wipe_action.setChecked(True)
    window.result_view.grab()
    assert window.statusBar().currentMessage() == "boyutlar farklı — özgün görüntü sonuca uyarlandı"
    window.compare_action.setChecked(True)
    assert window._result_box.title() == "Sonuç — Özgün Görüntü gösteriliyor"
    assert_turkish(widget_texts(window))
    assert missing_keys == set()


def test_switch_round_trip_preserves_preview_parameters_and_history(create_window, settings, qapp):
    window = create_window(settings)
    window.open_sample_image()
    window.apply_operation("flip", {"mode": "v"})
    window.undo()
    toolbox = window.ops_panel.toolbox
    toolbox.setCurrentIndex(GROUPS.index("F Morphology"))
    page = toolbox.currentWidget()
    erode = next(box for box in page.findChildren(QGroupBox) if box.title() == "Erode")
    erode.findChildren(QSpinBox)[0].setValue(7)
    choice = erode.findChild(QComboBox)
    choice.setCurrentIndex(choice.findData("ellipse"))
    params = window.ops_panel.current_params("erode")
    window.ops_panel.cancel_pending_preview()
    window.preview_operation("erode", params)
    preview = window._preview_image
    window.show_histogram_window()
    window.show_frequency_inspector()
    window._frequency_dialog._render()
    qapp.processEvents()

    def snapshot():
        return (widget_texts(window), plot_texts(window._dialog_histogram),
                plot_texts(window._frequency_dialog), window.statusBar().currentMessage())

    english = snapshot()
    changes = []
    window.ops_panel.paramsChanged.connect(changes.append)
    window._language_actions["tr"].trigger()
    assert toolbox.currentWidget() is page
    assert window.ops_panel.current_params("erode") == params
    assert choice.currentText() == "Elips"
    assert window._preview_image is preview
    assert "Önizleme" in window.statusBar().currentMessage()
    assert window.history_panel.item(1).text() == "Çevirme (Yön=Dikey)"
    assert window.history_panel.currentRow() == 0
    assert window.state.can_redo()
    assert window._frequency_dialog.windowTitle() == "Frekans İnceleyici"
    assert window._frequency_dialog.axes[0].get_title() == "Genlik spektrumu"
    assert_turkish(widget_texts(window))
    window._language_actions["en"].trigger()
    assert snapshot() == english
    assert changes == []
    assert window._preview_image is preview
    assert window.ops_panel.current_params("erode") == params
    next(button for button in erode.findChildren(QAbstractButton) if button.text() == "Apply").click()
    assert window.state.history_labels()[-1].startswith(get_op("erode").label)


def test_language_menu_persists_and_unknown_setting_falls_back(create_window, settings):
    window = create_window(settings)
    view = next(action.menu() for action in window.menuBar().actions() if action.text() == "&View")
    language = next(action.menu() for action in view.actions() if action.text() == "Language")
    english, turkish = language.actions()
    assert [english.text(), turkish.text()] == ["English", "Türkçe"]
    assert english.isChecked() and not turkish.isChecked()
    turkish.trigger()
    assert current_language() == "tr"
    assert language.title() == "Dil"
    assert turkish.isChecked() and not english.isChecked()
    settings.sync()
    stored = QSettings(settings.fileName(), QSettings.Format.IniFormat)
    assert stored.value("language") == "tr"

    set_language("en")
    reopened = create_window(stored)
    assert current_language() == "tr"
    assert reopened._language_actions["tr"].isChecked()
    assert reopened.operations_dock.windowTitle() == "İşlemler"
    stored.setValue("language", "invalid")
    fallback = create_window(stored)
    assert fallback._language_actions["en"].isChecked()
    assert fallback.operations_dock.windowTitle() == "Operations"


def test_theme_labels_and_member_header_in_both_languages(create_window, settings):
    window = create_window(settings)
    window.set_theme("mina")
    assert [action.text() for action in window._theme_actions.values()] == [
        "Mina — Red", "Esin — Yellow", "Zeynep Sude — Blue",
        "Lidya — Pink", "Sueda — Green", "Hilal — Purple",
    ]
    assert "Red theme" in window.ops_panel.member_name.text()
    window.set_language("tr")
    assert [action.text() for action in window._theme_actions.values()] == [
        "Mina — Kırmızı", "Esin — Sarı", "Zeynep Sude — Mavi",
        "Lidya — Pembe", "Sueda — Yeşil", "Hilal — Mor",
    ]
    assert "Kırmızı tema" in window.ops_panel.member_name.text()
    assert window._theme_actions["mina"].isChecked()
    window._theme_actions["sueda"].trigger()
    assert "Yeşil tema" in window.ops_panel.member_name.text()
    window.set_language("en")
    assert "Green theme" in window.ops_panel.member_name.text()
