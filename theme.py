"""Shared day/night Qt styles; no application state or data access."""

# 全局样式表：现代简洁风格
_APP_STYLE = """
QLineEdit#pdfSearch {
    background-color: #ffffff;
    color: #333333;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 3px 6px;
    selection-background-color: #4a90d9;
    selection-color: #ffffff;
}
QWidget#bookmarkPanel {
    background-color: #f5f6fa;
}
QTreeWidget#bookmarkTree {
    background-color: #ffffff;
    alternate-background-color: #f5f6fa;
    color: #333333;
    border: 1px solid #d0d0d0;
}
QTreeWidget#bookmarkTree QHeaderView::section {
    background-color: #f5f6fa;
    color: #333333;
    border: 1px solid #d0d0d0;
    padding: 4px;
}
QTreeWidget#bookmarkTree::item:selected {
    background-color: #4a90d9;
    color: #ffffff;
}
QDialog#modelSettingsDialog {
    background-color: #f5f6fa;
}
QDialog#modelSettingsDialog QLineEdit, QDialog#modelSettingsDialog QListWidget {
    background-color: #ffffff;
    color: #333333;
    border: 1px solid #d0d0d0;
    padding: 4px;
}
QLabel {
    color: #333333;
}
QMainWindow {
    background-color: #f5f6fa;
}
QFrame#card {
    background-color: #ffffff;
    border: 1px solid #e4e6eb;
    border-radius: 10px;
}
QToolBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e0e0e0;
    padding: 4px;
    spacing: 6px;
}
QToolBar QLabel {
    color: #333333;
    font-size: 13px;
    font-weight: 500;
}
QToolButton {
    background-color: #ffffff;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 4px 10px;
    color: #333333;
    font-size: 13px;
}
QToolButton:hover {
    background-color: #e8f0fe;
    border-color: #4a90d9;
}
QToolButton:disabled {
    background-color: #f0f0f0;
    border-color: #e0e0e0;
    color: #b0b0b0;
}
/* 工具栏内的按钮（搜索/上一个/下一个）与 QToolButton 风格统一 */
QToolBar QPushButton {
    background-color: #ffffff;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 4px 10px;
    color: #333333;
    font-size: 13px;
}
QToolBar QPushButton:hover {
    background-color: #e8f0fe;
    border-color: #4a90d9;
}
QToolBar QPushButton:disabled {
    background-color: #f0f0f0;
    border-color: #e0e0e0;
    color: #b0b0b0;
}
QMenuBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e0e0e0;
    font-size: 13px;
}
QMenuBar::item {
    padding: 5px 10px;
    background: transparent;
}
QMenuBar::item:selected {
    background-color: #e8f0fe;
    border-radius: 4px;
}
QMenu {
    background-color: #ffffff;
    border: 1px solid #d0d0d0;
    padding: 4px;
    font-size: 13px;
}
QMenu::item {
    padding: 6px 24px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #e8f0fe;
}
QPushButton {
    background-color: #4a90d9;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 6px 14px;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #3a80c9;
}
QPushButton:disabled {
    background-color: #c0c0c0;
}
QTextEdit {
    background-color: #ffffff;
    border: 1px solid #d0d0d0;
    border-radius: 8px;
    padding: 8px;
    font-size: 14px;
    color: #222222;
    selection-background-color: #4a90d9;
    selection-color: #ffffff;
}
QScrollArea {
    background-color: #e8e8e8;
    border: none;
}
QScrollBar:vertical {
    background: #f0f0f0;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #c0c0c0;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #a0a0a0;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #f0f0f0;
    height: 10px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: #c0c0c0;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: #a0a0a0; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollArea::corner, QTreeWidget#bookmarkTree::corner { background: #f0f0f0; }
QSpinBox, QComboBox {
    background-color: #ffffff;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 3px 6px;
    min-height: 22px;
}
QSlider::groove:horizontal {
    height: 4px;
    background: #d0d0d0;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #4a90d9;
    width: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QStatusBar {
    background-color: #ffffff;
    border-top: 1px solid #e0e0e0;
    color: #666666;
}
QSplitter::handle {
    background-color: #d0d0d0;
    width: 3px;
}
QSplitter::handle:hover {
    background-color: #4a90d9;
}
"""


