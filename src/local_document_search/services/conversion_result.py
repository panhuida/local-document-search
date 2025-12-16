from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class ConversionResult:
    success: bool
    content: Optional[str]
    conversion_type: Optional[int]
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    file_path: Optional[str] = None
    file_type: Optional[str] = None

    def sanitized(self):  # convenience helper
        if self.content:
            self.content = self.content.replace('\x00', '')
        return self
