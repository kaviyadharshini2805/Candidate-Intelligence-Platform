import sys
import os
sys.path.append(os.getcwd())
from src.analytics.pipeline_runner import PipelineRunner, SourceInput

try:
    sources = [
        SourceInput(name="notes.txt", content_type="txt", text="Location: Bengaluru, Karnataka, India")
    ]
    runner = PipelineRunner({"notes.txt": 30, "csv.csv": 20})
    result = runner.run(sources=sources, projection_config=None)
    print("Errors:", result.error)
    print("Warnings:", result.validation_errors)
    if result.canonical:
        c = result.canonical
        print("Name:", c.full_name)
        print("Emails:", c.emails)
        print("Phones:", c.phones)
        print("Location:", c.location)
        print("Education:", [e.institution for e in c.education])
    else:
        print("No golden record")
except Exception as e:
    print("Exception:", e)
