import os
from dataclasses import dataclass, field, fields
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# FAISS wheels may not include every CPU-specific wrapper. The generic wrapper
# is portable and avoids a harmless AVX2 import warning on Windows.
os.environ.setdefault("FAISS_OPT_LEVEL", "generic")


@dataclass
class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "auto")
    llm_model: str = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")
    groq_base_url: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemma-4-26b-a4b-it")
    gemini_base_url: str = os.getenv(
        "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai"
    )
    gemini_fallback_models: list[str] = field(
        default_factory=lambda: ["gemma-4-26b-a4b-it"]
    )

    mistral_api_key: str = os.getenv("MISTRAL_API_KEY", "")
    mistral_model: str = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
    mistral_base_url: str = os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1")
    mistral_fallback_models: list[str] = field(
        default_factory=lambda: ["mistral-large-latest"]
    )

    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    groq_fallback_models: list[str] = field(
        default_factory=lambda: ["openai/gpt-oss-20b", "allam-2-7b"]
    )

    provider_priority: str = os.getenv("PROVIDER_PRIORITY", "groq,gemini,mistral")

    max_resume_chars: int = int(os.getenv("MAX_RESUME_CHARS", "8000"))
    max_jd_chars: int = int(os.getenv("MAX_JD_CHARS", "6000"))
    max_rag_chunks: int = int(os.getenv("MAX_RAG_CHUNKS", "3"))
    max_questions_per_generation: int = int(os.getenv("MAX_QUESTIONS_PER_GENERATION", "5"))

    embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    embedding_device: str = os.getenv("EMBEDDING_DEVICE", "cpu")
    embedding_cache_dir: str = os.getenv("EMBEDDING_CACHE_DIR", "./data/embedding_cache")
    embedding_cache_enabled: bool = os.getenv("EMBEDDING_CACHE_ENABLED", "true").lower() == "true"

    whisper_model: str = os.getenv("WHISPER_MODEL", "base")
    whisper_device: str = os.getenv("WHISPER_DEVICE", "cpu")

    vector_store_type: str = os.getenv("VECTOR_STORE_TYPE", "faiss")
    vector_store_path: str = os.getenv("VECTOR_STORE_PATH", "./data/vector_store")

    database_path: str = os.getenv("DATABASE_PATH", "./data/interview_assistant.db")

    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    allowed_extensions: list[str] | None = None

    chunk_size: int = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    top_k_retrieval: int = int(os.getenv("TOP_K_RETRIEVAL", "5"))
    max_context_chars: int = int(os.getenv("MAX_CONTEXT_CHARS", "6000"))

    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "60"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    retry_backoff_factor: float = float(os.getenv("RETRY_BACKOFF_FACTOR", "1.5"))
    max_tokens: int = int(os.getenv("MAX_TOKENS", "1800"))

    streamlit_port: int = int(os.getenv("STREAMLIT_PORT", "8501"))
    streamlit_theme: str = os.getenv("STREAMLIT_THEME", "light")

    temp_dir: str = os.getenv("TEMP_DIR", "./data/temp")

    def __post_init__(self):
        if self.allowed_extensions is None:
            self.allowed_extensions = [
                ".pdf",
                ".docx",
                ".txt",
                ".wav",
                ".mp3",
                ".m4a",
                ".ogg",
                ".flac",
            ]

        Path(self.vector_store_path).mkdir(parents=True, exist_ok=True)
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        Path("./data").mkdir(parents=True, exist_ok=True)
        Path("./data/uploads").mkdir(parents=True, exist_ok=True)
        Path(self.embedding_cache_dir).mkdir(parents=True, exist_ok=True)
        Path(self.temp_dir).mkdir(parents=True, exist_ok=True)

    def as_dict(self) -> dict[str, object]:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls()


def reload_settings() -> Settings:
    """Re-read environment variables and return a fresh Settings instance."""
    global settings
    load_dotenv()
    settings = Settings()
    return settings


settings = Settings()
