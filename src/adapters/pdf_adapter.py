import os
import pdfplumber
from src.adapters.base import BaseInputAdapter, RawPayload, register_adapter

@register_adapter(".pdf", "text")
class PDFAdapter(BaseInputAdapter):
    """
    Adapter to ingest unstructured Resume PDF files.
    Extracts text content from all pages.
    """
    def __init__(self, filepath: str):
        self.filepath = filepath

    def read(self) -> RawPayload:
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"PDF file not found: {self.filepath}")
        
        # Check for empty/zero-byte file
        if os.path.getsize(self.filepath) == 0:
            return RawPayload(
                source_name=os.path.basename(self.filepath),
                content_type="pdf",
                content=""
            )
            
        text_content = []
        try:
            with pdfplumber.open(self.filepath) as pdf:
                for page in pdf.pages:
                    try:
                        text = page.extract_text()
                        if text:
                            text_content.append(text)
                    except Exception:
                        # Skip corrupted pages
                        continue
        except Exception as exc:
            # Corrupted PDF — return empty content with a note
            return RawPayload(
                source_name=os.path.basename(self.filepath),
                content_type="pdf",
                content=f"[PDF extraction failed: {exc}]"
            )
                    
        full_text = "\n--- PAGE BREAK ---\n".join(text_content)
        
        # Warn if no text was extracted (likely a scanned image PDF)
        if not full_text.strip():
            full_text = "[No extractable text found — this may be a scanned image PDF]"
        
        return RawPayload(
            source_name=os.path.basename(self.filepath),
            content_type="pdf",
            content=full_text
        )
