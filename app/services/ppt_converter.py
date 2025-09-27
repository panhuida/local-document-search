import os
import shutil
import subprocess
import sys
from flask import current_app
from pathlib import Path

# Try to import win32com when on Windows; otherwise fallback to LibreOffice headless (soffice)
_has_win32 = False
try:
    if sys.platform == 'win32':
        import win32com.client as win32  # type: ignore
        from win32com.client import constants  # type: ignore
        import pythoncom  # type: ignore
        _has_win32 = True
except Exception:
    _has_win32 = False

def convert_ppt_to_pptx(ppt_path: str) -> str | None:
    """
    使用 Microsoft PowerPoint 的 COM 接口将 .ppt 转换为 .pptx。

    Args:
        ppt_path: 待转换的 .ppt 文件的路径。

    Returns:
        转换后的 .pptx 文件路径，如果转换失败则返回 None。
    """
    powerpoint = None
    presentation = None
    
    ppt_path_obj = Path(ppt_path).resolve()
    pptx_path_obj = ppt_path_obj.with_suffix('.pptx')

    # 如果 .pptx 文件已存在，则直接返回
    if pptx_path_obj.exists():
        current_app.logger.info(f"Skipping conversion for {pptx_path_obj} as {pptx_path_obj} already exists.")
        return str(pptx_path_obj)

    # Prefer Windows COM automation when available
    if _has_win32:
        try:
            pythoncom.CoInitialize()
            powerpoint = win32.gencache.EnsureDispatch('PowerPoint.Application')
            presentation = powerpoint.Presentations.Open(str(ppt_path_obj), ReadOnly=False)
            presentation.SaveAs(str(pptx_path_obj), FileFormat=constants.ppSaveAsOpenXMLPresentation)
            current_app.logger.info(f"Successfully converted {ppt_path_obj} to {pptx_path_obj} via PowerPoint COM")
            return str(pptx_path_obj)
        except Exception as e:
            current_app.logger.error(f"Failed to convert {ppt_path_obj} to .pptx using PowerPoint COM: {e}", exc_info=True)
            return None
        finally:
            try:
                if presentation:
                    presentation.Close()
            except Exception:
                pass
            try:
                if powerpoint:
                    powerpoint.Quit()
            except Exception:
                pass
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

    # Fallback to LibreOffice (soffice) headless conversion on non-Windows platforms
    soffice_path = shutil.which('soffice') or shutil.which('libreoffice')
    if not soffice_path:
        current_app.logger.error("LibreOffice (soffice) not found on PATH; cannot convert .ppt to .pptx on this platform.")
        return None
    try:
        subprocess.check_call([
            soffice_path,
            '--headless',
            '--convert-to', 'pptx:MS PowerPoint 2007 XML',
            '--outdir', str(ppt_path_obj.parent),
            str(ppt_path_obj)
        ])
        if pptx_path_obj.exists():
            current_app.logger.info(f"Successfully converted {ppt_path_obj} to {pptx_path_obj} via LibreOffice")
            return str(pptx_path_obj)
        else:
            current_app.logger.error(f"LibreOffice conversion completed but output file not found: {pptx_path_obj}")
            return None
    except subprocess.CalledProcessError as e:
        current_app.logger.error(f"LibreOffice conversion failed for {ppt_path_obj}: {e}", exc_info=True)
        return None
