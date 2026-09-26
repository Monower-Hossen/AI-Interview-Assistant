import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from config.settings import settings
from utils.file_utils import is_audio_file


@dataclass
class TranscriptionResult:
    text: str
    language: str
    duration: float
    segments: list


class SpeechToText:
    def __init__(self):
        self._model = None
        self._model_config = None

    def _load_model(self, model_size: str | None = None, device: str | None = None):
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise ImportError("faster-whisper not installed. Run: pip install faster-whisper")

        model_size = model_size or settings.whisper_model
        device = device or settings.whisper_device
        compute_type = "int8" if device == "cpu" else "float16"

        config_key = (model_size, device, compute_type)
        if self._model is not None and self._model_config == config_key:
            return

        self._model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            download_root=os.path.join(settings.vector_store_path, "whisper_models"),
        )
        self._model_config = config_key

    def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        model_size: str | None = None,
        device: str | None = None,
    ) -> TranscriptionResult:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        self._load_model(model_size, device)

        if not is_audio_file(audio_path):
            audio_path = self._convert_audio(audio_path)

        segments, info = self._model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )

        text_parts = []
        segment_list = []

        for segment in segments:
            text_parts.append(segment.text.strip())
            segment_list.append(
                {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                }
            )

        full_text = " ".join(text_parts).strip()

        return TranscriptionResult(
            text=full_text,
            language=info.language,
            duration=info.duration,
            segments=segment_list,
        )

    def _convert_audio(self, audio_path: str) -> str:
        try:
            from pydub import AudioSegment
        except ImportError:
            raise ImportError("pydub not installed. Run: pip install pydub")

        ext = Path(audio_path).suffix.lower()
        audio = AudioSegment.from_file(audio_path, format=ext[1:])

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            audio.export(tmp.name, format="wav")
            return tmp.name

    def transcribe_from_bytes(
        self,
        audio_bytes: bytes,
        format: str = "wav",
        model_size: str | None = None,
        device: str | None = None,
    ) -> TranscriptionResult:
        with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            result = self.transcribe(tmp_path, model_size=model_size, device=device)
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

        return result


_speech_to_text_instance = None


def get_speech_to_text() -> SpeechToText:
    global _speech_to_text_instance
    if _speech_to_text_instance is None:
        _speech_to_text_instance = SpeechToText()
    return _speech_to_text_instance


def reset_speech_to_text():
    global _speech_to_text_instance
    _speech_to_text_instance = None


def transcribe_audio(
    audio_path: str,
    language: str | None = None,
    model_size: str | None = None,
    device: str | None = None,
) -> TranscriptionResult:
    stt = get_speech_to_text()
    return stt.transcribe(audio_path, language, model_size, device)
