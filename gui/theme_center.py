from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from PyQt5.QtCore import QObject, pyqtSignal, Qt
from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QComboBox,
    QPushButton,
    QColorDialog,
    QDialog,
    QGroupBox,
    QFormLayout,
    QCheckBox,
)


def qc(x) -> QColor:
    """Coerce to QColor."""
    if isinstance(x, QColor):
        return QColor(x)
    x = str(x).strip()
    return QColor(x) if x.startswith("#") else QColor(x)


@dataclass
class Theme:
    name: str
    # QPalette roles (minimum set; Qt derives others)
    window: QColor
    base: QColor
    alt_base: QColor
    text: QColor
    disabled_text: QColor
    button: QColor
    button_text: QColor
    highlight: QColor
    highlighted_text: QColor
    link: QColor
    # Extra named colors for paint-code/QSS
    colors: Dict[str, QColor] = field(default_factory=dict)
    base_font_pt: int = 10

    def with_accent(self, accent: QColor) -> "Theme":
        t = Theme(**{**self.__dict__})
        t.colors = dict(self.colors)
        t.colors["accent"] = qc(accent)
        t.highlight = qc(accent)
        t.link = qc(accent)
        return t


# ---------------------------------------------------------------------------
# Built-in themes
# ---------------------------------------------------------------------------

HACKER_GREEN = Theme(
    name="Hacker Green (Dark)",
    window=qc("#050607"),
    base=qc("#0b0d0f"),
    alt_base=qc("#101417"),
    text=qc("#c7f7d4"),
    disabled_text=qc("#4aa36a"),
    button=qc("#0f1417"),
    button_text=qc("#c7f7d4"),
    highlight=qc("#00ff66"),
    highlighted_text=qc("#001a0a"),
    link=qc("#00ff66"),
    colors={
        # Generic UI tokens
        "accent": qc("#00ff66"),
        "border": qc("#144d2c"),
        "header_bg": qc("#0e1113"),
        "panel": qc("#0b0d0f"),
        "panel_2": qc("#101417"),

        # Graph / neon tokens used by session_graph.py
        "window_bg": qc("#000000"),
        "neon": qc("#00ff66"),
        "neon_dim": qc("#00c955"),

        # Status
        "danger": qc("#ff3b3b"),
        "warning": qc("#ffb020"),

        # Scrollbars
        "scroll_handle": qc("#1d6b3f"),
        "scroll_handle_hover": qc("#2a8a53"),

        # Chips (if used)
        "chip_operator_bg": qc("#0f2a1a"),
        "chip_operator_fg": qc("#c7f7d4"),
        "chip_admin_bg": qc("#2a0f0f"),
        "chip_admin_fg": qc("#ffd6d6"),
    },
    base_font_pt=10,
)


_BUILTINS = {t.name: t for t in (HACKER_GREEN,)}


def make_palette(t: Theme) -> QPalette:
    pal = QPalette()
    pal.setColor(QPalette.Window, t.window)
    pal.setColor(QPalette.WindowText, t.text)
    pal.setColor(QPalette.Base, t.base)
    pal.setColor(QPalette.AlternateBase, t.alt_base)
    pal.setColor(QPalette.ToolTipBase, t.base)
    pal.setColor(QPalette.ToolTipText, t.text)
    pal.setColor(QPalette.Text, t.text)
    pal.setColor(QPalette.Button, t.button)
    pal.setColor(QPalette.ButtonText, t.button_text)
    pal.setColor(QPalette.Highlight, t.highlight)
    pal.setColor(QPalette.HighlightedText, t.highlighted_text)
    pal.setColor(QPalette.Link, t.link)
    pal.setColor(QPalette.Disabled, QPalette.Text, t.disabled_text)
    pal.setColor(QPalette.Disabled, QPalette.WindowText, t.disabled_text)
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, t.disabled_text)
    pal.setColor(QPalette.Disabled, QPalette.ToolTipText, t.disabled_text)
    return pal


