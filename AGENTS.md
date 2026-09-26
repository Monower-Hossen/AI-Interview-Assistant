# AGENTS.md

## Commands

### Lint
```bash
.venv\Scripts\python -m ruff check .
```

### Lint & Auto-Fix
```bash
.venv\Scripts\python -m ruff check . --fix
```

### Format
```bash
.venv\Scripts\python -m black .
```

### Type Check
```bash
.venv\Scripts\python -m mypy .
```

### Tests
```bash
.venv\Scripts\python -m pytest tests/ -v
```

### Tests with Coverage
```bash
.venv\Scripts\python -m pytest tests/ --cov=services --cov=rag --cov=utils --cov=database -v
```

### Run App
```bash
.venv\Scripts\python -m streamlit run app.py
```

### Install Dev Dependencies
```bash
.venv\Scripts\pip install -r requirements-dev.txt
```

## Project Structure

```
ai-interview-assistant/
├── app.py                      # Main Streamlit application entry point
├── requirements.txt            # Python dependencies (runtime)
├── requirements-dev.txt        # Python dependencies (development)
├── pyproject.toml              # Project config (ruff, mypy, pytest, black)
├── .env.example                # Environment variables template
├── .gitignore                  # Git ignore rules
├── README.md                   # Project documentation
├── AGENTS.md                   # This file
│
├── config/
│   ├── __init__.py             # Config exports
│   └── settings.py             # Configuration management
│
├── database/
│   ├── __init__.py             # Database exports
│   ├── db.py                   # SQLAlchemy setup
│   └── models.py               # SQLAlchemy models
│
├── rag/
│   ├── __init__.py             # RAG exports
│   ├── document_loader.py      # PDF/DOCX/TXT loading
│   ├── text_splitter.py        # Text chunking
│   ├── embeddings.py           # Sentence Transformers embeddings
│   ├── vector_store.py         # FAISS vector storage
│   └── retriever.py            # Document retrieval
│
├── services/
│   ├── __init__.py             # Services exports
│   ├── llm_service.py          # LLM abstraction (Groq/Gemini/Mistral)
│   ├── resume_analyzer.py      # Resume analysis & scoring
│   ├── job_analyzer.py         # Job description analysis
│   ├── job_matcher.py          # Resume-Job matching
│   ├── interview_generator.py  # Question generation
│   ├── answer_evaluator.py     # Answer evaluation
│   ├── report_generator.py     # Report generation
│   └── speech_to_text.py       # Whisper transcription
│
├── ui/
│   ├── __init__.py             # UI exports
│   ├── dashboard.py            # Dashboard page
│   ├── resume_page.py          # Resume analyzer page
│   ├── job_page.py             # Job matcher page
│   ├── interview_page.py       # Mock interview page
│   ├── report_page.py          # Reports page
│   └── settings_page.py        # Settings page
│
├── utils/
│   ├── __init__.py             # Utils exports
│   ├── file_utils.py           # File handling utilities
│   └── helpers.py              # Helper functions
│
├── data/                       # Data directory (gitignored)
│   ├── uploads/                # Uploaded files
│   └── vector_store/           # FAISS index
│
└── tests/
    ├── conftest.py             # Pytest fixtures (env isolation, settings, temp dirs)
    └── test_core.py            # Unit tests
```

## Key Modules

- **config.settings**: Centralized configuration via pydantic-like dataclass, loads from `.env`
- **services.llm_service**: Multi-provider LLM with automatic fallback (Groq → Gemini → Mistral)
- **services.resume_analyzer**: Resume parsing, scoring, structured output validation
- **services.job_analyzer**: Job description parsing, requirement extraction
- **services.job_matcher**: Resume-JD matching, gap analysis, recommendations
- **services.interview_generator**: 7-category question generation with difficulty levels
- **services.answer_evaluator**: 5-dimensional answer scoring (0-10) with feedback
- **services.report_generator**: Interview reports with improvement plans
- **rag/**: Complete RAG pipeline (load → split → embed → store → retrieve)
- **database/**: SQLAlchemy models for sessions, analyses, matches, interviews, evaluations
- **utils/helpers**: Text cleaning, email/phone extraction, skill deduplication, JSON parsing
- **utils/file_utils**: File validation, sanitization, type detection

## Test Fixtures (conftest.py)

- `isolate_environment` (autouse): Restores os.environ after each test
- `mock_settings`: Fresh Settings instance with test-safe defaults
- `temp_data_dir`: Temporary data directories for file/vector/db operations