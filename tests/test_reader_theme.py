"""Check rendered reader backgrounds, not only stylesheet strings."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pymupdf
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtGui import QPalette
import settings
from main import MainWindow
from theme import _APP_STYLE


class ReaderThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config = patch.object(settings, "_config_dir", return_value=self.temp.name)
        self.key = patch.object(settings, "get_llm_key", return_value="")
        self.config.start()
        self.key.start()
        self.app.setStyleSheet(_APP_STYLE)
        self.window = MainWindow()
        self.window.resize(2100, 800)
        self.window.show()
        QTest.qWait(50)
        self.book = Path(self.temp.name) / "book.pdf"
        self.plain = Path(self.temp.name) / "plain.pdf"
        doc = pymupdf.open()
        for i in range(3):
            doc.new_page().insert_text((72, 72), "Theme regression")
        doc.save(self.plain)
        doc.set_toc([[1, "First chapter", 1], [2, "Subsection", 2], [1, "Second chapter", 3]])
        doc.save(self.book)
        doc.close()

    def tearDown(self):
        self.window.close_pdf()
        self.window.close()
        self.window.float_btn.close()
        self.window.deleteLater()
        self.app.processEvents()
        self.config.stop()
        self.key.stop()
        self.temp.cleanup()
        self.app.setStyleSheet(_APP_STYLE)

    def background(self, widget):
        QTest.qWait(30)
        image = widget.grab().toImage()
        self.assertFalse(image.isNull())
        return image.pixelColor(image.width() - 12, image.height() - 12)

    def assert_dark(self, widget):
        color = self.background(widget)
        self.assertLess(max(color.red(), color.green(), color.blue()), 100, color.name())

    def assert_light(self, widget):
        color = self.background(widget)
        self.assertGreater(min(color.red(), color.green(), color.blue()), 220, color.name())

    def test_empty_reader_before_and_after_close_and_restore(self):
        w = self.window
        w._set_theme("dark")
        self.assert_dark(w.viewer.viewport())
        self.assert_dark(w.viewer._container)
        w.load_pdf(str(self.book))
        w.close_pdf()
        self.assertTrue(w.viewer._empty_label.isVisible())
        self.assert_dark(w.viewer.viewport())
        self.assert_dark(w.viewer._container)
        w._set_theme("light")
        self.assert_light(w.viewer.viewport())
        self.assert_light(w.viewer._container)
        w._set_theme("dark")
        restored = MainWindow()
        try:
            restored.show()
            self.assertEqual(restored.theme, "dark")
            self.assert_dark(restored.viewer.viewport())
        finally:
            restored.close()
            restored.float_btn.close()
            restored.deleteLater()
            self.app.processEvents()

    def test_search_field_readable_and_preserves_text(self):
        w = self.window
        w.search_edit.setText("word")
        for theme in ("dark", "light", "dark"):
            w._set_theme(theme)
            if theme == "dark":
                self.assert_dark(w.search_edit)
                self.assertGreater(w.search_edit.palette().color(QPalette.ColorRole.Text).lightness(), 150)
            else:
                self.assert_light(w.search_edit)
                self.assertLess(w.search_edit.palette().color(QPalette.ColorRole.Text).lightness(), 100)
            self.assertEqual(w.search_edit.text(), "word")

    def test_populated_bookmarks_and_empty_hint_follow_theme(self):
        w = self.window
        w.load_pdf(str(self.book))
        w.bookmark_action.setChecked(True)
        for theme in ("dark", "light", "dark"):
            w._set_theme(theme)
            self.assertTrue(w.bookmark_tree.isVisible())
            self.assertEqual(w.bookmark_tree.topLevelItemCount(), 2)
            if theme == "dark":
                self.assert_dark(w.bookmark_tree.viewport())
                self.assert_dark(w.bookmark_tree.header())
                self.assertGreater(w.bookmark_tree.palette().color(QPalette.ColorRole.Text).lightness(), 150)
                for bar in (w.bookmark_tree.horizontalScrollBar(), w.viewer.horizontalScrollBar()):
                    if bar.isVisible():
                        image = bar.grab().toImage()
                        color = image.pixelColor(5, image.height() // 2)
                        self.assertLess(max(color.red(), color.green(), color.blue()), 110)
            else:
                self.assert_light(w.bookmark_tree.viewport())
                self.assert_light(w.bookmark_tree.header())
            item = w.bookmark_tree.topLevelItem(1)
            w.bookmark_tree.setCurrentItem(item)
            w._on_bookmark_clicked(item, 0)
            QTest.qWait(50)
            self.assertFalse(w.viewer.page_widgets[2].visibleRegion().isEmpty())
        w.load_pdf(str(self.plain))
        w.bookmark_action.setChecked(True)
        self.assertFalse(w.bookmark_tree.isVisible())
        self.assertTrue(w.bookmark_hint.isVisible())
        self.assert_dark(w.bookmark_panel)


if __name__ == "__main__":
    unittest.main()
