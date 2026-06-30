"""
InstrumentedMergeEngine — transparent subclass of MergeEngine that intercepts
every scalar merge decision and records a ConflictRecord for the analytics layer.

The base MergeEngine is completely unchanged.
"""
from typing import Dict, Any, List, Optional, TypeVar
import re
from src.merge.engine import MergeEngine
from src.models.canonical import (
    InternalCandidate, ProvenanceValue, ConflictRecord
)

T = TypeVar("T")

# Fields that are displayed with short truncation in the conflict report
_TRUNCATE_LEN = 120


def _fmt(val: Any) -> Optional[str]:
    """Safely convert a value to a short display string."""
    if val is None:
        return None
    s = str(val)
    return s[:_TRUNCATE_LEN] + "..." if len(s) > _TRUNCATE_LEN else s


class InstrumentedMergeEngine(MergeEngine):
    """
    Thin wrapper around MergeEngine that captures field-level merge conflicts.

    Usage:
        engine = InstrumentedMergeEngine(source_priorities=...)
        merged = engine.merge(base, incoming)
        conflicts = engine.get_conflicts()   # List[ConflictRecord]
    """

    def __init__(self, source_priorities: Optional[Dict[str, int]] = None):
        super().__init__(source_priorities=source_priorities)
        self._conflicts: List[ConflictRecord] = []
        self._current_field: str = "unknown"

    # ── Public API ──────────────────────────────────────────────────────────

    def get_conflicts(self) -> List[ConflictRecord]:
        return list(self._conflicts)

    def reset_conflicts(self) -> None:
        self._conflicts.clear()

    # ── Internal hooks ──────────────────────────────────────────────────────

    def _record_conflict(
        self,
        field: str,
        current: "ProvenanceValue[Any]",
        incoming: "ProvenanceValue[Any]",
        winner: "ProvenanceValue[Any]",
        decision_rule: str,
    ) -> None:
        curr_prio  = self._get_priority(current.provenance.source)
        inc_prio   = self._get_priority(incoming.provenance.source)

        is_winner_a = winner.provenance.source == current.provenance.source
        winning_val  = _fmt(winner.value)
        rejected_val = _fmt(incoming.value if is_winner_a else current.value)
        winner_src   = winner.provenance.source

        self._conflicts.append(ConflictRecord(
            field=field,
            source_a=current.provenance.source,
            value_a=_fmt(current.value),
            confidence_a=current.provenance.confidence,
            priority_a=curr_prio,
            source_b=incoming.provenance.source,
            value_b=_fmt(incoming.value),
            confidence_b=incoming.provenance.confidence,
            priority_b=inc_prio,
            winner_source=winner_src,
            winning_value=winning_val,
            rejected_value=rejected_val,
            decision_rule=decision_rule,
        ))

    def _merge_scalar(
        self,
        current: Optional["ProvenanceValue[T]"],
        incoming: Optional["ProvenanceValue[T]"],
    ) -> Optional["ProvenanceValue[T]"]:
        # Delegate to parent — captures winner
        result = super()._merge_scalar(current, incoming)

        # Only record when both sides had a value (i.e. a real conflict existed)
        if current and incoming and result:
            val_a = str(current.value) if current.value is not None else ""
            val_b = str(incoming.value) if incoming.value is not None else ""

            # Skip if normalized values are identical — no conflict
            norm_a = re.sub(r'[\s\-/]+', '', val_a.strip().lower())
            norm_b = re.sub(r'[\s\-/]+', '', val_b.strip().lower())
            if norm_a != norm_b:
                reason = result.provenance.decision_reason or "unknown"

                # Classify decision rule for display
                if "priority" in reason.lower():
                    rule = "source_priority"
                elif "confidence" in reason.lower():
                    rule = "confidence"
                elif "recency" in reason.lower():
                    rule = "recency"
                else:
                    rule = "auto"

                self._record_conflict(
                    field=self._current_field,
                    current=current,
                    incoming=incoming,
                    winner=result,
                    decision_rule=rule,
                )

        return result

    # ── Override merge() to set field name context ───────────────────────────

    def merge(self, base: InternalCandidate, incoming: InternalCandidate) -> InternalCandidate:
        """
        Overrides merge to tag each scalar merge call with the correct field name.
        Uses targeted _merge_scalar calls so the field tag is accurate.
        """
        from src.models.canonical import InternalWorkExperience, InternalEducation

        candidate_id = base.candidate_id

        def _scalar(field_name: str, a, b):
            self._current_field = field_name
            return self._merge_scalar(a, b)

        full_name        = _scalar("full_name",        base.full_name,        incoming.full_name) or base.full_name
        headline         = _scalar("headline",         base.headline,         incoming.headline)
        years_experience = _scalar("years_experience", base.years_experience, incoming.years_experience)
        city             = _scalar("location.city",    base.city,             incoming.city)
        region           = _scalar("location.region",  base.region,           incoming.region)
        country          = _scalar("location.country", base.country,          incoming.country)
        rejected_links = []
        def _scalar_link(field_name: str, base_val, inc_val):
            res = _scalar(field_name, base_val, inc_val)
            # Only compare when all three are non-None and have non-None values
            if base_val and inc_val and res and base_val.value is not None and inc_val.value is not None and res.value is not None:
                if res.value == base_val.value:
                    if inc_val.value != base_val.value:
                        rejected_links.append(inc_val)
                elif res.value == inc_val.value:
                    if base_val.value != inc_val.value:
                        rejected_links.append(base_val)
            return res

        linkedin         = _scalar_link("links.linkedin",   base.linkedin,         incoming.linkedin)
        github           = _scalar_link("links.github",     base.github,           incoming.github)
        portfolio        = _scalar_link("links.portfolio",  base.portfolio,        incoming.portfolio)

        self._current_field = "emails"
        emails = self._merge_lists(base.emails, incoming.emails)

        self._current_field = "phones"
        phones = self._merge_lists(base.phones, incoming.phones)

        self._current_field = "links.other"
        incoming_other = list(incoming.other_links)
        for r_link in rejected_links:
            incoming_other.append(r_link)
        other_links = self._merge_lists(base.other_links, incoming_other)

        self._current_field = "skills"
        skills = self._merge_lists(base.skills, incoming.skills)

        # Experience
        merged_experience = list(base.experience)
        for inc_exp in incoming.experience:
            matched = False
            for idx, base_exp in enumerate(merged_experience):
                if self._is_same_experience(base_exp, inc_exp):
                    self._current_field = "experience"
                    merged_experience[idx] = self._merge_experience_items(base_exp, inc_exp)
                    matched = True
                    break
            if not matched:
                merged_experience.append(inc_exp)

        # Education
        merged_education = list(base.education)
        for inc_edu in incoming.education:
            matched = False
            for idx, base_edu in enumerate(merged_education):
                if self._is_same_education(base_edu, inc_edu):
                    self._current_field = "education"
                    merged_education[idx] = self._merge_education_items(base_edu, inc_edu)
                    matched = True
                    break
            if not matched:
                merged_education.append(inc_edu)

        from src.models.canonical import InternalCandidate as _IC
        return _IC(
            candidate_id=candidate_id,
            full_name=full_name,
            emails=emails,
            phones=phones,
            city=city,
            region=region,
            country=country,
            linkedin=linkedin,
            github=github,
            portfolio=portfolio,
            other_links=other_links,
            headline=headline,
            years_experience=years_experience,
            skills=skills,
            experience=merged_experience,
            education=merged_education,
        )
