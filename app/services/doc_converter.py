import os
import shutil
import subprocess
import sys
from flask import current_app
from pathlib import Path

# Try to import Windows COM automation (pywin32). If not available (e.g., on Linux),
# we'll fall back to using LibreOffice (soffice) in headless mode for conversions.
_has_win32 = False
try:
    if sys.platform == 'win32':
        import win32com.client as win32  # type: ignore
        from win32com.client import constants  # type: ignore
        _has_win32 = True
except Exception:
    _has_win32 = False

def convert_doc_to_docx(doc_path: str) -> str | None:
    """
    使用 Microsoft Word 的 COM 接口将 .doc 转换为 .docx。

    Args:
        doc_path: 待转换的 .doc 文件的路径。

    Returns:
        转换后的 .docx 文件路径，如果转换失败则返回 None。
    """
    word = None
    doc = None
    doc_path_obj = Path(doc_path).resolve()
    docx_path_obj = doc_path_obj.with_suffix('.docx')

    # 如果 .docx 文件已存在，则直接返回
    if docx_path_obj.exists():
        current_app.logger.info(f"Skipping conversion for {doc_path_obj} as {docx_path_obj} already exists.")
        return str(docx_path_obj)

    # If running on Windows and pywin32 is available, use COM automation.
    if _has_win32:
        try:
            word = win32.gencache.EnsureDispatch('Word.Application')
            word.Visible = False

            doc = word.Documents.Open(str(doc_path_obj))
            doc.SaveAs(str(docx_path_obj), FileFormat=constants.wdFormatXMLDocument)
            current_app.logger.info(f"Successfully converted {doc_path_obj} to {docx_path_obj} via Word COM")
            return str(docx_path_obj)
        except Exception as e:
            current_app.logger.error(f"Failed to convert {doc_path_obj} to .docx using Word COM: {e}", exc_info=True)
            return None
        finally:
            if doc:
                try:
                    doc.Close(False)
                except Exception:
                    pass
            if word:
                try:
                    word.Quit()
                except Exception:
                    pass

    # Fallback: use LibreOffice (soffice) in headless mode to convert .doc -> .docx
    # soffice must be installed on Linux (package: libreoffice-core / libreoffice-common / libreoffice-writer)
    soffice_path = shutil.which('soffice') or shutil.which('libreoffice')
    if not soffice_path:
        current_app.logger.error("LibreOffice (soffice) not found on PATH; cannot convert .doc to .docx on this platform.")
        return None

    try:
        # Use --headless --convert-to docx to perform conversion and place output in the same directory
        subprocess.check_call([
            soffice_path,
            '--headless',
            '--convert-to', 'docx:MS Word 2007 XML',
            '--outdir', str(doc_path_obj.parent),
            str(doc_path_obj)
        ])
        if docx_path_obj.exists():
            current_app.logger.info(f"Successfully converted {doc_path_obj} to {docx_path_obj} via LibreOffice")
            return str(docx_path_obj)
        else:
            current_app.logger.error(f"LibreOffice conversion completed but output file not found: {docx_path_obj}")
            return None
    except subprocess.CalledProcessError as e:
        current_app.logger.error(f"LibreOffice conversion failed for {doc_path_obj}: {e}", exc_info=True)
        return None
