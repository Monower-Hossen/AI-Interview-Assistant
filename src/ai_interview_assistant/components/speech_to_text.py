import whisper
import os
from ai_interview_assistant.entity import STTConfig
from ai_interview_assistant import logger
from pathlib import Path

class SpeechToText:
    def __init__(self, config: STTConfig):
        """
        Initializes the Speech-to-Text component using OpenAI Whisper.
        """
        self.config = config
        try:
            logger.info(f"Loading Whisper model: {self.config.model_name}...")
            self.model = whisper.load_model(self.config.model_name)
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise e

    def transcribe(self, audio_file_path: Path) -> str:
        """
        Transcribes the provided audio file into text.
        """
        try:
            if not os.path.exists(audio_file_path):
                raise FileNotFoundError(f"Audio file not found at: {audio_file_path}")

            logger.info(f"Transcribing audio: {audio_file_path}")
            # Whisper handles internal audio resampling to 16k
            result = self.model.transcribe(str(audio_file_path))
            text = result.get("text", "").strip()
            
            logger.info("Transcription completed successfully.")
            return text
            
        except Exception as e:
            logger.error(f"Transcription Error: {e}")
            raise e