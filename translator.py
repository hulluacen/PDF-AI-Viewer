"""免费在线翻译引擎。

主引擎：微软 Edge 官方翻译 API（无需认证、国内可访问、翻译质量好、支持批量）
备用引擎：通用 OpenAI 兼容大模型（需 API Key，翻译质量高）、MyMemory（免费、无需 key）

失败时自动回退到下一个引擎。
"""

import json
from contextlib import contextmanager
from urllib.parse import urlsplit
import ipaddress

import requests


class TranslationError(Exception):
    """翻译失败异常。"""


class BaseTranslator:
    """翻译器基类。"""

    name = "base"

    def translate(self, text: str, src: str = "auto", dst: str = "zh") -> str:
        raise NotImplementedError


class EdgeTranslator(BaseTranslator):
    """微软 Edge 官方翻译 API（无需认证）。"""

    name = "微软 Edge 翻译"

    # 语言代码映射
    _LANG = {
        "zh": "zh-CHS",
        "en": "en",
        "ja": "ja",
        "ko": "ko",
        "fr": "fr",
        "de": "de",
        "es": "es",
        "ru": "ru",
    }

    def translate(self, text: str, src: str = "auto", dst: str = "zh") -> str:
        if not text.strip():
            return ""
        to = self._LANG.get(dst, dst)
        from_lang = "en" if src == "auto" else self._LANG.get(src, src)
        url = "https://edge.microsoft.com/translate/translatetext"
        params = {
            "from": from_lang,
            "to": to,
            "api-version": "3.0",
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
            ),
            "Origin": "https://www.microsoft.com",
            "Referer": "https://www.microsoft.com/",
        }
        resp = requests.post(url, params=params, json=[text], headers=headers, timeout=15)
        resp.raise_for_status()
        result = resp.json()
        if isinstance(result, list) and result:
            translations = result[0].get("translations", [])
            if translations:
                return translations[0].get("text", "")
        raise TranslationError("Edge 翻译返回异常: " + str(result)[:200])


