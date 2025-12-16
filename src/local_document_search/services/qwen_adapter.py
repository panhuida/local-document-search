"""Qwen-OCR 适配器：通过 DashScope SDK 提供 OCR 服务。

当配置 IMAGE_CAPTION_PROVIDER=qwen-ocr 时使用。
依赖：dashscope 官方库。
环境变量：
  DASHSCOPE_API_KEY  (必需, 这是阿里云模型服务的通用 key)
  IMAGE_CAPTION_PROMPT (可选, Qwen-OCR 通常不需要特定 prompt)
"""
from __future__ import annotations
import os
import json
from typing import Optional, List, Dict, Any
import base64
from http import HTTPStatus
import dashscope

# Qwen-OCR 的 prompt 主要是为了满足 API 格式，内容影响不大
DEFAULT_PROMPT = "请对这张图片进行文字识别"

class _DashScopeQwenOCRClient:
    """
    一个包装器，用于调用 DashScope 的 Qwen-VL-OCR API，
    并将请求和响应格式适配为与 OpenAI ChatCompletion 类似。
    """
    def __init__(self, api_key: str, model: str):
        if dashscope is None:
            raise RuntimeError("dashscope 库未安装, 无法使用 qwen-ocr。请运行: pip install dashscope")
        
        dashscope.api_key = api_key
        self.model = model

    def _prepare_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将 OpenAI 格式的 messages 转换为 DashScope 格式。"""
        # Expecting OpenAI-style messages: list with one user message containing
        # content array of parts like {"type":"text","text":...} and
        # {"type":"image_url","image_url":{"url":...}}
        if not messages or not isinstance(messages, list):
            raise ValueError("Invalid messages format for DashScope conversion.")

        first = messages[0]
        if not isinstance(first, dict) or first.get("role") != "user":
            raise ValueError("Currently only single user message is supported for Qwen-OCR adapter")

        contents = first.get("content") or []
        image_part = None
        text_part = DEFAULT_PROMPT

        for part in contents:
            if not isinstance(part, dict):
                continue
            ptype = part.get("type")
            if ptype == "image_url":
                image_part = part.get("image_url", {}).get("url")
            elif ptype == "text":
                text_part = part.get("text") or text_part

        if not image_part:
            raise ValueError("Image URL not found in messages.")

        # DashScope example expects content to be a list where the image is
        # represented as an object with key `image` and additional params.
        ds_message = {
            "role": "user",
            "content": [
                {"image": image_part, "enable_rotate": True},
                {"text": text_part}
            ]
        }

        return [ds_message]

    def create(self, *args, **kwargs) -> Any:
        """模拟 OpenAI 的 `chat.completions.create` 方法。"""
        model = kwargs.get("model", self.model)
        messages = kwargs.get("messages")

        if not messages:
            raise ValueError("`messages` is a required argument.")

        try:
            prepared_messages = self._prepare_messages(messages)
            
            # Pass api_key to the call in case environment not set globally
            response = dashscope.MultiModalConversation.call(
                api_key=dashscope.api_key,
                model=model,
                messages=prepared_messages,
                ocr_options={"task": "text_recognition"}
            )

            if response.status_code == HTTPStatus.OK:
                # 将 DashScope 的响应转换为 OpenAI ChatCompletion 格式
                text_content = ""
                # response might be dict-like or object-like depending on SDK
                choices = []
                try:
                    # prefer attribute access
                    choices = getattr(response.output, "choices", [])
                except Exception:
                    try:
                        choices = response.get("output", {}).get("choices", [])
                    except Exception:
                        choices = []

                for choice in choices:
                    # different shapes: choice.message.content OR choice["message"]["content"]
                    parts = []
                    if hasattr(choice, "message") and getattr(choice.message, "content", None) is not None:
                        parts = choice.message.content
                    else:
                        # try mapping/dict style
                        msg = (choice.get("message") if isinstance(choice, dict) else None) or {}
                        parts = msg.get("content", [])

                    for part in parts:
                        if isinstance(part, dict) and "text" in part:
                            text_content += part["text"]
                        elif hasattr(part, "text"):
                            text_content += getattr(part, "text")

                return self._create_chat_completion_object(text_content, model, response)
            else:
                error_message = f"DashScope API Error: {response.code} - {response.message}"
                return self._create_chat_completion_object(error_message, model, response, is_error=True)

        except Exception as e:
            # Try to surface DashScope-specific error details when available
            err_info = {}
            try:
                # response variable may exist in outer scope if raised after call
                if 'response' in locals() and response is not None:
                    # prefer attribute access
                    err_info['code'] = getattr(response, 'code', None)
                    err_info['message'] = getattr(response, 'message', None)
                    # also check dict-style
                    if not err_info['code'] and isinstance(response, dict):
                        err_info['code'] = response.get('code')
                        err_info['message'] = response.get('message')
            except Exception:
                pass

            error_message = f"An unexpected error occurred: {e}"
            # Log to Flask app logger when available, otherwise use standard logging
            try:
                from flask import current_app
                if current_app and hasattr(current_app, 'logger'):
                    current_app.logger.exception("Qwen-OCR call failed: %s | response_info=%s", error_message, err_info)
                else:
                    raise RuntimeError("no flask app")
            except Exception:
                import logging
                logging.exception("Qwen-OCR call failed: %s | response_info=%s", error_message, err_info)

            return self._create_chat_completion_object(error_message, model, None, is_error=True)

    def _create_chat_completion_object(self, content: str, model: str, dash_response: Any, is_error: bool = False) -> Any:
        """创建一个模拟的 ChatCompletion 对象。"""
        # 这是一个简化的模拟，只包含 MarkItDown 需要的关键字段
        class MockMessage:
            def __init__(self, content):
                self.content = content

        class MockChoice:
            def __init__(self, content):
                self.message = MockMessage(content)

        class MockUsage:
            def __init__(self, usage_data):
                self.prompt_tokens = usage_data.get('input_tokens', 0) if usage_data else 0
                self.completion_tokens = usage_data.get('output_tokens', 0) if usage_data else 0
                self.total_tokens = self.prompt_tokens + self.completion_tokens

        usage_data = {}
        try:
            usage_data = getattr(dash_response, 'usage', {}) or {}
        except Exception:
            try:
                usage_data = dash_response.get('usage', {}) if isinstance(dash_response, dict) else {}
            except Exception:
                usage_data = {}

        class ChatCompletion:
            def __init__(self, content, usage):
                self.choices = [MockChoice(content)]
                self.usage = MockUsage(usage)
        
        return ChatCompletion(content, usage_data)


class _DashScopeClientFacade:
    """
    一个模拟 OpenAI Client 的外观类，将 chat.completions 的调用指向我们的包装器。
    """
    def __init__(self, api_key: str, model: str):
        self.chat = type("_Chat", (), {
            "completions": _DashScopeQwenOCRClient(api_key=api_key, model=model)
        })()


def build_markitdown_with_qwen(markdown_cls=None, *, model: Optional[str] = None, prompt: Optional[str] = None):
    """
    构建一个使用 Qwen-OCR (DashScope SDK) 作为 LLM 后端的 MarkItDown 实例。
    """
    from markitdown import MarkItDown as _MK
    MK = markdown_cls or _MK

    if dashscope is None:
        raise RuntimeError("dashscope 库未安装, 无法使用 qwen-ocr。请运行: pip install dashscope")

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise EnvironmentError("缺少 DASHSCOPE_API_KEY 环境变量")

    # Qwen-OCR 的模型名称
    _model = model or "qwen-vl-ocr-latest"
    _prompt = prompt or os.getenv("IMAGE_CAPTION_PROMPT") or DEFAULT_PROMPT
    
    # 创建我们的外观客户端
    client = _DashScopeClientFacade(api_key=api_key, model=_model)
    
    return MK(llm_client=client, llm_model=_model, llm_prompt=_prompt)

__all__ = ["build_markitdown_with_qwen"]