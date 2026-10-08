"""Exercise the actual progress Cancel button while PDF pages are loading."""
import unittest
from pathlib import Path
from unittest.mock import patch
import test_reader_controls as support
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QProgressDialog, QPushButton, QMessageBox
import pymupdf

class LoadCancelTests(support.ReaderControlsTests):
    def test_cancel_preserves_current_document(self):
        self._check_cancel(False)

    def test_cancel_from_empty_window(self):
        self._check_cancel(True)

    def _check_cancel(self, empty):
        w = self.window
        target = Path(self.temp.name) / "cancel.pdf"
        doc = pymupdf.open()
        for _ in range(40):
            doc.new_page()
        doc.save(target)
        doc.close()
        if empty:
            w.close_pdf()
        old_doc, old_pdf = w.viewer.doc, w.current_pdf
        old_pages = list(w.viewer.page_widgets)
        old_bookmarks = w.bookmark_tree.topLevelItemCount()
        for cancel_at in (0, 7, 40):
            seen = []
            class CancelDialog(QProgressDialog):
                def setValue(dialog, value):
                    super().setValue(value)
                    seen.append(value)
                    if value == cancel_at:
                        button = next(b for b in dialog.findChildren(QPushButton)
                                      if b.text() == "取消")
                        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
            with patch("main.QProgressDialog", CancelDialog), patch.object(QMessageBox, "critical") as error:
                w.load_pdf(str(target))
                error.assert_not_called()
            self.assertIs(w.viewer.doc, old_doc)
            self.assertEqual(w.current_pdf, old_pdf)
            self.assertEqual(w.viewer.page_widgets, old_pages)
            self.assertEqual(w.bookmark_tree.topLevelItemCount(), old_bookmarks)
            self.assertEqual(w.status.currentMessage(), "已取消加载 PDF")
            self.assertFalse(w._loading_pdf)
            self.assertLessEqual(max(seen), cancel_at)
            # Closing the staged document must release its Windows file handle.
            target.rename(target.with_suffix(".tmp"))
            target.with_suffix(".tmp").rename(target)
        w.load_pdf(str(target))
        self.assertEqual(len(w.viewer.page_widgets), 40)
        self.assertEqual(w.current_pdf, str(target.resolve()))

    def test_repeated_open_has_visible_page_area(self):
        from PyQt6.QtCore import QEvent
        w = self.window
        for mode in (1, 2, 0):
            w.zoom_mode.setCurrentIndex(mode)
            for _ in range(6):
                w.close_pdf()
                w.load_pdf(str(self.pdf))
                QTest.qWait(30)
                self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
                viewer = w.viewer
                self.assertGreater(viewer._container.width(), 0)
                self.assertGreater(viewer._container.height(), 0)
                page = viewer.page_widgets[0]
                self.assertTrue(page.isVisible())
                self.assertGreater(page.visibleRegion().boundingRect().width(), 0)
                self.assertTrue(page._rendered)
                # Sample the actual viewport: generated PDF background is white.
                position = page.mapTo(viewer.viewport(), page.rect().center())
                position.setY(min(position.y(), viewer.viewport().height() // 2))
                self.assertTrue(viewer.viewport().rect().contains(position))
                color = viewer.viewport().grab().toImage().pixelColor(position)
                self.assertGreater(color.red(), 240)
                self.assertGreater(color.green(), 240)
                self.assertGreater(color.blue(), 240)

    def test_open_failure_preserves_current_document(self):
        old_doc, old_pdf = self.window.viewer.doc, self.window.current_pdf
        with patch.object(QMessageBox, "critical") as error:
            self.window.load_pdf(str(Path(self.temp.name) / "missing.pdf"))
            error.assert_called_once()
        self.assertIs(self.window.viewer.doc, old_doc)
        self.assertEqual(self.window.current_pdf, old_pdf)
        self.assertFalse(self.window._loading_pdf)

if __name__ == "__main__":
    unittest.main()