class OpenAICompatTranslator(BaseTranslator):
    """通用 OpenAI 兼容大模型接口（需 API Key）。

    支持任意 OpenAI 兼容服务商（OpenRouter、DeepSeek、智谱、本地 Ollama 等），
    由用户配置 base_url、model、api_key。支持翻译、总结等大模型能力。
    """

    name = "大模型"

    def __init__(self, api_key: str = "", base_url: str = "", model: str = "", service: str = "openai"):
        self.api_key = api_key
        self.base_url = self.normalize_url(base_url)
        self.model = model
        self.service = service

    @staticmethod
    def normalize_url(url):
        url = url.strip().rstrip("/")
        if url.endswith("/chat/completions"):
            url = url[:-len("/chat/completions")]
        return url

    @contextmanager
    def _request(self, method, url, **kwargs):
        host = urlsplit(url).hostname or ""
        try:
            local = host.lower() == "localhost" or ipaddress.ip_address(host).is_loopback
        except ValueError:
            local = host.lower() == "localhost"
        # 回环接口直接连接，避免系统代理或环境代理转发本地模型请求。
        with requests.Session() as session:
            session.trust_env = not local
            try:
                response = session.request(method, url, **kwargs)
            except requests.exceptions.ConnectionError as exc:
                raise TranslationError(
                    f"无法连接接口 {url}。请确认服务正在监听此地址；"
                    "PopTrans 的 AI 后台可能在空闲后退出，请先在 PopTrans 中触发一次翻译。"
                ) from exc
            with response:
                response.raise_for_status()
                yield response

    def _headers(self):
        headers = {"Content-Type": "application/json"}
        if self.api_key and self.service != "poptrans":
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def check_poptrans(self):
        parsed = urlsplit(self.base_url)
        url = f"{parsed.scheme}://{parsed.netloc}/health"
        with self._request("GET", url, timeout=15) as response:
            result = response.json()
        if not result.get("translator_ready"):
            raise TranslationError("PopTrans 已连接，但翻译模型尚未就绪：" + str(result.get("translator_status", "加载中")))
        return result

    def _validate(self):
        """校验大模型配置，缺失时抛出可读的错误。"""
        if self.service == "poptrans":
            if not self.base_url:
                raise TranslationError("请填写 PopTrans 接口地址")
            return
        host = urlsplit(self.base_url).hostname or ""
        try:
            local = host.lower() == "localhost" or ipaddress.ip_address(host).is_loopback
        except ValueError:
            local = host.lower() == "localhost"
        if not self.api_key and not local:
            raise TranslationError("未配置大模型 API Key，请在「设置 → 大模型设置」中填写")
        if not self.base_url:
            raise TranslationError("未配置大模型接口地址，请在「设置 → 大模型设置」中填写")
        if not self.model:
            raise TranslationError("未配置大模型名称，请在「设置 → 大模型设置」中填写")

    def _chat(self, prompt: str, timeout: int = 60, target_lang: str = "zh") -> str:
        """调用大模型，返回文本结果。"""
        self._validate()
        url = f"{self.base_url}/chat/completions"
        if self.service == "poptrans":
            payload = {"messages": [{"role": "user", "content": prompt}],
                       "stream": False, "target_lang": target_lang}
        else:
            payload = {"model": self.model, "messages": [{"role": "user", "content": prompt}],
                       "temperature": 0.3}
        with self._request("POST", url, json=payload, headers=self._headers(), timeout=timeout) as resp:
            resp.encoding = "utf-8"
            result = resp.json()
        try:
            content = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            raise TranslationError("大模型返回异常: " + str(result)[:200])
        if content and content.strip():
            return content.strip()
        raise TranslationError("大模型返回空结果")

    def _stream_messages(self, messages: list, timeout: int = 120, temperature: float = 0.3):
        """流式调用大模型（支持多轮 messages），逐块 yield 文本内容。"""
        self._validate()
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model, "messages": messages,
            "temperature": temperature, "stream": True,
        }
        with self._request("POST", url, json=payload, headers=self._headers(), timeout=timeout,
                           stream=True) as resp:
            # 强制 UTF-8 解码，避免 SSE 流未声明 charset 时按 ISO-8859-1 解码导致乱码
            resp.encoding = "utf-8"
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data: "):
                    data = line[6:]
                elif line == "data: [DONE]":
                    break
                else:
                    continue
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                try:
                    delta = chunk["choices"][0]["delta"].get("content", "")
                except (KeyError, IndexError):
                    continue
                if delta:
                    yield delta

    def _chat_stream(self, prompt: str, timeout: int = 120):
        """流式调用大模型（单条 user 提示），逐块 yield 文本内容。"""
        return self._stream_messages([{"role": "user", "content": prompt}], timeout)

    # 与 Chatbox 保持一致：系统提示词用其默认值，不自定义人设、不限制回答长短。
    # （公式显示端仍有 latex_fallback 做兕底，输出语言跟随用户提问的语言）
    _CHAT_SYSTEM = "You are a helpful assistant."

    def chat_stream(self, history: list, doc_text: str = "", timeout: int = 180):
        """多轮对话问答，流式 yield 回答内容（温度固定 0，同 Chatbox 默认）。

        history: [{"role": "user"/"assistant", "content": "..."}, ...]，不含系统消息。
        doc_text: 当前阅读的文献全文（可选）。非空时像 Chatbox 附加文件一样，
        作为首对 user/assistant 消息注入；系统提示词本身保持不变。
        """
        if self.service == "poptrans":
            raise TranslationError("PopTrans 接口仅用于翻译，不支持文献问答；请切换到 OpenAI 兼容模型服务。")
        messages = [{"role": "system", "content": self._CHAT_SYSTEM}]
        if doc_text.strip():
            messages.append({
                "role": "user",
                "content": f"以下是我正在阅读的文献内容：\n\n{doc_text}",
            })
            messages.append({
                "role": "assistant",
                "content": "好的，我已了解上述文献内容，请提问。",
            })
        messages.extend(history)
        return self._stream_messages(messages, timeout, temperature=0)

    def summarize_stream(self, text: str, lang: str = "zh"):
        """流式总结文本，逐块 yield 内容。"""
        if self.service == "poptrans":
            raise TranslationError("PopTrans 接口仅用于翻译，不支持全文总结；请切换到 OpenAI 兼容模型服务。")
        if not text.strip():
            return
        prompt = (
            "你是一位精通各领域前沿研究的学术文献解读专家，面对一篇给定的论文，"
            "请你高效阅读并迅速提取出其核心内容。要求在解读过程中，"
            "先对文献的背景、研究目的和问题进行简明概述，再详细梳理研究方法、"
            "关键数据、主要发现及结论，同时对新颖概念进行通俗易懂的解释，"
            "帮助读者理解论文的逻辑与创新点；最后，请对文献的优缺点进行客观评价，"
            "并指出可能的后续研究方向。整体报告结构清晰、逻辑严谨。\n"
            "请务必使用中文输出，并可使用 Markdown 格式（如标题、列表、加粗）"
            "使报告层次分明、便于阅读。\n"
            "重要：遇到数学公式时，请使用 Unicode 数学符号和纯文本表示"
            "（例如 E = mc²、x₁ + x₂、f(x) = ax² + bx + c），"
            "不要使用 LaTeX 语法（如 $...$、\\frac、^、_ 等），"
            "因为本软件无法渲染 LaTeX 公式。\n\n"
            "以下是待解读的论文文本：\n\n"
            f"{text}"
        )
        yield from self._chat_stream(prompt)

    def list_models(self) -> list:
        """从服务商拉取可用模型列表。"""
        if not self.base_url:
            raise TranslationError("未配置大模型接口地址，请在「设置」中填写")
        if self.service == "poptrans":
            self.check_poptrans()
            return []
        url = f"{self.base_url}/models"
        with self._request("GET", url, headers=self._headers(), timeout=15) as resp:
            result = resp.json()
        models = result.get("data", [])
        names = []
        for m in models:
            mid = m.get("id")
            if mid:
                names.append(mid)
        return names

    def translate(self, text: str, src: str = "auto", dst: str = "zh") -> str:
        if not text.strip():
            return ""
        if self.service == "poptrans":
            return self._chat(text, target_lang=dst)
        prompt = (
            f"请将以下文本翻译成{'中文' if dst == 'zh' else dst}，"
            f"只输出翻译结果，不要添加任何解释或原文：\n\n{text}"
        )
        return self._chat(prompt)

    def summarize(self, text: str, lang: str = "zh") -> str:
        """总结文本内容。"""
        if not text.strip():
            return ""
        prompt = (
            "你是一位精通各领域前沿研究的学术文献解读专家，面对一篇给定的论文，"
            "请你高效阅读并迅速提取出其核心内容。要求在解读过程中，"
            "先对文献的背景、研究目的和问题进行简明概述，再详细梳理研究方法、"
            "关键数据、主要发现及结论，同时对新颖概念进行通俗易懂的解释，"
            "帮助读者理解论文的逻辑与创新点；最后，请对文献的优缺点进行客观评价，"
            "并指出可能的后续研究方向。整体报告结构清晰、逻辑严谨。\n"
            "请务必使用中文输出，并可使用 Markdown 格式（如标题、列表、加粗）"
            "使报告层次分明、便于阅读。\n"
            "重要：遇到数学公式时，请使用 Unicode 数学符号和纯文本表示"
            "（例如 E = mc²、x₁ + x₂、f(x) = ax² + bx + c），"
            "不要使用 LaTeX 语法（如 $...$、\\frac、^、_ 等），"
            "因为本软件无法渲染 LaTeX 公式。\n\n"
            "以下是待解读的论文文本：\n\n"
            f"{text}"
        )
        return self._chat(prompt, timeout=90)


