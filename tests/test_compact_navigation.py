"""Real input for compact page, zoom and match navigation."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_reader_theme as fixtures
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest


class CompactNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.ReaderThemeTests.setUpClass()

    def setUp(self):
        self.fixture = fixtures.ReaderThemeTests()
        self.fixture.setUp()
        self.w = self.fixture.window

    def tearDown(self):
        self.fixture.tearDown()

    def test_page_arrows_input_and_boundaries(self):
        w = self.w
        self.assertEqual(w.page_label.text(), "/ 0")
        self.assertFalse(w.page_prev_btn.isEnabled())
        self.assertFalse(w.page_next_btn.isEnabled())
        w.load_pdf(str(self.fixture.book)); QTest.qWait(150)
        self.assertEqual(w.page_label.text(), "/ 3")
        self.assertFalse(w.page_prev_btn.isEnabled())
        QTest.mouseClick(w.page_next_btn, Qt.MouseButton.LeftButton)
        self.assertEqual(w.page_spin.value(), 2)
        w.page_spin.setFocus(); w.page_spin.selectAll()
        QTest.keyClicks(w.page_spin, "3"); QTest.keyClick(w.page_spin, Qt.Key.Key_Return)
        self.assertEqual(w.page_spin.value(), 3)
        self.assertFalse(w.page_next_btn.isEnabled())
        QTest.mouseClick(w.page_prev_btn, Qt.MouseButton.LeftButton)
        self.assertEqual(w.page_spin.value(), 2)
        w.close_pdf()
        self.assertEqual(w.page_spin.value(), 0)
        self.assertEqual(w.page_label.text(), "/ 0")
        self.assertFalse(w.page_prev_btn.isEnabled())
        self.assertFalse(w.page_next_btn.isEnabled())

    def test_zoom_presets_typed_input_fitting_and_invalid_text(self):
        w = self.w
        w.load_pdf(str(self.fixture.book)); QTest.qWait(150)
        zoom = w.zoom_selector
        zoom.setFocus(); zoom.selectAll()
        QTest.keyClicks(zoom, "175%"); QTest.keyClick(zoom, Qt.Key.Key_Return)
        self.assertEqual(w.viewer.zoom, 1.75)
        index = zoom.findData(75)
        zoom.setCurrentIndex(index); zoom.activated.emit(index)
        self.assertEqual(w.viewer.zoom, .75)
        for fit in ("width", "page"):
            index = zoom.findData(fit)
            zoom.setCurrentIndex(index); zoom.activated.emit(index)
            QTest.qWait(150)
            self.assertEqual(zoom.fit_mode, fit)
            self.assertEqual(zoom.value(), round(w.viewer.zoom * 100))
        zoom.selectAll(); QTest.keyClicks(zoom, str(zoom.value()))
        QTest.keyClick(zoom, Qt.Key.Key_Return)
        self.assertEqual(w.viewer.fit_mode, w.viewer.FIT_NONE)
        previous = w.viewer.zoom
        zoom.selectAll(); QTest.keyClicks(zoom, "abc"); QTest.keyClick(zoom, Qt.Key.Key_Return)
        self.assertEqual(w.viewer.zoom, previous)
        self.assertEqual(zoom.currentText(), f"{zoom.value()}%")
        zoom.setValue(9999); self.assertEqual(w.viewer.zoom, 5)
        zoom.setValue(0); self.assertEqual(w.viewer.zoom, .1)

    def test_search_arrows_keyboard_wrap_reset_and_document_switch(self):
        w = self.w
        w.load_pdf(str(self.fixture.book))
        w.activateWindow(); w.setFocus(); QTest.qWait(40)
        QTest.keyClick(w, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
        self.assertTrue(w.search_edit.hasFocus())
        QTest.keyClicks(w.search_edit, "Theme")
        QTest.keyClick(w.search_edit, Qt.Key.Key_Return)
        self.assertEqual(w.search_count_label.text(), "1 / 3")
        QTest.keyClick(w, Qt.Key.Key_F3)
        self.assertEqual(w.search_count_label.text(), "2 / 3")
        QTest.keyClick(w, Qt.Key.Key_F3, Qt.KeyboardModifier.ShiftModifier)
        self.assertEqual(w.search_count_label.text(), "1 / 3")
        QTest.mouseClick(w.search_next_btn, Qt.MouseButton.LeftButton)
        self.assertEqual(w.search_count_label.text(), "2 / 3")
        w.search_edit.setFocus()
        QTest.keyClick(w.search_edit, Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier)
        self.assertEqual(w.search_count_label.text(), "1 / 3")
        QTest.keyClick(w.search_edit, Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier)
        self.assertEqual(w.search_count_label.text(), "3 / 3")
        QTest.keyClick(w.search_edit, Qt.Key.Key_Return)
        self.assertEqual(w.search_count_label.text(), "1 / 3")
        with patch.object(w.viewer, "clear_search", wraps=w.viewer.clear_search) as clear:
            w.search_edit.setText("absen")
            w.search_edit.setText("absent")
            self.assertEqual(clear.call_count, 1)
        self.assertFalse(w.search_next_btn.isEnabled())
        self.assertEqual(w.search_count_label.text(), "0 / 0")
        w._do_search()
        self.assertEqual(w.search_count_label.text(), "未找到")
        QTest.keyClick(w.search_edit, Qt.Key.Key_Escape)
        self.assertEqual(w.search_edit.text(), "")
        self.assertEqual(w.search_count_label.text(), "0 / 0")
        w.search_edit.setText("Theme"); w._do_search()
        w.load_pdf(str(self.fixture.plain))
        self.assertEqual(w._search_results, [])
        self.assertFalse(w.search_next_btn.isEnabled())
        w._do_search(-1)
        self.assertEqual(w.search_count_label.text(), "3 / 3")
        w.close_pdf()
        self.assertEqual(w.search_count_label.text(), "0 / 0")


if __name__ == "__main__":
    unittest.main()
