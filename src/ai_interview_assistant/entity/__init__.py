from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class LLMConfig:
    model_name: str
    temperature: float
    max_tokens: int
    prompt_template: str

@dataclass(frozen=True)
class STTConfig:
    model_name: str
    sample_rate: int

@dataclass(frozen=True)
class TTSConfig:
    language: str
    slow: bool

@dataclass(frozen=True)
class ArtifactsConfig:
    root_dir: Path
    audio_store: Path
    ffmpeg_path: str