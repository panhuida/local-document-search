"""示例：使用 Google Gemini API 为 MarkItDown 的图片 / PPTX 生成描述。

本示例实现一个最小的适配器，使 google-genai 的客户端看起来像 MarkItDown 期望的 OpenAI client:
  client.chat.completions.create(model=..., messages=[...])

运行前准备：
1. 安装依赖（requirements 已添加 google-genai）：
   pip install -r requirements.txt
2. 设置环境变量：
   Windows CMD:
       set GEMINI_API_KEY=你的APIKey
   PowerShell:
       $env:GEMINI_API_KEY="你的APIKey"
3. 运行脚本：
   python scripts/markitdown_gemini_example.py path/to/image.jpg

说明：
- MarkItDown 内部对 llm_client 的唯一调用是在 _image_converter / _llm_caption 中：
      client.chat.completions.create(model=model, messages=messages)
  其中 messages 结构为 OpenAI 新版多模态格式： [{'role':'user','content':[{'type':'text','text':...},{'type':'image_url','image_url':{'url': data_uri}}]}]
- 我们解析 messages，只支持单个 user 消息，抽取文本 prompt 与 data URI 图片，调用 Gemini 的 generate_content。
- Gemini 模型示例： gemini-2.5-flash  (可按需要替换其它多模态模型)。

限制与简化：
- 未实现流式输出；
- 仅支持单张图片；
- 若有多条 text 或多张 image 仅取第一条；
- 未做重试与速率限制，可按需要用 tenacity 增强。
"""
from __future__ import annotations
import os
import base64
import re
import sys
from dataclasses import dataclass
from typing import List, Any, Optional
import argparse

try:
    from google import genai  # 新版统一入口 (google-genai>=0.3.0)，旧版可能使用 google.genai
except ImportError:
    print("未安装 google-genai，请先: pip install google-genai", file=sys.stderr)
    raise

# ----------------------------- OpenAI 响应兼容数据结构 -----------------------------
@dataclass
class _ChoiceMessage:
    content: str

@dataclass
class _Choice:
    message: _ChoiceMessage

@dataclass
class _ChatCompletionResponse:
    choices: List[_Choice]

# ----------------------------- Gemini -> OpenAI 接口适配层 -----------------------------
class GeminiChatCompletionsAPI:
    def __init__(self, client: genai.Client):
        self._client = client

    def create(self, model: str, messages: List[dict]):  # 与 OpenAI 期望签名对齐
        # 仅支持单 user 消息
        if not messages:
            raise ValueError("messages 为空")
        if len(messages) != 1 or messages[0].get("role") != "user":
            raise ValueError("当前适配器仅支持单个 user 消息")

        contents = messages[0].get("content", [])
        prompt_text = None
        image_bytes = None
        image_mime = None

        for part in contents:
            ptype = part.get("type")
            if ptype == "text" and prompt_text is None:
                prompt_text = part.get("text")
            elif ptype == "image_url" and image_bytes is None:
                image_url = part.get("image_url", {}).get("url")
                if image_url and image_url.startswith("data:"):
                    # data URI: data:mime;base64,xxx
                    m = re.match(r"data:([^;]+);base64,(.+)", image_url)
                    if m:
                        image_mime = m.group(1)
                        image_bytes = base64.b64decode(m.group(2))
        if prompt_text is None:
            prompt_text = "Caption this image."
        if image_bytes is None:
            raise ValueError("未找到图片 data URI 内容。")
        if image_mime is None:
            image_mime = "image/jpeg"

        # 组装 Gemini API contents
        from google.genai import types  # 延迟导入 types
        parts = [
            types.Part.from_bytes(data=image_bytes, mime_type=image_mime),
            prompt_text,
        ]
        resp = self._client.models.generate_content(model=model, contents=parts)
        text = getattr(resp, "text", None)
        if text is None:
            # 兼容可能的 candidates 结构
            candidates = getattr(resp, "candidates", [])
            if candidates:
                # 简单拼接
                text = "\n".join(
                    [
                        "".join([seg.text for seg in getattr(c, "content", []).parts if getattr(seg, "text", None)])
                        if getattr(c, "content", None) else ""
                        for c in candidates
                    ]
                ).strip()
        if text is None:
            text = "(No caption generated)"
        return _ChatCompletionResponse(choices=[_Choice(message=_ChoiceMessage(content=text))])

class GeminiOpenAICompatClient:
    """提供一个与 OpenAI Python SDK (只用到 chat.completions.create) 兼容的最小客户端。"""
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError("缺少 GEMINI_API_KEY 环境变量")
        # 新 SDK 客户端初始化
        self._client = genai.Client(api_key=api_key)
        self.chat = type("_Chat", (), {"completions": GeminiChatCompletionsAPI(self._client)})()

# ----------------------------- 示例使用 -----------------------------

def run_example(image_path: str, model: str = "gemini-2.5-flash", prompt: str | None = None):
    from markitdown import MarkItDown

    client = GeminiOpenAICompatClient()
    md = MarkItDown(llm_client=client, llm_model=model, llm_prompt=prompt)
    result = md.convert(image_path)
    print("=== Markdown 输出 ===")
    print(result.text_content)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MarkItDown + Gemini 图片描述示例")
    parser.add_argument("image", help="图片文件路径")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Gemini 模型名称")
    parser.add_argument("--prompt", help="自定义描述提示词，可覆盖环境变量 GEMINI_PROMPT")
    args = parser.parse_args()
    run_example(args.image, model=args.model, prompt=args.prompt)