class MyMemoryTranslator(BaseTranslator):
    """MyMemory 免费翻译 API（无需 key）。"""

    name = "MyMemory"

    def translate(self, text: str, src: str = "auto", dst: str = "zh") -> str:
        if not text.strip():
            return ""
        lang = "zh-CN" if dst == "zh" else dst
        src_code = "en" if src == "auto" else src
        url = "https://api.mymemory.translated.net/get"
        params = {
            "q": text,
            "langpair": f"{src_code}|{lang}",
        }
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        }
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        result = resp.json()
        if result.get("responseStatus") == 200:
            translated = result.get("responseData", {}).get("translatedText", "")
            if translated:
                return translated
        raise TranslationError("MyMemory 返回异常: " + str(result)[:200])


class Translator:
    """翻译管理器，支持自动回退或指定引擎。"""

    def __init__(self, llm_key: str = "", llm_base_url: str = "", llm_model: str = "", llm_service: str = "openai"):
        self.llm = OpenAICompatTranslator(llm_key, llm_base_url, llm_model, llm_service)
        self.engines = [
            EdgeTranslator(),
            self.llm,
            MyMemoryTranslator(),
        ]

    def configure_llm(self, api_key: str, base_url: str, model: str, service: str = "openai"):
        """配置大模型参数。"""
        self.llm.api_key = api_key
        self.llm.base_url = self.llm.normalize_url(base_url)
        self.llm.model = model
        self.llm.service = service

    def list_llm_models(self) -> list:
        """拉取大模型可用模型列表。"""
        return self.llm.list_models()

    def summarize(self, text: str, lang: str = "zh") -> str:
        """用大模型总结文本。"""
        return self.llm.summarize(text, lang=lang)

    def summarize_stream(self, text: str, lang: str = "zh"):
        """流式总结文本，逐块 yield 内容。"""
        yield from self.llm.summarize_stream(text, lang=lang)

    def engine_names(self) -> list:
        """返回所有引擎名称。"""
        return [e.name for e in self.engines]

    def translate(self, text: str, src: str = "auto", dst: str = "zh",
                  engine: str = "auto") -> str:
        """翻译文本。

        engine: "auto" 表示自动回退；否则指定引擎名称。
        """
        if not text.strip():
            return ""
        if engine != "auto":
            # 指定引擎
            for e in self.engines:
                if e.name == engine:
                    return e.translate(text, src=src, dst=dst)
            raise TranslationError(f"未知翻译引擎: {engine}")
        # 自动回退
        errors = []
        for e in self.engines:
            try:
                result = e.translate(text, src=src, dst=dst)
                if result and result.strip():
                    return result
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{e.name}: {exc}")
        raise TranslationError("所有翻译引擎均失败: " + "; ".join(errors))
