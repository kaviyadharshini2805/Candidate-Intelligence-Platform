import sys, os
sys.path.insert(0, '.')
from src.analytics.pipeline_runner import PipelineRunner, SourceInput

def main():
    # Try empty
    runner = PipelineRunner()
    res = runner.run([
        SourceInput(name="notes1.txt", content_type="txt", text="Name: John"),
        SourceInput(name="notes2.txt", content_type="txt", text="Name: John\nEmail: a@b.com"),
    ])
    if res.error: print(f"Error: {res.error}")
    
    # Try with conflicting links where one is None
    res = runner.run([
        SourceInput(name="notes1.txt", content_type="txt", text="Name: John\nLinkedIn: https://linkedin.com/in/a"),
        SourceInput(name="notes2.txt", content_type="txt", text="Name: John\nEmail: a@b.com"),
    ])
    if res.error: print(f"Error: {res.error}")

    # Try with experience
    res = runner.run([
        SourceInput(name="notes1.txt", content_type="txt", text="Name: John\nExperience:\nGoogle - Eng\n"),
        SourceInput(name="notes2.txt", content_type="txt", text="Name: John\nExperience:\nMicrosoft - Eng\n"),
    ])
    if res.error: print(f"Error: {res.error}")
    
    print("Done fuzzing")

if __name__ == "__main__":
    main()
