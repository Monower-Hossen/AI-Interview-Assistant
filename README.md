# AI Interview Assistant

## Overview

AI Interview Assistant is a comprehensive, production-quality application designed to help students and job seekers prepare for real-world job interviews. Built as a Final Year University Project, it demonstrates expertise in Generative AI, LLMs, RAG, Vector Databases, Embeddings, Prompt Engineering, Speech-to-Text, and modern software engineering practices.

The application analyzes resumes, matches them against job descriptions, generates personalized interview questions, conducts mock interviews with AI evaluation, and provides detailed performance reports with improvement plans.

## Features

### 📄 Resume Analysis
- Upload PDF, DOCX, or TXT resumes
- Extract structured information: education, experience, skills, projects, certifications
- AI-powered scoring across 6 categories (Technical Skills, Experience, Projects, Education, Certifications, Structure)
- Contact information extraction (email, phone, LinkedIn, GitHub, portfolio)

### 🎯 Job Description Matching
- Paste or upload job descriptions
- Extract requirements: skills, experience, education, responsibilities, keywords
- Compare resume vs job description with detailed match scores
- Identify matching skills, missing skills, skill gaps, and experience gaps
- Actionable recommendations for improvement

### 🤖 Interview Question Generation
- 7 question categories: Technical, HR, Behavioral, Situational, Project-based, Resume-based, Job-specific
- 3 difficulty levels: Easy, Medium, Hard
- Personalized questions based on resume, job description, and skill gaps
- Dynamic follow-up question generation based on answers

### 🎤 Mock Interview Engine
- Interactive interview sessions with real-time AI evaluation
- Text and voice answer modes
- Voice answers transcribed using local Whisper (no paid APIs)
- Immediate feedback after each answer

### 📊 Answer Evaluation
- 5-dimensional scoring (0-10): Technical Accuracy, Relevance, Communication, Confidence, Completeness
- Detailed feedback: strengths, weaknesses, missing points, incorrect points
- Suggested better answers
- Communication and technical feedback

### 📈 Interview Reports
- Overall, Technical, Communication, HR, and Problem-Solving scores
- Strengths and weaknesses analysis
- Frequently missed concepts
- Recommended topics, projects, and practice questions
- 7-day and 30-day improvement plans

### 📊 Dashboard & Progress Tracking
- Resume score, job match score, latest interview score
- Interview history with score trends
- Skill gap visualization
- Progress charts over time

## Architecture

```
ai-interview-assistant/
├── app.py                      # Main Streamlit application entry point
├── requirements.txt            # Python dependencies
├── requirements-dev.txt        # Development dependencies
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
├── README.md                  # This file
│
├── config/
│   ├── __init__.py            # Config exports
│   └── settings.py            # Configuration management
│
├── database/
│   ├── __init__.py            # Database exports
│   ├── db.py                  # SQLAlchemy setup
│   └── models.py              # SQLAlchemy models
│
├── rag/
│   ├── __init__.py            # RAG exports
│   ├── document_loader.py     # PDF/DOCX/TXT loading
│   ├── text_splitter.py       # Text chunking
│   ├── embeddings.py          # Sentence Transformers embeddings
│   ├── vector_store.py        # FAISS vector storage
│   └── retriever.py           # Document retrieval
│
├── services/
│   ├── __init__.py            # Services exports
│   ├── llm_service.py         # LLM abstraction (Groq/Gemini/Mistral)
│   ├── resume_analyzer.py     # Resume analysis & scoring
│   ├── job_analyzer.py        # Job description analysis
│   ├── job_matcher.py         # Resume-Job matching
│   ├── interview_generator.py # Question generation
│   ├── answer_evaluator.py    # Answer evaluation
│   ├── report_generator.py    # Report generation
│   └── speech_to_text.py      # Whisper transcription
│
├── ui/
│   ├── __init__.py            # UI exports
│   ├── dashboard.py           # Dashboard page
│   ├── resume_page.py         # Resume analyzer page
│   ├── job_page.py            # Job matcher page
│   ├── interview_page.py      # Mock interview page
│   ├── report_page.py         # Reports page
│   └── settings_page.py       # Settings page
│
├── utils/
│   ├── __init__.py            # Utils exports
│   ├── file_utils.py          # File handling utilities
│   └── helpers.py             # Helper functions
│
├── data/                      # Data directory (gitignored)
│   ├── uploads/               # Uploaded files
│   └── vector_store/          # FAISS index
│
└── tests/
    ├── conftest.py            # Pytest fixtures
    └── test_core.py           # Unit tests
```

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **LLM** | Groq (Llama 3.1) / Gemini / Mistral | Primary/Alternative LLM providers (free tiers) |
| **Embeddings** | Sentence Transformers (all-MiniLM-L6-v2) | Local text embeddings |
| **Vector DB** | FAISS | Local vector similarity search |
| **Speech-to-Text** | Faster-Whisper | Local audio transcription |
| **Frontend** | Streamlit | Web UI framework |
| **Database** | SQLite + SQLAlchemy | Local data persistence |
| **Document Processing** | PyPDF, python-docx | PDF/DOCX text extraction |
| **LLM Orchestration** | LangChain Core | Prompts, structured output |
| **Testing** | pytest | Unit testing |
| **Code Quality** | Ruff, Black, mypy | Linting, formatting, type checking |

