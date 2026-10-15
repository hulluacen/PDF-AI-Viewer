"""Editable source above a read-only translation, with a resizable divider."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QPlainTextEdit, QSplitter, QTextEdit, QVBoxLayout


class TranslationPanel(QSplitter):
    def __init__(self, card_factory, parent=None):
        super().__init__(Qt.Orientation.Vertical, parent)
        self.setObjectName("translationPanel")
        self.setChildrenCollapsible(False)
        self.setHandleWidth(6)
        source_card = card_factory()
        source_card.setMinimumHeight(90)
        source_layout = QVBoxLayout(source_card)
        source_layout.setContentsMargins(12, 10, 12, 12)
        source_layout.addWidget(QLabel("原文（可编辑）"))
        self.source_edit = QPlainTextEdit()
        self.source_edit.setAccessibleName("可编辑翻译原文")
        self.source_edit.setToolTip("可直接编辑原文；Ctrl+T 翻译，不会修改 PDF 文件。")
        self.source_edit.setPlaceholderText("在 PDF 中选中文本，或在此输入、修改后翻译。")
        source_layout.addWidget(self.source_edit)
        self.addWidget(source_card)
        result_card = card_factory()
        result_card.setMinimumHeight(100)
        result_layout = QVBoxLayout(result_card)
        result_layout.setContentsMargins(12, 10, 12, 12)
        result_layout.addWidget(QLabel("译文"))
        self.result_view = QTextEdit()
        self.result_view.setReadOnly(True)
        self.result_view.setAccessibleName("翻译结果")
        result_layout.addWidget(self.result_view)
        self.addWidget(result_card)
        self.handle(1).setToolTip("拖动调整原文和译文区域高度")
        self.setStretchFactor(0, 0)
        self.setStretchFactor(1, 1)
        self.setSizes([150, 450])
