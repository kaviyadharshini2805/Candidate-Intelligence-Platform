import csv
import os
from typing import List, Dict
from src.adapters.base import BaseInputAdapter, RawPayload, register_adapter

@register_adapter(".csv", "structured")
class CSVAdapter(BaseInputAdapter):
    """
    Adapter to ingest Recruiter CSV exports.
    Reads CSV rows and returns a list of records.
    """
    def __init__(self, filepath: str):
        self.filepath = filepath

    def read(self) -> RawPayload:
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"CSV file not found: {self.filepath}")
        
        # Check for empty/zero-byte file
        if os.path.getsize(self.filepath) == 0:
            return RawPayload(
                source_name=os.path.basename(self.filepath),
                content_type="csv",
                content=[]
            )
            
        records: List[Dict[str, str]] = []
        # Try multiple encodings to handle non-UTF8 files
        for encoding in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
            try:
                with open(self.filepath, mode='r', encoding=encoding, errors='replace') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        records.append(dict(row))
                break  # Success
            except (UnicodeDecodeError, csv.Error):
                records = []
                continue
                
        return RawPayload(
            source_name=os.path.basename(self.filepath),
            content_type="csv",
            content=records
        )
