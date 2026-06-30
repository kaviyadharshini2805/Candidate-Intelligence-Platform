import sys
import os
sys.path.append(os.getcwd())
from src.parser.text_parser import TextParser

parser = TextParser()
text = """
EDUCATION
Bachelor of Engineering in Mechatronics
09/2023 – 04/2027
"""
from src.adapters.base import RawPayload
data = parser.parse(RawPayload(source_name="test.pdf", content_type="pdf", content=text))
print("Education extracted:", data.get('education'))

text2 = """
EDUCATION
B.E. Computer Science and Engineering
2023 - Present
"""
data2 = parser.parse(RawPayload(source_name="test2.pdf", content_type="pdf", content=text2))
print("Education extracted 2:", data2.get('education'))
