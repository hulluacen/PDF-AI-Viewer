"""PDF 内部链接目标点回归检查；离屏运行，不调用网络接口。"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
TEST_HOME = ROOT / "build-regression" / "test-user"
TEST_HOME.mkdir(parents=True, exist_ok=True)
os.environ["USERPROFILE"] = str(TEST_HOME)

import pymupdf
from PyQt6.QtWidgets import QApplication, QMessageBox
from main import MainWindow
import settings

class InternalLinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_linked_and_plain_documents_can_be_loaded_consecutively(self):
        with tempfile.TemporaryDirectory(dir=TEST_HOME) as tmp, \
             patch.object(settings, "_config_dir", return_value=tmp), \
             patch.object(settings, "get_llm_key", return_value=""), \
             patch.object(QMessageBox, "critical", side_effect=AssertionError("PDF load failed")):
            linked = Path(tmp) / "linked.pdf"
            plain = Path(tmp) / "plain.pdf"
            doc = pymupdf.open()
            doc.new_page()
            doc.new_page()
            doc[0].insert_text((72, 72), "Internal link regression")
            doc[1].insert_text((72, 500), "Destination text")
            for i, y in enumerate((80.91998, 500)):
                doc[0].insert_link({"kind": pymupdf.LINK_GOTO, "from": pymupdf.Rect(72, 90+i*30, 180, 110+i*30), "page": 1, "to": pymupdf.Point(82, y)})
            doc[0].insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(72, 160, 180, 180), "uri": "https://example.com"})
            doc.save(linked)
            doc.close()
            doc = pymupdf.open()
            doc.new_page().insert_text((72, 72), "Plain PDF regression")
            doc.save(plain)
            doc.close()
            w = MainWindow()
            try:
                w.resize(1000, 700)
                w.show()
                self.app.processEvents()
                for path in (linked, plain, linked):
                    w.load_pdf(str(path))
                    self.app.processEvents()
                    self.assertIsNotNone(w.viewer.doc)
                    for page in w.viewer.page_widgets:
                        page.ensure_rendered()
                        self.assertFalse(page.pixmap.isNull())
                    if path == linked:
                        page = w.viewer.page_widgets[0]
                        self.assertEqual(len(page._internal_links), 2)
                        self.assertEqual(len(page._links), 1)
                        for (_, index, anchor), y in zip(page._internal_links, (80.91998, 500)):
                            self.assertEqual(index, 1)
                            self.assertAlmostEqual(anchor.x0, 82, places=3)
                            self.assertAlmostEqual(anchor.y0, y, places=3)
                            self.assertFalse(anchor.is_empty)
                        anchor = page._internal_links[1][2]
                        w.viewer.go_to_internal_link(1, anchor)
                        self.app.processEvents()
                        target = w.viewer.page_widgets[1]
                        bar = w.viewer.verticalScrollBar()
                        expected = max(bar.minimum(), min(int(target.y() + anchor.y0*w.viewer.zoom - w.viewer.viewport().height()/2), bar.maximum()))
                        self.assertEqual(bar.value(), expected)
                        self.assertIn("Destination text", w.viewer.document_text())
                        self.assertTrue(w.viewer.search("Destination"))
                    else:
                        self.assertEqual(len(w.viewer.page_widgets), 1)
                        self.assertFalse(w.viewer.page_widgets[0]._internal_links)
                w.close_pdf()
            finally:
                w.close()
                self.app.processEvents()

if __name__ == "__main__":
    unittest.main(verbosity=2)
