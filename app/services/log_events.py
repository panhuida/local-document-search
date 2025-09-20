from enum import Enum


class LogEvent(str, Enum):
    SCAN_START = "scan_start"
    SCAN_COMPLETE = "scan_complete"
    FILE_PROCESSING = "file_processing"
    FILE_SKIP = "file_skip"
    FILE_SUCCESS = "file_success"
    FILE_ERROR = "file_error"
    CANCEL_ACK = "cancel_ack"  # 新增：收到取消请求立即反馈（早于正式cancelled终止事件）
    CANCELLED = "cancelled"
    DONE = "done"
    CRITICAL_ERROR = "critical_error"

    @classmethod
    def list(cls):  # pragma: no cover
        return [e.value for e in cls]
