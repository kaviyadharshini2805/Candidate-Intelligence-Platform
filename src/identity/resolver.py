from typing import List, Dict, Any
from src.models.canonical import InternalCandidate
from src.identity.fuzzy_resolver import FuzzyResolver, MATCH_CONFIRMED, MATCH_PROBABLE_MANUAL_REVIEW

class IdentityResolver:
    """
    Resolves candidate identities.
    1. First attempts deterministic matching via emails and phone numbers.
    2. If deterministic matching fails, triggers the FuzzyResolver to check for potential matches
       using name and company similarity.
    """
    def __init__(self):
        # Index mapping identifier keys to candidate_id
        self.registry: Dict[str, str] = {}
        # Initialize fuzzy resolver
        self.fuzzy_resolver = FuzzyResolver()
        # Record resolution metadata for downstream audit logging
        self.resolved_metadata: Dict[str, Dict[str, Any]] = {}

    def resolve(self, incoming: InternalCandidate, existing_candidates: List[InternalCandidate]) -> str:
        """
        Resolves candidate identity. First checks deterministic criteria.
        If missing, runs fuzzy name/company matching.
        """
        incoming_keys = []
        for e in incoming.emails:
            if e.value:
                incoming_keys.append(f"email:{e.value}")
        for p in incoming.phones:
            if p.value:
                incoming_keys.append(f"phone:{p.value}")

        # 1. Deterministic Check: Registry index lookup
        for key in incoming_keys:
            if key in self.registry:
                resolved_id = self.registry[key]
                for k in incoming_keys:
                    self.registry[k] = resolved_id
                return resolved_id

        # 2. Deterministic Check: Existing candidates attributes lookup
        for candidate in existing_candidates:
            existing_keys = []
            for e in candidate.emails:
                if e.value:
                    existing_keys.append(f"email:{e.value}")
            for p in candidate.phones:
                if p.value:
                    existing_keys.append(f"phone:{p.value}")

            if set(incoming_keys) & set(existing_keys):
                resolved_id = candidate.candidate_id
                for k in incoming_keys:
                    self.registry[k] = resolved_id
                for k in existing_keys:
                    self.registry[k] = resolved_id
                return resolved_id

        # 3. Fuzzy Check: Run FuzzyResolver on existing candidates
        for candidate in existing_candidates:
            status, score = self.fuzzy_resolver.resolve_fuzzy(incoming, candidate)
            
            if status in [MATCH_CONFIRMED, MATCH_PROBABLE_MANUAL_REVIEW]:
                resolved_id = candidate.candidate_id
                
                # Record resolution metadata
                self.resolved_metadata[incoming.candidate_id] = {
                    "match_type": "fuzzy",
                    "confidence_score": round(score, 2),
                    "status": status,
                    "matched_with_id": resolved_id,
                    "matched_with_name": candidate.full_name.value if candidate.full_name else "Unknown"
                }
                
                # Update registry with incoming keys for future speedups
                for k in incoming_keys:
                    self.registry[k] = resolved_id
                    
                return resolved_id

        # 4. Fallback: New candidate. Register identifiers under new ID.
        for k in incoming_keys:
            self.registry[k] = incoming.candidate_id
        return incoming.candidate_id
