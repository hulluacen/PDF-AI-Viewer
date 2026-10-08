"""Independent model settings view; network probes use their own clients."""
import copy
from urllib.parse import urlsplit
from PyQt6.QtCore import QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QDialog, QHBoxLayout, QVBoxLayout, QLabel, QListWidget,
                            QLineEdit, QComboBox, QPushButton, QMessageBox)
import model_profiles as profiles
import settings
from translator import OpenAICompatTranslator


class ConnectionProbe(QThread):
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, profile, key, operation, parent=None):
        super().__init__(parent)
        self.profile = dict(profile)
        self.key = key
        self.operation = operation

    def run(self):
        try:
            p = self.profile
            client = OpenAICompatTranslator(self.key, p["base_url"], p["model"], p["service"])
            if p["service"] == "poptrans":
                client.check_poptrans()
                result = "PopTrans 已连接，翻译模型已就绪。"
            elif self.operation == "models":
                result = client.list_models()
            else:
                client._chat("Reply with OK.", timeout=15)
                result = "当前配置的模型已成功响应。"
            self.succeeded.emit(result)
        except Exception as exc:
            # Never expose a credential in an error box, including third-party errors.
            message = str(exc)
            if self.key:
                message = message.replace(self.key, "[已隐藏密钥]")
            self.failed.emit(message)


