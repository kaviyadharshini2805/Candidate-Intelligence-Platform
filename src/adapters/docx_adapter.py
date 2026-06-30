import os
import docx
from src.adapters.base import BaseInputAdapter, RawPayload, register_adapter

@register_adapter(".docx", "text")
class DocxAdapter(BaseInputAdapter):
    """
    Adapter to ingest unstructured Resume DOCX files.
    Extracts text paragraphs from Word document.
    """
    def __init__(self, filepath: str):
        self.filepath = filepath

    def read(self) -> RawPayload:
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"DOCX file not found: {self.filepath}")
        
        # Check for empty/zero-byte file
        if os.path.getsize(self.filepath) == 0:
            return RawPayload(
                source_name=os.path.basename(self.filepath),
                content_type="docx",
                content=""
            )
            
        try:
            doc = docx.Document(self.filepath)
            text_content = []
            for paragraph in doc.paragraphs:
                if paragraph.text:
                    text_content.append(paragraph.text)
                    
            full_text = "\n".join(text_content)
        except Exception as exc:
            # Corrupted DOCX
            return RawPayload(
                source_name=os.path.basename(self.filepath),
                content_type="docx",
                content=f"[DOCX extraction failed: {exc}]"
            )
        
        return RawPayload(
            source_name=os.path.basename(self.filepath),
            content_type="docx",
            content=full_text
        )
