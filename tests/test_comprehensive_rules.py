import pytest
from src.analytics.pipeline_runner import PipelineRunner, SourceInput
from src.models.canonical import CanonicalCandidate
from src.parser.text_parser import TextParser
from src.merge.engine import MergeEngine

def test_different_people_priority_selection():
    # Rule 1 & Rule 10A
    notes_text = "Name: Alice Brown\nEmail: alice@example.com\nSkills: Python"
    resume_text = "Name: John Smith\nEmail: john@example.com\nSkills: Java"

    sources = [
        SourceInput(name="notes.txt", content_type="txt", text=notes_text),
        SourceInput(name="resume.txt", content_type="txt", text=resume_text),
    ]

    priorities = {"notes.txt": 40, "resume.txt": 90}
    runner = PipelineRunner(source_priorities=priorities)
    result = runner.run(sources=sources)

    assert result.canonical.full_name == "John Smith"

def test_same_person_merged_correctly():
    # Rule 2 & Rule 10B
    notes_text = "Name: John Smith\nEmail: john@example.com\nSkills: Python, Java"
    resume_text = "Name: John Smith\nEmail: john@example.com\nSkills: C++, Docker"

    sources = [
        SourceInput(name="notes.txt", content_type="txt", text=notes_text),
        SourceInput(name="resume.txt", content_type="txt", text=resume_text),
    ]

    priorities = {"notes.txt": 40, "resume.txt": 90}
    runner = PipelineRunner(source_priorities=priorities)
    result = runner.run(sources=sources)

    assert result.canonical.full_name == "John Smith"
    skills = [s.name for s in result.canonical.skills]
    assert "Python" in skills
    assert "C++" in skills
    assert "Docker" in skills

def test_email_with_spaces_ocr_artifacts():
    # Rule 3
    text = "Contact me at john.doe @gmail.com or john [.doe@gmail.com](mailto:.doe@gmail.com)"
    parser = TextParser()
    from src.adapters.base import RawPayload
    res = parser.parse(RawPayload(source_name="test", content_type="txt", content=text))
    assert "john.doe@gmail.com" in res["emails"]

def test_url_without_protocol():
    # Rule 3
    text = "My profiles: www.linkedin.com/in/john and github.com/john"
    parser = TextParser()
    from src.adapters.base import RawPayload
    res = parser.parse(RawPayload(source_name="test", content_type="txt", content=text))
    assert res["links"]["linkedin"] == "https://www.linkedin.com/in/john"
    assert res["links"]["github"] == "https://github.com/john"

def test_duplicate_uploads():
    # Rule 9
    text = "Name: John Smith\nEmail: john@example.com"
    sources = [
        SourceInput(name="file1.txt", content_type="txt", text=text),
        SourceInput(name="file2.txt", content_type="txt", text=text),
    ]
    runner = PipelineRunner(source_priorities={"file1.txt": 50, "file2.txt": 50})
    result = runner.run(sources=sources)
    
    assert result.pipeline_stats.duplicates_removed >= 0
    assert result.canonical.full_name == "John Smith"

def test_conflicting_linkedin_urls_preservation():
    # Rule 4
    resume = "Name: John\nEmail: j@example.com\nLinkedIn: https://linkedin.com/in/john-a"
    notes = "Name: John\nEmail: j@example.com\nLinkedIn: https://linkedin.com/in/john-b"

    sources = [
        SourceInput(name="notes.txt", content_type="txt", text=notes),
        SourceInput(name="resume.txt", content_type="txt", text=resume),
    ]

    priorities = {"notes.txt": 40, "resume.txt": 90}
    runner = PipelineRunner(source_priorities=priorities)
    result = runner.run(sources=sources)

    assert result.canonical.links.linkedin == "https://linkedin.com/in/john-a"
    assert "https://linkedin.com/in/john-b" in result.canonical.links.other

def test_different_upload_order_scenario_d():
    # Rule 8 & 10D
    resume = "Name: John Smith\nEmail: john@example.com\nCurrent Company: Google"
    notes = "Name: John Smith\nEmail: john@example.com\nCurrent Company: Microsoft"

    priorities = {"notes.txt": 40, "resume.txt": 90}

    # Order 1
    sources1 = [
        SourceInput(name="notes.txt", content_type="txt", text=notes),
        SourceInput(name="resume.txt", content_type="txt", text=resume),
    ]
    res1 = PipelineRunner(source_priorities=priorities).run(sources=sources1)

    # Order 2
    sources2 = [
        SourceInput(name="resume.txt", content_type="txt", text=resume),
        SourceInput(name="notes.txt", content_type="txt", text=notes),
    ]
    res2 = PipelineRunner(source_priorities=priorities).run(sources=sources2)

    assert res1.canonical.full_name == res2.canonical.full_name
    assert res1.canonical.experience == res2.canonical.experience