def build_global_qss(t: Theme) -> str:
    c = t.colors
    b = c.get("border", qc("#144d2c")).name()
    acc = c.get("accent", qc("#00ff66")).name()
    header_bg = c.get("header_bg", t.alt_base).name()
    sh = c.get("scroll_handle", qc("#1d6b3f")).name()
    shh = c.get("scroll_handle_hover", qc("#2a8a53")).name()

    # IMPORTANT: Avoid transparency anywhere. The app uses a custom titlebar in
    # some builds; any translucent background causes the tab-strip to show the
    # desktop behind it.
    return f"""
    QWidget {{
        background: {t.window.name()};
        color: {t.text.name()};
        font-size: {t.base_font_pt}pt;
    }}

    QMainWindow {{
        background: {t.window.name()};
    }}

    /* If MainWindow uses a wrapper widget (objectName="MainWrapper"),
       force it to be opaque to avoid "transparent tabs" artifacts. */
    QWidget#MainWrapper {{
        background: {t.base.name()};
        border: 1px solid {b};
        border-radius: 14px;
    }}

    /* Common tabbed views (Sessions / Listeners / Payloads / Operators ...) */
    QTabWidget, QTabWidget::pane {{
        background: {t.base.name()};
        border: 1px solid {b};
        border-radius: 12px;
    }}
    QTabBar {{
        background: {t.base.name()};
    }}
    QTabBar::tab {{
        background: {t.button.name()};
        border: 1px solid {b};
        border-bottom: none;
        padding: 7px 12px;
        margin-right: 6px;
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
        color: {t.text.name()};
        min-height: 24px;
    }}
    QTabBar::tab:selected {{
        background: {t.base.name()};
        border-color: {acc};
    }}
    QTabBar::tab:hover {{
        border-color: {acc};
    }}

    /* --- Tooltips --- */
    QToolTip {{
        background: {t.base.name()};
        color: {t.text.name()};
        border: 1px solid {b};
        padding: 6px 8px;
        border-radius: 8px;
    }}

    /* --- Menus --- */
    QMenu {{
        background: {t.base.name()};
        border: 1px solid {b};
        padding: 6px;
        border-radius: 10px;
    }}
    QMenu::item {{
        padding: 7px 10px;
        border-radius: 8px;
        background: transparent;
        color: {t.text.name()};
    }}
    QMenu::item:selected {{
        background: {acc};
        color: {t.highlighted_text.name()};
    }}

    /* --- Group boxes / cards --- */
    QGroupBox {{
        border: 1px solid {b};
        border-radius: 12px;
        margin-top: 10px;
        padding: 10px;
        background: {t.base.name()};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 6px;
        color: {t.text.name()};
        font-weight: 600;
    }}

    QFrame#Card, QWidget#Card {{
        background: {t.base.name()};
        border: 1px solid {b};
        border-radius: 12px;
    }}

    /* --- Buttons --- */
    QPushButton {{
        background: {t.button.name()};
        color: {t.button_text.name()};
        border: 1px solid {b};
        border-radius: 10px;
        padding: 7px 12px;
        font-weight: 700;
    }}
    QPushButton:hover {{
        border-color: {acc};
    }}
    QPushButton:pressed {{
        background: {t.alt_base.name()};
    }}
    QPushButton:disabled {{
        color: {t.disabled_text.name()};
        border-color: {b};
        background: {t.alt_base.name()};
    }}

    QPushButton#Primary {{
        background: {acc};
        color: {t.highlighted_text.name()};
        border-color: {acc};
    }}

    QPushButton:checked {{
        background: {header_bg};
        border-color: {acc};
    }}

    /* --- Inputs --- */
    QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox {{
        background: {t.alt_base.name()};
        border: 1px solid {b};
        border-radius: 10px;
        padding: 7px 10px;
        selection-background-color: {acc};
        selection-color: {t.highlighted_text.name()};
    }}
    QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {acc};
    }}
    QComboBox {{
        background: {t.alt_base.name()};
        border: 1px solid {b};
        border-radius: 10px;
        padding: 6px 10px;
    }}
    QComboBox QAbstractItemView {{
        background: {t.base.name()};
        border: 1px solid {b};
        selection-background-color: {acc};
        selection-color: {t.highlighted_text.name()};
        outline: 0;
    }}

    /* --- Tabs (force opaque) --- */
    QTabWidget {{
        background: {t.window.name()};
    }}
    QTabWidget::pane {{
        border: 1px solid {b};
        border-radius: 12px;
        top: -1px;
        background: {t.base.name()};
    }}
    QTabBar {{
        background: {t.window.name()};
    }}
    QTabBar::tab {{
        background: {t.button.name()};
        border: 1px solid {b};
        border-bottom: none;
        padding: 7px 12px;
        margin-right: 6px;
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
        color: {t.text.name()};
        min-height: 24px;
    }}
    QTabBar::tab:selected {{
        background: {t.base.name()};
        border-color: {acc};
    }}
    QTabBar::tab:hover {{
        border-color: {acc};
    }}

    /* --- Tables --- */
    QHeaderView::section {{
        background: {header_bg};
        color: {t.text.name()};
        padding: 6px 8px;
        border: 1px solid {b};
        font-weight: 800;
    }}
    QTableView {{
        gridline-color: {b};
        alternate-background-color: {t.alt_base.name()};
        selection-background-color: {acc};
        selection-color: {t.highlighted_text.name()};
        border: 1px solid {b};
        border-radius: 12px;
        background: {t.base.name()};
    }}

    /* --- Scrollbars --- */
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 4px 2px 4px 0;
    }}
    QScrollBar::handle:vertical {{
        background: {sh};
        border-radius: 5px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {shh}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        margin: 0 4px 2px 4px;
    }}
    QScrollBar::handle:horizontal {{
        background: {sh};
        border-radius: 5px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {shh}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

    /* --- Splitters --- */
    QSplitter::handle {{
        background: {b};
    }}
    QSplitter::handle:hover {{
        background: {acc};
    }}

    /* --- Explicitly de-transparent common containers --- */
    QToolBar, QMenuBar, QStatusBar {{
        background: {t.window.name()};
    }}
    QScrollArea, QDockWidget, QFrame, QStackedWidget {{
        background: {t.base.name()};
    }}
    """


