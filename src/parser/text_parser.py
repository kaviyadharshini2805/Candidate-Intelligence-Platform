import re
from typing import Dict, Any, List
from src.parser.base import BaseParser
from src.adapters.base import RawPayload

class TextParser(BaseParser):
    """
    Heuristics and Regex-based parser for unstructured text sources (PDF, DOCX, Notes TXT).
    Assigns lower extraction confidence (e.g., 0.6) compared to structured sources.
    """
    def parse(self, payload: RawPayload) -> Dict[str, Any]:
        text = payload.content if isinstance(payload.content, str) else ""
        
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
            "confidence": 0.6  # Default extraction confidence for heuristics
        }

        if not text.strip():
            return result

        # Clean common copy-paste spacing artifacts in email address patterns
        cleaned_text = re.sub(r'([a-zA-Z0-9._%+-]+)\s*@\s*([a-zA-Z0-9.-]+)\s*\.\s*([a-zA-Z]{2,})', r'\1@\2.\3', text)

        # 1. Regex Extraction for Email
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, cleaned_text)
        result["emails"] = list(set(emails))

        # 2. Regex Extraction for Phone Numbers
        phone_pattern = r'\+?\(?[0-9]{1,4}\)?[-.\s]?\(?[0-9]{1,3}\)?[-.\s]?[0-9]{3,5}[-.\s]?[0-9]{3,5}'
        phones = re.findall(phone_pattern, cleaned_text)
        result["phones"] = list(set([p.strip() for p in phones if len(p.strip()) >= 7]))

        # 3. Regex Extraction for Links (handles optional http/https protocol)
        linkedin_pattern = r'(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+'
        github_pattern = r'(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_-]+'
        portfolio_pattern = r'(?:https?://)?(?:www\.)?[a-zA-Z0-9_-]+\.(?:com|org|net|io|me)'
        
        linkedin = re.search(linkedin_pattern, cleaned_text, re.IGNORECASE)
        if linkedin:
            val = linkedin.group(0)
            if not val.startswith("http"): val = "https://" + val
            result["links"]["linkedin"] = val
            
        github = re.search(github_pattern, cleaned_text, re.IGNORECASE)
        if github:
            val = github.group(0)
            if not val.startswith("http"): val = "https://" + val
            result["links"]["github"] = val
            
        # Parse portfolio / other links
        all_links = re.findall(r'(?:https?://)[^\s]+', cleaned_text)
        # Fallback to general domain-like words if no https prefix found
        if not all_links:
            all_links = re.findall(r'\b[a-zA-Z0-9.-]+\.(?:com|org|net|io|me)\b', cleaned_text)

        # Domains that belong to email providers — must never be treated as portfolio URLs
        _EMAIL_PROVIDER_DOMAINS = {
            "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
            "icloud.com", "protonmail.com", "live.com", "msn.com",
            "ymail.com", "rediffmail.com", "aol.com", "zoho.com",
        }

        for link in all_links:
            link = link.rstrip('.,;()[]{}')
            # Skip if it contains @ — it's an email address fragment, not a URL
            if "@" in link:
                continue
            # Skip LinkedIn and GitHub (already captured above)
            if "linkedin.com" in link or "github.com" in link:
                continue
            # Strip protocol for domain comparison
            bare = re.sub(r'^https?://(www\.)?', '', link).rstrip('/')
            # Skip known email provider domains
            if any(bare == d or bare.startswith(d + '/') for d in _EMAIL_PROVIDER_DOMAINS):
                continue
            if not result["links"]["portfolio"] and re.search(portfolio_pattern, link):
                result["links"]["portfolio"] = link
            else:
                if link not in result["links"]["other"]:
                    result["links"]["other"].append(link)

        # 4. Extract Candidate Name
        # In recruiter notes, name might appear as "Candidate: John Doe" or "Name: John Doe"
        name_match = re.search(r'(?:Candidate|Name)\s*:\s*([^\n\r]+)', text, re.IGNORECASE)
        if name_match:
            result["full_name"] = name_match.group(1).strip()
        else:
            # Fallback: assume the first non-empty line in a resume is the name
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            for line in lines[:3]:
                # Exclude header words, contact info, page markers
                if (len(line.split()) in [2, 3] and 
                    "page" not in line.lower() and 
                    "resume" not in line.lower() and 
                    "cv" not in line.lower() and 
                    "@" not in line):
                    result["full_name"] = line
                    break

        # 5. Skill Extraction using predefined dictionary keyword matches
        skill_dict = [
            "python", "java", "javascript", "typescript", "c++", "c#", "rust", "go",
            "html", "css", "sql", "nosql", "postgresql", "mysql", "mongodb", "redis",
            "fastapi", "django", "flask", "react", "next.js", "angular", "vue",
            "docker", "kubernetes", "aws", "gcp", "azure", "ci/cd", "git",
            "machine learning", "deep learning", "nlp", "computer vision", "yolo",
            "data science", "pandas", "numpy", "tensorflow", "pytorch", "faiss"
        ]
        text_lower = text.lower()
        extracted_skills = []
        for skill in skill_dict:
            # Use lookarounds instead of \b to properly match skills containing symbols like C++ or C#
            pattern = r'(?<!\w)' + re.escape(skill) + r'(?!\w)'
            if re.search(pattern, text_lower):
                # Format to title case or standard
                standard_name = skill.title()
                if skill in ["next.js", "c++", "c#", "ci/cd", "nlp", "aws", "gcp", "yolo", "faiss"]:
                    # Keep specialized casing
                    casing_map = {
                        "next.js": "Next.js", "c++": "C++", "c#": "C#", "ci/cd": "CI/CD",
                        "nlp": "NLP", "aws": "AWS", "gcp": "GCP", "yolo": "YOLO", "faiss": "FAISS"
                    }
                    standard_name = casing_map.get(skill, standard_name)
                extracted_skills.append(standard_name)
        result["skills"] = list(set(extracted_skills))

        # 6. Extract Headline/Bio
        # Heuristics: Search for a paragraph after the name or keywords like "Professional Summary", "About Me", "Bio"
        bio_match = re.search(r'(?:Summary|About\s*Me|Bio|Profile)\s*\n+(.+?)(?=\n\s*(?:Experience|Work|Education|Skills|\d))', text, re.DOTALL | re.IGNORECASE)
        if bio_match:
            result["headline"] = re.sub(r'\s+', ' ', bio_match.group(1)).strip()

        # 7. Extract Work Experience Section
        # Find sections containing Experience, Work History, Employment
        exp_match = re.search(r'(?:Experience|Work\s*History|Employment\s*History)\s*\n+(.+?)(?=\n\s*(?:Education|Skills|Projects|Certifications|$))', text, re.DOTALL | re.IGNORECASE)
        if exp_match:
            exp_text = exp_match.group(1)
            # Find individual entries. Typically lines starting with date range or company name
            # Let's split by paragraph and look for job indicators
            paragraphs = [p.strip() for p in exp_text.split("\n\n") if p.strip()]
            for p in paragraphs:
                lines = [l.strip() for l in p.split("\n") if l.strip()]
                if not lines:
                    continue
                # First line of paragraph is usually company and title
                company_title_line = lines[0]
                company = "Unknown Company"
                title = "Unknown Title"
                
                # Split by separators like "at", "at the", "|", "-", ","
                parts = re.split(r'\s+at\s+|\s*\|\s*|\s*-\s*|\s*,\s*', company_title_line, maxsplit=1)
                if len(parts) == 2:
                    title = parts[0].strip()
                    company = parts[1].strip()
                else:
                    company = company_title_line
                
                # Try to extract dates (e.g. Jan 2020 - Present, 2020-01 to 2023-05)
                start_date = None
                end_date = None
                date_match = re.search(r'([A-Za-z]+ \d{4}|\d{4}-\d{2}|\d{2}/\d{4})\s*(?:-|to)\s*(Present|Current|[A-Za-z]+ \d{4}|\d{4}-\d{2}|\d{2}/\d{4})', p, re.IGNORECASE)
                if date_match:
                    start_date = date_match.group(1)
                    end_date = date_match.group(2)
                
                summary = " ".join(lines[1:]) if len(lines) > 1 else "Extracted from resume text."
                
                result["experience"].append({
                    "company": company,
                    "title": title,
                    "start": start_date,
                    "end": end_date,
                    "summary": summary
                })

        # 8. Extract Education Section
        edu_match = re.search(r'(?:Education|Academic\s*History|University|College)\s*\n+(.+?)(?=\n\s*(?:Experience|Work|Skills|Projects|Certifications|$))', text, re.DOTALL | re.IGNORECASE)
        if edu_match:
            edu_text = edu_match.group(1)
            paragraphs = [p.strip() for p in edu_text.split("\n\n") if p.strip()]
            for p in paragraphs:
                lines = [l.strip() for l in p.split("\n") if l.strip()]
                if not lines:
                    continue
                
                inst = lines[0]
                # If first line starts with a degree prefix, it's a degree/field line, not an institution.
                degree_prefix_match = re.match(r'^(?:B\.?E\.?|B\.?S\.?|B\.?Tech|M\.?S\.?|M\.?Tech|Ph\.?D|Bachelor|Master|Degree)\b', lines[0], re.IGNORECASE)
                if degree_prefix_match:
                    found_inst = False
                    for line in lines[1:]:
                        if any(w in line.lower() for w in ["university", "college", "school", "institute", "academy", "polytechnic"]):
                            inst = line
                            found_inst = True
                            break
                    if not found_inst and len(lines) > 1:
                        inst = lines[1]
                    elif not found_inst:
                        inst = "Unknown Institution"

                degree = None
                field = None
                end_year = None
                
                # Check for degree indicators
                degree_match = re.search(r'\b(B\.?S\.?|M\.?S\.?|B\.?E\.?|B\.?Tech|Ph\.?D|Bachelor|Master|Degree)\b', p, re.IGNORECASE)
                if degree_match:
                    degree = degree_match.group(1)
                    
                field_match = re.search(r'(?:in|major in|of)\s+([A-Za-z\s]{3,30})', p, re.IGNORECASE)
                if field_match:
                    field = field_match.group(1).strip()
                elif degree_match:
                    deg_span_end = degree_match.end()
                    after_deg = p[deg_span_end:].strip()
                    after_deg = re.sub(r'^[.,\s]+(?:in|of|major\s+in)?\s+', '', after_deg, flags=re.IGNORECASE)
                    field_parts = re.split(r'\b(?:19\d{2}|20\d{2}|present|current|ongoing)\b', after_deg, flags=re.IGNORECASE)
                    if field_parts:
                        field_candidate = field_parts[0].strip().rstrip('.,;()[]{}–-— \t')
                        if len(field_candidate) >= 3:
                            field = field_candidate
                    
                # Chronological token-based date extraction (resilient to slashes, months, and spaces)
                date_tokens = re.findall(r'\b(19\d{2}|20\d{2}|present|current|ongoing|now)\b', p, re.IGNORECASE)
                if date_tokens:
                    last_token = date_tokens[-1].lower()
                    if last_token in ["present", "current", "ongoing", "now"]:
                        end_year = None
                    else:
                        try:
                            end_year = int(last_token)
                        except ValueError:
                            end_year = None
                    
                result["education"].append({
                    "institution": inst,
                    "degree": degree,
                    "field": field,
                    "end_year": end_year
                })

        # Estimate years of experience from jobs
        total_months = 0
        for exp in result["experience"]:
            # Simple heuristic: parse years from dates
            start = exp.get("start")
            end = exp.get("end")
            if start and end:
                start_year_m = re.search(r'\b(19\d{2}|20\d{2})\b', start)
                end_year_m = re.search(r'\b(19\d{2}|20\d{2})\b', end)
                if start_year_m and end_year_m:
                    s_yr = int(start_year_m.group(1))
                    e_yr = int(end_year_m.group(1))
                    total_months += (e_yr - s_yr) * 12
                elif start_year_m and "present" in end.lower():
                    s_yr = int(start_year_m.group(1))
                    total_months += (2026 - s_yr) * 12  # Reference year is 2026
        if total_months > 0:
            result["years_experience"] = round(total_months / 12, 1)

        return result
