# 修改记录 / Changelog

## 未发布 / Unreleased

- 紧急修复大文件加载取消无效：逐页检查取消，新文档成功后才替换旧文档；取消/打开失败释放临时文档，保留原阅读状态，支持再次打开。

- 新增缩放 −/+ 按钮与百分比输入（10%–500%，Enter 确认），与滑块、快捷键、Ctrl+滚轮、适配模式同步；缩放位于页码跳转后、搜索前，与导航同一行。
- 新增「书签」开关及左侧 PDF 内置书签树，支持层级展示与目标位置跳转；无书签时明确提示，切换/关闭 PDF 清理目录。
- 关于窗口增加 hulluacen fork 的说明与项目链接，保留原作者项目和邮箱。
- 切换固定缩放时停止待执行的自动适配，防止手动比例被覆盖；切换 PDF 释放旧文档句柄。
- 新增 tests/test_reader_controls.py 覆盖缩放交互、书签生命周期及关于归属信息。
- 未修改单词选择逻辑；未替换已发布的 v0.1.0 tag 或附件。

Added editable zoom controls, a toggleable embedded PDF outline and fork attribution in About. Fixed pending fit updates overriding manual zoom and released previous PDF handles when switching documents. Existing release assets remain unchanged.

## 仓库维护 / Repository maintenance — 2026-10-08

- 移除 main 的 dist 目录，忽略本地构建与同步输出，保留 PyInstaller spec。
- 下载、克隆及反馈入口统一指向 hulluacen/PDF-AI-Viewer；上游来源和许可证保留。
- exe 与校验文件仅通过 Releases 发布；保留已有 v0.1.0 tag 和附件，不重写历史。
- 本次仅调整仓库文件与文档，程序版本仍为 0.1.0。

Build output is removed from main and ignored locally. Packaging configuration remains tracked; executables and checksums are distributed through this fork’s Releases. Existing history, v0.1.0 tag and assets are preserved. No application code or version change.

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
- 0.1.0 Release 已重新打包；提取打包模块确认版本为 0.1.0，离屏启动检查通过。

### 范围与限制

- Windows 0.1.0 exe 和 SHA256SUMS.txt 已发布到本 fork 的 Releases；main 不再跟踪 dist 构建输出。历史提交及已发布 tag、附件保留。
- PopTrans 接口用于翻译，不支持全文总结或文献问答；此类能力需要 OpenAI 兼容模型。
- PopTrans 后台空闲退出后，需要先在 PopTrans 中触发一次翻译再重试。本项目不自动启动后台或下载模型。
- 未将 WinError 10061 的确切原因归结为模型列表接口缺失；连接拒绝与 HTTP 接口兼容属于不同阶段。

### English

Initial versioned fork release. Fixes PDF internal-link destination handling and high-DPI rendering; adds explicit PopTrans translation mode, health checks, optional credentials/model name, direct loopback requests and URL normalization. Connection probes no longer alter the active configuration. Existing OpenAI-compatible authentication and streaming remain supported. The Windows 0.1.0 executable and checksum are published through this fork’s Releases; dist build output is no longer tracked on main. PopTrans translation does not provide document summarization or chat.
