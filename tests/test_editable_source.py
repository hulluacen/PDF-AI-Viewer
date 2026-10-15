"""Editable source payloads and stale replies, using real workers with fake networking."""
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_reader_theme as fixtures
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QPlainTextEdit
import settings
from translator import TranslationError


class EditableSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.ReaderThemeTests.setUpClass()

    def setUp(self):
        self.fixture = fixtures.ReaderThemeTests()
        self.fixture.setUp()
        self.w = self.fixture.window

    def tearDown(self):
        if self.w.worker is not None:
            self.w.worker.wait(3000)
            fixtures.ReaderThemeTests.app.processEvents()
        self.fixture.tearDown()

    def wait_translation(self):
        for _ in range(150):
            QTest.qWait(20)
            if not self.w.worker.isRunning() and not self.w._translation_busy:
                return
        self.fail("Translation did not finish")

    def test_selection_verbatim_manual_edit_and_button_payload(self):
        w = self.w
        w.load_pdf(str(self.fixture.book))
        pdf_bytes = self.fixture.book.read_bytes()
        w.viewer.textSelected.emit("typeCamTableConfiguration")
        self.assertIsInstance(w.source_edit, QPlainTextEdit)
        self.assertEqual(w.source_edit.toPlainText(), "typeCamTableConfiguration")
        self.assertIsNone(w.worker)
        w.viewer.textSelectedAt.emit("typeCamTableConfiguration", QPoint(200, 200))
        self.assertTrue(w.float_btn.isVisible())
        edited = "  type Cam Table Configuration\nPLCDataType  "
        w.source_edit.setPlainText(edited)
        self.assertFalse(w.float_btn.isVisible())
        w.viewer.textSelected.emit("")
        self.assertEqual(w.source_edit.toPlainText(), edited)
        with patch.object(w.translator, "translate", return_value="凸轮表配置") as translate:
            QTest.mouseClick(w.translate_btn, Qt.MouseButton.LeftButton)
            self.wait_translation()
            self.assertEqual(translate.call_args.args[0], edited)
        self.assertEqual(w.result_view.toPlainText(), "凸轮表配置")
        self.assertEqual(self.fixture.book.read_bytes(), pdf_bytes)

    def test_manual_input_without_pdf_shortcut_and_empty_input(self):
        w = self.w
        self.assertIsNone(w.current_pdf)
        self.assertFalse(w.translate_btn.isEnabled())
        w.source_edit.setPlainText("specialPLCName")
        w.activateWindow(); w.source_edit.setFocus(); QTest.qWait(50)
        with patch.object(w.translator, "translate", return_value="专有名词") as translate:
            QTest.keyClick(w.source_edit, Qt.Key.Key_T, Qt.KeyboardModifier.ControlModifier)
            self.wait_translation()
            self.assertEqual(translate.call_args.args[0], "specialPLCName")
        w.source_edit.setPlainText(" \n\t ")
        self.assertFalse(w.translate_btn.isEnabled())
        with patch.object(w.translator, "translate") as translate:
            w._translate_current()
            self.assertFalse(translate.called)

    def test_edit_during_request_ignores_old_result_and_prevents_overlap(self):
        w = self.w
        release = threading.Event()
        w.source_edit.setPlainText("oldIdentifier")
        def delayed(text, engine):
            release.wait(2)
            return "OLD RESULT"
        try:
            with patch.object(w.translator, "translate", side_effect=delayed):
                w._translate_current()
                first_worker = w.worker
                w.source_edit.setPlainText("newIdentifier")
                self.assertFalse(w.translate_btn.isEnabled())
                w._translate_current()
                self.assertIs(w.worker, first_worker)
                release.set()
                self.wait_translation()
            self.assertNotIn("OLD RESULT", w.result_view.toPlainText())
            self.assertNotIn("请等待", w.result_view.toPlainText())
            self.assertTrue(w.translate_btn.isEnabled())
            with patch.object(w.translator, "translate", return_value="NEW RESULT") as translate:
                w._translate_current(); self.wait_translation()
                self.assertEqual(translate.call_args.args[0], "newIdentifier")
            self.assertEqual(w.result_view.toPlainText(), "NEW RESULT")
        finally:
            release.set()

    def test_cancel_preserves_draft_but_new_document_and_close_clear_it(self):
        w = self.w
        w.load_pdf(str(self.fixture.book))
        w.source_edit.setPlainText("edited draft")
        with patch.object(w.viewer, "load_document_progress", return_value=None):
            w.load_pdf(str(self.fixture.plain))
        self.assertEqual(w.source_edit.toPlainText(), "edited draft")
        w.load_pdf(str(self.fixture.plain))
        self.assertEqual(w.source_edit.toPlainText(), "")
        w.source_edit.setPlainText("new draft")
        w.close_pdf()
        self.assertEqual(w.source_edit.toPlainText(), "")
        self.assertFalse(w.translate_btn.isEnabled())

    def test_close_during_request_ignores_old_failure(self):
        w = self.w
        w.load_pdf(str(self.fixture.book))
        release = threading.Event()
        def delayed(text, engine):
            release.wait(2)
            raise TranslationError("OLD FAILURE")
        try:
            with patch.object(w.translator, "translate", side_effect=delayed):
                w.source_edit.setPlainText("identifier")
                w._translate_current()
                w.close_pdf()
                release.set()
                self.wait_translation()
            self.assertNotIn("OLD FAILURE", w.result_view.toPlainText())
            self.assertEqual(w.source_edit.toPlainText(), "")
            self.assertFalse(w.translate_btn.isEnabled())
        finally:
            release.set()

    def test_theme_font_and_saved_splitter_preserve_text_and_result(self):
        w = self.w
        w.source_edit.setPlainText("typeCamTableConfiguration")
        with patch.object(w.translator, "translate", return_value="凸轮表配置"):
            w._translate_current(); self.wait_translation()
        for theme in ("dark", "light"):
            w._set_theme(theme)
            self.assertEqual(w.source_edit.toPlainText(), "typeCamTableConfiguration")
            self.assertEqual(w.result_view.toPlainText(), "凸轮表配置")
        w._adjust_font(1)
        self.assertEqual(w.source_edit.document().defaultFont().pointSize(), w.font_size)
        self.assertEqual(w.result_view.toPlainText(), "凸轮表配置")
        before = w.translation_panel.sizes()
        w.translation_panel.moveSplitter(before[0] + 40, 1)
        sizes = w.translation_panel.sizes()
        self.assertNotEqual(sizes, before)
        self.assertEqual(settings.load_settings()["translation_splitter_sizes"], sizes)
        self.assertNotIn("typeCamTableConfiguration", Path(settings._settings_file()).read_text())


if __name__ == "__main__":
    unittest.main()
