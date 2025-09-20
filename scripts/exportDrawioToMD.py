import zlib
import sys
import base64
import xml.etree.ElementTree as ET
from urllib.parse import unquote
import re

def decode_drawio_data(data_text):
    """
    尝试多种方式解码 draw.io 数据
    """
    if not data_text or not data_text.strip():
        return None
        
    try:
        # 方法1: 标准的 base64 + zlib 解压
        data = base64.b64decode(data_text)
        xml = zlib.decompress(data, wbits=-15)
        xml = xml.decode('utf-8')
        return unquote(xml)
    except:
        try:
            # 方法2: 尝试不同的 zlib 参数
            data = base64.b64decode(data_text)
            xml = zlib.decompress(data)
            xml = xml.decode('utf-8')
            return unquote(xml)
        except:
            try:
                # 方法3: 直接 base64 解码（无压缩）
                xml = base64.b64decode(data_text).decode('utf-8')
                return unquote(xml)
            except:
                try:
                    # 方法4: URL 解码后再尝试
                    xml = unquote(data_text)
                    return xml
                except:
                    # 方法5: 直接返回原始数据
                    return data_text

def clean_html_text(text):
    """清理 HTML 标签和实体"""
    if not text:
        return ""
    
    # 处理 HTML 实体
    text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    text = text.replace('&nbsp;', ' ').replace('&quot;', '"').replace('&#39;', "'")
    
    # 移除 HTML 标签，但保留内容
    text = re.sub(r'<[^>]+>', '', text)
    
    # 清理多余空格和换行
    text = ' '.join(text.split())
    
    return text.strip()

def process_diagram(diagram):
    """处理单个图表，返回文本内容列表"""
    diagram_name = diagram.get('name', '未命名图表')
    
    # 检查是否有嵌套的 mxGraphModel
    mxGraphModel = diagram.find('mxGraphModel')
    
    if mxGraphModel is not None:
        # 新格式：直接包含 mxGraphModel
        xml_root = mxGraphModel
    else:
        # 旧格式：需要解码 diagram 内容
        diagram_text = diagram.text
        if not diagram_text:
            return diagram_name, []
        
        # 解码数据
        xml_content = decode_drawio_data(diagram_text)
        if not xml_content:
            return diagram_name, []
        
        # 解析 XML
        try:
            xml = ET.fromstring(xml_content)
        except ET.ParseError as e:
            print(f"XML 解析错误 (图表: {diagram_name}): {e}")
            return diagram_name, []
        
        # 获取 mxGraphModel
        if xml.tag == 'mxGraphModel':
            xml_root = xml
        else:
            xml_root = xml.find('.//mxGraphModel')
            if xml_root is None:
                return diagram_name, []
    
    # 获取根单元格
    root_element = xml_root.find('root')
    if root_element is None:
        return diagram_name, []
    
    text_contents = []
    
    # 解析元素，简单列出所有文本内容
    for child in root_element:
        value = child.attrib.get('value', '')
        ID = child.attrib.get('id')
        
        # 跳过默认的根单元格
        if ID in ['0', '1']:
            continue
            
        # 处理有值的单元格
        if value and value.strip():
            cleaned_value = clean_html_text(value)
            if cleaned_value:
                text_contents.append(cleaned_value)
    
    return diagram_name, text_contents

if len(sys.argv) != 3:
    print("使用方法: python exportDrawioToMD.py <输入文件.drawio> <输出文件.md>")
    sys.exit(1)

inputPath = sys.argv[1]
outputPath = sys.argv[2]

try:
    tree = ET.parse(inputPath)
    root = tree.getroot()
    
    print(f"根元素: {root.tag}")
    
    # 查找所有 diagram 元素
    diagrams = root.findall('diagram')
    print(f"找到 {len(diagrams)} 个图表")
    
    if not diagrams:
        print("错误: 找不到 diagram 元素")
        sys.exit(1)
    
    # 处理所有图表
    all_results = []
    total_texts = 0
    
    for i, diagram in enumerate(diagrams, 1):
        print(f"\n处理第 {i} 个图表...")
        diagram_name, text_contents = process_diagram(diagram)
        all_results.append((diagram_name, text_contents))
        
        print(f"图表名称: {diagram_name}")
        print(f"找到 {len(text_contents)} 个文本内容")
        
        for j, text in enumerate(text_contents, 1):
            print(f"  {j}. {text[:50]}{'...' if len(text) > 50 else ''}")
        
        total_texts += len(text_contents)
    
    # 写入输出文件
    with open(outputPath, 'w', encoding="utf-8") as file:
        file.write(f"# Draw.io 文件内容\n\n")
        file.write(f"总共 {len(diagrams)} 个页面，{total_texts} 个文本项目\n\n")
        file.write("---\n\n")
        
        for diagram_name, text_contents in all_results:
            file.write(f"## {diagram_name}\n\n")
            
            if text_contents:
                for text in text_contents:
                    file.write(f"- {text}\n")
            else:
                file.write("*此页面没有找到文本内容*\n")
            
            file.write("\n")

    print(f"\n转换完成！输出文件: {outputPath}")
    print(f"共处理了 {len(diagrams)} 个页面，{total_texts} 个文本项目")

except FileNotFoundError:
    print(f"错误: 找不到输入文件 {inputPath}")
except Exception as e:
    print(f"发生错误: {e}")
    import traceback
    traceback.print_exc()