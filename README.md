
# Candidate Intelligence Engine

A production-grade candidate data ingestion, normalization, and merging platform built as part of the Eightfold Engineering Intern assignment.

The system ingests, normalizes, and matches candidate profiles from multiple structured and unstructured sources. It resolves merge conflicts using a configurable attribute-level priority engine, tracks value lineage (provenance), and generates a unified canonical candidate profile.

The **Candidate Intelligence Engine** is a production-style AI engineering system that consolidates fragmented candidate information into a single validated canonical profile. It also supports runtime-configurable output projection using JSON/YAML configuration files, enabling dynamic reshaping of the final output without modifying core application logic.

# Candidate Intelligence Platform

## 1. Project Overview
The Candidate Intelligence Platform is a robust, production-grade system designed to ingest, normalize, and merge candidate profiles from diverse sources (such as ATS JSON exports, recruiter CSVs, and PDF/Word resumes). It automatically resolves identity conflicts, tracks the provenance of each data field, and produces structured canonical outputs.

**Real-world use case (HR / recruitment analytics):** In modern recruitment, candidate data is often scattered across multiple platforms (LinkedIn, ATS, email, raw resumes). This platform acts as a central intelligence engine, unifying fragmented profiles into a single "Golden Record." This enables HR teams and recruitment analysts to perform accurate talent analytics, matching, and reporting without dealing with duplicate or conflicting records.
>>>>>>> 0fd0377 (Removed Placeholders)

## 2. Tech Stack
* **Python**: Core data processing and pipeline orchestration.
* **Streamlit**: Interactive user interface for uploading files and viewing conflict resolution.
* **RapidFuzz**: Fuzzy string matching for robust identity resolution and name similarity.
* **Pydantic**: Data validation and strict typing for canonical models.

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

### Core Capabilities

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

## Processing Pipeline

The system follows a deterministic and explainable pipeline:

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

## Getting Started

### Prerequisites

- Python 3.8+
- pip package manager
- Virtual environment (recommended)

### Installation & Setup

#### 1. Clone the Repository

```bash
git clone https://github.com/kaviyadharshini2805/Candidate-Intelligence-Platform.git
```

#### 2. Navigate to Project Folder

```bash
cd Candidate-Intelligence-Platform
```

#### 3. Create Virtual Environment (Recommended)

```bash
python -m venv venv
```

**Activate the Virtual Environment:**

**Windows:**
```bash
venv\Scripts\activate
```

**Mac/Linux:**
```bash
source venv/bin/activate
```

#### 4. Install Dependencies

```bash
## 3. Run Instructions
To run this project locally, execute the following commands in your terminal:

```bash
git clone <repo>
cd Candidate-Intelligence-Platform
>>>>>>> 0fd0377 (Removed Placeholders)
pip install -r requirements.txt
streamlit run app.py
```

#### 5. Run the Application

**Start the Streamlit Dashboard:**
```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`

#### 6. Run Tests

```bash
pytest tests/
```

#### 7. View Output

- Upload input files in the Streamlit UI
- Or check sample results in:
```
sample_output/output.json
```

---

## Internal Canonical Profile

The system generates a unified canonical profile with the following structure:

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

The internal model remains unchanged while output is dynamically reshaped using YAML/JSON configuration files. This enables dynamic reshaping of the final output without modifying core application logic.

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

All outputs are validated using Pydantic to ensure data integrity:

- Required field validation
- Data type validation
- Email format validation
- Phone format validation
- Country code validation
- JSON schema validation

---

## Testing

Run the test suite to verify functionality:

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

## Design Principles

- Clean Architecture
- SOLID Principles
- Modular Design
- Deterministic Processing
- Explainable Systems
- Configuration-Driven Development
- Production-Oriented Engineering

---

## Assumptions

- Input data is partially structured
- Email/phone are primary identity keys
- Rule-based deterministic conflict resolution
- In-memory processing without database

---

## Descoped Features

The following features were intentionally not implemented in this version:

- No real-time LinkedIn scraping
- No cloud database integration
- No ML training pipeline
- No distributed system architecture

---

## Live Demo

[![Try the live application here](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://candidate-intelligence-platform-nth6plavdpzorspnfpyxtr.streamlit.app/)

---

## Author

**Kaviyadharshini**

- Email: [kaviyadharshini.works@gmail.com](mailto:kaviyadharshini.works@gmail.com)
- GitHub: [https://github.com/kaviyadharshini2805](https://github.com/kaviyadharshini2805)
- LinkedIn: [https://www.linkedin.com/in/kaviyadharshini-works](https://www.linkedin.com/in/kaviyadharshini-works)

---

## License

This project is part of the Eightfold Engineering Intern assignment.

---

## Support

For issues, questions, or contributions, please reach out via the contact information above or open an issue on GitHub.
=======
## 4. Output Example
Below is a mock representation of the generated Golden Record output structure:

```json
{
  "candidate_id": "123",
  "name": "Example Name",
  "email": "example@gmail.com",
  "skills": ["Python", "SQL"],
  "status": "merged"
}
```

## 5. Tests
The platform includes a comprehensive Pytest suite that validates pipeline execution, identity matching logic, and normalization output structures.

To run the test suite:
```bash
pytest tests/
```

## 6. Assumptions
* **Mock data used**: The system relies on mock candidate data provided in JSON and CSV formats for demonstration purposes.
* **Email/phone as primary identifiers**: The identity resolution engine assumes that emails and phone numbers are the most reliable indicators of a unique candidate.
* **Rule-based conflict resolution**: Conflicts between data sources are resolved using predefined priority rules (e.g., ATS JSON data might be prioritized over raw PDF extraction).

## 7. Descoped Features
* **No real LinkedIn scraping**: The system does not actively scrape live LinkedIn profiles to avoid rate limiting and terms-of-service violations.
* **No cloud DB**: Data is processed in-memory and projected to JSON outputs; no persistent cloud database (like PostgreSQL or MongoDB) is implemented.
* **No ML training pipeline**: The system uses deterministic heuristics and fuzzy matching rather than training custom machine learning models for entity extraction.