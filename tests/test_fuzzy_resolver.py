import pytest
from typing import Optional
from datetime import datetime
from src.models.canonical import InternalCandidate, ProvenanceValue, ProvenanceMetadata, InternalWorkExperience
from src.identity.fuzzy_resolver import FuzzyResolver, MATCH_CONFIRMED, MATCH_PROBABLE_MANUAL_REVIEW, NO_MATCH
from src.identity.resolver import IdentityResolver

def create_mock_candidate(name: str, company: Optional[str], email: Optional[str] = None, phone: Optional[str] = None) -> InternalCandidate:
    """
    Helper to construct a mock InternalCandidate.
    """
    prov = ProvenanceMetadata(source="test_source", method="test_method", confidence=1.0)
    
    experience = []
    if company:
        experience.append(InternalWorkExperience(
            company=ProvenanceValue(value=company, provenance=prov),
            title=ProvenanceValue(value="Software Engineer", provenance=prov)
        ))
        
    emails = []
    if email:
        emails.append(ProvenanceValue(value=email, provenance=prov))
        
    phones = []
    if phone:
        phones.append(ProvenanceValue(value=phone, provenance=prov))

    return InternalCandidate(
        full_name=ProvenanceValue(value=name, provenance=prov),
        emails=emails,
        phones=phones,
        experience=experience
    )

def test_fuzzy_resolver_exact_match():
    resolver = FuzzyResolver()
    cand1 = create_mock_candidate("John Doe", "Google")
    cand2 = create_mock_candidate("John Doe", "Google")
    
    score = resolver.calculate_match_score(cand1, cand2)
    assert score == 1.0
    status, _ = resolver.resolve_fuzzy(cand1, cand2)
    assert status == MATCH_CONFIRMED

def test_fuzzy_resolver_similar_name_company():
    resolver = FuzzyResolver()
    # Levenshtein on 'John Doe' vs 'Jon Doe' is high, Jaro-Winkler on 'Google' vs 'Google LLC' is high
    cand1 = create_mock_candidate("John Doe", "Google")
    cand2 = create_mock_candidate("Jon Doe", "Google LLC")
    
    status, score = resolver.resolve_fuzzy(cand1, cand2)
    assert score > 0.85
    assert status == MATCH_CONFIRMED

def test_fuzzy_resolver_probable_review():
    resolver = FuzzyResolver()
    # Name matches somewhat, but companies differ
    cand1 = create_mock_candidate("John Doe", "Google")
    cand2 = create_mock_candidate("John Doe", "Microsoft")
    
    status, score = resolver.resolve_fuzzy(cand1, cand2)
    # Name weight is 0.6. Name matches exactly (1.0). Company matches 0 (0.0). Composite is 0.6 * 1.0 + 0.4 * 0 = 0.6
    # Wait, the threshold for MATCH_PROBABLE_MANUAL_REVIEW is 0.65 to 0.85.
    # Let's test a slightly closer one:
    cand3 = create_mock_candidate("John Doe", "Google")
    cand4 = create_mock_candidate("Jon Doe", "Alphabet") # Alphabet vs Google has 0 similarity. Name similarity is around 0.87.
    # Composite: 0.87 * 0.6 = ~0.52.
    # Let's verify a case where company matches somewhat (e.g. 'Google Cloud' vs 'Google'):
    # Jaro-Winkler of 'Google' and 'Google Cloud' is ~0.89. Levenshtein of name is 1.0.
    # Composite: 1.0 * 0.6 + 0.89 * 0.4 = 0.95 (CONFIRMED)
    # Let's verify a case yielding 0.65 - 0.85:
    # Name: 'John Smith' vs 'Johnny Smith' (similarity ~0.83). Company: 'Google' vs 'Microsoft' (0.0) -> composite 0.83 * 0.6 = ~0.50
    # Name: 'John Smith' vs 'John Smith' (1.0). Company: 'Google Inc' vs 'Gol' (Jaro-Winkler ~0.72) -> composite 0.6 * 1.0 + 0.4 * 0.72 = 0.888
    # Name: 'John Smith' vs 'Jack Smith' (Levenshtein ~0.75). Company: 'Google' vs 'Alphabet' (0.0) -> composite 0.75 * 0.6 = 0.45.
    # Let's construct a case with composite between 0.65 and 0.85:
    cand5 = create_mock_candidate("John Smith", "Google")
    cand6 = create_mock_candidate("Jack Smith", "Google LLC")
    # Name: 'John Smith' vs 'Jack Smith' -> Levenshtein is ~0.75.
    # Company: 'Google' vs 'Google LLC' -> Jaro-Winkler is ~0.93.
    # Composite: 0.75 * 0.6 + 0.93 * 0.4 = 0.45 + 0.372 = 0.822 (MATCH_PROBABLE_MANUAL_REVIEW)
    status, score = resolver.resolve_fuzzy(cand5, cand6)
    assert 0.65 <= score <= 0.85
    assert status == MATCH_PROBABLE_MANUAL_REVIEW

def test_identity_resolver_deterministic_first():
    resolver = IdentityResolver()
    
    # Create candidates with matching email (deterministic) but different names/companies
    cand1 = create_mock_candidate("John Doe", "Google", email="john@example.com")
    cand2 = create_mock_candidate("Jon Smith", "Microsoft", email="john@example.com")
    
    resolved_id = resolver.resolve(cand1, [])
    cand1.candidate_id = resolved_id
    
    resolved_id2 = resolver.resolve(cand2, [cand1])
    assert resolved_id2 == cand1.candidate_id
    # Assert no fuzzy resolution metadata was recorded because deterministic resolved it
    assert resolved_id2 not in resolver.resolved_metadata

def test_identity_resolver_fuzzy_fallback():
    resolver = IdentityResolver()
    
    # Create candidates with completely different contact info, but similar name/company
    cand1 = create_mock_candidate("Kaviyadharshini M", "Google", email="kavya@example.com")
    cand2 = create_mock_candidate("Kaviyadharshini M", "Google LLC", email="kavya.works@example.com")
    
    id1 = resolver.resolve(cand1, [])
    cand1.candidate_id = id1
    
    id2 = resolver.resolve(cand2, [cand1])
    
    # Should fall back to fuzzy matching and merge them under id1
    assert id2 == id1
    assert cand2.candidate_id in resolver.resolved_metadata
    meta = resolver.resolved_metadata[cand2.candidate_id]
    assert meta["match_type"] == "fuzzy"
    assert meta["status"] == MATCH_CONFIRMED
