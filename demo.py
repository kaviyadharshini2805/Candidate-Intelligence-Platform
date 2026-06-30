import os
import json
import subprocess
import sys

def run_demo():
    print("====================================================")
    # 1. Create directory structure if needed
    os.makedirs("sample_data", exist_ok=True)
    os.makedirs("output", exist_ok=True)

    # 2. Write sample recruiter CSV export
    csv_path = "sample_data/recruiter_export.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("name,email,phone,current_company,title\n")
        f.write("Kaviyadharshini M,kaviyadharshini.works@gmail.com,1234567890,Google,Software Intern\n")
    print(f"Created sample structured CSV: {csv_path}")

    # 3. Write sample recruiter notes (unstructured text)
    notes_path = "sample_data/recruiter_notes.txt"
    with open(notes_path, "w", encoding="utf-8") as f:
        f.write("Candidate Name: Kaviyadharshini M\n")
        f.write("Contact: kaviyadharshini.works@gmail.com\n")
        f.write("GitHub: https://github.com/kaviyadharshini2805\n")
        f.write("LinkedIn: https://linkedin.com/in/kaviyadharshini-m\n")
        f.write("Headline: Aspiring Data Scientist and AI Engineer. Passionate about LLMs and system architectures.\n")
        f.write("Skills learned: Python, Java, SQL, Machine Learning, TensorFlow, AWS, FastAPI, Pytest\n")
        f.write("Work History:\n")
        f.write("Google - Software Intern | Jan 2026 - Present\n")
        f.write("Working on deep learning systems and pot-hole verification pipelines using YOLOv8.\n")
        f.write("\n")
        f.write("Education:\n")
        f.write("Rathinam Technical Campus\n")
        f.write("Bachelor of Engineering in Computer Science | 2023 - 2027\n")
    print(f"Created sample unstructured Notes: {notes_path}")

    # 4. Define default and custom configs
    default_config = "config/default_projection.json"
    custom_config = "config/custom_projection.json"

    # 5. Run the pipeline with the default projection configuration
    print("\nRunning pipeline with Default Ingestion Schema...")
    default_output = "output/candidate_default.json"
    subprocess.run([
        sys.executable, "src/main.py",
        "-i", csv_path, notes_path,
        "-c", default_config,
        "-o", default_output
    ])

    # 6. Run the pipeline with the custom projection configuration
    print("\nRunning pipeline with Custom Projection Schema...")
    custom_output = "output/candidate_projected.json"
    subprocess.run([
        sys.executable, "src/main.py",
        "-i", csv_path, notes_path,
        "-c", custom_config,
        "-o", custom_output
    ])

    # 7. Print and inspect the output JSONs
    print("\n====================================================")
    print("DEFAULT INGESTION SCHEMA OUTPUT (Golden Record):")
    with open(default_output, "r", encoding="utf-8") as f:
        print(json.dumps(json.load(f), indent=2))

    print("\n====================================================")
    print("CUSTOM RESHAPED SCHEMA OUTPUT (Projected & Anonymized):")
    with open(custom_output, "r", encoding="utf-8") as f:
        print(json.dumps(json.load(f), indent=2))
        
    print("\n====================================================")
    print(f"Demo complete! Outputs saved in the 'output/' directory.")

if __name__ == "__main__":
    run_demo()
