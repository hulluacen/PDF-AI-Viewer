"""Reader toolbar construction; actions continue to use existing window callbacks."""
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QAction, QShortcut, QKeySequence
from PyQt6.QtWidgets import QToolBar, QLabel, QSpinBox, QComboBox, QToolButton, QLineEdit
from toolbar_icons import apply_toolbar_icons


class ZoomSelector(QComboBox):
    """One editable field for percentage presets and fitting modes."""
    percentRequested = pyqtSignal(int)
    fitRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("zoomSelector")
        self.setEditable(True)
        self.lineEdit().setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setFixedWidth(116)
        self._value = 150
        self.fit_mode = "width"
        for percent in (10, 25, 50, 75, 100, 125, 150, 175, 200, 300, 400, 500):
            self.addItem(f"{percent}%", percent)
        self.insertSeparator(self.count())
        self.addItem("实际大小（100%）", 100)
        self.addItem("适合页面", "page")
        self.addItem("适合宽度", "width")
        self.setCurrentIndex(self.findData("width"))
        self.setEditText("150%")
        self.activated.connect(self._activate)
        self.lineEdit().returnPressed.connect(lambda: self._commit(force=True))
        self.lineEdit().editingFinished.connect(self._commit)
        self.setToolTip("缩放比例：可输入10%–500%，或选择常用比例及适配方式")
        self.setAccessibleName("缩放比例与适配方式")

    def _activate(self, index):
        data = self.itemData(index)
        if data in ("page", "width") and self.currentText() == self.itemText(index):
            self.choose_fit(data)
        elif isinstance(data, int):
            self.setValue(data)
        else:
            self._commit()

    def choose_fit(self, mode):
        self.fit_mode = mode
        self.fitRequested.emit()

    def value(self):
        return self._value

    def selectAll(self):
        self.lineEdit().selectAll()

    def setValue(self, value):
        value = max(10, min(500, int(value)))
        changed = self._value != value or self.fit_mode is not None
        self.fit_mode = None
        self._value = value
        self._display()
        if changed:
            self.percentRequested.emit(value)

    def _commit(self, force=False):
        text = self.currentText().strip().removesuffix("%").strip()
        try:
            value = int(text)
        except ValueError:
            self._display()
            return
        # Leaving an unchanged fit percentage must keep its responsive mode.
        if force or value != self._value or self.currentText().strip() != f"{self._value}%":
            self.setValue(value)

    def _display(self):
        blocked = self.blockSignals(True)
        data = self.fit_mode if self.fit_mode is not None else self._value
        self.setCurrentIndex(self.findData(data))
        self.setEditText(f"{self._value}%")
        self.blockSignals(blocked)

    def sync(self, zoom, mode):
        self._value = max(10, min(500, round(zoom * 100)))
        self.fit_mode = mode
        self._display()


class SearchField(QLineEdit):
    previousRequested = pyqtSignal()
    clearRequested = pyqtSignal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.previousRequested.emit()
            event.accept()
        elif event.key() == Qt.Key.Key_Escape:
            self.clearRequested.emit()
            event.accept()
        else:
            super().keyPressEvent(event)


