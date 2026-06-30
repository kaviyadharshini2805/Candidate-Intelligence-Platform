import sys, io, csv, json, os
sys.path.insert(0, '.')
from src.analytics.pipeline_runner import PipelineRunner, SourceInput

def main():
    notes_text = """
    Name: John Doe
    Email: john.doe@example.com
    Phone: +1 555-1234
    Skills: Java, Spring Boot, MySQL
    """
    
    # We will mock the PDF content for speed, passing it as a text source but naming it like the PDF
    # Actually, we can just use the real PDF and pass completely different notes.
    pdf_path = None
    for root, dirs, files in os.walk('E:\\Projects\\Resume Parser'):
        for f in files:
            if 'KAVIYADHARSHINI' in f.upper():
                pdf_path = os.path.join(root, f)
                break
        if pdf_path: break
    
    if not pdf_path:
        print("PDF not found!")
        return

    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()

    sources = [
        SourceInput(name="recruiter_notes.txt", content_type="txt", text=notes_text),
        SourceInput(name=os.path.basename(pdf_path), content_type="pdf", raw_bytes=pdf_bytes)
    ]
    
    priorities = {
        "recruiter_notes.txt": 30,
        os.path.basename(pdf_path): 50
    }
    
    runner = PipelineRunner(source_priorities=priorities)
    result = runner.run(sources=sources)
    
    print(f"Golden Record Candidate: {result.canonical.full_name}")
    print(f"Sources Merged: {result.pipeline_stats.records_parsed}")

if __name__ == "__main__":
    main()
