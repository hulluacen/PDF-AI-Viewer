"""阅读问答记录（Markdown）的读写。

问答内容统一写到 data/chatnotes，路径摘要区分同名 PDF。
旧的 PDF 同目录笔记与旧回退笔记会复制导入，原件保留。

文件格式（每条问答以带序号的标题开头，便于逐条解析回来）::

    # A.pdf 阅读问答记录

    <!-- 说明行，不算正文 -->

    ## 1. 问：为什么要用 Transformer？
    > 第 3 页 · 2026-09-30 14:22

    **答：**

    因为……

    ---
"""

import datetime
import os
import re
import hashlib
from pathlib import Path
from storage_paths import _copy_missing, application_dir

import settings

# 文件头说明：首次创建时写入，提醒人这个文件是什么
HEADER_NOTE = (
    "<!-- 本文件由「PDF 阅读翻译器」的 AI 问答功能自动追加，"
    "可直接编辑、补充笔记；删除条目不影响阅读。 -->"
)

_ANSWER_MARK = "**答：**"

# 问题标题行：^## <序号>. 问：<问题>
_Q_RE = re.compile(r"^##[ \t]+\d+\.[ \t]*问：(.*)$", re.M)
# 上下文标记行：> 第 N 页 · 时间
_META_RE = re.compile(r"^>[ \t]*第[ \t]*(\d+)[ \t]*页[ \t]*·[ \t]*(.+?)[ \t]*$", re.M)


def md_path_for(pdf_path: str) -> str:
    """Portable notes, with a path identifier to separate same-named PDFs."""
    absolute = Path(pdf_path).resolve()
    try:
        identity = str(absolute.relative_to(application_dir())).replace("\\", "/")
    except ValueError:
        identity = os.path.normcase(str(absolute))
    suffix = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    target = Path(settings.chatnotes_dir()) / f"{absolute.stem}-{suffix}.md"
    if not target.exists():
        # Import old sidecar / fallback notes once, without changing originals.
        for old in (absolute.with_suffix(".md"), Path(settings.chatnotes_dir()) / f"{absolute.stem}.md"):
            if old.is_file():
                _copy_missing(old, target)
                break
    return str(target)


def _header(pdf_path: str) -> str:
    return (
        f"# {os.path.basename(pdf_path)} 阅读问答记录\n\n"
        f"{HEADER_NOTE}\n\n"
    )


def _entry_count(text: str) -> int:
    """已有问答条数（按问题标题行统计，对无法逐条解析的文件同样适用）。"""
    return len(_Q_RE.findall(text))


def load_chat_log(pdf_path: str):
    """读取问答记录。

    返回 (exchanges, raw)：
    - 解析成功：exchanges 为问答列表，raw 为 None；
    - 文件不存在或为空：([], None)；
    - 文件格式被改坏 / 不是本功能写的：([], 原文)，界面按原文展示。
    """
    try:
        path = md_path_for(pdf_path)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return [], None
    if not text.strip():
        return [], None

    marks = list(_Q_RE.finditer(text))
    if not marks:
        return [], text

    exchanges = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        block = text[m.end():end]
        question = " ".join(m.group(1).split())
        page, when = 0, ""
        mm = _META_RE.search(block)
        if mm:
            page = int(mm.group(1))
            when = mm.group(2).strip()
        idx = block.find(_ANSWER_MARK)
        answer = block[idx + len(_ANSWER_MARK):] if idx >= 0 else block
        answer = answer.replace(HEADER_NOTE, "")
        answer = re.sub(r"\n?---\s*\Z", "", answer.strip()).strip()
        if question:
            exchanges.append({"q": question, "a": answer, "page": page, "time": when})
    return exchanges, None


def append_exchange(pdf_path: str, question: str, answer: str, page: int = 0):
    """追加一轮问答。

    返回 (实际写入路径, 错误信息)，无法写入时由界面提示。
    """
    question = " ".join((question or "").split())
    if not question:
        return None, "问题为空，未写入笔记"
    when = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        lines = [f"## {_next_index(pdf_path)}. 问：{question}\n"]
    except OSError as exc:
        return None, f"无法访问便携笔记目录：{exc}"
    if page:
        lines.append(f"> 第 {page} 页 · {when}\n")
    else:
        lines.append(f"> {when}\n")
    lines.append(f"\n{_ANSWER_MARK}\n\n{(answer or '').strip()}\n\n---\n\n")
    entry = "".join(lines)

    try:
        path = md_path_for(pdf_path)
        _write_entry(path, pdf_path, entry)
        return path, None
    except OSError as exc:
        return None, f"写入便携问答笔记失败：{exc}"


def _write_entry(path: str, pdf_path: str, entry: str) -> None:
    """追加写入；文件不存在时先写文件头。"""
    existed = os.path.exists(path)
    with open(path, "a", encoding="utf-8") as f:
        if not existed:
            f.write(_header(pdf_path))
        f.write(entry)


def _next_index(pdf_path: str) -> int:
    """下一条问答的序号，尽量与文件里已有条数衔接。"""
    path = md_path_for(pdf_path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            head = f.read()
    except OSError:
        return 1
    return _entry_count(head) + 1
