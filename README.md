# Multi-Source Candidate Data Transformer

A production-grade candidate data ingestion, normalization, and merging platform built as part of the Eightfold Engineering Intern assignment. 

The system ingests, normalizes, matches candidate profiles, resolves merge conflicts using a configurable attribute-level priority engine, tracks value lineage (provenance), and projects custom output shapes dynamically at runtime using a JSON configuration file.

---

## 🚀 Key Features

* **Ports & Adapters Architecture**: Clean separation between data sources (adapters), extraction models (parsers), core normalization, and output formatting (projections).
* **Heterogeneous Ingestion**: Out-of-the-box support for:
  * **Structured Sources**: Recruiter CSV exports, ATS JSON blobs.
  * **Unstructured Sources**: PDF Resumes, Word (.docx) Resumes, Recruiter Notes (.txt).
* **Deterministic Identity Resolution**: Matches candidates automatically by hashing and checking overlap of primary identifiers (emails, phone numbers).
* **Attribute-Level Provenance & Merging**: Merges candidate profiles field-by-field. Conflict resolution follows a hierarchy: **Source Priority** (configured via JSON) $\rightarrow$ **Extraction Confidence** $\rightarrow$ **Recency (Timestamp)**.
* **Configurable Projection Engine**: Runtime JSON config shapes the output without modifying source code (supports field remapping, subset selection, output-time anonymization, and missing-value fallbacks).
* **Industrial Validation**: Uses Pydantic v2 for strict type safety and business validation.

---

## 📂 Project Structure

```text
resume_parser/
├── config/
│   ├── default_projection.json    # Default full candidate schema configuration
│   └── custom_projection.json     # Custom subset and remapped configuration
├── src/
│   ├── __init__.py
│   ├── main.py                    # Pipeline Orchestrator and CLI Entrypoint
│   ├── adapters/                  # Ingestion Layer (loads files and extracts raw text)
│   │   ├── base.py
│   │   ├── csv_adapter.py
│   │   ├── json_adapter.py
│   │   ├── pdf_adapter.py
│   │   ├── docx_adapter.py
│   │   └── notes_adapter.py
│   ├── parser/                    # Parsing Layer (extracts raw fields from source text)
│   │   ├── base.py
│   │   ├── structured_parser.py
│   │   └── text_parser.py
│   ├── normalizers/               # Cleaning Layer (E.164 phones, YYYY-MM dates, title case)
│   │   ├── __init__.py
│   │   └── normalizer.py
│   ├── models/                    # Data models (Canonical schema & provenance wrappers)
│   │   ├── __init__.py
│   │   └── canonical.py
│   ├── identity/                  # Entity matching layer (deterministic hashing)
│   │   ├── __init__.py
│   │   └── resolver.py
│   ├── merge/                     # Merge & Conflict resolution engine
│   │   ├── __init__.py
│   │   └── engine.py
│   ├── projection/                # Output projection engine (runtime configurable mapping)
│   │   ├── __init__.py
│   │   └── engine.py
│   └── utils/
│       └── pdf_generator.py       # Compiled PDF design document generator
├── tests/                         # Unit and integration test suites
│   ├── test_normalizers.py
│   ├── test_merge.py
│   ├── test_projection.py
│   └── test_pipeline.py
├── requirements.txt               # Dependencies
├── demo.py                        # Automated demonstration runner
├── generate_pdf.py                # Compiles the 1-page Design Document
└── Kaviyadharshini_M_kaviyadharshini.works@gmail.com_Eightfold.pdf # Compiled design PDF
```

---

## 🛠️ Setup & Execution

### 1. Prerequisites
Ensure Python 3.10+ is installed.

### 2. Install Dependencies
Set up a virtual environment and install the required libraries:
```bash
python -m venv venv
venv\Scripts\activate      # On Windows (use source venv/bin/activate on Unix)
pip install -r requirements.txt
```

### 3. Run the Demonstration
Run the automated demo script, which creates mock CSV/Notes files, runs both default and custom configurations, and prints the outputs to stdout:
```bash
python demo.py
```

### 4. Run the Pipeline CLI
Ingest custom files by calling the main entrypoint:
```bash
python src/main.py -i <path_to_file1> <path_to_file2> -c config/default_projection.json -o output/result.json
```

---

## 🧪 Running Tests

We achieve high reliability using `pytest` for unit and integration testing. Run the full test suite with:
```bash
python -m pytest tests/
```

---

## 📝 Design One-Pager (Deliverable)

The assignment requires a one-page design document PDF outlining pipeline workflows, normalization choices, and edge cases.
* **Location**: [Kaviyadharshini_M_kaviyadharshini.works@gmail.com_Eightfold.pdf](file:///E:/Projects/Resume%20Parser/Kaviyadharshini_M_kaviyadharshini.works@gmail.com_Eightfold.pdf)
* **Re-compile**: If you want to re-compile this PDF, run:
  ```bash
  python generate_pdf.py
  ```