## Project Structure

See the Architecture section above for the complete directory structure.

## Installation

### Prerequisites
- Python 3.10+
- Git
- (Optional) FFmpeg for audio processing

### Windows PowerShell

```powershell
# Clone the repository
git clone <your-repo-url>
cd ai-interview-assistant

# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Copy environment template
Copy-Item .env.example .env

# Edit .env with your API keys
notepad .env

# Run the application
streamlit run app.py
```

### Using uv (faster)

```bash
# Install uv if not available
pip install uv

# Create environment and install
uv venv
.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
```

### Linux/macOS

```bash
git clone <your-repo-url>
cd ai-interview-assistant
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
streamlit run app.py
```

## Python Version

- **Recommended:** Python 3.10 or 3.11
- **Minimum:** Python 3.10
- **Tested:** Python 3.10, 3.11, 3.12

## Virtual Environment

Always use a virtual environment to avoid dependency conflicts:

```bash
# Create
python -m venv .venv

# Activate (Windows)
.venv\Scripts\Activate.ps1

# Activate (Linux/macOS)
source .venv/bin/activate

# Deactivate
deactivate
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Required - Choose provider mode
LLM_PROVIDER=auto                    # auto, groq, gemini, or mistral
PROVIDER_PRIORITY=groq,gemini,mistral  # Order for auto mode

# Groq API (Primary - generous free tier)
# Get from: https://console.groq.com/keys
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=groq/compound
GROQ_BASE_URL=https://api.groq.com/openai/v1

# Gemini API (Alternative - generous free tier)
# Get from: https://aistudio.google.com/apikey
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai

# Mistral API (Alternative - Free tier available)
# Get from: https://console.mistral.ai/
MISTRAL_API_KEY=your_mistral_api_key_here
MISTRAL_MODEL=mistral-small-latest
MISTRAL_BASE_URL=https://api.mistral.ai/v1

# Embeddings (local, no API key needed)
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DEVICE=cpu

# Whisper (local speech-to-text)
WHISPER_MODEL=base                    # tiny, base, small, medium, large
WHISPER_DEVICE=cpu                    # cpu or cuda

# Vector Database
VECTOR_STORE_TYPE=faiss               # FAISS vector store
VECTOR_STORE_PATH=./data/vector_store

# Database
DATABASE_PATH=./data/interview_assistant.db

# RAG Settings
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_RETRIEVAL=5

# API Settings
REQUEST_TIMEOUT=60
MAX_RETRIES=3
RETRY_BACKOFF_FACTOR=1.5

# Streamlit
STREAMLIT_PORT=8501
STREAMLIT_THEME=light
```

### Groq API Setup
1. Go to https://console.groq.com/keys
2. Create a new API key
3. Add to `.env` as `GROQ_API_KEY`
4. Free tier: 14,400 requests/day, 6,000 tokens/minute

### Gemini API Setup
1. Go to https://aistudio.google.com/apikey
2. Create a new API key
3. Add to `.env` as `GEMINI_API_KEY`
4. Free tier available

