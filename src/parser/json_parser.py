from src.parser.base import BaseParser
from src.adapters.base import RawPayload
from typing import Dict, Any

class JSONParser(BaseParser):
    """
    Parser specifically for ATS JSON payloads.
    Maps typical structured JSON keys to standard raw keys, supporting nested objects and arrays.
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
            "confidence": 1.0  # JSON structured data is highly reliable
        }

        if not content:
            return result

        if not isinstance(content, dict):
            # If it's a list or other types, wrap/default it
            if isinstance(content, list) and len(content) > 0:
                data = content[0]
            else:
                data = {}
        else:
            data = content

        # Support nested "profile" or root
        profile = data.get("profile", data) if isinstance(data, dict) else {}
        if not isinstance(profile, dict):
            profile = {}

        # 1. Full Name
        result["full_name"] = profile.get("name") or profile.get("candidate_name") or profile.get("full_name")

        # 2. Emails (support string or list)
        emails = profile.get("emails") or profile.get("email_addresses") or profile.get("email") or []
        if isinstance(emails, str):
            result["emails"].append(emails)
        elif isinstance(emails, list):
            result["emails"].extend([e for e in emails if isinstance(e, str)])

        # 3. Phones (support string or list)
        phones = profile.get("phones") or profile.get("phone_numbers") or profile.get("phone") or []
        if isinstance(phones, str):
            result["phones"].append(phones)
        elif isinstance(phones, list):
            result["phones"].extend([p for p in phones if isinstance(p, str)])

        # 4. Location (nested city/region/country)
        loc = profile.get("location") or {}
        if isinstance(loc, dict):
            result["location"] = [
                loc.get("city") or loc.get("town"),
                loc.get("region") or loc.get("state"),
                loc.get("country")
            ]
        elif isinstance(loc, list) and len(loc) >= 3:
            result["location"] = loc[:3]

        # 5. Links
        links = profile.get("links") or {}
        if isinstance(links, dict):
            result["links"]["linkedin"] = links.get("linkedin")
            result["links"]["github"] = links.get("github")
            result["links"]["portfolio"] = links.get("portfolio")
            other = links.get("other") or []
            if isinstance(other, list):
                result["links"]["other"].extend(other)
            elif isinstance(other, str):
                result["links"]["other"].append(other)

        # 6. Headline / Professional Summary
        result["headline"] = profile.get("headline") or profile.get("bio") or profile.get("summary") or profile.get("professional_summary")

        # 7. Years of Experience
        result["years_experience"] = profile.get("years_experience") or profile.get("experience_years")

        # 8. Skills (support list of strings or list of dicts with 'name')
        skills = profile.get("skills") or []
        if isinstance(skills, list):
            for skill in skills:
                if isinstance(skill, str):
                    result["skills"].append(skill)
                elif isinstance(skill, dict) and skill.get("name"):
                    result["skills"].append(skill["name"])

        # 9. Experience (support list of experience objects)
        exp_list = profile.get("experience") or profile.get("work_history") or []
        if isinstance(exp_list, list):
            for exp in exp_list:
                if isinstance(exp, dict):
                    result["experience"].append({
                        "company": exp.get("company") or "Unknown Company",
                        "title": exp.get("title") or "Unknown Title",
                        "start": exp.get("start"),
                        "end": exp.get("end"),
                        "summary": exp.get("summary") or exp.get("description") or ""
                    })

        # 10. Education
        edu_list = profile.get("education") or profile.get("academic_history") or []
        if isinstance(edu_list, list):
            for edu in edu_list:
                if isinstance(edu, dict):
                    result["education"].append({
                        "institution": edu.get("institution") or edu.get("school") or "Unknown Institution",
                        "degree": edu.get("degree"),
                        "field": edu.get("field") or edu.get("major"),
                        "end_year": edu.get("end_year") or edu.get("year")
                    })

        return result
