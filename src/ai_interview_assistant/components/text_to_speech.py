from gtts import gTTS
import os
from ai_interview_assistant.entity import TTSConfig
from ai_interview_assistant import logger
from pathlib import Path

class TextToSpeech:
    def __init__(self, config: TTSConfig):
        """
        Initializes the Text-to-Speech component using Google Text-to-Speech (gTTS).
        """
        self.config = config

    def generate_speech(self, text: str, output_path: Path, language: str = None):
        """
        Converts text to an audio file and saves it to the specified path.
        """
        lang = language if language else self.config.language
        try:
            logger.info(f"Converting text to speech. Language: {lang}")
            
            # Ensure the target directory exists before saving the audio file
            output_path.parent.mkdir(parents=True, exist_ok=True)

            tts = gTTS(text=text, lang=lang, slow=self.config.slow)
            tts.save(str(output_path))
            
            logger.info(f"Speech audio saved successfully at: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error occurred in Text-to-Speech component: {e}")
            raise e