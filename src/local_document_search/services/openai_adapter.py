"""OpenAI 适配器：提供与 MarkItDown 一致的多模态 caption 支持。

当配置 IMAGE_CAPTION_PROVIDER=openai 时使用。
依赖：openai 官方库 (假定已安装)。
环境变量：
  OPENAI_API_KEY  (必需)
  OPENAI_IMAGE_MODEL  (可选，默认 gpt-4o-mini)
  IMAGE_CAPTION_PROMPT (可选，覆盖默认)
"""
from __future__ import annotations
import os
from typing import Optional

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

DEFAULT_PROMPT = "Write a detailed caption for this image."


def build_markitdown_with_openai(markdown_cls=None, *, model: Optional[str] = None, prompt: Optional[str] = None):
    from markitdown import MarkItDown as _MK
    MK = markdown_cls or _MK

    if OpenAI is None:
        raise RuntimeError("openai 库未安装，无法使用 openai 提供的图像描述。")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("缺少 OPENAI_API_KEY 环境变量")

    client = OpenAI(api_key=api_key)
    _model = model or os.getenv("OPENAI_IMAGE_MODEL", "gpt-4o-mini")
    _prompt = prompt or os.getenv("IMAGE_CAPTION_PROMPT") or DEFAULT_PROMPT
    return MK(llm_client=client, llm_model=_model, llm_prompt=_prompt)

__all__ = ["build_markitdown_with_openai"]
