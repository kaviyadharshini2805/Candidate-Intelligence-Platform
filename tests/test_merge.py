from datetime import datetime
from src.merge.engine import MergeEngine
from src.models.canonical import InternalCandidate, ProvenanceValue, ProvenanceMetadata, InternalWorkExperience

def test_merge_engine_priority():
    # Priority: notes (30) > json (20) > pdf (10)
    engine = MergeEngine()
    
    prov_pdf = ProvenanceMetadata(source="resume.pdf", method="heuristics", confidence=0.6, timestamp=datetime(2026, 1, 1))
    prov_json = ProvenanceMetadata(source="ats_profile.json", method="api", confidence=0.9, timestamp=datetime(2026, 1, 2))
    
    name_pdf = ProvenanceValue(value="Jon Doe", provenance=prov_pdf)
    name_json = ProvenanceValue(value="Johnathan Doe", provenance=prov_json)
    
    cand_pdf = InternalCandidate(full_name=name_pdf)
    cand_json = InternalCandidate(full_name=name_json)
    
    # JSON has higher source priority and confidence, so it should survive
    merged = engine.merge(cand_pdf, cand_json)
    assert merged.full_name.value == "Johnathan Doe"
    
    # Reverse merge - json should still survive
    merged_rev = engine.merge(cand_json, cand_pdf)
    assert merged_rev.full_name.value == "Johnathan Doe"

def test_merge_engine_confidence_tie_breaker():
    engine = MergeEngine()
    
    # Same source, different confidence
    prov1 = ProvenanceMetadata(source="resume.pdf", method="regex", confidence=0.5, timestamp=datetime(2026, 1, 1))
    prov2 = ProvenanceMetadata(source="resume.pdf", method="llm", confidence=0.9, timestamp=datetime(2026, 1, 1))
    
    headline_low = ProvenanceValue(value="Low Conf Summary", provenance=prov1)
    headline_high = ProvenanceValue(value="High Conf Summary", provenance=prov2)
    
    cand1 = InternalCandidate(headline=headline_low)
    cand2 = InternalCandidate(headline=headline_high)
    
    merged = engine.merge(cand1, cand2)
    assert merged.headline.value == "High Conf Summary"

def test_merge_engine_recency_tie_breaker():
    engine = MergeEngine()
    
    # Same source and confidence, different timestamp
    prov_old = ProvenanceMetadata(source="resume.pdf", method="regex", confidence=0.7, timestamp=datetime(2026, 1, 1))
    prov_new = ProvenanceMetadata(source="resume.pdf", method="regex", confidence=0.7, timestamp=datetime(2026, 1, 10))
    
    hl_old = ProvenanceValue(value="Old Resume Headline", provenance=prov_old)
    hl_new = ProvenanceValue(value="New Resume Headline", provenance=prov_new)
    
    cand_old = InternalCandidate(headline=hl_old)
    cand_new = InternalCandidate(headline=hl_new)
    
    merged = engine.merge(cand_old, cand_new)
    assert merged.headline.value == "New Resume Headline"

def test_merge_experience_items():
    engine = MergeEngine()
    prov = ProvenanceMetadata(source="ats_profile.json", method="api", confidence=0.9)
    
    exp1 = InternalWorkExperience(
        company=ProvenanceValue(value="Google", provenance=prov),
        title=ProvenanceValue(value="Software Engineer", provenance=prov),
        start=ProvenanceValue(value="2020-01", provenance=prov)
    )
    
    exp2 = InternalWorkExperience(
        company=ProvenanceValue(value="Google Inc.", provenance=prov),
        title=ProvenanceValue(value="Software Engineer I", provenance=prov),
        end=ProvenanceValue(value="2022-01", provenance=prov)
    )
    
    cand1 = InternalCandidate(experience=[exp1])
    cand2 = InternalCandidate(experience=[exp2])
    
    merged = engine.merge(cand1, cand2)
    # The experience items match based on fuzzy indicators ("Google" in "Google Inc." and title overlaps)
    # So they should be resolved to a single merged experience item
    assert len(merged.experience) == 1
    assert merged.experience[0].company.value in ["Google", "Google Inc."]
    assert merged.experience[0].start.value == "2020-01"
    assert merged.experience[0].end.value == "2022-01"
