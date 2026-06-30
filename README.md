# Candidate Intelligence Platform

A system I built for the Eightfold Engineering Intern assignment to solve a real headache in recruitment: candidate data scattered across resumes, ATS exports, recruiter notes, and spreadsheets, all saying slightly different things about the same person.

This platform pulls all of that together, cleans it up, resolves the conflicts, and produces one trustworthy "golden record" per candidate — with a clear trail showing exactly where each piece of data came from.

## Why this exists

In real recruiting workflows, the same candidate's info often lives in five different places: LinkedIn, the ATS, an emailed resume, recruiter notes, maybe a CSV from a sourcing tool. These don't agree with each other half the time. This project is my attempt at building the "central brain" that reconciles all of that into a single clean profile recruiters and analysts can actually trust.

## What it does

- Ingests candidates from CSVs, ATS JSON exports, PDF/DOCX resumes, recruiter notes, and optionally GitHub profiles
- Normalizes and cleans fields (names, emails, phone numbers, skills, locations)
- Matches records that belong to the same person, even when the source data is messy
- Resolves conflicts using configurable priority rules (e.g. "trust ATS over a scanned resume")
- Tracks provenance — every field remembers which source it came from and how confident the system is
- Reshapes the final output on the fly using a YAML/JSON config, without touching the core code
- Validates everything with Pydantic before it goes out the door

## Tech stack

**Backend:** Python, FastAPI, Pydantic, Pandas, PyMuPDF, python-docx, RapidFuzz
**Frontend:** Streamlit, Plotly
**Testing:** PyTest

## Project layout

```
candidate-ai-engine/
├── backend/
│   └── app/
│       ├── canonicalizers/
│       ├── extractors/
│       ├── merge_engine/
│       ├── normalizers/
│       ├── projection/
│       ├── schemas/
│       └── main.py
├── frontend/streamlit/dashboard.py
├── sample_data/
├── tests/
├── requirements.txt
└── config.toml
```

## How a candidate flows through the system

Source detection → extraction → normalization → canonicalization → entity resolution → conflict resolution → confidence scoring → provenance tracking → projection → validation → final JSON.

## Getting it running

```bash
git clone https://github.com/kaviyadharshini2805/Candidate-Intelligence-Platform.git
cd Candidate-Intelligence-Platform
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

It'll open at `http://localhost:8501`. Run the tests anytime with `pytest tests/`, and sample output lives in `sample_output/output.json`.

## What a canonical profile looks like

```json
{
  "full_name": "Example Name",
  "emails": ["example@gmail.com"],
  "phones": ["+91XXXXXXXXXX"],
  "skills": ["Python", "SQL", "FastAPI", "Machine Learning"],
  "location": { "city": "Chennai", "region": "Tamil Nadu", "country": "IN" },
  "overall_confidence": 0.92,
  "field_provenance": {
    "email": { "source": "ATS", "confidence": 0.95 }
  }
}
```

## Configurable output shape

The internal data model never changes, but you can reshape what gets exported using a simple config — handy when different teams want different views of the same data.

```yaml
fields:
  - path: candidate_full_name
    from: full_name
  - path: primary_contact_email
    from: emails[0]
  - path: verified_phone
    from: phones[0]
include_provenance: false
include_confidence: false
on_missing: omit
```

Which produces something like:

```json
{
  "candidate_full_name": "Example Name",
  "primary_contact_email": "example@gmail.com",
  "verified_phone": "+91XXXXXXXXXX"
}
```

## Dashboard

Upload files, watch the pipeline run step by step, inspect the canonical and projected outputs side by side, check confidence scores, compare sources, tweak the projection config, export to JSON/PDF, and toggle dark mode if that's your thing.

## A few honest notes

This was built as an assignment, so some things are intentionally out of scope: no live LinkedIn scraping (rate limits and ToS issues), no cloud database (everything's in-memory), and no custom ML training — entity matching relies on deterministic rules and fuzzy string matching (RapidFuzz) rather than a trained model. Email and phone number are treated as the primary identity keys, and conflict resolution follows fixed priority rules rather than learned ones.

## Try it live

[Live demo on Streamlit](https://candidate-intelligence-platform-nth6plavdpzorspnfpyxtr.streamlit.app/)

## Author

**Kaviyadharshini**
[Email](mailto:kaviyadharshini.works@gmail.com) · [GitHub](https://github.com/kaviyadharshini2805) · [LinkedIn](https://www.linkedin.com/in/kaviyadharshini-works)

Built as part of the Eightfold Engineering Intern assignment. Questions or issues — reach out above or open a GitHub issue.