def build_reader_toolbar(window):
    toolbar = QToolBar("主工具栏")
    toolbar.setMovable(False)
    window.addToolBar(toolbar)
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    toolbar.setIconSize(QSize(22, 22))

    window.bookmark_action = QAction("书签", window)
    window.bookmark_action.setCheckable(True)
    window.bookmark_action.setEnabled(False)
    window.bookmark_action.setToolTip("显示或隐藏 PDF 内置书签目录")
    window.bookmark_action.toggled.connect(window.bookmark_panel.setVisible)
    toolbar.addAction(window.bookmark_action)

    open_action = window.open_pdf_action
    toolbar.addAction(open_action)
    window.open_pdf_action = open_action
    open_action.setToolTip("打开 PDF（Ctrl+O）")

    close_action = QAction("关闭 PDF", window)
    close_action.triggered.connect(window.close_pdf)
    close_action.setEnabled(False)
    toolbar.addAction(close_action)
    close_action.setToolTip("关闭当前 PDF")
    window.close_action = close_action

    toolbar.addSeparator()

    # AI 总结（整篇文档）
    summary_action = QAction("全文总结", window)
    summary_action.triggered.connect(window._summarize_current)
    summary_action.setEnabled(False)
    toolbar.addAction(summary_action)
    summary_action.setToolTip("生成全文总结")
    window.summary_action = summary_action

    # AI 阅读问答（边读边问）
    window.chat_action = QAction("AI 问答", window)
    window.chat_action.setToolTip("AI 问答，笔记保存到 data/chatnotes（Ctrl+Shift+Q）")
    window.chat_action.triggered.connect(window._open_chat)
    window.chat_action.setEnabled(False)
    toolbar.addAction(window.chat_action)

    toolbar.addSeparator()

    # Page navigation: arrows + editable page / total.
    window.page_prev_btn = QToolButton()
    window.page_prev_btn.setToolTip("上一页 PDF")
    window.page_prev_btn.setAccessibleName("上一页 PDF")
    window.page_prev_btn.clicked.connect(lambda: window.viewer.go_to_page(window.page_spin.value() - 1))
    window.page_next_btn = QToolButton()
    window.page_next_btn.setToolTip("下一页 PDF")
    window.page_next_btn.setAccessibleName("下一页 PDF")
    window.page_next_btn.clicked.connect(lambda: window.viewer.go_to_page(window.page_spin.value() + 1))
    for button in (window.page_prev_btn, window.page_next_btn):
        button.setIconSize(QSize(22, 22))
        button.setEnabled(False)
        toolbar.addWidget(button)
    window.page_spin = QSpinBox()
    window.page_spin.setRange(0, 1)
    window.page_spin.setValue(0)
    window.page_spin.setFixedWidth(58)
    window.page_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
    window.page_spin.setKeyboardTracking(False)
    window.page_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
    window.page_spin.setAccessibleName("当前页码")
    window.page_spin.setToolTip("输入页码，按 Enter 跳转")
    window.page_spin.setEnabled(False)
    window.page_spin.valueChanged.connect(window._on_spin_changed)
    toolbar.addWidget(window.page_spin)
    window.page_label = QLabel("/ 0")
    window.page_label.setEnabled(False)
    toolbar.addWidget(window.page_label)
    toolbar.addSeparator()

    window.zoom_out_btn = QToolButton()
    window.zoom_out_btn.setText("−")
    window.zoom_out_btn.setToolTip("缩小 10 个百分点（Ctrl+-）")
    window.zoom_out_btn.clicked.connect(lambda: window._zoom_pdf(-1))
    toolbar.addWidget(window.zoom_out_btn)
    window.zoom_selector = ZoomSelector()
    window.zoom_percent = window.zoom_selector  # Existing percentage API remains available.
    window.zoom_selector.percentRequested.connect(window._on_zoom_changed)
    window.zoom_selector.fitRequested.connect(window._apply_selected_zoom)
    toolbar.addWidget(window.zoom_selector)
    window.zoom_in_btn = QToolButton()
    window.zoom_in_btn.setText("+")
    window.zoom_in_btn.setToolTip("放大 10 个百分点（Ctrl++）")
    window.zoom_in_btn.clicked.connect(lambda: window._zoom_pdf(1))
    toolbar.addWidget(window.zoom_in_btn)
    toolbar.addSeparator()

    # Find matches, kept separate from the PDF page controls.
    window.search_edit = SearchField()
    window.search_edit.setObjectName("pdfSearch")
    window.search_edit.setPlaceholderText("搜索文档…")
    window.search_edit.setFixedWidth(180)
    window.search_edit.setClearButtonEnabled(True)
    window.search_edit.setAccessibleName("搜索文档文本")
    window.search_edit.returnPressed.connect(window._do_search)
    window.search_edit.previousRequested.connect(lambda: window._do_search(-1))
    window.search_edit.clearRequested.connect(window.search_edit.clear)
    window.search_edit.textChanged.connect(window._reset_search)
    toolbar.addWidget(window.search_edit)
    window.search_btn = QToolButton()
    window.search_btn.setToolTip("搜索文档（Enter）")
    window.search_btn.setAccessibleName("搜索文档")
    window.search_btn.clicked.connect(lambda: window._do_search())
    toolbar.addWidget(window.search_btn)
    window.search_count_label = QLabel("0 / 0")
    window.search_count_label.setMinimumWidth(52)
    window.search_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    window.search_count_label.setToolTip("当前匹配 / 全部匹配")
    toolbar.addWidget(window.search_count_label)
    for attr, title, step, shortcut in (
        ("search_prev_btn", "上一个匹配", -1, "Shift+Enter / Shift+F3"),
        ("search_next_btn", "下一个匹配", 1, "Enter / F3"),
    ):
        button = QToolButton()
        button.setIconSize(QSize(18, 18))
        button.setToolTip(f"{title}（{shortcut}）")
        button.setAccessibleName(title)
        button.setEnabled(False)
        button.clicked.connect(lambda checked=False, direction=step: window._do_search(direction))
        setattr(window, attr, button)
        toolbar.addWidget(button)
    def focus_find():
        window.search_edit.setFocus()
        window.search_edit.selectAll()
    QShortcut(QKeySequence("Ctrl+F"), window, activated=focus_find)
    QShortcut(QKeySequence("F3"), window, activated=lambda: window._do_search(1))
    QShortcut(QKeySequence("Shift+F3"), window, activated=lambda: window._do_search(-1))
    apply_toolbar_icons(window)
    for action in (window.bookmark_action, open_action, close_action,
                   summary_action, window.chat_action):
        toolbar.widgetForAction(action).setAccessibleName(action.text())
    return toolbar
