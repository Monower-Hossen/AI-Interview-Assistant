from pathlib import Path
from ai_interview_assistant.components.speech_to_text import SpeechToText
from ai_interview_assistant.components.text_to_speech import TextToSpeech
from ai_interview_assistant.config.configuration import ConfigurationManager

class AudioHandler:
    """
    Unified component for handling voice interactions (STT and TTS).
    """
    def __init__(self, config_manager: ConfigurationManager):
        self.stt = SpeechToText(config_manager.get_stt_config())
        self.tts = TextToSpeech(config_manager.get_tts_config())

    def voice_to_text(self, audio_path: Path) -> str:
        """Transcribes candidate audio input."""
        return self.stt.transcribe(audio_path)

    def text_to_voice(self, text: str, output_path: Path, language: str = "bn"):
        """Generates AI interviewer speech."""
        self.tts.generate_speech(text, output_path, language=language)

    def record_session_clip(self):
        """
        Placeholder for real-time recording logic if moved from data_ingestion.
        """
        pass