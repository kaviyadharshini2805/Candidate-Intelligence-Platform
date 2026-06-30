import pytest
from src.projection.engine import ProjectionEngine
from src.models.canonical import CanonicalCandidate, SkillItem, LinksSchema

def test_projection_engine_subset_and_remapping():
    engine = ProjectionEngine()
    
    candidate = CanonicalCandidate(
        full_name="Kaviyadharshini M",
        emails=["kaviyadharshini.works@gmail.com"],
        phones=["+919876543210"],
        skills=[SkillItem(name="Python", confidence=0.9, sources=["resume.pdf"])]
    )
    
    config = {
        "fields": [
            { "path": "name", "from": "full_name", "type": "string", "required": True },
            { "path": "email", "from": "emails[0]", "type": "string" },
            { "path": "skills_list", "from": "skills[].name", "type": "string[]" }
        ],
        "include_confidence": False,
        "on_missing": "null"
    }
    
    projected = engine.project(candidate, config)
    assert projected == {
        "name": "Kaviyadharshini M",
        "email": "kaviyadharshini.works@gmail.com",
        "skills_list": ["Python"]
    }

def test_projection_engine_missing_fields_omit():
    engine = ProjectionEngine()
    
    candidate = CanonicalCandidate(
        full_name="Kaviyadharshini M"
    )
    
    config = {
        "fields": [
            { "path": "full_name", "type": "string" },
            { "path": "headline", "type": "string" } # Missing field
        ],
        "include_confidence": False,
        "on_missing": "omit" # Omit missing fields
    }
    
    projected = engine.project(candidate, config)
    assert projected == {
        "full_name": "Kaviyadharshini M"
        # headline should be missing
    }

def test_projection_engine_missing_fields_error():
    engine = ProjectionEngine()
    candidate = CanonicalCandidate(full_name="John Doe")
    
    config = {
        "fields": [
            { "path": "headline", "type": "string", "required": True }
        ],
        "on_missing": "error"
    }
    
    with pytest.raises(ValueError):
        engine.project(candidate, config)

def test_projection_engine_anonymize():
    engine = ProjectionEngine()
    
    candidate = CanonicalCandidate(
        full_name="Jane Doe",
        skills=[SkillItem(name="Java", confidence=0.8, sources=["resume.pdf"])]
    )
    
    config = {
        "fields": [
            { "path": "candidate_name", "from": "full_name", "normalize": "anonymize" },
            { "path": "candidate_skills", "from": "skills[].name", "normalize": "anonymize" }
        ],
        "include_confidence": False,
        "on_missing": "null"
    }
    
    projected = engine.project(candidate, config)
    assert projected["candidate_name"] == "J. D."
    assert projected["candidate_skills"] == ["[Redacted Skill]"]
