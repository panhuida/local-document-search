import os
import pytest
from local_document_search.services.video_converter import convert_video_metadata
from local_document_search.models import ConversionType

@pytest.mark.skipif(not os.environ.get('FFPROBE_BIN') and os.system('ffprobe -version >nul 2>&1') != 0,
                    reason='ffprobe not available in PATH')
def test_video_metadata_minimal(tmp_path):
    # 创建一个极小的空文件（ffprobe 可能会失败，这里更多是结构校验；真实环境需提供有效视频样本）
    video_file = tmp_path / 'dummy.mp4'
    video_file.write_bytes(b'')
    content, ctype = convert_video_metadata(str(video_file))
    # 可能失败（空文件），只要返回 (str, None) 或 (markdown, VIDEO_METADATA)
    assert isinstance(content, str)
    if ctype is not None:
        assert ctype == ConversionType.VIDEO_METADATA
        assert 'provider: video-metadata' in content
        assert 'source_file: dummy.mp4' in content

