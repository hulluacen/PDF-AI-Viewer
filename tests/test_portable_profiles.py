"""Portable migration, isolated credentials, UI activation and real loopback probes."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import types
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
import storage_paths
import settings
import model_profiles
import chat_log
from model_settings_dialog import ModelSettingsDialog


class PortableTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.old = self.root / "old"
        self.old.mkdir()
        self.data = self.root / "portable" / "data"

    def tearDown(self):
        self.temp.cleanup()

    def test_migration_preserves_originals_and_never_overwrites(self):
        original = '{"theme":"dark","llm_model":"old-model"}'
        (self.old / "settings.json").write_text(original)
        (self.old / "recent.json").write_text('["old.pdf"]')
        (self.old / "reading_positions.json").write_text('{"old.pdf":{"page":4}}')
        (self.old / "chatnotes").mkdir()
        (self.old / "chatnotes" / "a.md").write_text("old note")
        storage_paths.initialize_data(self.data, self.old)
        self.assertEqual((self.data / "settings.json").read_text(), original)
        self.assertEqual((self.old / "settings.json").read_text(), original)
        self.assertEqual((self.data / "chatnotes" / "a.md").read_text(), "old note")
        (self.data / "recent.json").write_text("[]")
        storage_paths.initialize_data(self.data, self.old)
        self.assertEqual((self.data / "recent.json").read_text(), "[]")

    def test_existing_portable_config_wins_and_failed_copy_can_retry(self):
        (self.old / "settings.json").write_text('{"theme":"light"}')
        self.data.mkdir(parents=True)
        (self.data / "settings.json").write_text('{"theme":"dark"}')
        (self.old / "recent.json").write_text("[]")
        with patch.object(storage_paths, "_copy_missing", side_effect=OSError("copy failed")):
            with self.assertRaises(OSError):
                storage_paths.initialize_data(self.data, self.old)
        self.assertFalse((self.data / "migration-v1.json").exists())
        storage_paths.initialize_data(self.data, self.old)
        self.assertEqual((self.data / "settings.json").read_text(), '{"theme":"dark"}')

    def test_executable_not_cwd_or_meipass(self):
        with patch.object(sys, "frozen", True, create=True), \
             patch.object(sys, "executable", str(self.root / "portable" / "reader.exe")), \
             patch.object(sys, "_MEIPASS", str(self.root / "unpacked"), create=True):
            self.assertEqual(storage_paths.application_dir(), self.root / "portable")

    def test_atomic_failure_preserves_old_data(self):
        target = self.root / "settings.json"
        target.write_text('{"theme":"dark"}')
        with patch.object(storage_paths.os, "replace", side_effect=OSError("read only")):
            with self.assertRaises(OSError):
                storage_paths.atomic_json(target, {"theme": "light"})
        self.assertEqual(target.read_text(), '{"theme":"dark"}')
        self.assertEqual(list(self.root.glob(".write-*")), [])

    def test_portable_pdf_records_follow_directory_move(self):
        first = self.root / "first"
        second = self.root / "second"
        with patch.object(settings, "_config_dir", return_value=str(self.root)), \
             patch.object(settings, "application_dir", return_value=first):
            settings.add_recent(str(first / "books" / "a.pdf"))
            settings.save_position(str(first / "books" / "a.pdf"), 7, 99)
            self.assertIn("@portable/books/a.pdf", settings.load_positions())
        with patch.object(settings, "_config_dir", return_value=str(self.root)), \
             patch.object(settings, "application_dir", return_value=second):
            self.assertEqual(settings.load_recent(), [str(second / "books" / "a.pdf")])
            self.assertEqual(settings.get_position(str(second / "books" / "a.pdf")), {"page": 7, "scroll": 99})

    def test_corrupt_config_not_replaced(self):
        path = self.root / "settings.json"
        path.write_text("corrupt", encoding="utf-8")
        with patch.object(settings, "_config_dir", return_value=str(self.root)):
            with self.assertRaises(ValueError):
                model_profiles.load_profiles()
        self.assertEqual(path.read_text(), "corrupt")

    def test_notes_import_once_and_same_names_do_not_collide(self):
        for folder in ("a", "b"):
            (self.root / folder).mkdir()
        pdf = self.root / "a" / "book.pdf"
        sidecar = pdf.with_suffix(".md")
        original = "# book.pdf\n\n## 1. 问：old question\n> 第 2 页 · yesterday\n\n**答：**\nold answer\n\n---\n"
        sidecar.write_text(original, encoding="utf-8")
        with patch.object(settings, "_config_dir", return_value=str(self.data)):
            path, error = chat_log.append_exchange(str(pdf), "new question", "new answer", 3)
            self.assertIsNone(error)
            self.assertTrue(Path(path).is_relative_to(self.data))
            self.assertEqual(sidecar.read_text(encoding="utf-8"), original)
            exchanges, raw = chat_log.load_chat_log(str(pdf))
            self.assertEqual(len(exchanges), 2)
            self.assertEqual(exchanges[0]["q"], "old question")
            self.assertIsNone(raw)
            self.assertNotEqual(path, chat_log.md_path_for(str(self.root / "b" / "book.pdf")))


class ProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config = patch.object(settings, "_config_dir", return_value=self.temp.name)
        self.config.start()
        self.secrets = {}
        fake = types.SimpleNamespace(
            get_password=lambda service, name: self.secrets.get((service, name)),
            set_password=lambda service, name, key: self.secrets.__setitem__((service, name), key),
            delete_password=lambda service, name: self.secrets.pop((service, name), None))
        self.keyring = patch.dict(sys.modules, {"keyring": fake})
        self.keyring.start()

    def tearDown(self):
        self.keyring.stop()
        self.config.stop()
        self.temp.cleanup()

    def seed(self):
        settings.save_settings({"theme": "dark", "llm_base_url": "http://127.0.0.1:1234/v1",
                                "llm_model": "legacy-model", "llm_service": "openai"})
        self.secrets[(settings.APP_NAME, "llm_key")] = "legacy-secret"
        return model_profiles.load_profiles()

    def test_legacy_profile_and_independent_credentials(self):
        state = self.seed()
        self.assertEqual(settings.get_llm_key(), "legacy-secret")
        second = model_profiles.new_profile("second")
        second.update(base_url="http://localhost:4321/v1", model="second-model")
        model_profiles.save_profile_key(second, "second-secret")
        state["profiles"].append(second)
        model_profiles.save_profiles(state)
        self.assertEqual(settings.get_llm_model(), "legacy-model")
        state["active_id"] = second["id"]
        model_profiles.save_profiles(state)
        self.assertEqual(settings.get_llm_key(), "second-secret")
        self.assertEqual(settings.get_llm_model(), "second-model")
        self.assertEqual(self.secrets[(settings.APP_NAME, "llm_key")], "legacy-secret")
        saved = Path(settings._settings_file()).read_text(encoding="utf-8")
        self.assertNotIn("legacy-secret", saved)
        self.assertNotIn("second-secret", saved)
        self.assertEqual(settings.load_settings()["theme"], "dark")

    def test_ui_select_save_activate_and_drafts(self):
        state = self.seed()
        dialog = ModelSettingsDialog()
        changed = []
        dialog.activeChanged.connect(lambda: changed.append(True))
        dialog._add()
        new_id = dialog.current_id
        dialog.name.setText("local")
        dialog.url.setText("http://localhost:8989/v1/chat/completions")
        dialog.model.setCurrentText("local-model")
        dialog.key.setText("separate-secret")
        dialog.list.setCurrentRow(0)
        self.assertEqual(settings.get_llm_model(), "legacy-model")
        dialog.list.setCurrentRow(1)
        self.assertEqual(dialog.model.currentText(), "local-model")
        self.assertTrue(dialog._commit(False))
        self.assertEqual(changed, [])
        self.assertEqual(settings.get_llm_model(), "legacy-model")
        self.assertTrue(dialog._commit(True))
        self.assertEqual(model_profiles.load_profiles()["active_id"], new_id)
        self.assertEqual(settings.get_llm_key(), "separate-secret")
        self.assertEqual(settings.get_llm_base_url(), "http://localhost:8989/v1")
        self.assertEqual(len(changed), 1)
        dialog.list.setCurrentRow(0)
        self.assertEqual(dialog.key.text(), "legacy-secret")
        dialog.reject()
        reopened = ModelSettingsDialog()
        self.assertEqual(reopened.current_id, new_id)
        self.assertEqual(reopened.model.currentText(), "local-model")
        reopened.reject()

    def test_busy_active_change_and_keyring_failure_do_not_activate(self):
        self.seed()
        dialog = ModelSettingsDialog(can_change=lambda: False)
        dialog._add()
        dialog.url.setText("http://localhost:1/v1")
        dialog.model.setCurrentText("model")
        before = model_profiles.load_profiles()
        with patch("model_settings_dialog.QMessageBox.information"):
            self.assertFalse(dialog._commit(True))
        self.assertEqual(model_profiles.load_profiles(), before)
        dialog.can_change = lambda: True
        dialog.key.setText("secret")
        with patch.object(model_profiles, "save_profile_key", side_effect=RuntimeError("secret")), \
             patch("model_settings_dialog.QMessageBox.warning") as warning:
            self.assertFalse(dialog._commit(True))
            self.assertNotIn("secret", str(warning.call_args))
        self.assertEqual(model_profiles.load_profiles(), before)
        dialog.reject()

    def test_poptrans_does_not_use_or_modify_cloud_key(self):
        state = self.seed()
        p = model_profiles.new_profile("PopTrans", "poptrans")
        p["base_url"] = "http://localhost:8989/v1"
        state["profiles"].append(p)
        state["active_id"] = p["id"]
        model_profiles.save_profiles(state)
        model_profiles.save_profile_key(p, "must-not-be-stored")
        self.assertEqual(settings.get_llm_key(), "")
        self.assertEqual(len(self.secrets), 1)
        dialog = ModelSettingsDialog()
        self.assertFalse(dialog.key.isEnabled())
        self.assertFalse(dialog.model.isEnabled())
        self.assertFalse(dialog.models_btn.isEnabled())
        dialog.reject()

    def test_config_write_failure_restores_credential(self):
        self.seed()
        dialog = ModelSettingsDialog()
        dialog.key.setText("replacement-key")
        with patch.object(model_profiles, "save_profiles", side_effect=OSError("disk full")), \
             patch("model_settings_dialog.QMessageBox.warning"):
            self.assertFalse(dialog._commit(False))
        self.assertEqual(settings.get_llm_key(), "legacy-secret")
        dialog.reject()

    def test_threaded_probe_uses_selected_model_without_activation(self):
        calls = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                calls.append((self.path, None, self.headers.get("Authorization")))
                body = {"translator_ready": True} if self.path == "/health" else {"data": [{"id": "fetched-model"}]}
                self.respond(body)
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                calls.append((self.path, payload, self.headers.get("Authorization")))
                self.respond({"choices": [{"message": {"content": "OK"}}]})
            def respond(self, body):
                data = json.dumps(body).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        dialog = None
        try:
            self.seed()
            active = model_profiles.load_profiles()["active_id"]
            dialog = ModelSettingsDialog()
            dialog._add()
            dialog.url.setText(f"http://127.0.0.1:{server.server_port}/v1")
            dialog.model.setCurrentText("precise-model")
            dialog.key.setText("")
            for operation in ("models", "test", "poptrans"):
                if operation == "poptrans":
                    dialog.service.setCurrentIndex(1)
                dialog._start_probe(operation)
                self.assertFalse(dialog.list.isEnabled())
                for _ in range(100):
                    QTest.qWait(20)
                    if dialog.probe is None: break
                self.assertIsNone(dialog.probe)
                self.assertNotIn("失败", dialog.result.text())
            self.assertEqual(model_profiles.load_profiles()["active_id"], active)
            self.assertEqual([c[0] for c in calls], ["/v1/models", "/v1/chat/completions", "/health"])
            self.assertEqual(calls[1][1]["model"], "precise-model")
            self.assertIsNone(calls[1][2])
            self.assertIsNone(calls[2][2])
        finally:
            if dialog is not None:
                if dialog.probe is not None:
                    dialog.probe.wait(16000)
                    self.app.processEvents()
                dialog.reject()
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
