"""Standalone streaming summary view."""
import os
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QTextCursor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit
from app_resources import resource_path
from latex_fallback import latex_to_unicode


class SummaryWindow(QWidget):
    """AI 总结独立窗口，可缩放、可滚动显示长总结。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI 总结")
        self.resize(520, 620)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
        )
        # 窗口图标
        icon_path = resource_path("logo.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 标题栏
        header = QHBoxLayout()
        title = QLabel("AI 总结")
        title.setStyleSheet("font-size: 15px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch(1)
        layout.addLayout(header)

        # 总结内容（可滚动，支持 Markdown 渲染）
        self.text_view = QTextEdit()
        self.text_view.setReadOnly(True)
        layout.addWidget(self.text_view, 1)

        # 状态提示
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888;")
        layout.addWidget(self.status_label)

    def set_loading(self):
        """显示加载状态。"""
        self._accumulated = ""
        self.text_view.setPlainText("正在生成总结，请稍候...")
        self.status_label.setText("正在生成总结，请稍候...")

    def append_chunk(self, piece: str):
        """流式追加一块内容。

        流式阶段用 QTextCursor 增量插入纯文本，避免每次 setMarkdown 全量重解析
        导致界面卡顿；最终结果在 show_result 里一次性做 Markdown 渲染。
        """
        self._accumulated += piece
        # 若当前还是占位提示，先清空
        if self.text_view.toPlainText() == "正在生成总结，请稍候...":
            self.text_view.clear()
            self.status_label.setText("正在输出中...")
        cursor = self.text_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(piece)
        self.text_view.setTextCursor(cursor)
        # 滚动到底部
        sb = self.text_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def show_result(self, text: str):
        """显示总结结果（支持 Markdown 渲染）。"""
        if not text or not text.strip():
            self.text_view.setPlainText("（无总结结果）")
        else:
            text = self._latex_to_unicode(text)
            try:
                self.text_view.setMarkdown(text)
            except Exception:  # noqa: BLE001
                self.text_view.setPlainText(text)
        self.status_label.setText("")
        self.text_view.update()

    @staticmethod
    def _latex_to_unicode(text: str) -> str:
        """把常见的 LaTeX 数学公式转成可读的 Unicode 纯文本（兜底处理）。

        实现抽到 latex_fallback 模块，与问答窗口共用。
        """
        return latex_to_unicode(text)

    def show_error(self, error: str):
        """显示错误信息。"""
        self.text_view.setPlainText(f"总结失败：\n{error}")
        self.status_label.setText("")


