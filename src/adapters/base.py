from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any

class RawPayload(BaseModel):
    source_name: str
    content_type: str  # 'csv', 'json', 'pdf', 'docx', 'txt'
    content: Any       # Can be raw bytes, string, or pre-parsed collections
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class BaseInputAdapter(ABC):
    """
    Abstract Base Class for all Ingestion Adapters.
    Decouples source-specific details (I/O, file reading, API queries)
    from core parsing and transformation logic.
    """
    @abstractmethod
    def read(self) -> RawPayload:
        """
        Reads data from the source and wraps it in a standard RawPayload envelope.
        """
        pass

# The global adapter registry maps extensions to (AdapterClass, ParserName)
ADAPTER_REGISTRY = {}

def register_adapter(extension: str, parser_name: str):
    """
    Decorator to dynamically register concrete adapters.
    """
    def decorator(cls):
        ADAPTER_REGISTRY[extension.lower()] = (cls, parser_name)
        return cls
    return decorator