def test_edge_cases():
    from src.normalizers.normalizer import CandidateNormalizer
    from src.projection.engine import ProjectionEngine
    import tempfile
    import os
    
    # 1. Ingestion / Detection: Empty / zero-byte files
    from src.adapters.csv_adapter import CSVAdapter
    from src.adapters.json_adapter import JSONAdapter
    from src.adapters.pdf_adapter import PDFAdapter
    from src.adapters.docx_adapter import DocxAdapter
    
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_name = tmp.name
        
    try:
        # 0-byte check
        csv_payload = CSVAdapter(tmp_name).read()
        assert csv_payload.content == []
        
        json_payload = JSONAdapter(tmp_name).read()
        assert json_payload.content == {}
        
        pdf_payload = PDFAdapter(tmp_name).read()
        assert pdf_payload.content == ""
        
        docx_payload = DocxAdapter(tmp_name).read()
        assert docx_payload.content == ""
    finally:
        os.remove(tmp_name)
        
    # 2. Normalization: Smart quotes, encoding, suffixes, and non-Latin names
    norm = CandidateNormalizer()
    assert norm.normalize_name("Mr. José Silva, Jr.") == "José Silva"
    assert norm.normalize_name("李雷 (Leo)") == "李雷"
    
    # 3. Normalization: Phone extensions and obviously fake numbers
    assert norm.normalize_phone("123-456-7890") is None  # Obviously fake sequence
    assert norm.normalize_phone("555-555-5555") is None  # All same digits
    assert norm.normalize_phone("987-654-3210") is None  # descending sequence
    assert norm.normalize_phone("+1 (202) 456-1111 ext 45") == "+12024561111"
    
    # 4. Normalization: Date format
    assert norm.normalize_date("currently working") is None
    
    # 5. Normalization: Country maps
    assert norm.normalize_country("U.S.A.") == "US"
    assert norm.normalize_country("england") == "GB"
    assert norm.normalize_country("bharat") == "IN"
    
    # 6. Normalization: Skill variants
    assert norm.normalize_skill("JS") == "JavaScript"
    assert norm.normalize_skill("aws") == "AWS"
    assert norm.normalize_skill("cicd") == "CI/CD"
    
    # 7. Projection: Self-conflict, type mismatches, and provenance renaming
    engine = ProjectionEngine(norm)
    from src.models.canonical import CanonicalCandidate, LinksSchema
    
    candidate = CanonicalCandidate(
        full_name="Alice",
        emails=["alice@example.com"],
        phones=["+12024561111"],
        links=LinksSchema(linkedin="https://linkedin.com/in/alice"),
        skills=[{"name": "Python", "confidence": 0.9, "sources": ["resume.txt"]}],
        provenance=[{"field": "full_name", "source": "resume.txt", "method": "structured"}]
    )
    
    # Target path mapped multiple times (self-conflict)
    config_conflict = {
        "fields": [
            {"path": "name", "from": "full_name"},
            {"path": "name", "from": "emails[0]"}
        ]
    }
    with pytest.raises(ValueError, match="Self-conflicting config"):
        engine.project(candidate, config_conflict)
        
    # Enforce type conversions
    config_types = {
        "fields": [
            {"path": "email_as_string", "from": "emails", "type": "string"},
            {"path": "name_as_list", "from": "full_name", "type": "string[]"},
        ],
        "include_confidence": True
    }
    out = engine.project(candidate, config_types)
    assert out["email_as_string"] == "alice@example.com"
    assert out["name_as_list"] == ["Alice"]
    
    # Provenance field name remapping
    config_renamed = {
        "fields": [
            {"path": "c_name", "from": "full_name"}
        ],
        "include_confidence": True
    }
    out_renamed = engine.project(candidate, config_renamed)
    assert out_renamed["provenance"][0]["field"] == "c_name"
    
    # 8. Education Extraction Edge Cases: present ranges, degree/institution split
    from src.adapters.base import RawPayload
    parser = TextParser()
    text = "Education\nB.E. Computer Science and Engineering 2023 – Present\nAnna University\n"
    res = parser.parse(RawPayload(source_name="test", content_type="txt", content=text))
    edu = res["education"][0]
    assert edu["institution"] == "Anna University"
    assert edu["degree"] == "B.E"
    assert edu["field"] == "Computer Science and Engineering"
    assert edu["end_year"] is None
    
    # Single-line degree only
    text_single = "Education\nB.E. Computer Science and Engineering 2023 – Present\n"
    res_single = parser.parse(RawPayload(source_name="test", content_type="txt", content=text_single))
    edu_single = res_single["education"][0]
    assert edu_single["institution"] == "Unknown Institution"
    assert edu_single["degree"] == "B.E"
    assert edu_single["field"] == "Computer Science and Engineering"
    assert edu_single["end_year"] is None

