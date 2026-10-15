"""Icon rendering, keyboard actions and extracted worker/window behavior."""
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pymupdf
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
import settings
import model_profiles
from main import MainWindow
from toolbar_icons import ToolbarIcon
from background_tasks import TranslateWorker, SummarizeWorker, ChatWorker
from summary_window import SummaryWindow


class ToolbarRefactorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_vector_icons_render_at_multiple_densities_and_states(self):
        for name in ("bookmarks", "open", "close", "summary", "chat"):
            for theme in ("light", "dark"):
                engine = ToolbarIcon(name, theme)
                for dpr in (1.0, 1.5, 2.0):
                    for mode in (QIcon.Mode.Normal, QIcon.Mode.Disabled):
                        image = engine.scaledPixmap(QSize(24, 24), mode, QIcon.State.Off, dpr).toImage()
                        self.assertEqual(image.width(), round(24 * dpr))
                        self.assertEqual(image.devicePixelRatio(), dpr)
                        self.assertTrue(any(image.pixelColor(x, y).alpha() > 0
                                            for x in range(image.width()) for y in range(image.height())))
                icon = QIcon(engine)
                pixmap = icon.pixmap(QSize(24, 24), 2.0)
                self.assertEqual(pixmap.width(), 48)
                self.assertEqual(pixmap.devicePixelRatio(), 2.0)

    def test_toolbar_actions_shortcuts_and_theme(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(settings, "_config_dir", return_value=folder), \
             patch.object(model_profiles, "profile_key", return_value=""):
            pdf = Path(folder) / "toolbar.pdf"
            doc = pymupdf.open(); doc.new_page().insert_text((72, 72), "Reader toolbar")
            doc.set_toc([[1, "Chapter", 1]]); doc.save(pdf); doc.close()
            w = MainWindow()
            try:
                w.show(); w.activateWindow(); QTest.qWait(80)
                actions = [w.bookmark_action, w.open_pdf_action, w.close_action, w.summary_action, w.chat_action]
                for action in actions:
                    button = w.reader_toolbar.widgetForAction(action)
                    self.assertFalse(action.icon().isNull())
                    self.assertTrue(action.toolTip())
                    self.assertTrue(button.accessibleName())
                    self.assertEqual(button.toolButtonStyle(), Qt.ToolButtonStyle.ToolButtonIconOnly)
                self.assertFalse(w.close_action.isEnabled())
                with patch("main.QFileDialog.getOpenFileName", return_value=(str(pdf), "PDF")):
                    QTest.keyClick(w, Qt.Key.Key_O, Qt.KeyboardModifier.ControlModifier)
                    QTest.qWait(100)
                self.assertEqual(w.current_pdf, str(pdf))
                for action in (w.bookmark_action, w.close_action, w.summary_action, w.chat_action):
                    self.assertTrue(action.isEnabled())
                QTest.mouseClick(w.reader_toolbar.widgetForAction(w.bookmark_action), Qt.MouseButton.LeftButton)
                self.assertTrue(w.bookmark_action.isChecked())
                self.assertTrue(w.bookmark_panel.isVisible())
                for theme in ("dark", "light"):
                    w._set_theme(theme)
                    self.assertTrue(w.bookmark_action.isChecked())
                    self.assertTrue(w.bookmark_panel.isVisible())
                w.activateWindow(); w.setFocus(); QTest.qWait(50)
                QTest.keyClick(w, Qt.Key.Key_Q, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
                QTest.qWait(60)
                self.assertTrue(w.chat_window.isVisible())
                w.chat_window.close()
                QTest.mouseClick(w.reader_toolbar.widgetForAction(w.close_action), Qt.MouseButton.LeftButton)
                self.assertIsNone(w.current_pdf)
                self.assertFalse(w.close_action.isEnabled())
            finally:
                w.close_pdf(); w.close(); w.float_btn.close()
                w.deleteLater(); self.app.processEvents()

    def test_extracted_stream_workers_and_summary_view(self):
        translator = types.SimpleNamespace(translate=lambda text, engine: text.upper(),
                                           summarize_stream=lambda text: iter(("first", " second")))
        worker = TranslateWorker(translator, "hello")
        finished = []; worker.finished.connect(finished.append); worker.run()
        self.assertEqual(finished, ["HELLO"])
        summary = SummarizeWorker(translator, "document")
        chunks = []; result = []
        summary.chunk.connect(chunks.append); summary.finished.connect(result.append); summary.run()
        self.assertEqual(chunks, ["first", " second"])
        self.assertEqual(result, ["first second"])
        translator.llm = types.SimpleNamespace(chat_stream=lambda history, text: iter(("one", "two")))
        chat = ChatWorker(translator, [], "context")
        chat.chunk.connect(lambda piece: chat.stop())
        answers = []; chat.finished.connect(lambda text, stopped: answers.append((text, stopped))); chat.run()
        self.assertEqual(answers, [("one", True)])
        window = SummaryWindow()
        try:
            window.set_loading(); window.append_chunk("hello"); window.show_result("**hello**")
            self.assertEqual(window.text_view.toPlainText(), "hello")
            window.show_error("failed")
            self.assertIn("failed", window.text_view.toPlainText())
        finally:
            window.close(); window.deleteLater(); self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
