"""Image conversion logic (local OCR + EXIF front matter OR LLM caption) extracted from converters.

Public function:
    convert_image_to_markdown(file_path: str) -> tuple[str, ConversionType|None]
"""
import os
from flask import current_app
from local_document_search.models import ConversionType
from .provider_factory import get_markitdown_instance

def _build_image_front_matter(file_path: str, sha256_hash, file_stats, exif_data, ocr_lang):
    import datetime
    front_matter = {
        'source_file': os.path.basename(file_path),
        'provider': 'local-ocr',
        'hash_sha256': sha256_hash,
        'file_size': file_stats.st_size if file_stats else None,
        'modified_time': datetime.datetime.fromtimestamp(file_stats.st_mtime).isoformat() if file_stats else None,
        'exif': exif_data or {},
        'ocr_lang': ocr_lang,
    }
    def _yaml_dump(d, indent=0):
        lines = []
        for k, v in d.items():
            if isinstance(v, dict):
                lines.append(' ' * indent + f"{k}:")
                for sk, sv in v.items():
                    lines.append(' ' * (indent + 2) + f"{sk}: {sv}")
            else:
                lines.append(' ' * indent + f"{k}: {v}")
        return '\n'.join(lines)
    return _yaml_dump(front_matter)

def _local_ocr_convert(file_path: str):
    try:
        from PIL import Image, ExifTags
        import pytesseract
    except Exception as ie:
        return f"Local OCR dependencies missing (Pillow / pytesseract): {ie}", None

    exif_data = {}
    file_stats = None
    sha256_hash = None

    try:
        file_stats = os.stat(file_path)
        import hashlib
        with open(file_path, 'rb') as bf:
            img_bytes = bf.read()
        sha256_hash = hashlib.sha256(img_bytes).hexdigest()
    except Exception as meta_e:  # pragma: no cover - logging side effect only
        current_app.logger.warning(f"Failed to compute file metadata for {file_path}: {meta_e}")

    text_blocks = []
    with Image.open(file_path) as img:
        # Extract EXIF
        try:
            raw_exif = img._getexif() if hasattr(img, '_getexif') else None
            if raw_exif:
                tag_map = {}
                for tag_id, val in raw_exif.items():
                    tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                    tag_map[tag_name] = val
                def _safe(v):
                    if isinstance(v, bytes):
                        if len(v) <= 32:
                            try:
                                return v.decode('utf-8', 'ignore')
                            except Exception:
                                return v.hex()[:64]
                        return f"bytes[{len(v)}]"
                    if isinstance(v, (list, tuple)):
                        return [str(x) for x in v[:20]]
                    return v
                wanted_keys = [
                    'DateTimeOriginal','DateTime','Model','Make','LensModel','FNumber','ExposureTime','ISOSpeedRatings',
                    'FocalLength','Orientation','Software','GPSInfo'
                ]
                for k in wanted_keys:
                    if k in tag_map:
                        exif_data[k] = _safe(tag_map[k])
        except Exception as exif_e:  # pragma: no cover
            current_app.logger.info(f"No EXIF data extracted for {file_path}: {exif_e}")

        # OCR
        lang = current_app.config.get('TESSERACT_LANG', 'eng')
        try:
            import pytesseract
            ocr_text = pytesseract.image_to_string(img, lang=lang)
        except Exception as ocr_e:
            return f"Tesseract OCR failed for {file_path}: {ocr_e}", None
        if ocr_text and ocr_text.strip():
            text_blocks.append(ocr_text.strip())

        # Dimensions
        try:
            exif_data['Width'] = img.width
            exif_data['Height'] = img.height
            exif_data['Mode'] = img.mode
            exif_data['Format'] = img.format
        except Exception:  # pragma: no cover
            pass

    enable_front_matter = current_app.config.get('ENABLE_IMAGE_FRONT_MATTER', True)
    md_parts = []
    if enable_front_matter:
        yaml_block = _build_image_front_matter(file_path, sha256_hash, file_stats, exif_data, current_app.config.get('TESSERACT_LANG', 'eng'))
        md_parts.extend(['---', yaml_block, '---'])
    md_parts.append(f"# {os.path.basename(file_path)}")
    if text_blocks:
        md_parts.append('\n'.join(text_blocks))
    content = '\n\n'.join(md_parts) + '\n'
    return content, ConversionType.IMAGE_TO_MD

