# 修改记录 / Changelog

## 0.1.0 — 2026-10-08

本 fork 的首次源码版本，基于 fangvv/PDF-AI-Viewer。版本由 version.py 统一定义，程序“关于”窗口及 Qt 应用版本使用 0.1.0。

### 修复

- **内部链接 PDF 无法打开**：PyMuPDF 的链接目标为 Point，上游代码直接传给 Rect 会抛出断言。转换成非空锚点矩形，保留目标页及精确位置。
- **高 DPI 页面模糊**：以页面缩放 × 屏幕 DPR 渲染物理像素，并设置位图 DPR；页面布局、选择、高亮及链接仍使用逻辑坐标。屏幕倍率变化时重新渲染。
- **PopTrans 接口兼容**：增加显式“PopTrans 本地翻译”模式；不要求 API Key 或模型名，不发送已有云端 Key。使用 /health 检查模型就绪，直接调用 /v1/chat/completions，不依赖不存在的 /v1/models。发送原文及 target_lang。
- **本地代理和地址处理**：回环接口直接连接，公网接口保留默认代理行为；Base URL 和完整聊天地址均可输入。
- **设置检查改变当前配置**：检查连接使用临时客户端，保存才应用设置，取消对话框不改变当前运行接口。
- **打包环境 DLL 冲突**：记录构建子进程 PATH 清理方式，避免从 Poppler 工具路径误收集同名 ICU DLL，不修改系统 PATH。

### 验证

- 100%、150%、200% 下的渲染像素、逻辑尺寸和链接坐标检查通过。
- 带内部/外部链接及普通 PDF 连续加载、渲染、搜索和跳转回归通过。
- PopTrans 无鉴权、无模型名、代理绕过及健康检查通过；普通模型鉴权和流式请求回归通过。
- 实际调用本机运行中的 PopTrans，Hello world. 返回“你好，世界。”。
- 本地先前构建已做离屏启动和打包模块检查；0.1.0 的新增版本标识仅同步源码，未重新打包。

### 范围与限制

- 本次仅追加 0.1.0 源码版本与修改记录，**保留已上传的修复版 exe 和校验文件**，不恢复上游旧 exe，也不重新打包。已上传 exe 包含 BUG 修复，但其关于窗口版本号尚未更新。
- PopTrans 接口用于翻译，不支持全文总结或文献问答；此类能力需要 OpenAI 兼容模型。
- PopTrans 后台空闲退出后，需要先在 PopTrans 中触发一次翻译再重试。本项目不自动启动后台或下载模型。
- 未将 WinError 10061 的确切原因归结为模型列表接口缺失；连接拒绝与 HTTP 接口兼容属于不同阶段。

### English

Initial versioned fork release. Fixes PDF internal-link destination handling and high-DPI rendering; adds explicit PopTrans translation mode, health checks, optional credentials/model name, direct loopback requests and URL normalization. Connection probes no longer alter the active configuration. Existing OpenAI-compatible authentication and streaming remain supported. The previously uploaded bug-fix executable is retained in dist; its About version has not been rebuilt to match 0.1.0. PopTrans translation does not provide document summarization or chat.
