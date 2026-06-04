from ai_interview_assistant import logger
from pathlib import Path

class ProctoringEngine:
    """
    Monitors for suspicious activity during the interview process.
    """
    def __init__(self):
        logger.info("Proctoring Engine initialized.")

    def check_integrity(self, transcription: str, audio_path: Path = None) -> dict:
        """
        Analyzes audio and text for signs of cheating or environmental issues.
        """
        integrity_status = {
            "is_suspicious": False,
            "alerts": []
        }
        
        # Simple heuristic: alert on extremely short responses that aren't silence
        if 0 < len(transcription.split()) < 2 and transcription != "[No speech detected]":
             integrity_status["alerts"].append("Abnormally short response detected.")
             
        return integrity_status