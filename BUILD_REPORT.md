# 本地构建说明

日期：2026-10-07（Asia/Singapore）

项目：https://github.com/fangvv/PDF-AI-Viewer
Git 源码提交 SHA：`4a016f91609792555065c496c8f716d593601510`
必要源码及资源下载时逐文件验证了 Git blob SHA-1；应用源码和上游 spec 未修改。未下载上游 dist exe。

## 环境

- Python：3.14.2，Windows x64
- PyQt6：6.10.1
- PyMuPDF：1.28.2
- requests：2.32.5
- keyring：25.7.0
- PyInstaller：6.17.0
- pyinstaller-hooks-contrib：2025.10

## 产物

- 文件：`dist/PDF阅读翻译器.exe`
- 大小：64745546 字节（约 64.75 MB）
- SHA-256：`39837d9b8c5e453bc0fc86a5cc29a4adeb65b23d1dccf43843627a940d657313`

## 构建方式与修复

使用上游 spec，保留 exclusions 与 logo 资源。首次构建误从当前工具 PATH 收集 Poppler 的 ICU DLL，导致 QtCore 缺少导入符号。最终构建仅为子进程设置 PATH 为 Python、Python Scripts、Windows System32、Windows 后重新构建；未改系统 PATH。最终产物不包含冲突的 ICU DLL。

命令：`D:\GG\Python\python.exe -m PyInstaller --noconfirm --workpath build-clean "PDF阅读翻译器.spec"`。执行前须为该构建子进程使用上述 PATH。

最终构建日志：`build-clean.log`。

## 验证

- pip check 通过；PyMuPDF 和 keyring 可导入，Windows 凭据后端可初始化。
- 源码离屏检查：主窗口初始化、PDF 加载、页面渲染、文本提取、搜索通过。
- 最终 exe 离屏检查：子进程 PATH 仅含 Windows 系统目录，使用工作目录内隔离的 USERPROFILE，应用完成配置初始化，存活 10 秒，stderr 为空；检查后关闭了测试进程树。
- 静态检查：Windows x64，包含 logo、Qt Windows 平台插件和 keyring Windows 后端。
- 未做人工可见界面验收，也未调用在线翻译或大模型接口。

## 内部链接修复版本（2026-10-07）

旧版本在带内部跳转链接的 PDF 上将 `get_links()["to"]` 的 `Point` 传给 `Rect`，触发与用户截图一致的 AssertionError。已在 pdf_viewer.py 将目标点转换为从其坐标开始的非空锚点矩形，保留目标页与目的坐标。

新产物：`dist-fixed/PDF阅读翻译器.exe`

大小：64746248 字节。SHA-256：`5f5ca77724259e9e3c91b96f48f0ef444205eea3420083317db100510c4bc736`。

验证：`python tests/test_internal_links.py` 通过。另从最终 exe 提取 main 及全部应用模块，在本机同版本依赖下重跑相同回归检查通过；覆盖带内部链接/外部链接 PDF 的加载、渲染、目标坐标、真实跳转位置、文本提取、搜索，以及与普通 PDF 连续切换。修复版 exe 在仅含 Windows 系统目录的 PATH 下离屏启动、初始化配置并存活 8 秒，stderr 为空。未进行人工可见界面验收或在线接口测试。

使用原 spec，以清理后的构建子进程 PATH 执行 `python -m PyInstaller --noconfirm --workpath build-fixed --distpath dist-fixed "PDF阅读翻译器.spec"`。日志为 `build-fixed.log`。使用修复版时应关闭旧版并打开 dist-fixed 中的 exe。

## 高 DPI 与 PopTrans 修复版（2026-10-07）

产物：`dist-hdpi-poptrans/PDF阅读翻译器.exe`，64749339 字节。SHA-256：`2ff39c46ad65f6d54079325c8974862896a780f69472193c23977393203118e5`。

- 页面使用 zoom × 屏幕 DPR 生成物理像素位图，并设置位图 DPR；控件尺寸、文本选择、高亮与链接保持逻辑坐标。DPR 变化后重新渲染。
- 大模型设置新增显式 PopTrans 模式，持久化到 llm_service。该模式通过 /health 检查模型就绪，不查询 /v1/models，不要求或发送 API Key 与模型名；直接向 /v1/chat/completions 发送原文、stream=false 与 target_lang。接受 Base URL 或完整聊天接口地址。
- 回环请求绕过代理；公网接口仍采用默认代理。连接失败提示服务可能未监听或空闲退出；程序不启动/下载 PopTrans 后端。
- PopTrans 是翻译接口，此模式对总结和文献问答给出明确提示，不将它当作通用模型。普通模型鉴权和流式请求保留。
- 保存与取消设置互不干扰：检查使用临时配置，保存才改变当前翻译配置。

验证：100%、150%、200% 下 tests/test_bugfixes.py 全部通过；150% 下既有内部链接加载/跳转回归通过。最终 exe 中提取的全部应用模块在本机同版本依赖下通过上述五项回归，设置对话框选项、完整地址规范化、模式保存通过。源码与最终打包模块均实际调用正在运行的 PopTrans，Hello world. 返回“你好，世界。”。最终 exe 在只含 Windows 系统目录的 PATH 下、150% 离屏模式完成初始化并运行 8 秒，stderr 为空。未做人工可见界面验收。

构建沿用上游 spec 和排除列表，仅为构建子进程清理 PATH。命令：`python -m PyInstaller --noconfirm --workpath build-hdpi-poptrans --distpath dist-hdpi-poptrans "PDF阅读翻译器.spec"`；日志 `build-hdpi-poptrans.log`。

使用方法：关闭旧版，打开本目录新版。在大模型设置选择 PopTrans 本地翻译，地址填写 http://127.0.0.1:8989/v1，检查连接并保存，然后在主窗口选择“大模型”翻译引擎。如果 PopTrans AI 后台已空闲退出，需要在 PopTrans 中触发一次翻译后重试。
