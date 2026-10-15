"""Network worker threads; no window or persistent settings access."""
from PyQt6.QtCore import QThread, pyqtSignal
from translator import Translator, TranslationError


class TranslateWorker(QThread):
    """后台翻译线程，避免阻塞界面。"""

    finished = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, translator: Translator, text: str, engine: str = "auto",
                 parent=None):
        super().__init__(parent)
        self.translator = translator
        self.text = text
        self.engine = engine

    def run(self):
        try:
            result = self.translator.translate(self.text, engine=self.engine)
            self.finished.emit(result)
        except TranslationError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class SummarizeWorker(QThread):
    """后台 AI 总结线程，流式输出，避免阻塞界面。"""

    chunk = pyqtSignal(str)      # 每收到一块内容
    finished = pyqtSignal(str)   # 全部完成，携带完整结果
    failed = pyqtSignal(str)

    def __init__(self, translator: Translator, text: str, parent=None):
        super().__init__(parent)
        self.translator = translator
        self.text = text

    def run(self):
        parts = []
        try:
            for piece in self.translator.summarize_stream(self.text):
                if piece:
                    parts.append(piece)
                    self.chunk.emit(piece)
            self.finished.emit("".join(parts))
        except TranslationError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class ChatWorker(QThread):
    """后台问答线程，流式输出，避免阻塞界面。"""

    chunk = pyqtSignal(str)
    finished = pyqtSignal(str, bool)   # (完整回答, 是否被用户中断)
    failed = pyqtSignal(str)

    def __init__(self, translator: Translator, history: list,
                 doc_text: str = "", parent=None):
        super().__init__(parent)
        self.translator = translator
        self.history = history
        self.doc_text = doc_text
        self._stop = False

    def stop(self):
        """请求中断（流循环下一次迭代时生效）。"""
        self._stop = True

    def run(self):
        parts = []
        stopped = False
        try:
            for piece in self.translator.llm.chat_stream(self.history,
                                                         self.doc_text):
                if self._stop:
                    stopped = True
                    break
                if piece:
                    parts.append(piece)
                    self.chunk.emit(piece)
            self.finished.emit("".join(parts), stopped or self._stop)
        except TranslationError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


