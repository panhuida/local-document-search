"""显示当前 MarkItDown / Gemini 适配下实际生效的图片描述提示词。

优先级（从高到低）：
1. 运行时显式参数 (--prompt)
2. 构建实例时传入的 llm_prompt (build_markitdown_with_gemini(prompt=...))
3. 环境变量 GEMINI_PROMPT
4. 环境变量 GEMINI_IMAGE_PROMPT
5. MarkItDown 内部默认："Write a detailed caption for this image."

功能：
- 列出所有来源的值及最终决策
- 可选 --prompt <text> 查看如果显式覆盖会是什么结果
- 可选 --simulate <image_path> 真实调用一次并输出使用的 prompt（不会缓存 prompt，只打印）
  * simulate 时若指定 --dry-run，则不真正调用 LLM，只展示将要使用的 prompt

用法：
    python scripts/show_effective_prompt.py
    python scripts/show_effective_prompt.py --prompt "用中文生成技术描述" 
    python scripts/show_effective_prompt.py --simulate sample.jpg
    python scripts/show_effective_prompt.py --simulate sample.jpg --prompt "覆盖"

注意：
- simulate 依赖 GEMINI_API_KEY；若未设置则提示跳过
- 不会修改现有任何缓存
"""
from __future__ import annotations
import os
import sys
import argparse
from dataclasses import dataclass
from typing import Optional

DEFAULT_MARKITDOWN_PROMPT = "Write a detailed caption for this image."

@dataclass
class PromptSources:
    cli_prompt: Optional[str]
    instance_prompt: Optional[str]
    env_gemini_prompt: Optional[str]
    env_gemini_image_prompt: Optional[str]
    default_prompt: str = DEFAULT_MARKITDOWN_PROMPT

    def effective(self) -> str:
        return (
            self.cli_prompt
            or self.instance_prompt
            or self.env_gemini_prompt
            or self.env_gemini_image_prompt
            or self.default_prompt
        )


def build_markitdown_instance() -> tuple[object, Optional[str]]:
    """构建当前项目中的 MarkItDown 实例，并返回 (实例, 构建时传入的 prompt)
    由于我们在 converters 中使用 build_markitdown_with_gemini()，这里复用逻辑。
    若未配置 GEMINI_API_KEY，将返回无 llm 的实例，instance_prompt = None。
    """
    try:
        from app.services.gemini_adapter import build_markitdown_with_gemini
    except Exception:
        # 回退基础 MarkItDown
        from markitdown import MarkItDown
        return MarkItDown(), None

    # 不强行传 prompt，这样能看到实例层是否已有默认注入
    md = build_markitdown_with_gemini()
    # build_markitdown_with_gemini 内部无法直接取出 llm_prompt；这里反射访问（内部属性名）
    instance_prompt = getattr(md, "_llm_prompt", None)
    return md, instance_prompt


def print_sources(src: PromptSources):
    print("=== Prompt Sources ===")
    print(f"CLI --prompt: {repr(src.cli_prompt)}")
    print(f"Instance llm_prompt: {repr(src.instance_prompt)}")
    print(f"Env GEMINI_PROMPT: {repr(src.env_gemini_prompt)}")
    print(f"Env GEMINI_IMAGE_PROMPT: {repr(src.env_gemini_image_prompt)}")
    print(f"Default: {repr(src.default_prompt)}")
    print("----------------------")
    print(f"Effective Prompt => {repr(src.effective())}")


def simulate_generation(md, prompt: str, image_path: str, dry_run: bool):
    if not os.path.exists(image_path):
        print(f"[simulate] 文件不存在: {image_path}", file=sys.stderr)
        return
    if dry_run:
        print(f"[simulate] (dry-run) 将使用 prompt: {prompt}")
        return
    # 为确保使用的是我们期望的 prompt，可以在转换调用时显式传
    try:
        with open(image_path, 'rb') as f:
            result = md.convert(f, llm_prompt=prompt)
        print("=== Simulated Markdown (截断 400 字) ===")
        out = (result.text_content or '').strip()
        if len(out) > 400:
            out = out[:400] + '... (truncated)'
        print(out)
    except Exception as e:
        print(f"[simulate] 生成失败: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="显示当前有效图片描述 Prompt")
    parser.add_argument("--prompt", help="模拟显式传入 prompt 覆盖其它来源")
    parser.add_argument("--simulate", help="提供图片路径以真实调用一次")
    parser.add_argument("--dry-run", action="store_true", help="与 --simulate 一起使用，只展示将用的 prompt 不调用 LLM")
    args = parser.parse_args()

    md, instance_prompt = build_markitdown_instance()

    env_prompt = os.getenv("GEMINI_PROMPT")
    env_image_prompt = os.getenv("GEMINI_IMAGE_PROMPT")

    sources = PromptSources(
        cli_prompt=args.prompt,
        instance_prompt=instance_prompt,
        env_gemini_prompt=env_prompt,
        env_gemini_image_prompt=env_image_prompt,
    )

    print_sources(sources)

    if args.simulate:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("[simulate] 未设置 GEMINI_API_KEY，无法真正调用，多模态描述将不会生成。", file=sys.stderr)
        simulate_generation(md, sources.effective(), args.simulate, args.dry_run)


if __name__ == "__main__":
    main()
