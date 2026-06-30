"""
DecisionExplainer — reads the InternalCandidate's provenance data and produces
human-readable explanations for why each merged field won.

No business logic is duplicated. All reasoning is derived from the
ProvenanceMetadata already stored on every ProvenanceValue by the MergeEngine.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from src.models.canonical import InternalCandidate, CanonicalCandidate, ProvenanceValue


@dataclass
class FieldExplanation:
    """Structured explanation for a single merged scalar field."""
    field: str
    winner_source: str
    winner_confidence: float
    winner_value_preview: str
    alternative_sources: List[Dict[str, Any]]   # [{source, confidence, value_preview}]
    reasons: List[str]                           # ordered decision reasons
    decision_rule: str                           # 'source_priority' | 'confidence' | 'recency' | 'single_source'


_TRUNCATE = 120


def _preview(val: Any, truncate: int = _TRUNCATE) -> str:
    if val is None:
        return "(empty)"
    s = str(val)
    return s[:truncate] + "..." if len(s) > truncate else s


def _parse_reason(decision_reason: Optional[str]) -> tuple[str, List[str]]:
    """
    Converts the raw decision_reason string from MergeEngine into a
    structured (rule, reasons_list) pair for display.
    """
    if not decision_reason:
        return "single_source", ["Single source — no conflict resolution required."]

    r = decision_reason.lower()
    reasons: List[str] = []
    rule = "auto"

    if "single source" in r or "initial profile" in r:
        rule = "single_source"
        reasons = ["Only one source provided this field — no conflict resolution required."]
    elif "priority" in r:
        rule = "source_priority"
        reasons = [
            f"Source priority comparison: {decision_reason}",
            "Higher priority sources override lower priority ones for this field.",
        ]
    elif "confidence" in r:
        rule = "confidence"
        reasons = [
            f"Extraction confidence comparison: {decision_reason}",
            "Higher confidence extractions are preferred when source priority is equal.",
        ]
    elif "recency" in r:
        rule = "recency"
        reasons = [
            "Source priority and confidence were equal.",
            "The more recently processed source was selected as the tie-breaker.",
        ]
    else:
        rule = "auto"
        reasons = [decision_reason]

    return rule, reasons


class DecisionExplainer:
    """
    Produces per-field decision explanations from an InternalCandidate.

    Usage:
        explainer = DecisionExplainer(source_priorities)
        explanations = explainer.explain(internal_candidate)
    """

    def __init__(self, source_priorities: Optional[Dict[str, int]] = None):
        self._priorities = source_priorities or {}

    def _explain_scalar(
        self,
        field_name: str,
        prov_val: Optional[ProvenanceValue],
        alternatives: Optional[List[ProvenanceValue]] = None,
    ) -> Optional[FieldExplanation]:
        if not prov_val:
            return None

        rule, reasons = _parse_reason(prov_val.provenance.decision_reason)

        alt_info = []
        for alt in (alternatives or []):
            alt_info.append({
                "source": alt.provenance.source,
                "confidence": alt.provenance.confidence,
                "value_preview": _preview(alt.value),
                "priority": self._priorities.get(alt.provenance.source, 10),
            })

        return FieldExplanation(
            field=field_name,
            winner_source=prov_val.provenance.source,
            winner_confidence=prov_val.provenance.confidence,
            winner_value_preview=_preview(prov_val.value),
            alternative_sources=alt_info,
            reasons=reasons,
            decision_rule=rule,
        )

    def explain(self, internal: InternalCandidate) -> List[FieldExplanation]:
        """
        Generate FieldExplanation objects for every scalar field in the
        InternalCandidate that has provenance metadata.
        """
        explanations: List[FieldExplanation] = []

        scalar_fields = [
            ("Full Name",          internal.full_name),
            ("Headline / Summary", internal.headline),
            ("Years Experience",   internal.years_experience),
            ("Location — City",    internal.city),
            ("Location — Region",  internal.region),
            ("Location — Country", internal.country),
            ("LinkedIn URL",       internal.linkedin),
            ("GitHub URL",         internal.github),
            ("Portfolio URL",      internal.portfolio),
        ]

        for label, prov_val in scalar_fields:
            exp = self._explain_scalar(label, prov_val)
            if exp:
                explanations.append(exp)

        # List fields — explain each item
        for pv in internal.emails:
            exp = self._explain_scalar("Email", pv)
            if exp:
                explanations.append(exp)

        for pv in internal.phones:
            exp = self._explain_scalar("Phone", pv)
            if exp:
                explanations.append(exp)

        for pv in internal.skills:
            exp = self._explain_scalar(f"Skill: {pv.value}", pv)
            if exp:
                explanations.append(exp)

        # Experience sub-fields
        for exp_item in internal.experience:
            company = exp_item.company.value if exp_item.company else "?"
            exp = self._explain_scalar(f"Experience: {company}", exp_item.summary or exp_item.title)
            if exp:
                explanations.append(exp)

        return explanations
