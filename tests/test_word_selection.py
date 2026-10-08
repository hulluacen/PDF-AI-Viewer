"""Character selection and word gestures using generated PDFs and Qt events."""
import os,sys,unittest
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pymupdf
from PyQt6.QtCore import Qt,QPoint,QPointF
from PyQt6.QtTest import QTest,QSignalSpy
from PyQt6.QtWidgets import QApplication
from pdf_viewer import PdfPageWidget

class WordSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.doc=pymupdf.open();page=self.doc.new_page(width=420,height=300)
        page.insert_text((30,45),"alpha beta gamma",fontsize=14)
        page.insert_text((30,75),"second line here",fontsize=14)
        page.insert_text((30,105),"don't re-enter",fontsize=14)
        x=30+pymupdf.get_text_length("multi",fontsize=14)
        page.insert_text((30,135),"multi",fontsize=14,color=(1,0,0))
        page.insert_text((x,135),"color",fontsize=14,color=(0,0,1))
        page.insert_text((30,170),"中文测试",fontname="china-s",fontsize=14)
        self.widgets=[]
    def tearDown(self):
        for w in self.widgets:w.close()
        self.doc.close()
    def widget(self,zoom=1,rotation=0):
        self.doc[0].set_rotation(rotation)
        w=PdfPageWidget(self.doc[0],zoom);w.show();w.ensure_rendered();self.widgets.append(w)
        w._ensure_text_model();return w
    def coords(self,w,line,index,right=False):
        char=w._text_lines[line][1][index];r=pymupdf.Rect(char[1:])
        x=r.x1-0.1 if right else r.x0+0.1
        return QPoint(round(x*w.zoom),round((r.y0+r.y1)*w.zoom/2))
    def drag(self,w,line,start,endline,end,reverse=False):
        a=self.coords(w,line,start);b=self.coords(w,endline,end,True)
        if reverse:a,b=b,a
        spy=QSignalSpy(w.textSelected)
        QTest.mousePress(w,Qt.MouseButton.LeftButton,pos=a)
        QTest.mouseRelease(w,Qt.MouseButton.LeftButton,pos=b)
        self.assertTrue(spy)
        return spy[-1][0]
    def test_drag_selects_only_word_and_substring(self):
        for zoom in (0.75,1,1.5,2):
            w=self.widget(zoom)
            self.assertEqual(self.drag(w,0,6,0,9),"beta")
            self.assertEqual(self.drag(w,0,7,0,8),"et")
            self.assertEqual(self.drag(w,0,6,0,9,True),"beta")
            self.assertTrue(w._sel_rects)
            self.assertLess(sum(r.width() for r in w._sel_rects),100*zoom)
    def test_cross_line_selection_is_linear_not_rectangle(self):
        w=self.widget()
        self.assertEqual(self.drag(w,0,11,1,5),"gamma second")
        self.assertEqual(self.drag(w,0,11,1,5,True),"gamma second")
    def test_double_click_and_copy(self):
        w=self.widget(1.5);spy=QSignalSpy(w.textSelectedAt)
        QTest.mouseDClick(w,Qt.MouseButton.LeftButton,pos=self.coords(w,0,7))
        QTest.mouseRelease(w,Qt.MouseButton.LeftButton,pos=self.coords(w,0,7))
        self.assertEqual(w._extract_selected_text(),"beta")
        self.assertEqual(spy[-1][0],"beta")
        QTest.keyClick(w,Qt.Key.Key_C,Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(QApplication.clipboard().text(),"beta")
    def test_punctuation_and_split_spans(self):
        w=self.widget()
        for line,index,expected in [(2,1,"don't"),(2,3,"don't"),(2,8,"re-enter"),(3,6,"multicolor")]:
            QTest.mouseDClick(w,Qt.MouseButton.LeftButton,pos=self.coords(w,line,index))
            self.assertEqual(w._extract_selected_text(),expected)
    def test_chinese_character_selection(self):
        w=self.widget(2)
        self.assertEqual(self.drag(w,4,1,4,2),"文测")
        QTest.mouseDClick(w,Qt.MouseButton.LeftButton,pos=self.coords(w,4,1))
        self.assertEqual(w._extract_selected_text(),"文")
    def test_rotated_page_word_selection(self):
        w=self.widget(1.5,90)
        rect=pymupdf.Rect(w._text_lines[0][1][7][1:])
        pos=QPoint(round((rect.x0+rect.x1)*w.zoom/2),round((rect.y0+rect.y1)*w.zoom/2))
        QTest.mouseDClick(w,Qt.MouseButton.LeftButton,pos=pos)
        self.assertEqual(w._extract_selected_text(),"beta")
    def test_empty_page_and_existing_links(self):
        page=self.doc.new_page();w=PdfPageWidget(page,1);w.show();self.widgets.append(w)
        QTest.mouseDClick(w,Qt.MouseButton.LeftButton,pos=QPoint(50,50))
        self.assertEqual(w._extract_selected_text(),"")
        self.doc[0].insert_link({"kind":pymupdf.LINK_URI,"from":pymupdf.Rect(25,25,170,50),"uri":"https://example.com"})
        w=self.widget();spy=QSignalSpy(w.linkClicked)
        QTest.mouseClick(w,Qt.MouseButton.LeftButton,pos=QPoint(40,40))
        self.assertEqual(spy[-1][0],"https://example.com")

if __name__=="__main__":unittest.main()
