"""Member figures: assets, crops, and where the window shows them."""

import pytest
from PySide6.QtCore import QSettings

from ui import avatars
from ui.main_window import MainWindow
from ui.themes import THEMES, app_icon, theme_icon


def test_every_theme_has_a_member_figure():
    assert set(avatars.MEMBERS) == set(THEMES)
    for member in avatars.MEMBERS:
        assert (avatars.asset_dir() / f"{member}.png").is_file()


@pytest.mark.parametrize("member", avatars.MEMBERS)
def test_figure_is_cropped_to_opaque_pixels(qapp, member):
    fig = avatars.figure(member)
    assert not fig.isNull()
    assert fig.width() < 384 and fig.height() < 640
    # The crop touches opaque pixels on every edge.
    alpha = avatars._alpha(fig) > 16
    assert alpha[0].any() and alpha[-1].any() and alpha[:, 0].any() and alpha[:, -1].any()


@pytest.mark.parametrize("member", avatars.MEMBERS)
def test_head_crop_is_square_and_mostly_opaque(qapp, member):
    face = avatars.head(member)
    assert face.width() == face.height() > 32
    assert (avatars._alpha(face) > 16).mean() > 0.4


def test_scaling_keeps_pixels_crisp(qapp):
    big = avatars.scaled(avatars.head("mina"), 380)
    assert big.height() == 380
    assert big.pixelColor(0, 0) == big.pixelColor(1, 1)  # nearest-neighbour blocks


def test_theme_icons_use_member_heads(qapp):
    for theme in THEMES.values():
        assert not theme_icon(theme).isNull()
        assert not app_icon(theme).isNull()
        assert theme_icon(theme).cacheKey() == avatars.head_icon(theme.id).cacheKey()


def test_window_shows_selected_member(qapp, tmp_path):
    window = MainWindow(QSettings(str(tmp_path / "a.ini"), QSettings.Format.IniFormat))
    try:
        for theme in THEMES.values():
            window.set_theme(theme.id)
            assert window.original_view._placeholder is avatars.figure(theme.id)
            assert theme.member in window.ops_panel.member_name.text()
            assert not window.ops_panel.member_figure.pixmap().isNull()
    finally:
        window.close()
        window.deleteLater()
