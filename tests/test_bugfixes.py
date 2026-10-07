import os, sys, json, threading, unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import pymupdf
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF
from pdf_viewer import PdfPageWidget
from translator import OpenAICompatTranslator, TranslationError

class Handler(BaseHTTPRequestHandler):
    calls = []
    ready = True
    def log_message(self, *args): pass
    def send_json(self, body, status=200):
        data = json.dumps(body).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        self.calls.append(("GET", self.path, None, self.headers.get("Authorization")))
        if self.path == "/health": self.send_json({"translator_ready": self.ready, "translator_status": "loading"})
        elif self.path == "/v1/models": self.send_json({"data": [{"id": "test-model"}]})
        else: self.send_json({}, 404)
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.calls.append(("POST", self.path, body, self.headers.get("Authorization")))
        if self.path != "/v1/chat/completions": self.send_json({}, 404); return
        if body.get("stream"):
            data = b'data: {"choices":[{"delta":{"content":"OK"}}]}\n\ndata: [DONE]\n\n'
            self.send_response(200); self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
        else: self.send_json({"choices": [{"message": {"content": "translated"}}]})

class BugFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True); cls.worker.start()
        cls.base = "http://127.0.0.1:%d/v1" % cls.server.server_port
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.worker.join()
    def setUp(self): Handler.calls.clear(); Handler.ready = True
    def test_high_dpi_pixels_and_coordinates(self):
        doc = pymupdf.open(); doc.new_page(width=600, height=800)
        doc[0].insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(50,50,100,100), "uri": "https://example.com"})
        doc = pymupdf.open(stream=doc.tobytes(), filetype="pdf")
        for zoom in (0.75, 1.0, 1.5):
            w = PdfPageWidget(doc[0], zoom); w.ensure_rendered()
            ratio = w.devicePixelRatioF()
            self.assertEqual(w.pixmap.devicePixelRatioF(), ratio)
            self.assertAlmostEqual(w.pixmap.width(), 600*zoom*ratio, delta=1)
            self.assertEqual(w.width(), int(600*zoom))
            self.assertEqual(w.height(), int(800*zoom))
            self.assertEqual(w._link_at(QPointF(75*zoom,75*zoom)), "https://example.com")
            self.assertEqual(w._link_at(QPointF(125*zoom,125*zoom)), None)
            w.set_theme("dark"); w.ensure_rendered(); self.assertFalse(w.pixmap.isNull())
        doc.close()
    def test_poptrans_no_key_no_model_direct_connection(self):
        client = OpenAICompatTranslator(base_url=self.base+"/chat/completions", service="poptrans")
        with patch.dict(os.environ, {"HTTP_PROXY":"http://127.0.0.1:1", "HTTPS_PROXY":"http://127.0.0.1:1", "ALL_PROXY":"http://127.0.0.1:1", "NO_PROXY":""}):
            self.assertEqual(client.list_models(), [])
            self.assertEqual(client.translate("Hello", dst="zh"), "translated")
        self.assertEqual([x[1] for x in Handler.calls], ["/health", "/v1/chat/completions"])
        body = Handler.calls[1][2]
        self.assertEqual(body["messages"], [{"role":"user", "content":"Hello"}])
        self.assertEqual(body["target_lang"], "zh")
        self.assertNotIn("model", body)
        self.assertIsNone(Handler.calls[1][3])
    def test_poptrans_health_and_capability_errors(self):
        client = OpenAICompatTranslator(api_key="cloud-secret", base_url=self.base, service="poptrans")
        self.assertNotIn("Authorization", client._headers())
        Handler.ready=False
        with self.assertRaisesRegex(TranslationError, "尚未就绪"): client.check_poptrans()
        with self.assertRaisesRegex(TranslationError, "不支持文献问答"): list(client.chat_stream([]))
        with self.assertRaisesRegex(TranslationError, "不支持全文总结"): list(client.summarize_stream("text"))
    def test_openai_model_auth_and_stream_preserved(self):
        client=OpenAICompatTranslator("test-key", self.base, "test-model")
        self.assertEqual(client.list_models(), ["test-model"])
        self.assertEqual(client.translate("Hello"), "translated")
        self.assertEqual("".join(client.chat_stream([{"role":"user","content":"Hi"}])), "OK")
        self.assertTrue(all(x[3]=="Bearer test-key" for x in Handler.calls))
        self.assertEqual(Handler.calls[1][2]["model"], "test-model")

if __name__ == "__main__": unittest.main(verbosity=2)
