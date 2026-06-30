# Multi-Source Candidate Data Transformer

A production-grade candidate data ingestion, normalization, and merging platform built as part of the Eightfold Engineering Intern assignment.

The system ingests, normalizes, and matches candidate profiles from multiple structured and unstructured sources. It resolves merge conflicts using a configurable attribute-level priority engine, tracks value lineage (provenance), and generates a unified canonical candidate profile.

The **Candidate Intelligence Engine** is a production-style AI engineering system that consolidates fragmented candidate information into a single validated canonical profile. It also supports runtime-configurable output projection using JSON/YAML configuration files, enabling dynamic reshaping of the final output without modifying core application logic.

```
The system follows a deterministic and explainable pipeline:

- Source Detection
- Data Extraction
- Normalization
- Canonicalization
- Entity Resolution
- Conflict Resolution
- Confidence Scoring
- Provenance Tracking
- Runtime Projection
- Pydantic Validation
```

The final output is a **configurable JSON profile** generated without modifying application code.

---

## Features

### Supported Input Sources

**Structured Sources**
- Recruiter CSV
- ATS JSON

**Unstructured Sources**
- Resume (PDF)
- Resume (DOCX)
- Recruiter Notes (TXT)
- GitHub Profile URL (optional)

---

## Processing Pipeline

```
Source Detection
→ Data Extraction
→ Normalization
→ Canonicalization
→ Entity Resolution
→ Conflict Resolution
→ Confidence Scoring
→ Provenance Tracking
→ Projection Layer
→ Pydantic Validation
→ Final JSON Output
```

---

## Core Capabilities

- Multi-source candidate ingestion
- Resume parsing
- CSV & ATS JSON processing
- Deterministic merge engine
- Configurable source priority
- Field normalization
- Entity resolution
- Conflict resolution
- Canonical candidate profile generation
- Field-level provenance tracking
- Confidence scoring
- Runtime configurable projection
- Explainable decision-making
- FastAPI REST backend
- Streamlit dashboard

---

## Technology Stack

### Backend
- Python
- FastAPI
- Pydantic
- Pandas
- PyMuPDF
- python-docx
- YAML / JSON

### Frontend
- Streamlit
- Plotly
- Custom CSS

### Testing
- PyTest

---

## Project Structure

```
candidate-ai-engine/
├── backend/
│   ├── app/
│   │   ├── canonicalizers/
│   │   ├── extractors/
│   │   ├── merge_engine/
│   │   ├── normalizers/
│   │   ├── projection/
│   │   ├── schemas/
│   │   └── main.py
│
├── frontend/
│   └── streamlit/
│       └── dashboard.py
│
├── sample_data/
├── tests/
├── requirements.txt
├── config.toml
└── README.md
```

---

## Internal Canonical Profile

```json
{
  "full_name": "Example Name",
  "emails": ["example@gmail.com"],
  "phones": ["+91XXXXXXXXXX"],
  "skills": [
    "Python",
    "SQL",
    "FastAPI",
    "Machine Learning"
  ],
  "location": {
    "city": "Chennai",
    "region": "Tamil Nadu",
    "country": "IN"
  },
  "overall_confidence": 0.92,
  "field_provenance": {
    "email": {
      "source": "ATS",
      "confidence": 0.95
    }
  }
}
```

---

## Runtime Configurable Projection

The internal model remains unchanged while output is dynamically reshaped using YAML/JSON configuration.

### Example Configuration

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

### Output Example

```json
{
  "candidate_full_name": "Example Name",
  "primary_contact_email": "example@gmail.com",
  "verified_phone": "+91XXXXXXXXXX"
}
```

---

## Dashboard Features

- File upload & processing
- Pipeline execution visualization
- Canonical profile viewer
- Projected JSON viewer
- AI insights panel
- Confidence scoring summary
- Source comparison view
- Configuration editor
- JSON & PDF export
- Light/Dark mode toggle

---

## Validation

All outputs are validated using Pydantic:

- Required field validation
- Data type validation
- Email format validation
- Phone format validation
- Country code validation
- JSON schema validation

---

## Testing

```bash
pytest
```

### Test Coverage

- Data extraction
- Normalization
- Merge engine
- Entity resolution
- Projection layer
- Validation
- API endpoints

---

## Assumptions

- Input data is partially structured
- Email/phone are primary identity keys
- Rule-based deterministic conflict resolution
- In-memory processing without database

---

## Descoped Features

- No real-time LinkedIn scraping
- No cloud database integration
- No ML training pipeline
- No distributed system architecture

---

## Running the Project

```bash
git clone https://github.com/kaviyadharshini2805/Candidate-Intelligence-Engine.git
cd Candidate-Intelligence-Engine
pip install -r requirements.txt
streamlit run app.py
```

---

## Design Principles

- Clean Architecture
- SOLID Principles
- Modular Design
- Deterministic Processing
- Explainable Systems
- Configuration-Driven Development
- Production-Oriented Engineering

---

## Live Demo
```
https://candidate-intelligence-platform-nth6plavdpzorspnfpyxtr.streamlit.app/
```

## Author

**Kaviyadharshini**

- Email: kaviyadharshini.works@gmail.com
- GitHub: https://github.com/kaviyadharshini2805
- LinkedIn: https://www.linkedin.com/in/kaviyadharshini-works
