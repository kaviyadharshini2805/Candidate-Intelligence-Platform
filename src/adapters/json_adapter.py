import os
from src.adapters.base import BaseInputAdapter, RawPayload, register_adapter
from src.validators.json_validator import JSONValidator

@register_adapter(".json", "json")
class JSONAdapter(BaseInputAdapter):
    """
    Adapter to ingest ATS JSON profiles with validation checks.
    Reads JSON file, validates it, and returns the parsed payload.
    """
    def __init__(self, filepath: str):
        self.filepath = filepath

    def read(self) -> RawPayload:
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"JSON file not found: {self.filepath}")
        
        # Check for empty/zero-byte file
        if os.path.getsize(self.filepath) == 0:
            return RawPayload(
                source_name=os.path.basename(self.filepath),
                content_type="json",
                content={}
            )
            
        # Validate file syntax
        is_valid, err_msg, data = JSONValidator.validate_file(self.filepath)
        if not is_valid:
            raise ValueError(f"Malformed JSON: {err_msg}")
            
        return RawPayload(
            source_name=os.path.basename(self.filepath),
            content_type="json",
            content=data
        )