### Mistral API Setup
1. Go to https://console.mistral.ai/
2. Create a new API key
3. Add to `.env` as `MISTRAL_API_KEY`
4. Free tier available

## Running the Application

```bash
# Activate virtual environment
.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate  # Linux/macOS

# Run Streamlit app
streamlit run app.py

# Or specify port
streamlit run app.py --server.port 8501
```

The app will open at `http://localhost:8501`

## Example Workflow

1. **Start** - Open the app, you'll see the Dashboard
2. **Analyze Resume** - Go to "📄 Resume Analyzer", upload your resume (PDF/DOCX), click "Analyze"
3. **Analyze Job** - Go to "🎯 Job Matcher", paste or upload a job description, click "Analyze"
4. **Match** - Click "Match Resume with Job" to see compatibility scores and gaps
5. **Setup Interview** - Go to "🤖 Interview Setup", configure interview type/difficulty/questions, click "Generate Questions"
6. **Mock Interview** - Go to "🎤 Mock Interview", answer questions via text or voice
7. **View Report** - After completing, go to "📊 Interview Report" for detailed analysis
8. **Track Progress** - Dashboard shows your improvement over time

## Screenshots

*[Add screenshots here after running the application]*

- Dashboard with metrics and charts
- Resume analysis with scores
- Job match results with gaps
- Interview session in progress
- Answer evaluation feedback
- Final interview report
- Settings configuration

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=services --cov=rag --cov=utils --cov=database -v

# Run specific test file
pytest tests/test_core.py -v

# Run tests with coverage report
pytest tests/ --cov=services --cov=rag --cov=utils --cov=database --cov-report=html
```

### Linting & Formatting

```bash
# Lint with Ruff
ruff check .

# Auto-fix lint issues
ruff check . --fix

# Format with Black
black .

# Type check with mypy
mypy .

# Run all checks (CI style)
ruff check . && black --check . && mypy .
```

### Test Structure
- `tests/conftest.py` - Pytest fixtures for isolation
- `tests/test_core.py` - Core functionality tests (models, utilities, services)

### Mocking
Tests use mocked LLM responses to run without API keys.

## Troubleshooting

### Common Issues

**1. "ModuleNotFoundError: No module named 'faster_whisper'"**
```bash
pip install faster-whisper
```

**2. "CUDA out of memory" or Whisper slow**
- Use smaller model: `WHISPER_MODEL=tiny` or `base`
- Ensure `WHISPER_DEVICE=cpu` if no GPU

**3. "Groq API rate limit exceeded"**
- Wait and retry (automatic retry with backoff implemented)
- Check quota at https://console.groq.com/

**4. "FAISS index not found"**
- First run creates the index automatically
- Check `data/vector_store/` permissions

**5. "Database locked"**
- Close other instances of the app
- Check file permissions on `data/interview_assistant.db`

**6. "File too large"**
- Increase `MAX_FILE_SIZE_MB` in `.env`
- Compress PDF before upload

**7. Audio recording not working in browser**
- Use HTTPS or localhost (browser security)
- Allow microphone permissions
- Try text mode as alternative

### Performance Tips
- Use `WHISPER_MODEL=tiny` for fastest transcription
- Reduce `CHUNK_SIZE` for faster embedding

## Future Improvements

- [ ] Multi-user authentication
- [ ] Export reports as PDF
- [ ] Interview scheduling calendar
- [ ] Company-specific question banks
- [ ] Video interview simulation
- [ ] Peer review sharing
- [ ] Mobile-responsive UI
- [ ] Offline mode with local LLM (Ollama)
- [ ] Multi-language support
- [ ] Integration with job boards (LinkedIn, Indeed)

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest tests/ -v`
5. Run lint: `ruff check . && black --check .`
6. Format code: `black . && ruff check . --fix`
7. Type check: `mypy .`
8. Submit a pull request

## Final Year Project Presentation Points

