import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from src.adapters.base import RawPayload
from src.models.canonical import (
    InternalCandidate, ProvenanceValue, ProvenanceMetadata,
    InternalWorkExperience, InternalEducation
)

class CandidateNormalizer:
    """
    Standardizes and normalizes raw fields extracted by the Parsers.
    Prepares the record to be mapped into the InternalCandidate model.
    """
    
    # Simple ISO country mapping for common terms
    COUNTRY_MAP = {
        "united states": "US", "usa": "US", "us": "US", "u.s.": "US", "u.s.a.": "US", "america": "US",
        "india": "IN", "in": "IN", "bharat": "IN",
        "united kingdom": "GB", "uk": "GB", "gb": "GB", "great britain": "GB", "england": "GB",
        "canada": "CA", "ca": "CA",
        "germany": "DE", "de": "DE", "deutschland": "DE",
        "france": "FR", "fr": "FR",
        "australia": "AU", "au": "AU",
        "singapore": "SG", "sg": "SG",
        "japan": "JP", "jp": "JP",
        "china": "CN", "cn": "CN",
        "brazil": "BR", "br": "BR",
        "netherlands": "NL", "nl": "NL", "holland": "NL",
        "sweden": "SE", "se": "SE",
        "switzerland": "CH", "ch": "CH",
        "south korea": "KR", "kr": "KR", "korea": "KR",
        "israel": "IL", "il": "IL",
        "uae": "AE", "ae": "AE", "united arab emirates": "AE",
        "new zealand": "NZ", "nz": "NZ",
        "ireland": "IE", "ie": "IE",
        "spain": "ES", "es": "ES",
        "italy": "IT", "it": "IT",
        "mexico": "MX", "mx": "MX",
        "russia": "RU", "ru": "RU",
        "south africa": "ZA", "za": "ZA",
    }

    # Skill taxonomy normalization map
    SKILL_TAXONOMY = {
        # JavaScript variants
        "js": "JavaScript", "javascript": "JavaScript", "java script": "JavaScript",
        "es6": "JavaScript", "ecmascript": "JavaScript",
        # Python variants
        "py": "Python", "python": "Python", "python3": "Python", "py3": "Python",
        # TypeScript
        "ts": "TypeScript", "typescript": "TypeScript", "type script": "TypeScript",
        # C/C++/C#
        "c++": "C++", "cpp": "C++",
        "c#": "C#", "csharp": "C#", "c sharp": "C#",
        # Cloud
        "aws": "AWS", "amazon web services": "AWS",
        "gcp": "GCP", "google cloud": "GCP", "google cloud platform": "GCP",
        "azure": "Azure", "microsoft azure": "Azure",
        # ML/AI
        "ml": "Machine Learning", "machinelearning": "Machine Learning", "machine learning": "Machine Learning",
        "dl": "Deep Learning", "deeplearning": "Deep Learning", "deep learning": "Deep Learning",
        "nlp": "NLP", "natural language processing": "NLP",
        "ai": "Artificial Intelligence", "artificial intelligence": "Artificial Intelligence",
        "cv": "Computer Vision", "computer vision": "Computer Vision",
        # DevOps
        "docker": "Docker", "docker-compose": "Docker",
        "k8s": "Kubernetes", "kubernetes": "Kubernetes",
        "ci/cd": "CI/CD", "cicd": "CI/CD", "ci cd": "CI/CD",
        # Databases
        "postgres": "PostgreSQL", "postgresql": "PostgreSQL",
        "mongo": "MongoDB", "mongodb": "MongoDB",
        "mysql": "MySQL", "my sql": "MySQL",
        "redis": "Redis",
        "nosql": "NoSQL", "no sql": "NoSQL",
        "sql": "SQL",
        # Web frameworks
        "react": "React", "reactjs": "React", "react.js": "React",
        "angular": "Angular", "angularjs": "Angular",
        "vue": "Vue.js", "vuejs": "Vue.js", "vue.js": "Vue.js",
        "nextjs": "Next.js", "next.js": "Next.js",
        "node": "Node.js", "nodejs": "Node.js", "node.js": "Node.js",
        "django": "Django",
        "flask": "Flask",
        "fastapi": "FastAPI", "fast api": "FastAPI",
        "spring": "Spring", "spring boot": "Spring Boot", "springboot": "Spring Boot",
        # Other
        "git": "Git", "github": "GitHub",
        "html": "HTML", "html5": "HTML",
        "css": "CSS", "css3": "CSS",
        "rest": "REST API", "restful": "REST API", "rest api": "REST API",
        "graphql": "GraphQL", "graph ql": "GraphQL",
        "golang": "Go", "go": "Go",
        "rust": "Rust",
        "java": "Java",
        "scala": "Scala",
        "ruby": "Ruby",
        "r": "R",
        "swift": "Swift",
        "kotlin": "Kotlin",
        "terraform": "Terraform",
        "ansible": "Ansible",
        "pandas": "Pandas",
        "numpy": "NumPy",
        "tensorflow": "TensorFlow", "tf": "TensorFlow",
        "pytorch": "PyTorch",
        "scikit-learn": "Scikit-learn", "sklearn": "Scikit-learn",
        "tableau": "Tableau",
        "power bi": "Power BI", "powerbi": "Power BI",
        "agile": "Agile", "scrum": "Scrum",
    }

    def __init__(self, default_country_code: str = "IN"):
        self.default_country_code = default_country_code

    def normalize_name(self, name: Optional[str]) -> str:
        if not name:
            return "Unknown Candidate"
        # Strip honorifics and common suffixes
        cleaned = re.sub(r'\b(?:Mr|Dr|Mrs|Ms|Prof|Ph\.?D|Jr|Sr|III|II|IV)\b\.?', '', name, flags=re.IGNORECASE)
        # Strip content inside parentheses (e.g. nicknames)
        cleaned = re.sub(r'\([^)]*\)', '', cleaned)
        # Replace commas with space to remove suffix residue
        cleaned = cleaned.replace(",", " ")
        # Clean extra spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        # Title case — but preserve non-Latin scripts (they don't have title case)
        if cleaned and cleaned.isascii():
            return cleaned.title()
        return cleaned if cleaned else "Unknown Candidate"

    def normalize_email(self, email: Optional[str]) -> Optional[str]:
        if not email:
            return None
        cleaned = email.strip().lower()
        # Basic validation check
        if "@" in cleaned and "." in cleaned:
            return cleaned
        return None

    def normalize_phone(self, phone: Optional[str]) -> Optional[str]:
        if not phone:
            return None
        # Strip extensions (e.g. "ext 123", "x123", "extension 456")
        cleaned = re.sub(r'\s*(?:ext\.?|x|extension)\s*\d+', '', phone, flags=re.IGNORECASE)
        # Remove common formatting characters
        cleaned = re.sub(r'[\(\)\-\s\.]', '', cleaned)
        
        # Reject obviously fake numbers (all same digit, sequential, too short)
        digits_only = re.sub(r'\D', '', cleaned)
        if len(digits_only) < 7:
            return None
        if len(set(digits_only)) == 1:  # All same digit e.g. 1111111111
            return None
        if digits_only in ('1234567890', '0123456789', '9876543210'):
            return None
        
        # Check if already E.164
        if cleaned.startswith("+"):
            return cleaned
            
        # Basic parsing: if it starts with 00, map to +
        if cleaned.startswith("00"):
            return "+" + cleaned[2:]
            
        # Standardize local 10-digit number to E.164 (based on default country code)
        if len(digits_only) == 10 and digits_only.isdigit():
            if self.default_country_code == "US":
                return "+1" + digits_only
            elif self.default_country_code == "IN":
                return "+91" + digits_only
                
        # Fallback: if it's digit-like, return with + prefix if appropriate
        if digits_only.isdigit() and len(digits_only) >= 7:
            return "+" + digits_only
            
        return phone.strip()

    def normalize_date(self, date_str: Optional[str]) -> Optional[str]:
        """
        Converts date string to YYYY-MM.
        Handles relative terms like 'Present', 'Current', 'Now' as None.
        """
        if not date_str:
            return None
            
        cleaned = date_str.strip().lower()
        if cleaned in ["present", "current", "now", "ongoing", "active"] or "currently" in cleaned:
            return None
            
        # Try parsing YYYY-MM
        match = re.search(r'\b(\d{4})-(\d{2})\b', date_str)
        if match:
            return f"{match.group(1)}-{match.group(2)}"
            
        # Try parsing MM/YYYY or M/YYYY
        match = re.search(r'\b(\d{1,2})/(\d{4})\b', date_str)
        if match:
            month = int(match.group(1))
            year = int(match.group(2))
            return f"{year:04d}-{month:02d}"

        # Try parsing common text format (e.g., "Jan 2020", "January 2020")
        months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        months_full = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
        
        # Look for month name and 4 digit year
        for i, m in enumerate(months):
            if m in cleaned:
                year_match = re.search(r'\b(\d{4})\b', date_str)
                if year_match:
                    return f"{year_match.group(1)}-{i+1:02d}"
        for i, m in enumerate(months_full):
            if m in cleaned:
                year_match = re.search(r'\b(\d{4})\b', date_str)
                if year_match:
                    return f"{year_match.group(1)}-{i+1:02d}"

        # Try parsing 4-digit year only
        year_match = re.search(r'\b(\d{4})\b', date_str)
        if year_match:
            return f"{year_match.group(1)}-01"  # Default to January
            
        return date_str.strip()

    def normalize_country(self, country: Optional[str]) -> Optional[str]:
        if not country:
            return None
        cleaned = country.strip().lower()
        return self.COUNTRY_MAP.get(cleaned, country.strip().upper()[:2])

    def normalize_skill(self, skill: str) -> str:
        cleaned = skill.strip().lower()
        return self.SKILL_TAXONOMY.get(cleaned, skill.strip())

    def normalize_url(self, url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        cleaned = url.strip()
        # Add https prefix if missing
        if not cleaned.lower().startswith(("http://", "https://")):
            cleaned = "https://" + cleaned
        # Strip query parameters for standard social platforms
        if "linkedin.com" in cleaned.lower() or "github.com" in cleaned.lower():
            cleaned = cleaned.split("?")[0]
        return cleaned

    def normalize_to_internal(self, raw_data: Dict[str, Any], payload: RawPayload) -> InternalCandidate:
        """
        Takes raw dictionary values from parser and converts them to
        the InternalCandidate model with proper Provenance wrapping.
        """
        source = payload.source_name
        method = "structured_map" if payload.content_type in ["csv", "json"] else "regex_heuristics"
        confidence = raw_data.get("confidence", 0.6)
        
        prov_meta = ProvenanceMetadata(
            source=source,
            method=method,
            confidence=confidence
        )

        # Helper to create ProvenanceValue
        def make_prov(val: Any) -> ProvenanceValue[Any]:
            return ProvenanceValue(value=val, provenance=prov_meta)

        # Normalize scalar fields
        raw_name = raw_data.get("full_name")
        full_name = make_prov(self.normalize_name(raw_name)) if raw_name else None

        # Normalize list fields (emails, phones)
        emails = [make_prov(self.normalize_email(e)) for e in raw_data.get("emails", []) if self.normalize_email(e)]
        phones = [make_prov(self.normalize_phone(p)) for p in raw_data.get("phones", []) if self.normalize_phone(p)]

        # Normalize location components
        raw_loc = raw_data.get("location") or [None, None, None]
        city = make_prov(raw_loc[0].strip()) if raw_loc[0] else None
        region = make_prov(raw_loc[1].strip()) if raw_loc[1] else None
        country = make_prov(self.normalize_country(raw_loc[2])) if raw_loc[2] else None

        # Normalize Links
        raw_links = raw_data.get("links") or {}
        linkedin = make_prov(self.normalize_url(raw_links.get("linkedin"))) if raw_links.get("linkedin") else None
        github = make_prov(self.normalize_url(raw_links.get("github"))) if raw_links.get("github") else None
        portfolio = make_prov(self.normalize_url(raw_links.get("portfolio"))) if raw_links.get("portfolio") else None
        
        other_links = []
        for link in raw_links.get("other") or []:
            norm_link = self.normalize_url(link)
            if norm_link:
                other_links.append(make_prov(norm_link))

        raw_hl = raw_data.get("headline")
        headline = make_prov(raw_hl.strip()) if raw_hl else None

        raw_yexp = raw_data.get("years_experience")
        years_experience = make_prov(float(raw_yexp)) if raw_yexp is not None else None

        # Normalize Skills
        skills = [make_prov(self.normalize_skill(s)) for s in raw_data.get("skills", []) if s]

        # Normalize Experience
        experience_items = []
        for exp in raw_data.get("experience", []):
            comp = make_prov(exp.get("company", "Unknown Company").strip())
            title = make_prov(exp.get("title", "Unknown Title").strip())
            start = make_prov(self.normalize_date(exp.get("start"))) if exp.get("start") else None
            end = make_prov(self.normalize_date(exp.get("end"))) if exp.get("end") else None
            summary = make_prov(exp.get("summary", "").strip()) if exp.get("summary") else None
            
            experience_items.append(InternalWorkExperience(
                company=comp,
                title=title,
                start=start,
                end=end,
                summary=summary
            ))

        # Normalize Education
        education_items = []
        for edu in raw_data.get("education", []):
            inst = make_prov(edu.get("institution", "Unknown Institution").strip())
            degree = make_prov(edu.get("degree", "").strip()) if edu.get("degree") else None
            field = make_prov(edu.get("field", "").strip()) if edu.get("field") else None
            
            raw_ey = edu.get("end_year")
            end_year = None
            if raw_ey:
                try:
                    end_year = make_prov(int(raw_ey))
                except ValueError:
                    pass

            education_items.append(InternalEducation(
                institution=inst,
                degree=degree,
                field=field,
                end_year=end_year
            ))

        return InternalCandidate(
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
            experience=experience_items,
            education=education_items
        )
