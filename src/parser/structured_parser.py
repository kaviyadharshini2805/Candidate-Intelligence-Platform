from src.parser.base import BaseParser
from src.adapters.base import RawPayload
from typing import Dict, Any, List

class StructuredParser(BaseParser):
    """
    Parser for structured sources (CSV row dicts, ATS JSON blobs).
    Maps source-specific keys to standard raw keys.
    """
    def parse(self, payload: RawPayload) -> Dict[str, Any]:
        content = payload.content
        result: Dict[str, Any] = {
            "full_name": None,
            "emails": [],
            "phones": [],
            "location": [None, None, None],
            "links": {
                "linkedin": None,
                "github": None,
                "portfolio": None,
                "other": []
            },
            "headline": None,
            "years_experience": None,
            "skills": [],
            "experience": [],
            "education": [],
            "confidence": 1.0  # Structured data is highly reliable
        }

        if payload.content_type == "csv":
            # If CSV, we expect a single candidate row dict
            row = content if isinstance(content, dict) else (content[0] if isinstance(content, list) and len(content) > 0 else {})
            
            result["full_name"] = row.get("name") or row.get("full_name")
            if row.get("email"):
                result["emails"].append(row.get("email"))
            if row.get("phone"):
                result["phones"].append(row.get("phone"))
                
            company = row.get("current_company")
            title = row.get("title") or row.get("job_title")
            if company or title:
                result["experience"].append({
                    "company": company or "Unknown Company",
                    "title": title or "Unknown Title",
                    "start": None,
                    "end": None,
                    "summary": "Imported from recruiter CSV export."
                })
                
        elif payload.content_type == "json":
            # If JSON, we support custom mapping for typical ATS structures
            data = content.get("profile", content) if isinstance(content, dict) else {}
            
            result["full_name"] = data.get("name") or data.get("candidate_name") or data.get("full_name")
            
            # Map emails
            emails = data.get("emails") or data.get("email_addresses") or []
            if isinstance(emails, str):
                result["emails"].append(emails)
            elif isinstance(emails, list):
                result["emails"].extend(emails)
            elif data.get("email"):
                result["emails"].append(data.get("email"))
                
            # Map phones
            phones = data.get("phones") or data.get("phone_numbers") or []
            if isinstance(phones, str):
                result["phones"].append(phones)
            elif isinstance(phones, list):
                result["phones"].extend(phones)
            elif data.get("phone"):
                result["phones"].append(data.get("phone"))
                
            # Map location
            loc = data.get("location") or {}
            if isinstance(loc, dict):
                result["location"] = [
                    loc.get("city") or loc.get("town"),
                    loc.get("region") or loc.get("state") or loc.get("province"),
                    loc.get("country") or loc.get("country_code")
                ]
            elif isinstance(loc, list) and len(loc) == 3:
                result["location"] = loc

            # Map links
            links = data.get("links") or data.get("social_links") or []
            if isinstance(links, list):
                for link in links:
                    if "linkedin.com" in link:
                        result["links"]["linkedin"] = link
                    elif "github.com" in link:
                        result["links"]["github"] = link
                    else:
                        result["links"]["other"].append(link)
            elif isinstance(links, dict):
                result["links"]["linkedin"] = links.get("linkedin")
                result["links"]["github"] = links.get("github")
                result["links"]["portfolio"] = links.get("portfolio")
                result["links"]["other"] = links.get("other", [])

            result["headline"] = data.get("headline") or data.get("bio")
            result["years_experience"] = data.get("years_experience") or data.get("experience_years")
            
            # Map skills
            skills = data.get("skills") or []
            if isinstance(skills, list):
                result["skills"] = [s if isinstance(s, str) else s.get("name") for s in skills if s]
                
            # Map work experience
            experience = data.get("experience") or data.get("employment") or data.get("work_history") or []
            if isinstance(experience, list):
                for exp in experience:
                    result["experience"].append({
                        "company": exp.get("company") or exp.get("employer") or "Unknown Company",
                        "title": exp.get("title") or exp.get("job_title") or "Unknown Title",
                        "start": exp.get("start") or exp.get("start_date"),
                        "end": exp.get("end") or exp.get("end_date"),
                        "summary": exp.get("summary") or exp.get("description") or exp.get("responsibilities")
                    })
                    
            # Map education
            education = data.get("education") or data.get("academic") or data.get("education_history") or []
            if isinstance(education, list):
                for edu in education:
                    result["education"].append({
                        "institution": edu.get("institution") or edu.get("school") or "Unknown Institution",
                        "degree": edu.get("degree") or edu.get("degree_name"),
                        "field": edu.get("field") or edu.get("major") or edu.get("field_of_study"),
                        "end_year": edu.get("end_year") or edu.get("year_completed") or edu.get("grad_year")
                    })

        return result
