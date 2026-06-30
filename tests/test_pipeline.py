import os
import json
from src.main import run_pipeline

def test_full_pipeline_integration(tmp_path):
    # Create temporary mock inputs
    csv_file = tmp_path / "recruiter_export.csv"
    csv_file.write_text(
        "name,email,phone,current_company,title\n"
        "Kaviyadharshini M,kaviyadharshini.works@gmail.com,1234567890,Google,Software Intern",
        encoding="utf-8"
    )
    
    notes_file = tmp_path / "recruiter_notes.txt"
    notes_file.write_text(
        "Candidate: Kaviyadharshini M\n"
        "Email: kaviyadharshini.works@gmail.com\n"
        "GitHub: https://github.com/kaviyadharshini2805\n"
        "Skills: Python, Java, JavaScript, AWS\n",
        encoding="utf-8"
    )
    
    config_file = tmp_path / "projection.json"
    config_file.write_text(json.dumps({
        "fields": [
            { "path": "name", "from": "full_name", "type": "string", "required": True },
            { "path": "primary_email", "from": "emails[0]", "type": "string", "required": True },
            { "path": "github_link", "from": "links.github", "type": "string" },
            { "path": "skills", "from": "skills[].name", "type": "string[]" }
        ],
        "include_confidence": True,
        "on_missing": "null"
    }))

    # Execute pipeline
    results = run_pipeline(
        input_files=[str(csv_file), str(notes_file)],
        config_path=str(config_file)
    )

    # Verify merged and projected outputs
    assert len(results) == 1
    profile = results[0]
    assert profile["name"] == "Kaviyadharshini M"
    assert profile["primary_email"] == "kaviyadharshini.works@gmail.com"
    assert profile["github_link"] == "https://github.com/kaviyadharshini2805"
    assert set(profile["skills"]) == {"Python", "Java", "JavaScript", "AWS"}
    assert "overall_confidence" in profile
    assert len(profile["provenance"]) > 0

def test_text_parser_phone_extraction():
    from src.parser.text_parser import TextParser
    from src.adapters.base import RawPayload
    
    parser = TextParser()
    
    # Test case 1: spacing/grouping like +91 82708 49088
    text1 = "Candidate Phone: +91 82708 49088"
    payload1 = RawPayload(content=text1, content_type="txt", source_name="notes.txt")
    res1 = parser.parse(payload1)
    assert "+91 82708 49088" in res1["phones"]
    
    # Test case 2: standard US (555) 123-4567
    text2 = "Call me at (555) 123-4567"
    payload2 = RawPayload(content=text2, content_type="txt", source_name="notes.txt")
    res2 = parser.parse(payload2)
    assert "(555) 123-4567" in res2["phones"]