class ThemeManager(QObject):
    themeChanged = pyqtSignal(object)  # emits Theme
    _instance: Optional["ThemeManager"] = None

    def __init__(self):
        super().__init__()
        self._themes = dict(_BUILTINS)
        self._current: Theme = HACKER_GREEN
        self._font_scale = 1.0

    @classmethod
    def instance(cls) -> "ThemeManager":
        if not cls._instance:
            cls._instance = ThemeManager()
        return cls._instance

    def install(self, app: QApplication, theme_name: str | None = None):
        """Install theme into QApplication, loading persisted settings."""
        from PyQt5.QtCore import QSettings

        st = QSettings("SentinelCommander", "Console")
        name = theme_name or st.value("theme/name", HACKER_GREEN.name)
        accent_hex = st.value("theme/accent", "")
        scale = float(st.value("theme/font_scale", 1.0))
        self._font_scale = max(0.8, min(1.4, scale))
        base = self._themes.get(name, HACKER_GREEN)
        if accent_hex:
            base = base.with_accent(qc(accent_hex))
        self.apply(app, base)

    def apply(self, app: QApplication, theme: Theme):
        base_pt = max(7, int(round(theme.base_font_pt * self._font_scale)))
        # Monospace makes the "hacker" vibe consistent across widgets.
        app.setFont(QFont("DejaVu Sans Mono", base_pt))

        app.setPalette(make_palette(theme))
        app.setStyleSheet(build_global_qss(theme))
        self._current = theme
        self.themeChanged.emit(theme)

        # persist
        from PyQt5.QtCore import QSettings

        st = QSettings("SentinelCommander", "Console")
        st.setValue("theme/name", theme.name)
        st.setValue("theme/accent", theme.colors.get("accent", qc("#00ff66")).name())
        st.setValue("theme/font_scale", self._font_scale)

    def set_theme_by_name(self, app: QApplication, name: str):
        self.apply(app, self._themes.get(name, HACKER_GREEN))

    def set_accent(self, app: QApplication, color: QColor):
        self.apply(app, self._current.with_accent(color))

    def set_font_scale(self, app: QApplication, scale: float):
        self._font_scale = max(0.8, min(1.4, float(scale)))
        self.apply(app, self._current)

    def current(self) -> Theme:
        return self._current

    def theme_names(self) -> list[str]:
        return list(self._themes.keys())


def theme_color(key: str, fallback: str | QColor = "#00ff66") -> QColor:
    """Convenience accessor for paint code / widgets."""
    try:
        tm = ThemeManager.instance()
        col = tm.current().colors.get(key)
        if col is None:
            # map a few common logical keys to palette-ish ones
            if key == "window":
                col = tm.current().window
            elif key == "text":
                col = tm.current().text
            elif key == "base":
                col = tm.current().base
            else:
                col = qc(fallback)
        out = qc(col)
        out.setAlpha(255)  # hard clamp: NO transparency
        return out
    except Exception:
        return qc(fallback)


class ThemePanel(QDialog):
    """Small panel used by dashboard.py to let the user tweak theme."""

    def __init__(self, app: QApplication, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("Theme")
        self.setModal(False)
        self._app = app
        self._tm = ThemeManager.instance()

        grp = QGroupBox("Appearance", self)
        form = QFormLayout(grp)

        self.cmb = QComboBox()
        self.cmb.addItems(self._tm.theme_names())
        self.cmb.setCurrentText(self._tm.current().name)

        self.btn_accent = QPushButton("Pick Accent…")
        self.chk_huge = QCheckBox("Large UI")
        self.chk_huge.setToolTip("Increase base font size by ~20%")
        self.chk_huge.setChecked(False)

        form.addRow("Theme:", self.cmb)
        form.addRow("Accent:", self.btn_accent)
        form.addRow("", self.chk_huge)

        btn_apply = QPushButton("Apply")
        btn_apply.setObjectName("Primary")
        btn_close = QPushButton("Close")
        btns = QHBoxLayout()
        btns.addStretch()
        btns.addWidget(btn_apply)
        btns.addWidget(btn_close)

        root = QVBoxLayout(self)
        root.addWidget(grp)
        root.addLayout(btns)

        btn_apply.clicked.connect(self._apply)
        btn_close.clicked.connect(self.close)
        self.btn_accent.clicked.connect(self._pick_accent)

        self.resize(380, self.sizeHint().height())

    def _pick_accent(self):
        c0 = self._tm.current().colors.get("accent", qc("#00ff66"))
        c = QColorDialog.getColor(c0, self, "Select Accent Color")
        if c.isValid():
            self._tm.set_accent(self._app, c)

    def _apply(self):
        self._tm.set_theme_by_name(self._app, self.cmb.currentText())
        self._tm.set_font_scale(self._app, 1.2 if self.chk_huge.isChecked() else 1.0)