def _llm_image_convert(file_path: str, provider: str):
    md_instance = get_markitdown_instance(provider)
    convert_kwargs = {}
    prompt_env = os.getenv('IMAGE_CAPTION_PROMPT') or os.getenv('GEMINI_PROMPT') or os.getenv('GEMINI_IMAGE_PROMPT')
    if prompt_env:
        convert_kwargs['llm_prompt'] = prompt_env
    # Read bytes and normalize image format if needed (some providers/MarkItDown converters
    # may not accept WEBP streams). Convert WEBP to PNG in-memory and pass a BytesIO with
    # a .name attribute to help downstream detect type.
    from io import BytesIO
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        try:
            from PIL import Image
            buf = BytesIO(data)
            img = Image.open(buf)
            fmt = (img.format or '').upper()
            # If WEBP (or other non-standard formats), convert to PNG bytes
            if fmt == 'WEBP':
                out = BytesIO()
                img.save(out, format='PNG')
                out.seek(0)
                # Give a filename hint (some converters inspect file.name)
                setattr(out, 'name', os.path.basename(file_path) + '.png')
                result = md_instance.convert(out, **convert_kwargs)
            else:
                # restore buffer and pass original bytes
                buf.seek(0)
                setattr(buf, 'name', os.path.basename(file_path))
                result = md_instance.convert(buf, **convert_kwargs)
        except Exception as img_exc:
            # If we cannot inspect/convert via PIL, log and fallback to passing raw file
            current_app.logger.exception("Image format handling failed for %s; falling back to raw bytes: %s", file_path, img_exc)
            from io import BytesIO as _BytesIO
            fb = _BytesIO(data)
            setattr(fb, 'name', os.path.basename(file_path))
            result = md_instance.convert(fb, **convert_kwargs)
    except Exception as e:
        # If reading or conversion failed, re-raise to be handled by provider fallback logic
        current_app.logger.exception("Failed to prepare image stream for LLM convert for %s: %s", file_path, e)
        raise
    if not result.text_content or not result.text_content.strip():
        current_app.logger.warning(f"Image conversion for {file_path} resulted in empty content.")
        return f"# {os.path.basename(file_path)}\n\n", ConversionType.IMAGE_TO_MD
    return result.text_content, ConversionType.IMAGE_TO_MD

def convert_image_to_markdown(file_path: str):
    if not current_app.config.get('ENABLE_IMAGE_DESCRIPTION', False):
        current_app.logger.info(f"Image description is disabled. Skipping content extraction for {os.path.basename(file_path)}.")
        return f"# {os.path.basename(file_path)}\n", ConversionType.IMAGE_TO_MD

    primary = current_app.config.get('IMAGE_CAPTION_PROVIDER', 'google-genai').lower()
    chain = current_app.config.get('IMAGE_PROVIDER_CHAIN', []) or []
    # 若链为空，只尝试 primary
    providers = chain if chain else [primary]
    # 确保 primary 在链首（避免用户 chain 不含 primary）
    if primary not in providers:
        providers = [primary] + providers
    tried_errors = []
    for idx, provider in enumerate(providers, start=1):
        try:
            if provider == 'local':
                current_app.logger.info(f"[ProviderFallback] attempt={idx} provider=local mode=ocr file={os.path.basename(file_path)}")
                return _local_ocr_convert(file_path)
            current_app.logger.info(f"[ProviderFallback] attempt={idx} provider={provider} mode=llm file={os.path.basename(file_path)}")
            return _llm_image_convert(file_path, provider)
        except Exception as e:  # pragma: no cover
            err_msg = f"provider={provider} error={e}"
            tried_errors.append(err_msg)
            current_app.logger.warning(f"[ProviderFallback] failed attempt={idx} {err_msg}")
            continue
    # 全部失败 -> 返回聚合错误
    aggregate = '; '.join(tried_errors) if tried_errors else 'no providers attempted'
    current_app.logger.error(f"[ProviderFallback] all_failed file={os.path.basename(file_path)} errors={aggregate}")
    return f"Image OCR/caption extraction failed: {aggregate}", None

