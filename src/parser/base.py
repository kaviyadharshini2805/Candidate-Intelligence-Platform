from abc import ABC, abstractmethod
from typing import Dict, Any
from src.adapters.base import RawPayload

class BaseParser(ABC):
    """
    Abstract Base Class for all Ingestion Parsers.
    Parsers are responsible for extracting attributes from the standard RawPayload structure.
    Note: Parsers output a raw, un-normalized dict of values. Standardizing and validating
    occurs in the Normalization layer.
    """
    @abstractmethod
    def parse(self, payload: RawPayload) -> Dict[str, Any]:
        """
        Parses the payload and returns a dictionary of extracted fields.
        """
        pass
