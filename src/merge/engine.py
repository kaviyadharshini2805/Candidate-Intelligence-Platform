from typing import Dict, Any, List, Optional, TypeVar
from src.models.canonical import (
    InternalCandidate, ProvenanceValue, ProvenanceMetadata,
    InternalWorkExperience, InternalEducation
)

T = TypeVar('T')

class MergeEngine:
    """
    Combines two InternalCandidate profiles into a single merged InternalCandidate.
    Applies attribute-level conflict resolution rules based on:
    1. Source priority hierarchy (configured at initialization)
    2. Extraction confidence score
    3. Source recency (timestamp)
    """
    def __init__(self, source_priorities: Optional[Dict[str, int]] = None):
        # Default priorities: higher value = higher trust
        self.source_priorities = source_priorities or {
            "recruiter_notes.txt": 30,
            "ats_profile.json": 20,
            "recruiter_export.csv": 20,
            "resume.docx": 10,
            "resume.pdf": 10
        }

    def _get_priority(self, source: str) -> int:
        # Fallback to lowest priority (10) if source not registered
        return self.source_priorities.get(source, 10)

    def _should_replace_scalar(self, current: Optional[ProvenanceValue[Any]], incoming: Optional[ProvenanceValue[Any]]) -> bool:
        """
        Determines whether the current value should be replaced by the incoming value
        based on source priority, confidence, and timestamp recency.
        """
        if not incoming:
            return False
        if not current:
            return True

        # Rule 1: Source Priority
        curr_prio = self._get_priority(current.provenance.source)
        inc_prio = self._get_priority(incoming.provenance.source)
        if inc_prio != curr_prio:
            return inc_prio > curr_prio

        # Rule 2: Extraction Confidence
        if incoming.provenance.confidence != current.provenance.confidence:
            return incoming.provenance.confidence > current.provenance.confidence

        # Rule 3: Timestamp Recency (Tie-breaker)
        return incoming.provenance.timestamp > current.provenance.timestamp

    def _merge_scalar(self, current: Optional[ProvenanceValue[T]], incoming: Optional[ProvenanceValue[T]]) -> Optional[ProvenanceValue[T]]:
        if not incoming:
            if current:
                current_copy = current.model_copy(deep=True)
                current_copy.provenance.decision_reason = "Single source populated"
                return current_copy
            return None
        if not current:
            incoming_copy = incoming.model_copy(deep=True)
            incoming_copy.provenance.decision_reason = "Single source populated"
            return incoming_copy

        # Evaluate and assign explicit decision traces
        curr_prio = self._get_priority(current.provenance.source)
        inc_prio = self._get_priority(incoming.provenance.source)
        
        if inc_prio != curr_prio:
            if inc_prio > curr_prio:
                winner = incoming.model_copy(deep=True)
                winner.provenance.decision_reason = f"Source priority ({incoming.provenance.source}: {inc_prio}) > ({current.provenance.source}: {curr_prio})"
                return winner
            else:
                winner = current.model_copy(deep=True)
                winner.provenance.decision_reason = f"Source priority ({current.provenance.source}: {curr_prio}) > ({incoming.provenance.source}: {inc_prio})"
                return winner

        if incoming.provenance.confidence != current.provenance.confidence:
            if incoming.provenance.confidence > current.provenance.confidence:
                winner = incoming.model_copy(deep=True)
                winner.provenance.decision_reason = f"Confidence ({incoming.provenance.confidence}) > ({current.provenance.confidence})"
                return winner
            else:
                winner = current.model_copy(deep=True)
                winner.provenance.decision_reason = f"Confidence ({current.provenance.confidence}) > ({incoming.provenance.confidence})"
                return winner

        if incoming.provenance.timestamp > current.provenance.timestamp:
            winner = incoming.model_copy(deep=True)
            winner.provenance.decision_reason = "Recency tie-breaker (incoming newer)"
            return winner
        else:
            winner = current.model_copy(deep=True)
            winner.provenance.decision_reason = "Recency tie-breaker (current newer)"
            return winner

    def _merge_lists(self, current_list: List[ProvenanceValue[T]], incoming_list: List[ProvenanceValue[T]]) -> List[ProvenanceValue[T]]:
        """
        Merges two lists of elements by taking their union.
        If duplicates are found (matching value), keeps the one with the higher priority metadata.
        """
        merged_map: Dict[T, ProvenanceValue[T]] = {}
        for item in current_list:
            if item is None or item.value is None:
                continue
            item_copy = item.model_copy(deep=True)
            item_copy.provenance.decision_reason = "Initial profile value"
            merged_map[item.value] = item_copy
            
        for item in incoming_list:
            if item is None or item.value is None:
                continue
            val = item.value
            if val in merged_map:
                merged_item = self._merge_scalar(merged_map[val], item)
                if merged_item:
                    merged_map[val] = merged_item
            else:
                item_copy = item.model_copy(deep=True)
                item_copy.provenance.decision_reason = "Single source populated"
                merged_map[val] = item_copy
                
        return list(merged_map.values())

    def _is_same_experience(self, exp1: InternalWorkExperience, exp2: InternalWorkExperience) -> bool:
        """
        Heuristic to determine if two work history items refer to the same job.
        Matches if company names are highly similar and job titles overlap.
        """
        if not exp1.company or not exp2.company:
            return False
        if exp1.company.value is None or exp2.company.value is None:
            return False
        c1 = exp1.company.value.lower().replace(" ", "")
        c2 = exp2.company.value.lower().replace(" ", "")
        
        if not exp1.title or not exp2.title:
            return c1 == c2
        if exp1.title.value is None or exp2.title.value is None:
            return c1 == c2
        t1 = exp1.title.value.lower().replace(" ", "")
        t2 = exp2.title.value.lower().replace(" ", "")
        
        # Exact match of company and title (ignoring spacing/case)
        company_match = c1 == c2 or c1 in c2 or c2 in c1
        title_match = t1 == t2 or t1 in t2 or t2 in t1
        
        return company_match and title_match

    def _merge_experience_items(self, exp1: InternalWorkExperience, exp2: InternalWorkExperience) -> InternalWorkExperience:
        # Merge nested fields
        company = self._merge_scalar(exp1.company, exp2.company) or exp1.company
        title   = self._merge_scalar(exp1.title,   exp2.title)   or exp1.title
        start   = self._merge_scalar(exp1.start,   exp2.start)
        end     = self._merge_scalar(exp1.end,     exp2.end)
        summary = self._merge_scalar(exp1.summary, exp2.summary)
        
        return InternalWorkExperience(
            company=company,
            title=title,
            start=start,
            end=end,
            summary=summary
        )

    def _is_same_education(self, edu1: InternalEducation, edu2: InternalEducation) -> bool:
        """
        Heuristic to determine if two education items refer to the same study.
        """
        if not edu1.institution or not edu2.institution:
            return False
        if edu1.institution.value is None or edu2.institution.value is None:
            return False
        i1 = edu1.institution.value.lower().replace(" ", "")
        i2 = edu2.institution.value.lower().replace(" ", "")
        
        deg1 = edu1.degree.value.lower().replace(" ", "") if (edu1.degree and edu1.degree.value) else ""
        deg2 = edu2.degree.value.lower().replace(" ", "") if (edu2.degree and edu2.degree.value) else ""
        
        inst_match = i1 == i2 or i1 in i2 or i2 in i1
        deg_match = not deg1 or not deg2 or deg1 in deg2 or deg2 in deg1
        
        return inst_match and deg_match

    def _merge_education_items(self, edu1: InternalEducation, edu2: InternalEducation) -> InternalEducation:
        inst    = self._merge_scalar(edu1.institution, edu2.institution) or edu1.institution
        deg     = self._merge_scalar(edu1.degree,      edu2.degree)
        field   = self._merge_scalar(edu1.field,       edu2.field)
        end_yr  = self._merge_scalar(edu1.end_year,    edu2.end_year)
        
        return InternalEducation(
            institution=inst,
            degree=deg,
            field=field,
            end_year=end_yr
        )

    def merge(self, base: InternalCandidate, incoming: InternalCandidate) -> InternalCandidate:
        """
        Merges incoming candidate details into the base candidate.
        Returns a new merged InternalCandidate instance.
        """
        # Ensure candidate IDs match (resolved via IdentityResolver)
        candidate_id = base.candidate_id
        
        # Merge scalar fields — fall back to base if merge returns None (safety net)
        full_name = self._merge_scalar(base.full_name, incoming.full_name) or base.full_name
        headline = self._merge_scalar(base.headline, incoming.headline)
        years_experience = self._merge_scalar(base.years_experience, incoming.years_experience)
        
        # Location
        city = self._merge_scalar(base.city, incoming.city)
        region = self._merge_scalar(base.region, incoming.region)
        country = self._merge_scalar(base.country, incoming.country)
        
        # Links
        rejected_links = []
        def merge_link_track(base_val, inc_val):
            res = self._merge_scalar(base_val, inc_val)
            if base_val and inc_val and res:
                if res.value == base_val.value:
                    if inc_val.value != base_val.value:
                        rejected_links.append(inc_val)
                elif res.value == inc_val.value:
                    if base_val.value != inc_val.value:
                        rejected_links.append(base_val)
            return res

        linkedin = merge_link_track(base.linkedin, incoming.linkedin)
        github = merge_link_track(base.github, incoming.github)
        portfolio = merge_link_track(base.portfolio, incoming.portfolio)
        
        # Merge lists
        emails = self._merge_lists(base.emails, incoming.emails)
        phones = self._merge_lists(base.phones, incoming.phones)
        
        incoming_other = list(incoming.other_links)
        for r_link in rejected_links:
            incoming_other.append(r_link)
        other_links = self._merge_lists(base.other_links, incoming_other)
        skills = self._merge_lists(base.skills, incoming.skills)

        # Merge Experience list (match & merge or append)
        merged_experience = list(base.experience)
        for inc_exp in incoming.experience:
            matched = False
            for idx, base_exp in enumerate(merged_experience):
                if self._is_same_experience(base_exp, inc_exp):
                    merged_experience[idx] = self._merge_experience_items(base_exp, inc_exp)
                    matched = True
                    break
            if not matched:
                merged_experience.append(inc_exp)

        # Merge Education list (match & merge or append)
        merged_education = list(base.education)
        for inc_edu in incoming.education:
            matched = False
            for idx, base_edu in enumerate(merged_education):
                if self._is_same_education(base_edu, inc_edu):
                    merged_education[idx] = self._merge_education_items(base_edu, inc_edu)
                    matched = True
                    break
            if not matched:
                merged_education.append(inc_edu)

        return InternalCandidate(
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
            education=merged_education
        )