### Technical Highlights
1. **Multi-provider LLM Architecture** - Abstracted LLM service supporting Groq/Mistral with fallback
2. **RAG Pipeline** - Complete document processing, embedding, vector storage, and retrieval
3. **Structured Output** - Pydantic models for all LLM responses with validation
4. **Local Speech-to-Text** - Faster-Whisper integration (no paid APIs)
5. **Comprehensive Evaluation** - 5-dimensional answer scoring with actionable feedback
6. **Progress Tracking** - SQLite persistence with historical analytics

### AI/ML Concepts Demonstrated
- Generative AI with LLMs
- Retrieval-Augmented Generation (RAG)
- Vector embeddings and similarity search
- Prompt engineering with structured outputs
- Speech recognition (ASR)
- Multi-modal interaction (text + voice)

### Software Engineering Practices
- Modular, maintainable architecture
- Configuration management with environment variables
- Error handling with retry logic
- Database design with SQLAlchemy ORM
- Unit testing with mocking
- Code formatting (Black, Ruff)
- Git version control

## Viva Questions & Answers

**Q: Why did you choose Groq as the primary LLM provider?**
A: Groq offers free tier with high throughput (14,400 req/day), low latency via LPU inference, and OpenAI-compatible API making it easy to swap providers.

**Q: How does the RAG pipeline work?**
A: Documents → Load → Clean → Split (1000 chars, 200 overlap) → Embed (all-MiniLM-L6-v2) → Store in FAISS → Retrieve top-k → Inject into LLM context.

**Q: Why FAISS over ChromaDB?**
A: FAISS is lighter, faster for CPU, no separate server needed, and sufficient for local document retrieval use case.

**Q: How do you handle LLM rate limits?**
A: Tenacity retry with exponential backoff (1.5x), max 3 retries, configurable timeout, and provider fallback (Groq → Mistral).

**Q: How is answer evaluation structured?**
A: 5-dimension rubric (Technical Accuracy, Relevance, Communication, Confidence, Completeness) each 0-10, with qualitative feedback and suggested improvements.

**Q: How do you ensure data privacy?**
A: All processing local except LLM API calls. No data sent to third parties except LLM providers. API keys in `.env` (gitignored). SQLite local database.

**Q: What's the difference between behavioral and situational questions?**
A: Behavioral asks about past experiences (STAR method). Situational presents hypothetical scenarios relevant to the role.

**Q: How does the 7-day improvement plan work?**
A: LLM generates daily actionable items based on interview weaknesses, with specific activities, resources, and time estimates.

## Resume/CV Project Description

**AI Interview Assistant** | Final Year Project | Python, Streamlit, LLMs, RAG, FAISS, Whisper

- Built a full-stack AI-powered interview preparation platform using Groq/Mistral LLMs, local embeddings (Sentence Transformers), FAISS vector database, and Faster-Whisper for speech-to-text
- Implemented modular RAG pipeline: document loading (PDF/DOCX), text splitting, embedding generation, vector storage, and contextual retrieval
- Designed multi-provider LLM abstraction with automatic fallback, structured output validation (Pydantic), and retry logic with exponential backoff
- Developed 7-category personalized interview question generator with dynamic follow-up based on candidate responses
- Created comprehensive answer evaluation engine scoring 5 dimensions (0-10) with actionable feedback and suggested improvements
- Built interactive Streamlit dashboard with progress tracking, score analytics, and exportable interview reports
- Used SQLite/SQLAlchemy for persistence: user sessions, resume analyses, job matches, interview history, and evaluations
- Applied software engineering best practices: configuration management, error handling, unit testing (pytest), code formatting (Black/Ruff)

## GitHub Project Description

🤖 **AI Interview Assistant** - An intelligent interview preparation platform that helps students and job seekers practice for real interviews using Generative AI.

**Key Features:**
- 📄 Resume analysis with AI scoring
- 🎯 Job description matching & gap analysis  
- 🤖 Personalized interview questions (7 categories, 3 difficulties)
- 🎤 Mock interviews with text/voice input
- 📊 Detailed evaluation & improvement plans
- 📈 Progress tracking dashboard

**Tech Stack:** Python, Streamlit, Groq/Mistral LLMs, Sentence Transformers, FAISS, Faster-Whisper, SQLite, LangChain Core

**Free & Open Source:** Runs entirely on free APIs and local models - no paid services required.