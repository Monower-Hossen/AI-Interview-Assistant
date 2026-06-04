from ai_interview_assistant.config.configuration import ConfigurationManager
from ai_interview_assistant.components.speech_to_text import SpeechToText
from ai_interview_assistant.components.llm_handler import LLMHandler
from ai_interview_assistant.components.text_to_speech import TextToSpeech
from ai_interview_assistant.components.emotion_detector import EmotionDetector
from ai_interview_assistant.components.proctoring_engine import ProctoringEngine
from ai_interview_assistant import logger
import shutil
from ai_interview_assistant.components.question_bank import QuestionBank
import re
from ai_interview_assistant.utils.common import convert_to_wav, get_ffmpeg_executable
from pathlib import Path
import os
import uuid

class InterviewerPipeline:
    def __init__(self):
        self.config_manager = ConfigurationManager()
        self.artifacts_config = self.config_manager.get_artifacts_config()
        
        # Verify dependencies
        config_ffmpeg_path = self.artifacts_config.ffmpeg_path
        self.ffmpeg_path = get_ffmpeg_executable(config_ffmpeg_path)

        if not self.ffmpeg_path:
            logger.error("FFmpeg discovery failed. Checked system PATH, Registry, and common installation folders.")
            raise RuntimeError(
                f"FFmpeg not found (tried '{config_ffmpeg_path}' and discovery). "
                "Audio processing will fail. Please ensure FFmpeg is installed. "
                "Run 'python setup_env.py' to install it automatically, "
                "or provide the absolute path "
                "to ffmpeg.exe in 'config/config.yaml'."
            )

        logger.info(f"FFmpeg dependency verified at: {self.ffmpeg_path}")

        # Inject FFmpeg directory into system PATH if it's an absolute path
        # This helps external libraries like Whisper find FFmpeg
        if os.path.isabs(self.ffmpeg_path):
            ffmpeg_dir = os.path.dirname(self.ffmpeg_path)
            if ffmpeg_dir not in os.environ["PATH"]:
                os.environ["PATH"] += os.pathsep + ffmpeg_dir
                logger.info(f"Injected FFmpeg directory into system PATH: {ffmpeg_dir}")
        
        # Ensure audio store directory exists
        self.audio_store = Path(self.artifacts_config.audio_store)
        self.audio_store.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.stt = SpeechToText(config=self.config_manager.get_stt_config())
        self.llm = LLMHandler(config=self.config_manager.get_llm_config())
        self.tts = TextToSpeech(config=self.config_manager.get_tts_config())
        self.emotion_detector = EmotionDetector()
        self.proctoring_engine = ProctoringEngine()
        self.question_bank = QuestionBank(storage_dir=Path(self.artifacts_config.root_dir) / "roles")

    def start_interview(self, session_id: str = "default", job_role: str = "Software Engineer", resume_text: str = "", language: str = "bn"):
        """
        Initializes the interview with an AI greeting.
        """
        try:
            # Check for dynamic role config
            if not self.question_bank.exists(job_role):
                logger.info(f"Role '{job_role}' not found. Generating dynamic configuration...")
                # Default to 'Senior' for safety, or you could pass this dynamically
                new_config = self.llm.generate_role_config(job_role, experience_level="Senior")
                if "error" not in new_config:
                    self.question_bank.save_role_config(job_role, new_config)
            
            role_config = self.question_bank.get_role_config(job_role)
            
            ai_response_text = self.llm.generate_initial_question(
                session_id, job_role, resume_text, language=language, role_config=role_config
            )
            
            unique_id = str(uuid.uuid4())[:8]
            output_path = self.audio_store / f"ai_start_{unique_id}.mp3"
            self.tts.generate_speech(ai_response_text, output_path, language=language)

            return {
                "ai_response": ai_response_text,
                "audio_path": output_path
            }
        except Exception as e:
            logger.error(f"Failed to start interview: {e}")
            raise e

    def run_interview_step(self, input_audio_path: Path, session_id: str = "default", job_role: str = "Software Engineer", resume_text: str = "", language: str = "bn"):
        """
        Executes one full cycle of the interview: STT -> LLM -> TTS
        """
        try:
            # Pre-process audio to 16kHz WAV
            processed_audio_path = input_audio_path.with_name(f"proc_{input_audio_path.name}")
            convert_to_wav(input_audio_path, processed_audio_path, ffmpeg_path=self.ffmpeg_path)

            # 1. Speech to Text
            candidate_text = self.stt.transcribe(processed_audio_path)
            logger.info(f"Candidate said: {candidate_text}")
            
            # Handle silence or inaudible audio
            if not candidate_text:
                candidate_text = "[No speech detected]"
                logger.warning("No speech detected by STT component.")
            
            # Advanced Metric: Word Count (Fluency Indicator)
            word_count = len(candidate_text.split())

            # 1.1 Emotion Detection
            emotion = self.emotion_detector.analyze_sentiment(candidate_text)
            
            # 1.2 Proctoring Verification
            proctoring_results = self.proctoring_engine.check_integrity(candidate_text, processed_audio_path)

            # 2. LLM Processing
            ai_response_text = self.llm.get_response(candidate_text, session_id=session_id, job_role=job_role, resume_text=resume_text, language=language)
            logger.info(f"AI Interviewer Response: {ai_response_text}")
            
            # Advanced Metric: Confidence Extraction
            confidence = "N/A"
            confidence_match = re.search(r"\[CONFIDENCE:\s*(.*?)\]", ai_response_text)
            if confidence_match:
                confidence = confidence_match.group(1)
                ai_response_text = re.sub(r"\[CONFIDENCE:.*?\]", "", ai_response_text).strip()

            # 3. Text to Speech
            unique_id = str(uuid.uuid4())[:8]
            output_filename = f"ai_response_{unique_id}.mp3"
            output_path = self.audio_store / output_filename
            self.tts.generate_speech(ai_response_text, output_path, language=language)

            return {
                "candidate_text": candidate_text,
                "ai_response": ai_response_text,
                "audio_path": output_path,
                "metrics": {
                    "confidence": confidence,
                    "word_count": word_count,
                    "response_length": len(candidate_text),
                    "detected_emotion": emotion,
                    "proctoring": proctoring_results
                }
            }

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise e

    def get_performance_report(self, session_id: str):
        """
        Generates the final professional evaluation report.
        """
        logger.info(f"Generating final report for session: {session_id}")
        report = self.llm.generate_feedback(session_id)
        return report