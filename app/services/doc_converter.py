import os
import win32com.client as win32
from win32com.client import constants
from flask import current_app
from pathlib import Path

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

    try:
        # 启动 Word 应用程序
        word = win32.gencache.EnsureDispatch('Word.Application')
        word.Visible = False

        # 打开文档
        doc = word.Documents.Open(str(doc_path_obj))

        # 保存为 .docx 格式
        doc.SaveAs(str(docx_path_obj), FileFormat=constants.wdFormatXMLDocument)
        
        current_app.logger.info(f"Successfully converted {doc_path_obj} to {docx_path_obj}")
        return str(docx_path_obj)
    
    except Exception as e:
        # 记录详细的错误信息
        current_app.logger.error(f"Failed to convert {doc_path_obj} to .docx: {e}", exc_info=True)
        return None
    
    finally:
        # 确保文档和应用被正确关闭
        if doc:
            doc.Close(False)
        if word:
            word.Quit()
