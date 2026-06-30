import sys
import os
sys.path.append(os.getcwd())
from src.parser.text_parser import TextParser
from src.adapters.base import RawPayload

parser = TextParser()

texts = [
    """
Indian Institute of Technology Delhi
Bachelor of Technology — Computer Science and Engineering
Location: Bengaluru, Karnataka, India
    """
]

for t in texts:
    payload = RawPayload(source_name="test.txt", content_type="txt", content=t)
    result = parser.parse(payload)
    print(f"Text: '{t}'\nLocation extracted: {result.get('location')}\n")
