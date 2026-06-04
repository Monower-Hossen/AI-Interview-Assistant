from pathlib import Path
from pypdf import PdfReader
from ai_interview_assistant import logger
from ai_interview_assistant.utils.common import extract_text_from_pdf

class DataIngestor:
    """
    Handles the ingestion and parsing of Candidate Resumes and Job Descriptions.
    """
    def __init__(self):
        pass

    def parse_resume(self, pdf_path: Path) -> str:
        try:
            text = extract_text_from_pdf(pdf_path)
            logger.info(f"Successfully parsed resume: {pdf_path.name}")
            return text
        except Exception as e:
            logger.error(f"Failed to parse resume {pdf_path}: {e}")
            raise e

    def parse_job_description(self, jd_text: str) -> dict:
        # Placeholder for extracting key skills/requirements from JD
        return {"raw_text": jd_text}