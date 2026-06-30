"""
DataQualityAnalyzer — computes a detailed multi-dimensional data quality report
from a CanonicalCandidate.

All computation is read-only against the canonical model.
No business logic from the pipeline is duplicated here.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from src.models.canonical import CanonicalCandidate

# Enterprise field checklist — fields expected for a high-quality candidate profile.
_EXPECTED_FIELDS = [
    "full_name",
    "emails",
    "phones",
    "location",
    "headline",
    "years_experience",
    "skills",
    "experience",
    "education",
    "links.linkedin",
    "links.github",
    "links.portfolio",
]

# Fields suggested but not in the canonical model — shown as advisory suggestions only.
_ADVISORY_FIELDS = [
    "Expected Salary",
    "Notice Period",
    "Current Employment Status",
    "Work Authorization",
    "Preferred Location",
]


@dataclass
class FieldQuality:
    field: str
    present: bool
    confidence: float
    note: Optional[str] = None


@dataclass
class QualityReport:
    completeness_score: float       # 0–1: fraction of expected fields present
    consistency_score: float        # 0–1: no conflicting contacts / duplicates
    validity_score: float           # 0–1: validation warnings impact
    merge_quality_score: float      # 0–1: average extraction confidence
    overall_score: float            # weighted composite

    field_breakdown: List[FieldQuality]
    missing_fields: List[str]
    duplicate_fields: List[str]
    conflicting_fields: List[str]
    validation_warnings: List[str]
    suggestions: List[str]

    # Progress bar helpers (0–100 int)
    @property
    def completeness_pct(self) -> int:
        return int(self.completeness_score * 100)

    @property
    def consistency_pct(self) -> int:
        return int(self.consistency_score * 100)

    @property
    def validity_pct(self) -> int:
        return int(self.validity_score * 100)

    @property
    def merge_quality_pct(self) -> int:
        return int(self.merge_quality_score * 100)

    @property
    def overall_pct(self) -> int:
        return int(self.overall_score * 100)


class DataQualityAnalyzer:
    """
    Computes a DataQualityReport from a CanonicalCandidate.

    Usage:
        report = DataQualityAnalyzer().analyze(canonical)
    """

    def analyze(self, candidate: CanonicalCandidate) -> QualityReport:
        breakdown: List[FieldQuality] = []
        missing: List[str] = []
        duplicate: List[str] = []
        conflicting: List[str] = []
        suggestions: List[str] = []

        # ── Completeness ────────────────────────────────────────────────────
        present_count = 0

        def _check(label: str, present: bool, conf: float = 1.0, note: str = None):
            nonlocal present_count
            breakdown.append(FieldQuality(field=label, present=present, confidence=conf if present else 0.0, note=note))
            if present:
                present_count += 1
            else:
                missing.append(label)

        _check("Full Name",
               bool(candidate.full_name and candidate.full_name != "Unknown Candidate"),
               conf=1.0)
        _check("Email", bool(candidate.emails))
        _check("Phone", bool(candidate.phones))

        loc = candidate.location or []
        _check("Location", any(loc))

        _check("Headline / Summary", bool(candidate.headline))
        _check("Years Experience", candidate.years_experience is not None)
        _check("Skills", bool(candidate.skills),
               conf=max((s.confidence for s in candidate.skills), default=0.0))
        _check("Work Experience", bool(candidate.experience))
        _check("Education", bool(candidate.education))
        _check("LinkedIn", bool(candidate.links.linkedin))
        _check("GitHub", bool(candidate.links.github))
        _check("Portfolio", bool(candidate.links.portfolio))

        completeness = present_count / len(_EXPECTED_FIELDS)

        # ── Consistency ──────────────────────────────────────────────────────
        # Duplicate emails
        seen_emails: Dict[str, int] = {}
        for e in candidate.emails:
            seen_emails[e] = seen_emails.get(e, 0) + 1
        dup_emails = [e for e, c in seen_emails.items() if c > 1]
        if dup_emails:
            duplicate.extend([f"email:{e}" for e in dup_emails])

        # Duplicate phones
        seen_phones: Dict[str, int] = {}
        for p in candidate.phones:
            seen_phones[p] = seen_phones.get(p, 0) + 1
        dup_phones = [p for p, c in seen_phones.items() if c > 1]
        if dup_phones:
            duplicate.extend([f"phone:{p}" for p in dup_phones])

        # Conflicting provenance sources on the same field
        field_sources: Dict[str, set] = {}
        for rec in candidate.provenance:
            field_sources.setdefault(rec.field, set()).add(rec.source)
        for fname, srcs in field_sources.items():
            if len(srcs) > 1:
                conflicting.append(fname)

        consistency_penalty = (len(duplicate) * 0.1 + len(conflicting) * 0.05)
        consistency = max(0.0, 1.0 - consistency_penalty)

        # ── Validity ─────────────────────────────────────────────────────────
        warn_count = len(candidate.validation_warnings)
        validity = max(0.0, 1.0 - warn_count * 0.15)

        # ── Merge Quality ────────────────────────────────────────────────────
        # Average extraction confidence across all provenance entries
        confs = [r.confidence_score for r in candidate.provenance if r.confidence_score is not None]
        # Also factor in skill confidence
        confs += [s.confidence for s in candidate.skills]
        merge_quality = sum(confs) / len(confs) if confs else candidate.overall_confidence

        # ── Overall composite ────────────────────────────────────────────────
        overall = (
            completeness * 0.35
            + consistency * 0.20
            + validity    * 0.20
            + merge_quality * 0.25
        )

        # ── Suggestions ──────────────────────────────────────────────────────
        if missing:
            suggestions.append(
                f"Add the following fields to improve profile completeness: {', '.join(missing[:5])}."
            )
        if not candidate.links.linkedin:
            suggestions.append("A LinkedIn URL significantly improves recruiter confidence.")
        if not candidate.headline:
            suggestions.append("A professional headline / summary improves searchability.")
        if not candidate.experience:
            suggestions.append("No work experience was extracted — verify source documents.")
        if not candidate.skills:
            suggestions.append("No skills were extracted — verify source documents.")
        for advisory in _ADVISORY_FIELDS:
            suggestions.append(f"Consider adding: {advisory} (not in current sources).")

        return QualityReport(
            completeness_score=round(completeness, 3),
            consistency_score=round(consistency, 3),
            validity_score=round(validity, 3),
            merge_quality_score=round(merge_quality, 3),
            overall_score=round(overall, 3),
            field_breakdown=breakdown,
            missing_fields=missing,
            duplicate_fields=duplicate,
            conflicting_fields=conflicting,
            validation_warnings=candidate.validation_warnings,
            suggestions=suggestions,
        )