class ModelSettingsDialog(QDialog):
    activeChanged = pyqtSignal()

    def __init__(self, parent=None, can_change=None):
        super().__init__(parent)
        self.setObjectName("modelSettingsDialog")
        self.setWindowTitle("模型配置")
        self.resize(820, 490)
        self.state = profiles.load_profiles()
        self.drafts = {}
        self.keys = {}
        self.current_id = None
        self.probe = None
        self.can_change = can_change or (lambda: True)
        root = QHBoxLayout(self)
        left = QVBoxLayout()
        self.list = QListWidget()
        self.list.setMinimumWidth(190)
        self.list.setMaximumWidth(260)
        left.addWidget(QLabel("模型配置（点击查看，启用才切换）"))
        left.addWidget(self.list)
        buttons = QHBoxLayout()
        self.add_btn = QPushButton("新增")
        self.delete_btn = QPushButton("删除")
        buttons.addWidget(self.add_btn)
        buttons.addWidget(self.delete_btn)
        left.addLayout(buttons)
        root.addLayout(left)
        right = QVBoxLayout()
        self.name = QLineEdit()
        self.service = QComboBox()
        self.service.addItem("OpenAI 兼容模型", "openai")
        self.service.addItem("PopTrans 本地翻译", "poptrans")
        self.url = QLineEdit()
        self.url.setPlaceholderText("https://服务地址/v1 或 http://127.0.0.1:端口/v1")
        self.key = QLineEdit()
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText("此配置的独立密钥；无鉴权本地接口可留空")
        self.model = QComboBox()
        self.model.setEditable(True)
        for title, widget in (("配置名称", self.name), ("接口类型", self.service),
                              ("接口地址 (Base URL)", self.url), ("API Key", self.key),
                              ("模型名称", self.model)):
            right.addWidget(QLabel(title))
            right.addWidget(widget)
        network = QHBoxLayout()
        self.models_btn = QPushButton("获取模型列表")
        self.test_btn = QPushButton("检查连接")
        network.addWidget(self.models_btn)
        network.addWidget(self.test_btn)
        right.addLayout(network)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        right.addWidget(self.hint)
        self.result = QLabel()
        self.result.setWordWrap(True)
        right.addWidget(self.result)
        credentials = QLabel("密钥按配置存入 Windows 凭据管理器，不会随便携文件夹迁移。")
        credentials.setWordWrap(True)
        right.addWidget(credentials)
        folder_btn = QPushButton("打开数据目录")
        folder_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(settings._config_dir())))
        right.addWidget(folder_btn)
        right.addStretch()
        footer = QHBoxLayout()
        self.save_btn = QPushButton("保存配置")
        self.enable_btn = QPushButton("启用此配置")
        self.close_btn = QPushButton("关闭")
        for button in (self.save_btn, self.enable_btn, self.close_btn):
            footer.addWidget(button)
        right.addLayout(footer)
        root.addLayout(right, 1)
        self.list.currentRowChanged.connect(self._select)
        self.service.currentIndexChanged.connect(self._service_ui)
        self.add_btn.clicked.connect(self._add)
        self.delete_btn.clicked.connect(self._delete)
        self.save_btn.clicked.connect(lambda: self._commit(False))
        self.enable_btn.clicked.connect(lambda: self._commit(True))
        self.models_btn.clicked.connect(lambda: self._start_probe("models"))
        self.test_btn.clicked.connect(lambda: self._start_probe("test"))
        self.close_btn.clicked.connect(self.reject)
        self._rebuild(self.state["active_id"])

    def _profile(self, identifier):
        return next(p for p in self.state["profiles"] if p["id"] == identifier)

    def _capture(self):
        if self.current_id is None:
            return
        p = copy.deepcopy(self._profile(self.current_id))
        p.update(name=self.name.text().strip(), service=self.service.currentData(),
                 base_url=OpenAICompatTranslator.normalize_url(self.url.text()),
                 model=self.model.currentText().strip())
        self.drafts[self.current_id] = p
        self.keys[self.current_id] = self.key.text().strip()

    def _rebuild(self, selected):
        self.list.blockSignals(True)
        self.list.clear()
        row = 0
        for i, p in enumerate(self.state["profiles"]):
            label = p["name"] or "未命名配置"
            if p["id"] == self.state["active_id"]:
                label += "  [已启用]"
            self.list.addItem(label)
            if p["id"] == selected:
                row = i
        self.list.setCurrentRow(row)
        self.list.blockSignals(False)
        self.current_id = None
        self._select(row)

    def _select(self, row):
        if row < 0:
            return
        self._capture()
        self.current_id = self.state["profiles"][row]["id"]
        p = self.drafts.get(self.current_id, self._profile(self.current_id))
        self.name.setText(p["name"])
        self.service.setCurrentIndex(self.service.findData(p["service"]))
        self.url.setText(p["base_url"])
        if self.current_id not in self.keys:
            self.keys[self.current_id] = profiles.profile_key(p)
        self.key.setText(self.keys[self.current_id])
        self.model.clear()
        self.model.setCurrentText(p["model"])
        self.result.clear()
        self._service_ui()

    def _service_ui(self):
        poptrans = self.service.currentData() == "poptrans"
        self.key.setEnabled(not poptrans)
        self.model.setEnabled(not poptrans)
        self.models_btn.setEnabled(not poptrans and not self._probing())
        self.hint.setText("PopTrans 无需密钥和模型名，只支持翻译，不支持全文总结和文献问答。" if poptrans else
                          "检查连接会发送一条简短请求，验证当前选定模型；获取列表仅查询可用模型。")
        active = self.current_id == self.state["active_id"]
        self.enable_btn.setText("保存并保持启用" if active else "启用此配置")

    def _probing(self):
        return self.probe is not None and self.probe.isRunning()

    def _commit(self, activate):
        self._capture()
        p = self.drafts[self.current_id]
        if not p["name"]:
            QMessageBox.warning(self, "无法保存", "请填写配置名称。")
            return False
        if activate and (urlsplit(p["base_url"]).scheme not in ("http", "https") or not urlsplit(p["base_url"]).netloc):
            QMessageBox.warning(self, "无法启用", "请填写完整的 HTTP 或 HTTPS 接口地址。")
            return False
        if activate and p["service"] == "openai" and not p["model"]:
            QMessageBox.warning(self, "无法启用", "请填写或选择模型名称。")
            return False
        changes_active = activate or self.current_id == self.state["active_id"]
        if changes_active and not self.can_change():
            QMessageBox.information(self, "任务进行中", "请等待当前翻译、总结或问答结束后，再修改已启用配置。")
            return False
        updated = copy.deepcopy(self.state)
        for i, item in enumerate(updated["profiles"]):
            if item["id"] == self.current_id:
                updated["profiles"][i] = p
        if activate:
            updated["active_id"] = self.current_id
        old = self._profile(self.current_id)
        old_key = profiles.profile_key(old)
        key_written = False
        try:
            # Unchanged keys need no write; unavailable keyring must not look like successful saving.
            if p["service"] != "poptrans" and self.keys[self.current_id] != old_key:
                profiles.save_profile_key(p, self.keys[self.current_id])
                key_written = True
            profiles.save_profiles(updated)
        except Exception:
            if key_written:
                try:
                    profiles.save_profile_key(p, old_key)
                except Exception:
                    QMessageBox.warning(self, "密钥回退失败", "配置未保存，但密钥已变更，请重新检查此配置的密钥。")
            QMessageBox.warning(self, "保存失败", "无法保存配置或密钥，请检查数据目录权限和系统凭据服务。")
            return False
        self.state = updated
        if changes_active:
            self.activeChanged.emit()
        self._rebuild(self.current_id)
        self.result.setText("配置已保存并启用。" if activate else "配置已保存。")
        return True

    def _add(self):
        self._capture()
        p = profiles.new_profile()
        updated = copy.deepcopy(self.state)
        updated["profiles"].append(p)
        try:
            profiles.save_profiles(updated)
        except Exception:
            QMessageBox.warning(self, "新增失败", "无法写入数据目录。")
            return
        self.state = updated
        self._rebuild(p["id"])
        self.name.selectAll()
        self.name.setFocus()

    def _delete(self):
        if self.current_id == self.state["active_id"]:
            QMessageBox.information(self, "无法删除", "请先启用其他配置，再删除此配置。")
            return
        p = self._profile(self.current_id)
        if QMessageBox.question(self, "删除配置", f"删除“{p['name']}”？") != QMessageBox.StandardButton.Yes:
            return
        updated = copy.deepcopy(self.state)
        updated["profiles"] = [x for x in updated["profiles"] if x["id"] != self.current_id]
        try:
            profiles.save_profiles(updated)
        except Exception:
            QMessageBox.warning(self, "删除失败", "无法写入数据目录。")
            return
        # Keep the legacy credential so previous versions remain usable.
        if p["credential"] != "llm_key":
            try:
                profiles.save_profile_key(dict(p, service="openai"), "")
            except Exception:
                QMessageBox.warning(self, "密钥清理失败", "配置已删除，系统凭据中的密钥未能清理。")
        self.drafts.pop(self.current_id, None)
        self.keys.pop(self.current_id, None)
        self.state = updated
        self._rebuild(updated["active_id"])

    def _start_probe(self, operation):
        self._capture()
        p = self.drafts[self.current_id]
        parsed = urlsplit(p["base_url"])
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            QMessageBox.warning(self, "无法检查", "请填写完整的接口地址。")
            return
        self.probe = ConnectionProbe(p, self.keys[self.current_id], operation, self)
        self.probe.succeeded.connect(self._probe_ok)
        self.probe.failed.connect(lambda message: self.result.setText("连接失败：" + message))
        self.probe.finished.connect(self._probe_finished)
        self._set_busy(True)
        self.result.setText("正在检查，请稍候……")
        self.probe.start()

    def _set_busy(self, busy):
        for widget in (self.list, self.name, self.service, self.url, self.key, self.model,
                       self.add_btn, self.delete_btn, self.save_btn, self.enable_btn,
                       self.test_btn, self.models_btn, self.close_btn):
            widget.setEnabled(not busy)
        if not busy:
            self._service_ui()

    def _probe_ok(self, result):
        if isinstance(result, list):
            selected = self.model.currentText()
            self.model.clear()
            self.model.addItems(result)
            self.model.setCurrentText(selected)
            self.result.setText(f"已获取 {len(result)} 个模型。")
        else:
            self.result.setText(result)

    def _probe_finished(self):
        self._set_busy(False)
        self.probe.deleteLater()
        self.probe = None

    def reject(self):
        if self._probing():
            self.result.setText("正在检查连接，请等待请求结束后关闭。")
            return
        super().reject()

    def closeEvent(self, event):
        if self._probing():
            event.ignore()
        else:
            super().closeEvent(event)
