from typing import Callable, Dict, List
from .conversion_result import ConversionResult

# type alias: handler(file_path: str, file_type: str) -> ConversionResult
Handler = Callable[[str, str], ConversionResult]

_CONVERTER_REGISTRY: Dict[str, Handler] = {}

def register(exts: List[str]):
    def decorator(fn: Handler):
        for e in exts:
            _CONVERTER_REGISTRY[e.lower()] = fn
        return fn
    return decorator

def get_handler(ext: str) -> Handler | None:
    return _CONVERTER_REGISTRY.get(ext.lower())

def list_registered():
    return sorted(_CONVERTER_REGISTRY.keys())
