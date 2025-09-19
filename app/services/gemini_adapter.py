"""Gemini 适配器：为 MarkItDown 提供 OpenAI chat.completions.create 兼容接口。

MarkItDown 的多模态调用格式（_image_converter / _llm_caption）期望：
    client.chat.completions.create(model=..., messages=[{"role":"user","content":[{"type":"text","text":...},{"type":"image_url","image_url":{"url":data_uri}}]}])
返回对象需含： response.choices[0].message.content

本文件实现最小封装以调用 google-genai 的多模态能力（模型示例： gemini-2.5-flash）。

使用：
    from .gemini_adapter import build_markitdown_with_gemini
    md = build_markitdown_with_gemini()  # 若未配置 GEMINI_API_KEY 将回退无 LLM

环境变量：
    GEMINI_API_KEY  (必需)
    GEMINI_MODEL    (可选，默认 gemini-2.5-flash)
"""
from __future__ import annotations
import os
import re
import base64
from dataclasses import dataclass
from typing import List, Optional, Any

try:
    # 新版库名：google-genai (导入包路径 google.genai 或 google.genai)
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore
except Exception:  # pragma: no cover - 如果未安装则在构建时安全忽略
    genai = None  # type: ignore
    types = None  # type: ignore

# -------------------- OpenAI 兼容响应结构 --------------------
@dataclass
class _ChoiceMessage:
    content: str

@dataclass
class _Choice:
    message: _ChoiceMessage

@dataclass
class _ChatCompletionResponse:
    choices: List[_Choice]

# -------------------- chat.completions 适配 --------------------
class _GeminiChatCompletionsAPI:
    def __init__(self, client: Any):  # 使用 Any 避免类型解析错误
        self._client = client

    def create(self, model: str, messages: List[dict]):  # 与 OpenAI 期望签名
        if not messages:
            raise ValueError("messages 不能为空")
        if len(messages) != 1 or messages[0].get("role") != "user":
            raise ValueError("当前 Gemini 适配仅支持单个 user 消息")

        contents = messages[0].get("content", [])
        prompt_text: Optional[str] = None
        image_bytes: Optional[bytes] = None
        image_mime: Optional[str] = None

        for part in contents:
            ptype = part.get("type")
            if ptype == "text" and prompt_text is None:
                prompt_text = part.get("text")
            elif ptype == "image_url" and image_bytes is None:
                image_url = part.get("image_url", {}).get("url")
                if image_url and image_url.startswith("data:"):
                    m = re.match(r"data:([^;]+);base64,(.+)", image_url)
                    if m:
                        image_mime = m.group(1)
                        try:
                            image_bytes = base64.b64decode(m.group(2))
                        except Exception:
                            raise ValueError("无法解析图片 data URI 的 base64 内容")
        if prompt_text is None:
            prompt_text = "Describe this image."
        if image_bytes is None:
            raise ValueError("未找到图片 data URI 内容——MarkItDown 应该传入 base64 data URI")
        if image_mime is None:
            image_mime = "image/jpeg"

        parts: List[Any] = [types.Part.from_bytes(data=image_bytes, mime_type=image_mime), prompt_text]
        resp = self._client.models.generate_content(model=model, contents=parts)
        # 兼容 resp.text / candidates
        text = getattr(resp, "text", None)
        if not text:
            candidates = getattr(resp, "candidates", [])
            texts: List[str] = []
            for c in candidates:
                content = getattr(c, "content", None)
                if content and getattr(content, "parts", None):
                    for seg in content.parts:  # type: ignore
                        seg_text = getattr(seg, "text", None)
                        if seg_text:
                            texts.append(seg_text)
            text = "\n".join(texts).strip() if texts else "(No caption generated)"
        return _ChatCompletionResponse(choices=[_Choice(message=_ChoiceMessage(content=text))])

# -------------------- OpenAI 客户端外观 --------------------
class GeminiOpenAICompatClient:
    def __init__(self, api_key: Optional[str] = None):
        if genai is None:
            raise RuntimeError("未安装 google-genai，请先安装依赖: pip install google-genai")
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError("缺少 GEMINI_API_KEY 环境变量")
        self._client = genai.Client(api_key=api_key)
        # 模拟 openai.chat.completions 子层级
        self.chat = type("_Chat", (), {"completions": _GeminiChatCompletionsAPI(self._client)})()

# -------------------- 构建带 Gemini 的 MarkItDown 实例 --------------------

def build_markitdown_with_gemini(markdown_cls=None, *, model: Optional[str] = None, prompt: Optional[str] = None):
    """如果检测到 GEMINI_API_KEY 则构建带 LLM 的 MarkItDown，否则返回普通实例。
    :param markdown_cls: 注入自定义 MarkItDown 类（测试用）
    :param model: 自定义模型，默认读取 GEMINI_MODEL 或 gemini-2.5-flash
    :param prompt: 自定义提示词
    """
    from markitdown import MarkItDown as _MK
    MK = markdown_cls or _MK

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        # 回退：无 LLM
        return MK()
    model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    # 优先顺序: 显式参数 > 环境变量 GEMINI_PROMPT > 环境变量 GEMINI_IMAGE_PROMPT
    env_prompt = prompt or os.getenv("GEMINI_PROMPT") or os.getenv("GEMINI_IMAGE_PROMPT")
    client = GeminiOpenAICompatClient(api_key=api_key)
    return MK(llm_client=client, llm_model=model, llm_prompt=env_prompt)

__all__ = [
    "GeminiOpenAICompatClient",
    "build_markitdown_with_gemini",
]