# 夜间模式样式表
_APP_STYLE_DARK = """
QLineEdit#pdfSearch {
    background-color: #3a3a3a;
    color: #cccccc;
    border: 1px solid #4a4a4a;
    border-radius: 4px;
    padding: 3px 6px;
    selection-background-color: #4a90d9;
    selection-color: #ffffff;
}
QWidget#bookmarkPanel {
    background-color: #1e1e1e;
}
QTreeWidget#bookmarkTree {
    background-color: #242424;
    alternate-background-color: #2d2d2d;
    color: #cccccc;
    border: 1px solid #4a4a4a;
}
QTreeWidget#bookmarkTree QHeaderView::section {
    background-color: #3a3a3a;
    color: #cccccc;
    border: 1px solid #4a4a4a;
    padding: 4px;
}
QTreeWidget#bookmarkTree::item:selected {
    background-color: #4a90d9;
    color: #ffffff;
}
QDialog#modelSettingsDialog {
    background-color: #2d2d2d;
}
QDialog#modelSettingsDialog QLineEdit, QDialog#modelSettingsDialog QListWidget {
    background-color: #242424;
    color: #cccccc;
    border: 1px solid #4a4a4a;
    padding: 4px;
}
QDialog#modelSettingsDialog QLineEdit:disabled {
    color: #888888;
}
QLabel {
    color: #cccccc;
}
QMainWindow {
    background-color: #1e1e1e;
}
QFrame#card {
    background-color: #2d2d2d;
    border: 1px solid #3a3a3a;
    border-radius: 10px;
}
QToolBar {
    background-color: #2d2d2d;
    border-bottom: 1px solid #3a3a3a;
    padding: 4px;
    spacing: 6px;
}
QToolBar QLabel {
    color: #cccccc;
    font-size: 13px;
    font-weight: 500;
}
QToolButton {
    background-color: #3a3a3a;
    border: 1px solid #4a4a4a;
    border-radius: 4px;
    padding: 4px 10px;
    color: #cccccc;
    font-size: 13px;
}
QToolButton:hover {
    background-color: #4a4a4a;
    border-color: #4a90d9;
}
QToolButton:disabled {
    background-color: #2d2d2d;
    border-color: #3a3a3a;
    color: #666666;
}
/* 工具栏内的按钮（搜索/上一个/下一个）与 QToolButton 风格统一 */
QToolBar QPushButton {
    background-color: #3a3a3a;
    border: 1px solid #4a4a4a;
    border-radius: 4px;
    padding: 4px 10px;
    color: #cccccc;
    font-size: 13px;
}
QToolBar QPushButton:hover {
    background-color: #4a4a4a;
    border-color: #4a90d9;
}
QToolBar QPushButton:disabled {
    background-color: #2d2d2d;
    border-color: #3a3a3a;
    color: #666666;
}
QMenuBar {
    background-color: #2d2d2d;
    border-bottom: 1px solid #3a3a3a;
    font-size: 13px;
}
QMenuBar::item {
    padding: 5px 10px;
    background: transparent;
    color: #cccccc;
}
QMenuBar::item:selected {
    background-color: #4a4a4a;
    border-radius: 4px;
}
QMenu {
    background-color: #2d2d2d;
    border: 1px solid #4a4a4a;
    padding: 4px;
    font-size: 13px;
    color: #cccccc;
}
QMenu::item {
    padding: 6px 24px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #4a4a4a;
}
QPushButton {
    background-color: #4a90d9;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 6px 14px;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #3a80c9;
}
QPushButton:disabled {
    background-color: #555555;
}
QTextEdit {
    background-color: #252526;
    border: 1px solid #3a3a3a;
    border-radius: 8px;
    padding: 8px;
    font-size: 14px;
    color: #dddddd;
    selection-background-color: #4a90d9;
    selection-color: #ffffff;
}
QScrollArea {
    background-color: #2b2b2b;
    border: none;
}
QScrollBar:vertical {
    background: #2d2d2d;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #555555;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #666666;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #2d2d2d;
    height: 10px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: #555555;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: #666666; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollArea::corner, QTreeWidget#bookmarkTree::corner { background: #2d2d2d; }
QSpinBox, QComboBox {
    background-color: #3a3a3a;
    border: 1px solid #4a4a4a;
    border-radius: 4px;
    padding: 3px 6px;
    min-height: 22px;
    color: #cccccc;
}
QComboBox QAbstractItemView {
    background-color: #2d2d2d;
    color: #cccccc;
    selection-background-color: #4a4a4a;
}
QSlider::groove:horizontal {
    height: 4px;
    background: #4a4a4a;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #4a90d9;
    width: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QStatusBar {
    background-color: #2d2d2d;
    border-top: 1px solid #3a3a3a;
    color: #999999;
}
QSplitter::handle {
    background-color: #3a3a3a;
    width: 3px;
}
QSplitter::handle:hover {
    background-color: #4a90d9;
}
"""


