import os
from src.adapters.base import BaseInputAdapter, RawPayload, register_adapter

@register_adapter(".txt", "text")
class NotesAdapter(BaseInputAdapter):
    """
    Adapter to ingest Recruiter Notes and TXT files.
    Reads TXT contents as plain text.
    """
    def __init__(self, filepath: str):
        self.filepath = filepath

    def read(self) -> RawPayload:
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"TXT file not found: {self.filepath}")
            
        with open(self.filepath, mode='r', encoding='utf-8') as f:
            text = f.read()
            
        return RawPayload(
            source_name=os.path.basename(self.filepath),
            content_type="txt",
            content=text
        )
