from typing import Optional, Dict, Any, List
from rapidfuzz.distance import Levenshtein, JaroWinkler
from src.models.canonical import InternalCandidate

MATCH_CONFIRMED = "MATCH_CONFIRMED"
MATCH_PROBABLE_MANUAL_REVIEW = "MATCH_PROBABLE_MANUAL_REVIEW"
NO_MATCH = "NO_MATCH"

class FuzzyResolver:
    """
    Fuzzy Candidate Identity Resolver.
    Uses Levenshtein Distance for names and Jaro-Winkler for company names
    to calculate a weighted composite similarity score between two candidate records.
    """
    def __init__(self, name_weight: float = 0.6, company_weight: float = 0.4):
        self.name_weight = name_weight
        self.company_weight = company_weight

    def _get_latest_company(self, candidate: InternalCandidate) -> Optional[str]:
        """
        Helper to extract the candidate's current or latest company name.
        """
        if not candidate.experience:
            return None
        # We assume the first experience item is the latest
        latest_job = candidate.experience[0]
        return latest_job.company.value if latest_job.company else None

    def calculate_match_score(self, candidate_a: InternalCandidate, candidate_b: InternalCandidate) -> float:
        """
        Calculates a weighted composite score between two candidates.
        Name similarity (Levenshtein): 60%
        Latest company similarity (Jaro-Winkler): 40%
        """
        # 1. Compare names using Levenshtein normalized similarity
        name_a = candidate_a.full_name.value if candidate_a.full_name else ""
        name_b = candidate_b.full_name.value if candidate_b.full_name else ""
        
        if not name_a or not name_b:
            name_score = 0.0
        else:
            # normalized_similarity returns float [0.0 - 1.0]
            name_score = Levenshtein.normalized_similarity(name_a.lower(), name_b.lower())

        # 2. Compare company names using Jaro-Winkler
        company_a = self._get_latest_company(candidate_a)
        company_b = self._get_latest_company(candidate_b)
        
        if not company_a or not company_b:
            # If one candidate has no company, fall back to name similarity representing 100% of the score
            return name_score
        
        company_score = JaroWinkler.similarity(company_a.lower(), company_b.lower())

        # 3. Return weighted composite score
        composite_score = (name_score * self.name_weight) + (company_score * self.company_weight)
        return composite_score

    def resolve_fuzzy(self, candidate_a: InternalCandidate, candidate_b: InternalCandidate) -> tuple[str, float]:
        """
        Applies thresholding rules to classify the match.
        """
        score = self.calculate_match_score(candidate_a, candidate_b)
        
        if score > 0.85:
            return MATCH_CONFIRMED, score
        elif 0.65 <= score <= 0.85:
            return MATCH_PROBABLE_MANUAL_REVIEW, score
        else:
            return NO_MATCH, score
