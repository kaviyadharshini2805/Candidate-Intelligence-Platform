from typing import List, Optional, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
import uuid

T = TypeVar('T')

# ----------------------------------------------------
# 1. Provenance and Metadata Wrappers (Internal Use)
# ----------------------------------------------------

class ProvenanceMetadata(BaseModel):
    source: str
    method: str  # e.g., 'direct_input', 'regex_heuristics', 'nlp_parser'
    confidence: float = Field(ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    decision_reason: Optional[str] = None
    match_type: Optional[str] = None
    match_confidence: Optional[float] = None

class ProvenanceValue(BaseModel, Generic[T]):
    value: T
    provenance: ProvenanceMetadata

# ----------------------------------------------------
# 2. Canonical Output Schema Models (Eightfold Format)
# ----------------------------------------------------

class LocationSchema(BaseModel):
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None  # ISO-3166 alpha-2

class LinksSchema(BaseModel):
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    other: List[str] = Field(default_factory=list)

class SkillItem(BaseModel):
    name: str
    confidence: float = Field(ge=0.0, le=1.0)
    sources: List[str] = Field(default_factory=list)

class ExperienceItem(BaseModel):
    company: str
    title: str
    start: Optional[str] = None  # YYYY-MM
    end: Optional[str] = None    # YYYY-MM or null
    summary: Optional[str] = None

class EducationItem(BaseModel):
    institution: str
    degree: Optional[str] = None
    field: Optional[str] = None
    end_year: Optional[int] = None

class ProvenanceRecord(BaseModel):
    field: str
    source: str
    method: str
    decision_reason: Optional[str] = None
    match_type: Optional[str] = None
    confidence_score: Optional[float] = None


# ----------------------------------------------------
# 2b. Conflict and Diagnostics Models (Analytics Layer)
# ----------------------------------------------------

class ConflictRecord(BaseModel):
    """Represents a single field-level merge conflict between two sources."""
    field: str
    source_a: str
    value_a: Optional[str] = None
    confidence_a: float = 0.0
    priority_a: int = 0
    source_b: str
    value_b: Optional[str] = None
    confidence_b: float = 0.0
    priority_b: int = 0
    winner_source: str
    winning_value: Optional[str] = None
    rejected_value: Optional[str] = None
    decision_rule: str  # e.g. 'source_priority', 'confidence', 'recency', 'both_retained'


class SourceDiagnostic(BaseModel):
    """Per-source parse diagnostics reported by the analytics layer."""
    source_name: str
    content_type: str
    parse_time_ms: float = 0.0
    emails_found: int = 0
    phones_found: int = 0
    skills_found: int = 0
    experience_count: int = 0
    education_count: int = 0
    links_found: int = 0
    has_name: bool = False
    has_headline: bool = False
    sections_found: List[str] = Field(default_factory=list)
    sections_missing: List[str] = Field(default_factory=list)
    parser_confidence: float = 0.0
    error: Optional[str] = None

class CanonicalCandidate(BaseModel):
    candidate_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    full_name: str
    emails: List[str] = Field(default_factory=list)
    phones: List[str] = Field(default_factory=list)
    location: List[Optional[str]] = Field(
        default_factory=lambda: [None, None, None],
        description="[city, region, country]"
    )
    links: LinksSchema = Field(default_factory=LinksSchema)
    headline: Optional[str] = None
    years_experience: Optional[float] = None
    skills: List[SkillItem] = Field(default_factory=list)
    experience: List[ExperienceItem] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    provenance: List[ProvenanceRecord] = Field(default_factory=list)
    overall_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    validation_warnings: List[str] = Field(default_factory=list)
    data_quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    # Analytics layer — populated by InstrumentedMergeEngine and PipelineRunner
    merge_conflicts: List["ConflictRecord"] = Field(default_factory=list)
    parse_diagnostics: List["SourceDiagnostic"] = Field(default_factory=list)

# ----------------------------------------------------
# 3. Rich Internal Representation (For Normalization/Merge)
# ----------------------------------------------------

class InternalWorkExperience(BaseModel):
    company: ProvenanceValue[str]
    title: ProvenanceValue[str]
    start: Optional[ProvenanceValue[Optional[str]]] = None
    end: Optional[ProvenanceValue[Optional[str]]] = None
    summary: Optional[ProvenanceValue[Optional[str]]] = None

class InternalEducation(BaseModel):
    institution: ProvenanceValue[str]
    degree: Optional[ProvenanceValue[Optional[str]]] = None
    field: Optional[ProvenanceValue[Optional[str]]] = None
    end_year: Optional[ProvenanceValue[Optional[int]]] = None

class InternalCandidate(BaseModel):
    """
    Rich representation used internally during processing and merging.
    Allows attribute-level conflict resolution.
    """
    candidate_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    full_name: Optional[ProvenanceValue[str]] = None
    emails: List[ProvenanceValue[str]] = Field(default_factory=list)
    phones: List[ProvenanceValue[str]] = Field(default_factory=list)
    
    # Location components can come from different sources
    city: Optional[ProvenanceValue[Optional[str]]] = None
    region: Optional[ProvenanceValue[Optional[str]]] = None
    country: Optional[ProvenanceValue[Optional[str]]] = None
    
    # Links components
    linkedin: Optional[ProvenanceValue[Optional[str]]] = None
    github: Optional[ProvenanceValue[Optional[str]]] = None
    portfolio: Optional[ProvenanceValue[Optional[str]]] = None
    other_links: List[ProvenanceValue[str]] = Field(default_factory=list)
    
    headline: Optional[ProvenanceValue[Optional[str]]] = None
    years_experience: Optional[ProvenanceValue[Optional[float]]] = None
    
    # Flat lists are wrapped
    skills: List[ProvenanceValue[str]] = Field(default_factory=list)
    
    # Complex collections are lists of internal structured models
    experience: List[InternalWorkExperience] = Field(default_factory=list)
    education: List[InternalEducation] = Field(default_factory=list)

    def to_canonical(self) -> CanonicalCandidate:
        """
        Converts the rich internal representation to the public CanonicalCandidate schema.
        Flattens values, aggregates provenance, and calculates overall confidence.
        """
        provenance_records = []
        
        # Helper to safely extract value and log provenance
        def extract_val(field_name: str, prov_val: Optional[ProvenanceValue[Any]]) -> Any:
            if not prov_val:
                return None
            provenance_records.append(ProvenanceRecord(
                field=field_name,
                source=prov_val.provenance.source,
                method=prov_val.provenance.method,
                decision_reason=prov_val.provenance.decision_reason,
                match_type=prov_val.provenance.match_type,
                confidence_score=prov_val.provenance.match_confidence
            ))
            return prov_val.value

        # Extract scalar fields
        name_val = extract_val("full_name", self.full_name) or "Unknown Candidate"
        headline_val = extract_val("headline", self.headline)
        yexp_val = extract_val("years_experience", self.years_experience)

        # Extract emails & phones
        email_vals = []
        for e in self.emails:
            val = extract_val("emails", e)
            if val and val not in email_vals:
                email_vals.append(val)
                
        phone_vals = []
        for p in self.phones:
            val = extract_val("phones", p)
            if val and val not in phone_vals:
                phone_vals.append(val)

        # Extract location
        loc_city = extract_val("location.city", self.city)
        loc_region = extract_val("location.region", self.region)
        loc_country = extract_val("location.country", self.country)
        location_list = [loc_city, loc_region, loc_country]

        # Extract links
        linkedin_val = extract_val("links.linkedin", self.linkedin)
        github_val = extract_val("links.github", self.github)
        portfolio_val = extract_val("links.portfolio", self.portfolio)
        other_urls = []
        for l in self.other_links:
            val = extract_val("links.other", l)
            if val and val not in other_urls:
                other_urls.append(val)
        
        links_schema = LinksSchema(
            linkedin=linkedin_val,
            github=github_val,
            portfolio=portfolio_val,
            other=other_urls
        )

        # Extract experience
        exp_list = []
        for item in self.experience:
            c = extract_val("experience.company", item.company)
            t = extract_val("experience.title", item.title)
            s = extract_val("experience.start", item.start) if item.start else None
            e = extract_val("experience.end", item.end) if item.end else None
            sum_ = extract_val("experience.summary", item.summary) if item.summary else None
            exp_list.append(ExperienceItem(
                company=c, title=t, start=s, end=e, summary=sum_
            ))

        # Extract education
        edu_list = []
        for item in self.education:
            inst = extract_val("education.institution", item.institution)
            deg = extract_val("education.degree", item.degree) if item.degree else None
            fld = extract_val("education.field", item.field) if item.field else None
            ey = extract_val("education.end_year", item.end_year) if item.end_year else None
            edu_list.append(EducationItem(
                institution=inst, degree=deg, field=fld, end_year=ey
            ))

        # Skills require grouping to collect confidence and sources
        skills_map: Dict[str, List[ProvenanceValue[str]]] = {}
        for s in self.skills:
            normalized_name = s.value.strip()
            if normalized_name not in skills_map:
                skills_map[normalized_name] = []
            skills_map[normalized_name].append(s)

        skills_list = []
        for s_name, list_vals in skills_map.items():
            max_conf = max(item.provenance.confidence for item in list_vals)
            sources = list(set(item.provenance.source for item in list_vals))
            # Log provenance for the skills field
            for item in list_vals:
                provenance_records.append(ProvenanceRecord(
                    field="skills",
                    source=item.provenance.source,
                    method=item.provenance.method,
                    decision_reason=item.provenance.decision_reason,
                    match_type=item.provenance.match_type,
                    confidence_score=item.provenance.match_confidence
                ))
            skills_list.append(SkillItem(
                name=s_name,
                confidence=max_conf,
                sources=sources
            ))

        # Overall confidence: average of all extraction confidences collected in provenance
        confidences = []
        # Gather scalar confidences
        if self.full_name: confidences.append(self.full_name.provenance.confidence)
        if self.headline: confidences.append(self.headline.provenance.confidence)
        if self.years_experience: confidences.append(self.years_experience.provenance.confidence)
        
        # Gather lists confidences
        for e in self.emails: confidences.append(e.provenance.confidence)
        for p in self.phones: confidences.append(p.provenance.confidence)
        for l in self.other_links: confidences.append(l.provenance.confidence)
        for s in self.skills: confidences.append(s.provenance.confidence)
        
        # Location
        if self.city: confidences.append(self.city.provenance.confidence)
        if self.region: confidences.append(self.region.provenance.confidence)
        if self.country: confidences.append(self.country.provenance.confidence)
        
        # Complex collections
        for item in self.experience:
            confidences.append(item.company.provenance.confidence)
            confidences.append(item.title.provenance.confidence)
        for item in self.education:
            confidences.append(item.institution.provenance.confidence)

        overall_conf = sum(confidences) / len(confidences) if confidences else 1.0

        # Unique the provenance records to avoid redundancy
        unique_provenance = []
        seen_prov = set()
        for pr in provenance_records:
            key = (pr.field, pr.source, pr.method, pr.decision_reason)
            if key not in seen_prov:
                seen_prov.add(key)
                unique_provenance.append(pr)

        # Ingestion Validation & Sanitization Engine
        warnings = []
        for exp in exp_list:
            if exp.start and exp.end:
                try:
                    s_dt = datetime.strptime(exp.start, "%Y-%m")
                    e_dt = datetime.strptime(exp.end, "%Y-%m")
                    if s_dt > e_dt:
                        warnings.append(f"Validation Warning: Job at '{exp.company}' has end_date before start_date ({exp.end} < {exp.start}).")
                except ValueError:
                    pass

        if yexp_val is not None and yexp_val < 0:
            warnings.append("Validation Warning: Candidate has negative years of experience.")

        for edu in edu_list:
            if edu.end_year and edu.end_year > 2035:
                warnings.append(f"Validation Warning: Education institution '{edu.institution}' has graduation year ({edu.end_year}) in the far future.")

        if not email_vals and not phone_vals:
            warnings.append("Validation Warning: Candidate profile has no contact information (emails and phones are empty).")

        # Check for probable fuzzy match warnings (manual review recommended)
        is_probable_fuzzy = False
        fuzzy_score = 0.0
        if self.full_name and self.full_name.provenance.match_type == "fuzzy":
            is_probable_fuzzy = True
            fuzzy_score = self.full_name.provenance.match_confidence or 0.0
            
        if is_probable_fuzzy and fuzzy_score < 0.85:
            warnings.append(f"Validation Warning: Resolved duplicate candidate via probable fuzzy matching (score: {fuzzy_score}). Manual review recommended.")

        # Data Quality Score calculation
        score = 0.0
        if name_val and name_val != "Unknown Candidate":
            score += 0.15
        if email_vals:
            score += 0.25
        if phone_vals:
            score += 0.15
        if linkedin_val or github_val or portfolio_val or other_urls:
            score += 0.10
        if any(location_list):
            score += 0.10
        if exp_list:
            score += 0.15
        if edu_list:
            score += 0.10

        score = max(0.0, score - (len(warnings) * 0.1))

        return CanonicalCandidate(
            candidate_id=self.candidate_id,
            full_name=name_val,
            emails=email_vals,
            phones=phone_vals,
            location=location_list,
            links=links_schema,
            headline=headline_val,
            years_experience=yexp_val,
            skills=skills_list,
            experience=exp_list,
            education=edu_list,
            provenance=unique_provenance,
            overall_confidence=round(overall_conf, 2),
            validation_warnings=warnings,
            data_quality_score=round(score, 2)
        )
