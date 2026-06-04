import json
from pathlib import Path
from ai_interview_assistant import logger

class QuestionBank:
    """
    Manages and persists role-specific interview configurations and questions.
    """
    def __init__(self, storage_dir: Path):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_role_path(self, job_role: str) -> Path:
        # Sanitize filename
        safe_name = "".join([c if c.isalnum() else "_" for c in job_role.lower()])
        return self.storage_dir / f"{safe_name}.json"

    def exists(self, job_role: str) -> bool:
        return self._get_role_path(job_role).exists()

    def save_role_config(self, job_role: str, config: dict):
        try:
            path = self._get_role_path(job_role)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            logger.info(f"Saved configuration for role: {job_role}")
        except Exception as e:
            logger.error(f"Failed to save role config: {e}")

    def get_role_config(self, job_role: str) -> dict:
        path = self._get_role_path(job_role)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error reading role config for {job_role}: {e}")
        return {"topics": [], "sample_questions": []}