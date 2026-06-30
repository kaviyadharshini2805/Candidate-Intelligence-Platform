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
    
    pdf_path = None
    for root, dirs, files in os.walk('E:\\Projects\\Resume Parser'):
        for f in files:
            if 'KAVIYADHARSHINI' in f.upper():
                pdf_path = os.path.join(root, f)
                break
        if pdf_path: break

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
    
    # Let's mock a change in pipeline_runner to print
    with open('src/analytics/pipeline_runner.py', 'r') as f:
        content = f.read()
    
    if "print(f'Golden records before sort:" not in content:
        content = content.replace(
            "golden_records.sort(key=lambda x: x[1], reverse=True)",
            "print(f'Golden records before sort: {[(r[0].full_name.value, r[1]) for r in golden_records]}')\n            golden_records.sort(key=lambda x: x[1], reverse=True)"
        )
        with open('src/analytics/pipeline_runner.py', 'w') as f:
            f.write(content)

    runner = PipelineRunner(source_priorities=priorities)
    result = runner.run(sources=sources)
    
    print(f"Golden Record Candidate: {result.canonical.full_name}")

if __name__ == "__main__":
    main()
