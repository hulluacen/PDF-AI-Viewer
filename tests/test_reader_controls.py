"""Reader controls: isolated offscreen window and generated PDFs."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pymupdf
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QDialog, QLabel
import settings
from main import MainWindow

class ReaderControlsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.config = patch.object(settings, "_config_dir", return_value=cls.temp.name)
        cls.config.start()
        cls.key = patch.object(settings, "get_llm_key", return_value="")
        cls.key.start()
        cls.app = QApplication.instance() or QApplication([])
        cls.pdf = Path(cls.temp.name) / "bookmarks.pdf"
        doc = pymupdf.open()
        for i in range(3):
            doc.new_page().insert_text((72, 72), "Page %d" % (i + 1))
        doc.set_toc([[1, "Chapter", 1], [2, "Section", 2], [1, "End", 3]])
        doc.save(cls.pdf)
        doc.set_toc([])
        cls.plain = Path(cls.temp.name) / "plain.pdf"
        doc.save(cls.plain)
        doc.close()

    def setUp(self):
        self.window = MainWindow()
        self.window.resize(1600, 900)
        self.window.show()
        self.window.load_pdf(str(self.pdf))
        QTest.qWait(150)

    def tearDown(self):
        self.window.close_pdf()
        self.window.close()
        self.window.float_btn.close()
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    @classmethod
    def tearDownClass(cls):
        cls.key.stop()
        cls.config.stop()
        cls.temp.cleanup()

    def test_zoom_controls(self):
        w = self.window
        w.resize(2000, 800)
        QTest.qWait(150)
        self.assertTrue(w.zoom_percent.isVisible())
        self.assertTrue(w.zoom_in_btn.isVisible())
        previous = round(w.viewer.zoom * 100)
        w.zoom_in_btn.click()
        self.assertEqual(w.zoom_percent.value(), previous + 10)
        self.assertEqual(w.zoom_mode.currentIndex(), 2)
        w.zoom_out_btn.click()
        self.assertEqual(w.zoom_percent.value(), previous)
        w.zoom_percent.setFocus()
        w.zoom_percent.selectAll()
        QTest.keyClicks(w.zoom_percent, "175")
        QTest.keyClick(w.zoom_percent, Qt.Key.Key_Return)
        self.assertEqual(w.viewer.zoom, 1.75)
        self.assertEqual(w.zoom_slider.value(), 175)
        w.zoom_slider.setValue(200)
        self.assertEqual(w.zoom_percent.value(), 200)
        w.zoom_mode.setCurrentIndex(1)
        QTest.qWait(150)
        self.assertEqual(w.viewer.fit_mode, w.viewer.FIT_WIDTH)
        self.assertEqual(w.zoom_percent.value(), round(w.viewer.zoom * 100))
        w.viewer._fit_timer.start()
        w.zoom_percent.setValue(125)
        QTest.qWait(150)
        self.assertEqual(w.viewer.zoom, 1.25)
        w.zoom_percent.setValue(500)
        w.zoom_in_btn.click()
        self.assertEqual(w.viewer.zoom, 5)

    def test_bookmarks_lifecycle(self):
        w = self.window
        self.assertTrue(w.bookmark_action.isEnabled())
        w.bookmark_action.setChecked(True)
        QTest.qWait(150)
        self.assertTrue(w.bookmark_panel.isVisible())
        tree = w.bookmark_tree
        self.assertEqual(tree.topLevelItemCount(), 2)
        child = tree.topLevelItem(0).child(0)
        self.assertEqual(child.text(0), "Section")
        with patch.object(w.viewer, "go_to_internal_link", wraps=w.viewer.go_to_internal_link) as jump:
            w._on_bookmark_clicked(child, 0)
            self.assertEqual(jump.call_args.args[0], 1)
        w.load_pdf(str(self.plain))
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.assertEqual(tree.topLevelItemCount(), 0)
        self.assertTrue(w.bookmark_hint.isVisible())
        w.close_pdf()
        self.assertFalse(w.bookmark_action.isEnabled())
        self.assertFalse(w.bookmark_panel.isVisible())

    def test_about_keeps_upstream_and_fork(self):
        def inspect(dialog):
            text = "\n".join(label.text() for label in dialog.findChildren(QLabel))
            self.assertIn("https://github.com/hulluacen/PDF-AI-Viewer", text)
            self.assertIn("https://github.com/fangvv/PDF-AI-Viewer", text)
            self.assertIn("fangvv@qq.com", text)
            self.assertIn("fork", text)
            return 0
        with patch.object(QDialog, "exec", inspect):
            self.window._show_about()

if __name__ == "__main__":
    unittest.main()
