import os
import win32com.client as win32
from win32com.client import constants
from flask import current_app
from pathlib import Path
import pythoncom

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

    try:
        # 在多线程环境下需要初始化COM库
        pythoncom.CoInitialize()

        # 启动 PowerPoint 应用程序，并确保它在后台运行
        powerpoint = win32.gencache.EnsureDispatch('PowerPoint.Application')

        # 打开演示文稿，ReadOnly=False 确保可以保存
        presentation = powerpoint.Presentations.Open(str(ppt_path_obj), ReadOnly=False)

        # 保存为 .pptx 格式，使用正确的常量
        # constants.ppSaveAsOpenXMLPresentation 才是 .pptx 格式
        presentation.SaveAs(str(pptx_path_obj), FileFormat=constants.ppSaveAsOpenXMLPresentation)
        
        current_app.logger.info(f"Successfully converted {pptx_path_obj} to {pptx_path_obj}")
        return str(pptx_path_obj)
    
    except Exception as e:
        current_app.logger.error(f"Failed to convert {pptx_path_obj} to .pptx: {e}", exc_info=True)
        return None
    
    finally:
        # 确保演示文稿和应用被正确关闭
        if presentation:
            presentation.Close()
        if powerpoint:
            powerpoint.Quit()
        
        # 在多线程环境下，确保在函数退出时取消初始化COM库
        pythoncom.CoUninitialize()
